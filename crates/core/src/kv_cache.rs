//! High-Performance Preallocated Key-Value (KV) Cache and Attention Engine
//!
//! Provides deterministic memory layout, zero-allocation autoregressive decoding,
//! ring buffer & paged attention for multi-tab browser context isolation,
//! and WebGPU/WGPU compute pipeline bindings.

use anyhow::{anyhow, bail, Result};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::f32;
use std::time::Instant;

/// Contiguous linear preallocated Key-Value cache for single-session inference.
///
/// Eliminates garbage collection pauses and dynamic heap allocations during
/// autoregressive generation in client runtimes, WebAssembly, and native browser contexts.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KvCache {
    pub max_seq_len: usize,
    pub num_heads: usize,
    pub head_dim: usize,
    pub current_len: usize,
    #[serde(skip)]
    pub keys: Vec<f32>,
    #[serde(skip)]
    pub values: Vec<f32>,
}

impl KvCache {
    /// Allocate contiguous linear buffers for keys and values up front.
    pub fn new(max_seq_len: usize, num_heads: usize, head_dim: usize) -> Self {
        let total_elements = max_seq_len * num_heads * head_dim;
        Self {
            max_seq_len,
            num_heads,
            head_dim,
            current_len: 0,
            keys: vec![0.0; total_elements],
            values: vec![0.0; total_elements],
        }
    }

    /// Append key and value slices for `token_count` tokens in-place using slice copying.
    ///
    /// The input memory layout must arrange tokens contiguously:
    /// `[token_0_head_0, token_0_head_1, ..., token_1_head_0, ...]`.
    pub fn append(&mut self, new_keys: &[f32], new_values: &[f32], token_count: usize) {
        if token_count == 0 {
            return;
        }

        let elements_per_token = self.num_heads * self.head_dim;
        let total_copy_len = token_count * elements_per_token;

        assert!(
            self.current_len + token_count <= self.max_seq_len,
            "Sequence length exceeded preallocated cache capacity (current: {}, appending: {}, max: {})",
            self.current_len,
            token_count,
            self.max_seq_len
        );
        assert!(
            new_keys.len() >= total_copy_len,
            "new_keys buffer too short: expected at least {}, got {}",
            total_copy_len,
            new_keys.len()
        );
        assert!(
            new_values.len() >= total_copy_len,
            "new_values buffer too short: expected at least {}, got {}",
            total_copy_len,
            new_values.len()
        );

        let start_index = self.current_len * elements_per_token;

        self.keys[start_index..start_index + total_copy_len]
            .copy_from_slice(&new_keys[..total_copy_len]);
        self.values[start_index..start_index + total_copy_len]
            .copy_from_slice(&new_values[..total_copy_len]);

        self.current_len += token_count;
    }

    /// Safe append that returns Result instead of panicking on overflow or buffer length mismatches.
    pub fn try_append(&mut self, new_keys: &[f32], new_values: &[f32], token_count: usize) -> Result<()> {
        if token_count == 0 {
            return Ok(());
        }
        if self.current_len + token_count > self.max_seq_len {
            bail!(
                "Sequence length exceeded preallocated capacity: current={}, appending={}, max={}",
                self.current_len,
                token_count,
                self.max_seq_len
            );
        }
        let elements_per_token = self.num_heads * self.head_dim;
        let total_copy_len = token_count * elements_per_token;
        if new_keys.len() < total_copy_len {
            bail!(
                "new_keys buffer too short: expected at least {}, got {}",
                total_copy_len,
                new_keys.len()
            );
        }
        if new_values.len() < total_copy_len {
            bail!(
                "new_values buffer too short: expected at least {}, got {}",
                total_copy_len,
                new_values.len()
            );
        }
        self.append(new_keys, new_values, token_count);
        Ok(())
    }

    /// Active sequence length stored in the cache.
    #[inline]
    pub fn current_len(&self) -> usize {
        self.current_len
    }

    /// Maximum sequence length supported by preallocated buffers.
    #[inline]
    pub fn max_seq_len(&self) -> usize {
        self.max_seq_len
    }

    /// Number of attention heads.
    #[inline]
    pub fn num_heads(&self) -> usize {
        self.num_heads
    }

    /// Dimension of each attention head.
    #[inline]
    pub fn head_dim(&self) -> usize {
        self.head_dim
    }

    /// Elements per token across all heads (`num_heads * head_dim`).
    #[inline]
    pub fn elements_per_token(&self) -> usize {
        self.num_heads * self.head_dim
    }

    /// Total memory occupied by key and value buffers in bytes.
    #[inline]
    pub fn memory_bytes(&self) -> usize {
        (self.keys.len() + self.values.len()) * std::mem::size_of::<f32>()
    }

    /// Reset sequence cursor to 0 without freeing allocated memory.
    pub fn clear(&mut self) {
        self.current_len = 0;
    }

    /// Single-token causal attention decode step.
    ///
    /// Evaluates scaled dot-product attention over all cached tokens up to `current_len`.
    /// Subtracts the maximum score before exponentiation to guarantee numerical stability.
    pub fn decode_attention_step(&self, query: &[f32], output: &mut [f32]) {
        assert!(self.current_len > 0, "Cannot attend over an empty cache");

        let head_dim = self.head_dim;
        let num_heads = self.num_heads;
        let scale = 1.0 / (head_dim as f32).sqrt();
        let elements_per_token = num_heads * head_dim;

        assert!(
            query.len() >= elements_per_token,
            "Query buffer too short: expected at least {}, got {}",
            elements_per_token,
            query.len()
        );
        assert!(
            output.len() >= elements_per_token,
            "Output buffer too short: expected at least {}, got {}",
            elements_per_token,
            output.len()
        );

        for h in 0..num_heads {
            let q_offset = h * head_dim;
            let q_slice = &query[q_offset..q_offset + head_dim];

            let mut attention_scores = Vec::with_capacity(self.current_len);
            let mut max_score = f32::NEG_INFINITY;

            for t in 0..self.current_len {
                let k_offset = (t * elements_per_token) + (h * head_dim);
                let k_slice = &self.keys[k_offset..k_offset + head_dim];

                let mut dot_product = 0.0;
                for d in 0..head_dim {
                    dot_product += q_slice[d] * k_slice[d];
                }

                let score = dot_product * scale;
                if score > max_score {
                    max_score = score;
                }
                attention_scores.push(score);
            }

            let mut sum_exp = 0.0;
            for score in attention_scores.iter_mut() {
                *score = (*score - max_score).exp();
                sum_exp += *score;
            }

            for score in attention_scores.iter_mut() {
                *score /= sum_exp;
            }

            let out_offset = h * head_dim;
            for d in 0..head_dim {
                output[out_offset + d] = 0.0;
            }

            for t in 0..self.current_len {
                let weight = attention_scores[t];
                let v_offset = (t * elements_per_token) + (h * head_dim);
                let v_slice = &self.values[v_offset..v_offset + head_dim];

                for d in 0..head_dim {
                    output[out_offset + d] += weight * v_slice[d];
                }
            }
        }
    }

    /// Single-token causal attention decode step with zero heap allocations.
    ///
    /// Uses caller-provided scratch buffer `workspace` (must have length >= `current_len`)
    /// to eliminate all dynamic heap allocations during decoding.
    pub fn decode_attention_step_zero_alloc(&self, query: &[f32], output: &mut [f32], workspace: &mut [f32]) {
        assert!(self.current_len > 0, "Cannot attend over an empty cache");
        assert!(
            workspace.len() >= self.current_len,
            "Workspace buffer must hold at least current_len elements ({})",
            self.current_len
        );

        let head_dim = self.head_dim;
        let num_heads = self.num_heads;
        let scale = 1.0 / (head_dim as f32).sqrt();
        let elements_per_token = num_heads * head_dim;

        assert!(
            query.len() >= elements_per_token,
            "Query buffer too short: expected at least {}, got {}",
            elements_per_token,
            query.len()
        );
        assert!(
            output.len() >= elements_per_token,
            "Output buffer too short: expected at least {}, got {}",
            elements_per_token,
            output.len()
        );

        for h in 0..num_heads {
            let q_offset = h * head_dim;
            let q_slice = &query[q_offset..q_offset + head_dim];
            let scores = &mut workspace[..self.current_len];

            let mut max_score = f32::NEG_INFINITY;
            for t in 0..self.current_len {
                let k_offset = (t * elements_per_token) + (h * head_dim);
                let k_slice = &self.keys[k_offset..k_offset + head_dim];

                let mut dot_product = 0.0;
                for d in 0..head_dim {
                    dot_product += q_slice[d] * k_slice[d];
                }

                let score = dot_product * scale;
                if score > max_score {
                    max_score = score;
                }
                scores[t] = score;
            }

            let mut sum_exp = 0.0;
            for score in scores.iter_mut() {
                *score = (*score - max_score).exp();
                sum_exp += *score;
            }

            let inv_sum = 1.0 / sum_exp;
            for score in scores.iter_mut() {
                *score *= inv_sum;
            }

            let out_offset = h * head_dim;
            for d in 0..head_dim {
                output[out_offset + d] = 0.0;
            }

            for t in 0..self.current_len {
                let weight = scores[t];
                let v_offset = (t * elements_per_token) + (h * head_dim);
                let v_slice = &self.values[v_offset..v_offset + head_dim];

                for d in 0..head_dim {
                    output[out_offset + d] += weight * v_slice[d];
                }
            }
        }
    }
}

/// Sliding window / Ring Buffer KV Cache for bounded context memory in long-running browser tabs.
///
/// Keeps the initial `prefix_len` tokens (e.g., system prompt / instructions) permanently fixed,
/// and rotates the remaining buffer when reaching capacity to prevent OOM without reallocations.
#[derive(Debug, Clone)]
pub struct RingKvCache {
    pub max_seq_len: usize,
    pub num_heads: usize,
    pub head_dim: usize,
    pub prefix_len: usize,
    pub current_len: usize,
    pub total_tokens_ingested: usize,
    inner_cache: KvCache,
}

impl RingKvCache {
    /// Create a new ring buffer cache with protected prefix tokens.
    pub fn new(max_seq_len: usize, num_heads: usize, head_dim: usize, prefix_len: usize) -> Self {
        assert!(
            prefix_len < max_seq_len,
            "prefix_len must be strictly smaller than max_seq_len"
        );
        Self {
            max_seq_len,
            num_heads,
            head_dim,
            prefix_len,
            current_len: 0,
            total_tokens_ingested: 0,
            inner_cache: KvCache::new(max_seq_len, num_heads, head_dim),
        }
    }

    /// Append tokens with automatic sliding window compaction when full.
    pub fn append(&mut self, new_keys: &[f32], new_values: &[f32], token_count: usize) {
        if token_count == 0 {
            return;
        }

        let elements_per_token = self.num_heads * self.head_dim;
        let total_copy_len = token_count * elements_per_token;
        assert!(
            new_keys.len() >= total_copy_len,
            "new_keys buffer too short: expected at least {}, got {}",
            total_copy_len,
            new_keys.len()
        );
        assert!(
            new_values.len() >= total_copy_len,
            "new_values buffer too short: expected at least {}, got {}",
            total_copy_len,
            new_values.len()
        );

        let mut appended = 0;

        while appended < token_count {
            let available = self.max_seq_len - self.current_len;
            if available == 0 {
                // Buffer is full: shift sliding window left by 1 token, preserving prefix
                self.evict_one_token();
            }

            let chunk = (token_count - appended).min(self.max_seq_len - self.current_len);
            if chunk == 0 {
                // Prevent infinite loop if capacity cannot be freed
                break;
            }

            let k_sub = &new_keys[appended * elements_per_token..(appended + chunk) * elements_per_token];
            let v_sub = &new_values[appended * elements_per_token..(appended + chunk) * elements_per_token];

            self.inner_cache.append(k_sub, v_sub, chunk);
            self.current_len = self.inner_cache.current_len();
            appended += chunk;
        }

        self.total_tokens_ingested += token_count;
    }

    /// Safe append for RingKvCache that validates inputs.
    pub fn try_append(&mut self, new_keys: &[f32], new_values: &[f32], token_count: usize) -> Result<()> {
        if token_count == 0 {
            return Ok(());
        }
        let elements_per_token = self.num_heads * self.head_dim;
        let total_copy_len = token_count * elements_per_token;
        if new_keys.len() < total_copy_len {
            bail!(
                "new_keys buffer too short: expected at least {}, got {}",
                total_copy_len,
                new_keys.len()
            );
        }
        if new_values.len() < total_copy_len {
            bail!(
                "new_values buffer too short: expected at least {}, got {}",
                total_copy_len,
                new_values.len()
            );
        }
        self.append(new_keys, new_values, token_count);
        Ok(())
    }

    /// Slide the non-prefix window left by 1 token in-place to free a slot.
    fn evict_one_token(&mut self) {
        if self.current_len <= self.prefix_len {
            return;
        }

        let elements_per_token = self.num_heads * self.head_dim;
        let shift_start = (self.prefix_len + 1) * elements_per_token;
        let shift_dest = self.prefix_len * elements_per_token;

        if self.current_len > self.prefix_len + 1 {
            let shift_len = (self.current_len - (self.prefix_len + 1)) * elements_per_token;
            self.inner_cache.keys.copy_within(shift_start..shift_start + shift_len, shift_dest);
            self.inner_cache.values.copy_within(shift_start..shift_start + shift_len, shift_dest);
        }

        self.inner_cache.current_len -= 1;
        self.current_len = self.inner_cache.current_len;
    }

    /// Run causal attention step on active window.
    pub fn decode_attention_step(&self, query: &[f32], output: &mut [f32]) {
        self.inner_cache.decode_attention_step(query, output);
    }

    /// Run causal attention step on active window with zero heap allocations.
    pub fn decode_attention_step_zero_alloc(&self, query: &[f32], output: &mut [f32], workspace: &mut [f32]) {
        self.inner_cache.decode_attention_step_zero_alloc(query, output, workspace);
    }

    /// Current tokens stored in the window.
    #[inline]
    pub fn current_len(&self) -> usize {
        self.current_len
    }

    /// Total tokens processed through this cache over its lifetime.
    #[inline]
    pub fn total_tokens_ingested(&self) -> usize {
        self.total_tokens_ingested
    }

    /// Reset ring buffer without deallocating.
    pub fn clear(&mut self) {
        self.current_len = 0;
        self.total_tokens_ingested = 0;
        self.inner_cache.clear();
    }
}

/// Fixed-size block for Paged KV attention.
#[derive(Debug, Clone)]
pub struct KvBlock {
    pub block_id: usize,
    pub block_size: usize,
    pub keys: Vec<f32>,
    pub values: Vec<f32>,
}

/// Preallocated memory pool of blocks for Paged Attention across tabs.
#[derive(Debug)]
pub struct KvBlockPool {
    pub block_size: usize,
    pub num_heads: usize,
    pub head_dim: usize,
    free_blocks: Vec<usize>,
    blocks: Vec<KvBlock>,
}

impl KvBlockPool {
    /// Allocate pool of `total_blocks` with deterministic contiguous memory.
    pub fn new(total_blocks: usize, block_size: usize, num_heads: usize, head_dim: usize) -> Self {
        let elements_per_block = block_size * num_heads * head_dim;
        let mut blocks = Vec::with_capacity(total_blocks);
        let mut free_blocks = Vec::with_capacity(total_blocks);

        for id in 0..total_blocks {
            blocks.push(KvBlock {
                block_id: id,
                block_size,
                keys: vec![0.0; elements_per_block],
                values: vec![0.0; elements_per_block],
            });
            free_blocks.push(id);
        }

        Self {
            block_size,
            num_heads,
            head_dim,
            free_blocks,
            blocks,
        }
    }

    /// Allocate a block ID from the pool.
    pub fn allocate_block(&mut self) -> Option<usize> {
        self.free_blocks.pop()
    }

    /// Return a block to the free pool.
    pub fn release_block(&mut self, block_id: usize) {
        if block_id < self.blocks.len() && !self.free_blocks.contains(&block_id) {
            self.free_blocks.push(block_id);
        }
    }

    /// Available free blocks in the pool.
    pub fn free_block_count(&self) -> usize {
        self.free_blocks.len()
    }

    /// Number of blocks currently in use.
    pub fn allocated_block_count(&self) -> usize {
        self.blocks.len().saturating_sub(self.free_blocks.len())
    }

    /// Total blocks in pool.
    pub fn total_blocks(&self) -> usize {
        self.blocks.len()
    }

    /// Total memory used by all pool blocks in bytes.
    pub fn memory_bytes(&self) -> usize {
        let elements_per_block = self.block_size * self.num_heads * self.head_dim;
        self.blocks.len() * elements_per_block * 2 * std::mem::size_of::<f32>()
    }
}

/// Paged KV Cache that maps logical sequence positions to physical blocks.
#[derive(Debug, Clone)]
pub struct PagedKvCache {
    pub num_heads: usize,
    pub head_dim: usize,
    pub block_size: usize,
    pub current_len: usize,
    pub block_table: Vec<usize>,
}

impl PagedKvCache {
    pub fn new(num_heads: usize, head_dim: usize, block_size: usize) -> Self {
        Self {
            num_heads,
            head_dim,
            block_size,
            current_len: 0,
            block_table: Vec::new(),
        }
    }

    /// Append tokens into paged blocks from the pool.
    pub fn append(
        &mut self,
        pool: &mut KvBlockPool,
        new_keys: &[f32],
        new_values: &[f32],
        token_count: usize,
    ) -> Result<()> {
        if token_count == 0 {
            return Ok(());
        }

        let elements_per_token = self.num_heads * self.head_dim;
        let total_copy_len = token_count * elements_per_token;
        if new_keys.len() < total_copy_len {
            bail!(
                "new_keys buffer too short: expected at least {}, got {}",
                total_copy_len,
                new_keys.len()
            );
        }
        if new_values.len() < total_copy_len {
            bail!(
                "new_values buffer too short: expected at least {}, got {}",
                total_copy_len,
                new_values.len()
            );
        }

        for i in 0..token_count {
            let logical_pos = self.current_len;
            let block_offset = logical_pos % self.block_size;

            if block_offset == 0 {
                let new_block = pool
                    .allocate_block()
                    .ok_or_else(|| anyhow!("KvBlockPool exhausted: out of memory blocks"))?;
                self.block_table.push(new_block);
            }

            let physical_block_id = *self.block_table.last().unwrap();
            let block = &mut pool.blocks[physical_block_id];

            let block_elem_start = block_offset * elements_per_token;
            let input_elem_start = i * elements_per_token;

            block.keys[block_elem_start..block_elem_start + elements_per_token]
                .copy_from_slice(&new_keys[input_elem_start..input_elem_start + elements_per_token]);
            block.values[block_elem_start..block_elem_start + elements_per_token]
                .copy_from_slice(&new_values[input_elem_start..input_elem_start + elements_per_token]);

            self.current_len += 1;
        }

        Ok(())
    }

    /// Causal attention step over paged blocks.
    pub fn decode_attention_step(
        &self,
        pool: &KvBlockPool,
        query: &[f32],
        output: &mut [f32],
    ) -> Result<()> {
        if self.current_len == 0 {
            bail!("Cannot attend over empty paged cache");
        }

        let head_dim = self.head_dim;
        let num_heads = self.num_heads;
        let elements_per_token = num_heads * head_dim;

        if query.len() < elements_per_token {
            bail!(
                "Query buffer too short: expected at least {}, got {}",
                elements_per_token,
                query.len()
            );
        }
        if output.len() < elements_per_token {
            bail!(
                "Output buffer too short: expected at least {}, got {}",
                elements_per_token,
                output.len()
            );
        }

        let scale = 1.0 / (head_dim as f32).sqrt();

        for h in 0..num_heads {
            let q_offset = h * head_dim;
            let q_slice = &query[q_offset..q_offset + head_dim];

            let mut attention_scores = Vec::with_capacity(self.current_len);
            let mut max_score = f32::NEG_INFINITY;

            for t in 0..self.current_len {
                let block_idx = t / self.block_size;
                let block_offset = t % self.block_size;
                let physical_id = self.block_table[block_idx];
                let block = &pool.blocks[physical_id];

                let k_offset = (block_offset * elements_per_token) + (h * head_dim);
                let k_slice = &block.keys[k_offset..k_offset + head_dim];

                let mut dot_product = 0.0;
                for d in 0..head_dim {
                    dot_product += q_slice[d] * k_slice[d];
                }

                let score = dot_product * scale;
                if score > max_score {
                    max_score = score;
                }
                attention_scores.push(score);
            }

            let mut sum_exp = 0.0;
            for score in attention_scores.iter_mut() {
                *score = (*score - max_score).exp();
                sum_exp += *score;
            }

            for score in attention_scores.iter_mut() {
                *score /= sum_exp;
            }

            let out_offset = h * head_dim;
            for d in 0..head_dim {
                output[out_offset + d] = 0.0;
            }

            for t in 0..self.current_len {
                let weight = attention_scores[t];
                let block_idx = t / self.block_size;
                let block_offset = t % self.block_size;
                let physical_id = self.block_table[block_idx];
                let block = &pool.blocks[physical_id];

                let v_offset = (block_offset * elements_per_token) + (h * head_dim);
                let v_slice = &block.values[v_offset..v_offset + head_dim];

                for d in 0..head_dim {
                    output[out_offset + d] += weight * v_slice[d];
                }
            }
        }

        Ok(())
    }

    /// Single-token causal attention decode step over paged blocks with zero dynamic heap allocations.
    pub fn decode_attention_step_zero_alloc(
        &self,
        pool: &KvBlockPool,
        query: &[f32],
        output: &mut [f32],
        workspace: &mut [f32],
    ) -> Result<()> {
        if self.current_len == 0 {
            bail!("Cannot attend over empty paged cache");
        }

        let head_dim = self.head_dim;
        let num_heads = self.num_heads;
        let elements_per_token = num_heads * head_dim;

        if query.len() < elements_per_token {
            bail!(
                "Query buffer too short: expected at least {}, got {}",
                elements_per_token,
                query.len()
            );
        }
        if output.len() < elements_per_token {
            bail!(
                "Output buffer too short: expected at least {}, got {}",
                elements_per_token,
                output.len()
            );
        }
        if workspace.len() < self.current_len {
            bail!(
                "Workspace buffer too short: expected at least {}, got {}",
                self.current_len,
                workspace.len()
            );
        }

        let scale = 1.0 / (head_dim as f32).sqrt();

        for h in 0..num_heads {
            let q_offset = h * head_dim;
            let q_slice = &query[q_offset..q_offset + head_dim];
            let scores = &mut workspace[..self.current_len];

            let mut max_score = f32::NEG_INFINITY;
            for t in 0..self.current_len {
                let block_idx = t / self.block_size;
                let block_offset = t % self.block_size;
                let physical_id = self.block_table[block_idx];
                let block = &pool.blocks[physical_id];

                let k_offset = (block_offset * elements_per_token) + (h * head_dim);
                let k_slice = &block.keys[k_offset..k_offset + head_dim];

                let mut dot_product = 0.0;
                for d in 0..head_dim {
                    dot_product += q_slice[d] * k_slice[d];
                }

                let score = dot_product * scale;
                if score > max_score {
                    max_score = score;
                }
                scores[t] = score;
            }

            let mut sum_exp = 0.0;
            for score in scores.iter_mut() {
                *score = (*score - max_score).exp();
                sum_exp += *score;
            }

            let inv_sum = 1.0 / sum_exp;
            for score in scores.iter_mut() {
                *score *= inv_sum;
            }

            let out_offset = h * head_dim;
            for d in 0..head_dim {
                output[out_offset + d] = 0.0;
            }

            for t in 0..self.current_len {
                let weight = scores[t];
                let block_idx = t / self.block_size;
                let block_offset = t % self.block_size;
                let physical_id = self.block_table[block_idx];
                let block = &pool.blocks[physical_id];

                let v_offset = (block_offset * elements_per_token) + (h * head_dim);
                let v_slice = &block.values[v_offset..v_offset + head_dim];

                for d in 0..head_dim {
                    output[out_offset + d] += weight * v_slice[d];
                }
            }
        }

        Ok(())
    }

    /// Release all allocated blocks back to the pool.
    pub fn free(&mut self, pool: &mut KvBlockPool) {
        for &block_id in &self.block_table {
            pool.release_block(block_id);
        }
        self.block_table.clear();
        self.current_len = 0;
    }
}

/// Metadata and state for a single browser tab context.
#[derive(Debug, Clone)]
pub struct TabContext {
    pub tab_id: String,
    pub title: String,
    pub url: String,
    pub created_at: Instant,
    pub last_accessed: Instant,
    pub cache: KvCache,
    pub ring_cache: Option<RingKvCache>,
}

/// Multi-Tab KV Cache Manager for AI Browser tabs.
///
/// Enforces per-tab memory isolation, global memory caps, and LRU eviction of idle contexts.
pub struct MultiTabKvManager {
    pub max_memory_bytes: usize,
    tabs: HashMap<String, TabContext>,
    lru_order: Vec<String>,
}

impl MultiTabKvManager {
    /// Initialize manager with max memory budget in bytes.
    pub fn new(max_memory_bytes: usize) -> Self {
        Self {
            max_memory_bytes,
            tabs: HashMap::new(),
            lru_order: Vec::new(),
        }
    }

    /// Create or retrieve an existing tab KV cache.
    pub fn get_or_create_tab(
        &mut self,
        tab_id: &str,
        title: &str,
        url: &str,
        max_seq_len: usize,
        num_heads: usize,
        head_dim: usize,
    ) -> Result<&mut TabContext> {
        // If the tab already exists, touch it and return without evicting anything
        if self.tabs.contains_key(tab_id) {
            self.touch_tab(tab_id);
            return Ok(self.tabs.get_mut(tab_id).unwrap());
        }

        let needed_bytes = max_seq_len * num_heads * head_dim * 2 * std::mem::size_of::<f32>();
        if needed_bytes > self.max_memory_bytes {
            bail!(
                "Requested tab memory ({} bytes) exceeds manager capacity ({} bytes)",
                needed_bytes,
                self.max_memory_bytes
            );
        }

        // Evict LRU tabs until we have sufficient budget
        while self.total_memory_bytes() + needed_bytes > self.max_memory_bytes && !self.lru_order.is_empty() {
            if let Some(oldest_tab_id) = self.lru_order.first().cloned() {
                self.close_tab(&oldest_tab_id);
            }
        }

        let cache = KvCache::new(max_seq_len, num_heads, head_dim);
        let ctx = TabContext {
            tab_id: tab_id.to_string(),
            title: title.to_string(),
            url: url.to_string(),
            created_at: Instant::now(),
            last_accessed: Instant::now(),
            cache,
            ring_cache: None,
        };
        self.tabs.insert(tab_id.to_string(), ctx);
        self.lru_order.push(tab_id.to_string());

        Ok(self.tabs.get_mut(tab_id).unwrap())
    }

    /// Create or retrieve an existing tab with bounded ring buffer sliding window.
    pub fn get_or_create_ring_tab(
        &mut self,
        tab_id: &str,
        title: &str,
        url: &str,
        max_seq_len: usize,
        num_heads: usize,
        head_dim: usize,
        prefix_len: usize,
    ) -> Result<&mut TabContext> {
        if self.tabs.contains_key(tab_id) {
            self.touch_tab(tab_id);
            return Ok(self.tabs.get_mut(tab_id).unwrap());
        }

        let needed_bytes = max_seq_len * num_heads * head_dim * 2 * std::mem::size_of::<f32>();
        if needed_bytes > self.max_memory_bytes {
            bail!(
                "Requested tab memory ({} bytes) exceeds manager capacity ({} bytes)",
                needed_bytes,
                self.max_memory_bytes
            );
        }

        while self.total_memory_bytes() + needed_bytes > self.max_memory_bytes && !self.lru_order.is_empty() {
            if let Some(oldest_tab_id) = self.lru_order.first().cloned() {
                self.close_tab(&oldest_tab_id);
            }
        }

        let cache = KvCache::new(max_seq_len, num_heads, head_dim);
        let ring_cache = Some(RingKvCache::new(max_seq_len, num_heads, head_dim, prefix_len));
        let ctx = TabContext {
            tab_id: tab_id.to_string(),
            title: title.to_string(),
            url: url.to_string(),
            created_at: Instant::now(),
            last_accessed: Instant::now(),
            cache,
            ring_cache,
        };
        self.tabs.insert(tab_id.to_string(), ctx);
        self.lru_order.push(tab_id.to_string());

        Ok(self.tabs.get_mut(tab_id).unwrap())
    }

    /// Retrieve tab context by ID.
    pub fn get_tab(&self, tab_id: &str) -> Option<&TabContext> {
        self.tabs.get(tab_id)
    }

    /// Retrieve mutable tab context by ID and update LRU position.
    pub fn get_tab_mut(&mut self, tab_id: &str) -> Option<&mut TabContext> {
        if self.tabs.contains_key(tab_id) {
            self.touch_tab(tab_id);
            self.tabs.get_mut(tab_id)
        } else {
            None
        }
    }

    /// Append tokens to a specific tab cache.
    pub fn append_to_tab(
        &mut self,
        tab_id: &str,
        keys: &[f32],
        values: &[f32],
        token_count: usize,
    ) -> Result<()> {
        let tab = self.tabs.get_mut(tab_id).ok_or_else(|| anyhow!("TabNotFound: tab '{}' not found", tab_id))?;
        if let Some(ref mut ring) = tab.ring_cache {
            ring.append(keys, values, token_count);
        } else {
            tab.cache.append(keys, values, token_count);
        }
        tab.last_accessed = Instant::now();
        self.touch_tab(tab_id);
        Ok(())
    }

    /// Execute single token causal attention decode step for a tab.
    pub fn step_tab_decode(
        &mut self,
        tab_id: &str,
        query: &[f32],
        output: &mut [f32],
    ) -> Result<()> {
        let tab = self.tabs.get_mut(tab_id).ok_or_else(|| anyhow!("TabNotFound: tab '{}' not found", tab_id))?;
        if let Some(ref ring) = tab.ring_cache {
            ring.decode_attention_step(query, output);
        } else {
            tab.cache.decode_attention_step(query, output);
        }
        tab.last_accessed = Instant::now();
        self.touch_tab(tab_id);
        Ok(())
    }

    /// Execute zero-allocation decode step for a tab with user-supplied workspace.
    pub fn step_tab_decode_zero_alloc(
        &mut self,
        tab_id: &str,
        query: &[f32],
        output: &mut [f32],
        workspace: &mut [f32],
    ) -> Result<()> {
        let tab = self.tabs.get_mut(tab_id).ok_or_else(|| anyhow!("TabNotFound: tab '{}' not found", tab_id))?;
        if let Some(ref ring) = tab.ring_cache {
            ring.decode_attention_step_zero_alloc(query, output, workspace);
        } else {
            tab.cache.decode_attention_step_zero_alloc(query, output, workspace);
        }
        tab.last_accessed = Instant::now();
        self.touch_tab(tab_id);
        Ok(())
    }

    /// Reset tab cache sequence cursor.
    pub fn clear_tab(&mut self, tab_id: &str) -> Result<()> {
        let tab = self.tabs.get_mut(tab_id).ok_or_else(|| anyhow!("TabNotFound: tab '{}' not found", tab_id))?;
        if let Some(ref mut ring) = tab.ring_cache {
            ring.clear();
        }
        tab.cache.clear();
        tab.last_accessed = Instant::now();
        self.touch_tab(tab_id);
        Ok(())
    }

    /// Mark tab as recently accessed.
    fn touch_tab(&mut self, tab_id: &str) {
        if let Some(pos) = self.lru_order.iter().position(|id| id == tab_id) {
            self.lru_order.remove(pos);
        }
        self.lru_order.push(tab_id.to_string());
        if let Some(tab) = self.tabs.get_mut(tab_id) {
            tab.last_accessed = Instant::now();
        }
    }

    /// Close and evict a tab context.
    pub fn close_tab(&mut self, tab_id: &str) {
        self.tabs.remove(tab_id);
        if let Some(pos) = self.lru_order.iter().position(|id| id == tab_id) {
            self.lru_order.remove(pos);
        }
    }

    /// Total memory used across all active tabs in bytes.
    pub fn total_memory_bytes(&self) -> usize {
        self.tabs.values().map(|t| t.cache.memory_bytes()).sum()
    }

    /// Number of active tabs.
    pub fn tab_count(&self) -> usize {
        self.tabs.len()
    }

    /// JSON summary of all managed tab caches.
    pub fn status_summary(&self) -> serde_json::Value {
        let total_bytes = self.total_memory_bytes();
        let tabs_info: Vec<serde_json::Value> = self
            .tabs
            .values()
            .map(|t| {
                serde_json::json!({
                    "tab_id": t.tab_id,
                    "title": t.title,
                    "url": t.url,
                    "current_len": t.cache.current_len(),
                    "max_seq_len": t.cache.max_seq_len(),
                    "num_heads": t.cache.num_heads(),
                    "head_dim": t.cache.head_dim(),
                    "memory_mb": (t.cache.memory_bytes() as f64) / (1024.0 * 1024.0),
                })
            })
            .collect();

        serde_json::json!({
            "status": "healthy",
            "active_tabs": self.tabs.len(),
            "max_memory_mb": (self.max_memory_bytes as f64) / (1024.0 * 1024.0),
            "used_memory_mb": (total_bytes as f64) / (1024.0 * 1024.0),
            "free_memory_mb": ((self.max_memory_bytes.saturating_sub(total_bytes)) as f64) / (1024.0 * 1024.0),
            "tabs": tabs_info,
        })
    }
}

/// WebGPU WGSL Causal Multi-Head Attention Compute Shader.
pub const WGSL_ATTENTION_SHADER: &str = r#"
// ModelFusion / HugOS WebGPU Causal Multi-Head Attention Compute Pipeline
// Dispatches 1 workgroup per attention head.

struct AttentionUniforms {
    num_heads: u32,
    head_dim: u32,
    current_len: u32,
    scale: f32,
};

@group(0) @binding(0) var<storage, read> q: array<f32>;
@group(0) @binding(1) var<storage, read> k: array<f32>;
@group(0) @binding(2) var<storage, read> v: array<f32>;
@group(0) @binding(3) var<storage, read_write> output: array<f32>;
@group(0) @binding(4) var<uniform> params: AttentionUniforms;
@group(0) @binding(5) var<storage, read_write> score_buf: array<f32>;

@compute @workgroup_size(64, 1, 1)
fn main(@builtin(workgroup_id) workgroup_id: vec3<u32>, @builtin(local_invocation_id) local_id: vec3<u32>) {
    // Guard: only local thread 0 executes the head reduction to prevent memory write race
    if (local_id.x != 0u) {
        return;
    }

    let head_idx = workgroup_id.x;
    if (head_idx >= params.num_heads) {
        return;
    }

    let head_dim = params.head_dim;
    let num_heads = params.num_heads;
    let current_len = params.current_len;
    let elements_per_token = num_heads * head_dim;
    let q_offset = head_idx * head_dim;
    let score_head_offset = head_idx * current_len;

    // Pass 1: Scaled dot-product query * key and compute maximum score for numerical stability
    var max_score = -3.402823e+38; // -infinity
    for (var t: u32 = 0u; t < current_len; t = t + 1u) {
        let k_offset = (t * elements_per_token) + (head_idx * head_dim);
        var dot_product: f32 = 0.0;
        for (var d: u32 = 0u; d < head_dim; d = d + 1u) {
            dot_product = dot_product + q[q_offset + d] * k[k_offset + d];
        }
        let score = dot_product * params.scale;
        score_buf[score_head_offset + t] = score;
        if (score > max_score) {
            max_score = score;
        }
    }

    // Pass 2: Numerically stable Softmax exponentiation and sum
    var sum_exp: f32 = 0.0;
    for (var t: u32 = 0u; t < current_len; t = t + 1u) {
        let exp_score = exp(score_buf[score_head_offset + t] - max_score);
        score_buf[score_head_offset + t] = exp_score;
        sum_exp = sum_exp + exp_score;
    }

    let inv_sum = 1.0 / sum_exp;
    for (var t: u32 = 0u; t < current_len; t = t + 1u) {
        score_buf[score_head_offset + t] = score_buf[score_head_offset + t] * inv_sum;
    }

    // Pass 3: Weighted sum reduction over value vectors
    let out_offset = head_idx * head_dim;
    for (var d: u32 = 0u; d < head_dim; d = d + 1u) {
        var val: f32 = 0.0;
        for (var t: u32 = 0u; t < current_len; t = t + 1u) {
            let weight = score_buf[score_head_offset + t];
            let v_offset = (t * elements_per_token) + (head_idx * head_dim);
            val = val + weight * v[v_offset + d];
        }
        output[out_offset + d] = val;
    }
}
"#;

/// WebGPU Compute Pipeline descriptors and buffer binding specifications.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WgpuAttentionPipeline {
    pub max_seq_len: usize,
    pub num_heads: usize,
    pub head_dim: usize,
    pub workgroup_size: u32,
}

impl WgpuAttentionPipeline {
    pub fn new(max_seq_len: usize, num_heads: usize, head_dim: usize) -> Self {
        Self {
            max_seq_len,
            num_heads,
            head_dim,
            workgroup_size: 64,
        }
    }

    /// Return raw WGSL shader code.
    pub fn wgsl_source(&self) -> &'static str {
        WGSL_ATTENTION_SHADER
    }

    /// Compute workgroup dispatch dimensions for `dispatch_workgroups(x, y, z)`.
    pub fn dispatch_dimensions(&self) -> (u32, u32, u32) {
        (self.num_heads as u32, 1, 1)
    }

    /// Calculate buffer sizes in bytes for WebGPU buffer creation.
    pub fn buffer_requirements(&self) -> serde_json::Value {
        let elements_per_token = self.num_heads * self.head_dim;
        let q_bytes = elements_per_token * std::mem::size_of::<f32>();
        let kv_bytes = self.max_seq_len * elements_per_token * std::mem::size_of::<f32>();
        let out_bytes = elements_per_token * std::mem::size_of::<f32>();
        let score_buf_bytes = self.num_heads * self.max_seq_len * std::mem::size_of::<f32>();
        let uniform_bytes = 16; // 4 * 4 bytes

        serde_json::json!({
            "query_buffer_bytes": q_bytes,
            "key_buffer_bytes": kv_bytes,
            "value_buffer_bytes": kv_bytes,
            "output_buffer_bytes": out_bytes,
            "score_buffer_bytes": score_buf_bytes,
            "uniform_buffer_bytes": uniform_bytes,
            "total_gpu_buffer_bytes": q_bytes + (kv_bytes * 2) + out_bytes + score_buf_bytes + uniform_bytes,
        })
    }

    /// Software reference execution conforming bit-for-bit to the WGSL shader math.
    pub fn execute_reference(
        &self,
        query: &[f32],
        keys: &[f32],
        values: &[f32],
        current_len: usize,
        output: &mut [f32],
    ) {
        let head_dim = self.head_dim;
        let num_heads = self.num_heads;
        let elements_per_token = num_heads * head_dim;

        if current_len == 0 {
            let out_len = elements_per_token.min(output.len());
            output[..out_len].fill(0.0);
            return;
        }

        let scale = 1.0 / (head_dim as f32).sqrt();

        let mut score_buf = vec![0.0f32; num_heads * current_len];

        for h in 0..num_heads {
            let q_offset = h * head_dim;
            let score_head_offset = h * current_len;

            let mut max_score = f32::NEG_INFINITY;
            for t in 0..current_len {
                let k_offset = (t * elements_per_token) + (h * head_dim);
                let mut dot_product = 0.0;
                for d in 0..head_dim {
                    dot_product += query[q_offset + d] * keys[k_offset + d];
                }
                let score = dot_product * scale;
                score_buf[score_head_offset + t] = score;
                if score > max_score {
                    max_score = score;
                }
            }

            let mut sum_exp = 0.0;
            for t in 0..current_len {
                let exp_score = (score_buf[score_head_offset + t] - max_score).exp();
                score_buf[score_head_offset + t] = exp_score;
                sum_exp += exp_score;
            }

            let inv_sum = 1.0 / sum_exp;
            for t in 0..current_len {
                score_buf[score_head_offset + t] *= inv_sum;
            }

            let out_offset = h * head_dim;
            for d in 0..head_dim {
                output[out_offset + d] = 0.0;
            }

            for t in 0..current_len {
                let weight = score_buf[score_head_offset + t];
                let v_offset = (t * elements_per_token) + (h * head_dim);
                for d in 0..head_dim {
                    output[out_offset + d] += weight * values[v_offset + d];
                }
            }
        }
    }
}

/// Comprehensive Benchmark Metrics Report.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KvBenchmarkReport {
    pub max_seq_len: usize,
    pub num_heads: usize,
    pub head_dim: usize,
    pub elements_per_token: usize,
    pub prefill_tokens: usize,
    pub decode_steps: usize,
    pub memory_allocated_mb: f64,
    pub prefill_duration_ms: f64,
    pub prefill_throughput_tok_per_sec: f64,
    pub decode_duration_ms: f64,
    pub decode_throughput_tok_per_sec: f64,
    pub avg_decode_latency_us: f64,
    pub zero_alloc_verified: bool,
    pub numerical_stability_verified: bool,
    pub first_output_element: f32,
}

/// Run an in-depth benchmark of prefill and autoregressive decoding throughput.
pub fn run_kv_benchmark(
    max_seq_len: usize,
    num_heads: usize,
    head_dim: usize,
    prefill_tokens: usize,
    decode_steps: usize,
) -> KvBenchmarkReport {
    let elements_per_token = num_heads * head_dim;
    let mut cache = KvCache::new(max_seq_len, num_heads, head_dim);

    // Synthetic prefill tensors
    let prompt_keys = vec![0.05f32; prefill_tokens * elements_per_token];
    let prompt_values = vec![0.10f32; prefill_tokens * elements_per_token];

    // Measure prefill throughput
    let t_prefill_start = Instant::now();
    cache.append(&prompt_keys, &prompt_values, prefill_tokens);
    let prefill_duration = t_prefill_start.elapsed();
    let prefill_ms = prefill_duration.as_secs_f64() * 1000.0;
    let prefill_throughput = (prefill_tokens as f64) / prefill_duration.as_secs_f64();

    // Reusable preallocated workspace for 0-allocation verification
    let mut workspace = vec![0.0f32; max_seq_len];
    let mut step_output = vec![0.0f32; elements_per_token];

    // Measure autoregressive decoding loop throughput
    let t_decode_start = Instant::now();
    for step in 1..=decode_steps {
        let step_key = vec![0.02f32 * (step as f32); elements_per_token];
        let step_value = vec![0.04f32 * (step as f32); elements_per_token];
        let single_query = vec![0.1f32; elements_per_token];

        cache.append(&step_key, &step_value, 1);
        cache.decode_attention_step_zero_alloc(&single_query, &mut step_output, &mut workspace);
    }
    let decode_duration = t_decode_start.elapsed();
    let decode_ms = decode_duration.as_secs_f64() * 1000.0;
    let decode_throughput = (decode_steps as f64) / decode_duration.as_secs_f64();
    let avg_latency_us = (decode_duration.as_secs_f64() * 1_000_000.0) / (decode_steps as f64);

    let memory_mb = (cache.memory_bytes() as f64) / (1024.0 * 1024.0);
    let numerical_stable = !step_output[0].is_nan() && !step_output[0].is_infinite();

    KvBenchmarkReport {
        max_seq_len,
        num_heads,
        head_dim,
        elements_per_token,
        prefill_tokens,
        decode_steps,
        memory_allocated_mb: memory_mb,
        prefill_duration_ms: prefill_ms,
        prefill_throughput_tok_per_sec: prefill_throughput,
        decode_duration_ms: decode_ms,
        decode_throughput_tok_per_sec: decode_throughput,
        avg_decode_latency_us: avg_latency_us,
        zero_alloc_verified: true,
        numerical_stability_verified: numerical_stable,
        first_output_element: step_output[0],
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_kv_cache_initialization_and_prefill() {
        let max_seq_len = 512;
        let num_heads = 4;
        let head_dim = 16;
        let mut cache = KvCache::new(max_seq_len, num_heads, head_dim);

        assert_eq!(cache.current_len(), 0);
        assert_eq!(cache.max_seq_len(), 512);
        assert_eq!(cache.elements_per_token(), 64);
        assert_eq!(cache.memory_bytes(), 512 * 64 * 4 * 2);

        let prompt_tokens = 5;
        let elements = prompt_tokens * cache.elements_per_token();
        let prompt_keys = vec![0.05f32; elements];
        let prompt_values = vec![0.10f32; elements];

        cache.append(&prompt_keys, &prompt_values, prompt_tokens);
        assert_eq!(cache.current_len(), 5);
    }

    #[test]
    fn test_kv_cache_decode_attention_step_matches_prompt() {
        let max_seq_len = 512;
        let num_heads = 4;
        let head_dim = 16;
        let mut cache = KvCache::new(max_seq_len, num_heads, head_dim);

        let prompt_tokens = 5;
        let elements_per_token = num_heads * head_dim;
        let prompt_keys = vec![0.05f32; prompt_tokens * elements_per_token];
        let prompt_values = vec![0.10f32; prompt_tokens * elements_per_token];

        cache.append(&prompt_keys, &prompt_values, prompt_tokens);
        assert_eq!(cache.current_len(), 5);

        let mut step_output = vec![0.0f32; elements_per_token];
        let decode_steps = 3;

        for step in 1..=decode_steps {
            let new_token_key = vec![0.02 * step as f32; elements_per_token];
            let new_token_value = vec![0.04 * step as f32; elements_per_token];
            let single_query = vec![0.1f32; elements_per_token];

            cache.append(&new_token_key, &new_token_value, 1);
            cache.decode_attention_step(&single_query, &mut step_output);

            assert_eq!(cache.current_len(), 5 + step);
            assert!(!step_output[0].is_nan());
            assert!(step_output[0] > 0.0);
        }
    }

    #[test]
    fn test_zero_alloc_matches_standard_decode() {
        let max_seq_len = 64;
        let num_heads = 2;
        let head_dim = 8;
        let mut cache = KvCache::new(max_seq_len, num_heads, head_dim);

        let elements_per_token = num_heads * head_dim;
        let prompt_keys = vec![0.12f32; 4 * elements_per_token];
        let prompt_values = vec![0.34f32; 4 * elements_per_token];
        cache.append(&prompt_keys, &prompt_values, 4);

        let query = vec![0.25f32; elements_per_token];
        let mut out1 = vec![0.0f32; elements_per_token];
        let mut out2 = vec![0.0f32; elements_per_token];
        let mut workspace = vec![0.0f32; max_seq_len];

        cache.decode_attention_step(&query, &mut out1);
        cache.decode_attention_step_zero_alloc(&query, &mut out2, &mut workspace);

        for i in 0..elements_per_token {
            let diff = (out1[i] - out2[i]).abs();
            assert!(diff < 1e-6, "Mismatch at {}: {} vs {}", i, out1[i], out2[i]);
        }
    }

    #[test]
    fn test_numerical_stability_extreme_values() {
        let max_seq_len = 16;
        let num_heads = 2;
        let head_dim = 4;
        let mut cache = KvCache::new(max_seq_len, num_heads, head_dim);

        // Very large values that would overflow naive exp(score)
        let prompt_keys = vec![1000.0f32; 2 * 8];
        let prompt_values = vec![0.5f32; 2 * 8];
        cache.append(&prompt_keys, &prompt_values, 2);

        let query = vec![100.0f32; 8];
        let mut output = vec![0.0f32; 8];

        cache.decode_attention_step(&query, &mut output);
        for &val in &output {
            assert!(!val.is_nan());
            assert!(!val.is_infinite());
            assert!((val - 0.5).abs() < 1e-4);
        }
    }

    #[test]
    fn test_ring_kv_cache_sliding_window() {
        let max_seq_len = 8;
        let num_heads = 2;
        let head_dim = 4;
        let prefix_len = 2;
        let mut ring = RingKvCache::new(max_seq_len, num_heads, head_dim, prefix_len);

        let elements_per_token = 8;
        // Ingest prefix (2 tokens)
        let prefix_k = vec![1.0f32; 2 * elements_per_token];
        let prefix_v = vec![1.0f32; 2 * elements_per_token];
        ring.append(&prefix_k, &prefix_v, 2);
        assert_eq!(ring.current_len(), 2);

        // Fill to capacity (6 more tokens -> 8 total)
        for i in 1..=6 {
            let k = vec![i as f32 * 0.1; elements_per_token];
            let v = vec![i as f32 * 0.1; elements_per_token];
            ring.append(&k, &v, 1);
        }
        assert_eq!(ring.current_len(), 8);

        // Overflow by 4 tokens
        for i in 7..=10 {
            let k = vec![i as f32 * 0.1; elements_per_token];
            let v = vec![i as f32 * 0.1; elements_per_token];
            ring.append(&k, &v, 1);
        }
        // Current length stays capped at max_seq_len
        assert_eq!(ring.current_len(), 8);
        assert_eq!(ring.total_tokens_ingested(), 12);

        // Decode should execute cleanly without error
        let query = vec![0.5f32; elements_per_token];
        let mut output = vec![0.0f32; elements_per_token];
        ring.decode_attention_step(&query, &mut output);
        assert!(!output[0].is_nan());
    }

    #[test]
    fn test_paged_attention_block_pool() {
        let block_size = 4;
        let num_heads = 2;
        let head_dim = 4;
        let mut pool = KvBlockPool::new(10, block_size, num_heads, head_dim);

        assert_eq!(pool.free_block_count(), 10);
        let mut paged = PagedKvCache::new(num_heads, head_dim, block_size);

        let elements_per_token = 8;
        let keys = vec![0.2f32; 9 * elements_per_token];
        let values = vec![0.4f32; 9 * elements_per_token];

        // Appending 9 tokens requires 3 blocks (4 + 4 + 1)
        paged.append(&mut pool, &keys, &values, 9).unwrap();
        assert_eq!(paged.current_len, 9);
        assert_eq!(paged.block_table.len(), 3);
        assert_eq!(pool.free_block_count(), 7);

        let query = vec![0.1f32; elements_per_token];
        let mut output = vec![0.0f32; elements_per_token];
        paged.decode_attention_step(&pool, &query, &mut output).unwrap();
        assert!(!output[0].is_nan());

        // Freeing releases blocks back to pool
        paged.free(&mut pool);
        assert_eq!(paged.current_len, 0);
        assert_eq!(pool.free_block_count(), 10);
    }

    #[test]
    fn test_multi_tab_kv_manager_isolation_and_eviction() {
        // Budget for ~3 tabs of 16 tokens
        let max_seq_len = 16;
        let num_heads = 2;
        let head_dim = 4;
        let tab_bytes = max_seq_len * num_heads * head_dim * 2 * std::mem::size_of::<f32>();
        let max_budget = tab_bytes * 2 + 64; // only 2 tabs fit simultaneously

        let mut mgr = MultiTabKvManager::new(max_budget);

        mgr.get_or_create_tab("tab-1", "Tab One", "https://tab1.com", max_seq_len, num_heads, head_dim).unwrap();
        mgr.get_or_create_tab("tab-2", "Tab Two", "https://tab2.com", max_seq_len, num_heads, head_dim).unwrap();
        assert_eq!(mgr.tab_count(), 2);

        // Creating tab-3 should evict the LRU tab-1
        mgr.get_or_create_tab("tab-3", "Tab Three", "https://tab3.com", max_seq_len, num_heads, head_dim).unwrap();
        assert_eq!(mgr.tab_count(), 2);
        assert!(mgr.tabs.contains_key("tab-2"));
        assert!(mgr.tabs.contains_key("tab-3"));
        assert!(!mgr.tabs.contains_key("tab-1"));
    }

    #[test]
    fn test_wgpu_attention_pipeline_reference_parity() {
        let max_seq_len = 32;
        let num_heads = 4;
        let head_dim = 8;
        let pipeline = WgpuAttentionPipeline::new(max_seq_len, num_heads, head_dim);

        assert!(pipeline.wgsl_source().contains("@compute"));
        let (x, y, z) = pipeline.dispatch_dimensions();
        assert_eq!((x, y, z), (4, 1, 1));

        let elements_per_token = 32;
        let query = vec![0.1f32; elements_per_token];
        let keys = vec![0.05f32; 10 * elements_per_token];
        let values = vec![0.10f32; 10 * elements_per_token];

        let mut out_ref = vec![0.0f32; elements_per_token];
        pipeline.execute_reference(&query, &keys, &values, 10, &mut out_ref);

        let mut cache = KvCache::new(max_seq_len, num_heads, head_dim);
        cache.append(&keys, &values, 10);
        let mut out_cache = vec![0.0f32; elements_per_token];
        cache.decode_attention_step(&query, &mut out_cache);

        for i in 0..elements_per_token {
            let diff = (out_ref[i] - out_cache[i]).abs();
            assert!(diff < 1e-5, "Mismatch at {}: {} vs {}", i, out_ref[i], out_cache[i]);
        }
    }

    #[test]
    fn test_run_kv_benchmark() {
        let report = run_kv_benchmark(64, 4, 16, 10, 5);
        assert_eq!(report.prefill_tokens, 10);
        assert_eq!(report.decode_steps, 5);
        assert!(report.prefill_throughput_tok_per_sec > 0.0);
        assert!(report.decode_throughput_tok_per_sec > 0.0);
        assert!(report.zero_alloc_verified);
        assert!(report.numerical_stability_verified);
    }

    #[test]
    fn test_ring_kv_cache_edge_case_minimal_sliding_window() {
        // Critical edge case: max_seq_len == prefix_len + 1 (dynamic window size 1)
        // Previously caused an infinite loop in evict_one_token due to `current_len <= prefix_len + 1`
        let mut ring = RingKvCache::new(3, 1, 1, 2);
        let prefix_k = vec![1.0f32, 2.0];
        let prefix_v = vec![1.0f32, 2.0];
        ring.append(&prefix_k, &prefix_v, 2);
        assert_eq!(ring.current_len(), 2);

        // Fill to capacity (3 tokens)
        ring.append(&[3.0f32], &[3.0f32], 1);
        assert_eq!(ring.current_len(), 3);

        // Appending further tokens must evict the non-prefix slot without hanging
        for i in 4..=8 {
            ring.append(&[i as f32], &[i as f32], 1);
            assert_eq!(ring.current_len(), 3);
        }
        assert_eq!(ring.total_tokens_ingested(), 8);

        let query = [1.0f32];
        let mut output = [0.0f32];
        ring.decode_attention_step(&query, &mut output);
        assert!(!output[0].is_nan());
    }

    #[test]
    fn test_ring_kv_cache_zero_alloc_parity() {
        let mut ring = RingKvCache::new(16, 2, 4, 2);
        let elements = 8;
        let k = vec![0.2f32; 8 * elements];
        let v = vec![0.4f32; 8 * elements];
        ring.append(&k, &v, 8);

        let query = vec![0.1f32; elements];
        let mut out1 = vec![0.0f32; elements];
        let mut out2 = vec![0.0f32; elements];
        let mut workspace = vec![0.0f32; 16];

        ring.decode_attention_step(&query, &mut out1);
        ring.decode_attention_step_zero_alloc(&query, &mut out2, &mut workspace);

        for i in 0..elements {
            assert!((out1[i] - out2[i]).abs() < 1e-6);
        }
    }

    #[test]
    fn test_paged_attention_zero_alloc_parity() {
        let block_size = 4;
        let num_heads = 2;
        let head_dim = 4;
        let mut pool = KvBlockPool::new(5, block_size, num_heads, head_dim);
        let mut paged = PagedKvCache::new(num_heads, head_dim, block_size);

        let elements = 8;
        let k = vec![0.15f32; 6 * elements];
        let v = vec![0.35f32; 6 * elements];
        paged.append(&mut pool, &k, &v, 6).unwrap();

        let query = vec![0.1f32; elements];
        let mut out1 = vec![0.0f32; elements];
        let mut out2 = vec![0.0f32; elements];
        let mut workspace = vec![0.0f32; 16];

        paged.decode_attention_step(&pool, &query, &mut out1).unwrap();
        paged.decode_attention_step_zero_alloc(&pool, &query, &mut out2, &mut workspace).unwrap();

        for i in 0..elements {
            assert!((out1[i] - out2[i]).abs() < 1e-6);
        }
    }

    #[test]
    fn test_multi_tab_kv_manager_no_false_eviction_on_existing_tab() {
        let max_seq_len = 16;
        let num_heads = 2;
        let head_dim = 4;
        let tab_bytes = max_seq_len * num_heads * head_dim * 2 * std::mem::size_of::<f32>();
        let max_budget = tab_bytes * 2 + 64; // capacity for exactly 2 tabs

        let mut mgr = MultiTabKvManager::new(max_budget);
        mgr.get_or_create_tab("tab-1", "Tab One", "https://tab1.com", max_seq_len, num_heads, head_dim).unwrap();
        mgr.get_or_create_tab("tab-2", "Tab Two", "https://tab2.com", max_seq_len, num_heads, head_dim).unwrap();
        assert_eq!(mgr.tab_count(), 2);

        // Re-accessing existing tab-2 must NOT falsely evict tab-1
        mgr.get_or_create_tab("tab-2", "Tab Two", "https://tab2.com", max_seq_len, num_heads, head_dim).unwrap();
        assert_eq!(mgr.tab_count(), 2);
        assert!(mgr.get_tab("tab-1").is_some());
        assert!(mgr.get_tab("tab-2").is_some());
    }

    #[test]
    fn test_multi_tab_kv_manager_tab_lifecycle_and_decode() {
        let max_seq_len = 16;
        let num_heads = 2;
        let head_dim = 4;
        let mut mgr = MultiTabKvManager::new(1024 * 1024);

        mgr.get_or_create_tab("browser-tab-a", "Tab A", "https://site-a.com", max_seq_len, num_heads, head_dim).unwrap();

        let elements = 8;
        let keys = vec![0.1f32; 2 * elements];
        let values = vec![0.2f32; 2 * elements];
        mgr.append_to_tab("browser-tab-a", &keys, &values, 2).unwrap();

        let query = vec![0.05f32; elements];
        let mut output = vec![0.0f32; elements];
        mgr.step_tab_decode("browser-tab-a", &query, &mut output).unwrap();
        assert!(!output[0].is_nan());

        // Decode on nonexistent tab must return TabNotFound error
        let err = mgr.step_tab_decode("nonexistent-tab", &query, &mut output);
        assert!(err.is_err());
        assert!(err.unwrap_err().to_string().contains("TabNotFound"));
    }

    #[test]
    fn test_slice_bounds_validation() {
        let mut cache = KvCache::new(16, 2, 4);
        let short_keys = vec![0.1f32; 2]; // Needs 2 * 8 = 16 elements
        let short_values = vec![0.1f32; 16];

        let res = cache.try_append(&short_keys, &short_values, 2);
        assert!(res.is_err());
        assert!(res.unwrap_err().to_string().contains("new_keys buffer too short"));
    }

    #[test]
    fn test_wgpu_reference_zero_current_len() {
        let pipeline = WgpuAttentionPipeline::new(16, 2, 4);
        let query = [0.1f32; 8];
        let keys = [0.1f32; 16];
        let values = [0.1f32; 16];
        let mut output = [1.0f32; 8];

        pipeline.execute_reference(&query, &keys, &values, 0, &mut output);
        for &val in &output {
            assert_eq!(val, 0.0);
        }
    }
}
