use std::future::Future;
use std::sync::Arc;
use std::time::Duration;
use thiserror::Error;
use tokio::runtime::{Builder, Handle, Runtime};
use tokio::sync::oneshot;

/// Errors arising from compute pool or runtime operations.
#[derive(Debug, Error)]
pub enum ComputeError {
    #[error("Rayon thread pool initialization failed: {0}")]
    ThreadPoolInit(#[from] rayon::ThreadPoolBuildError),

    #[error("Compute task was dropped before completing (channel closed)")]
    ComputeDropped,

    #[error("Compute task panicked during execution: {0}")]
    ComputePanicked(String),
}

/// Errors arising during runtime initialization.
#[derive(Debug, Error)]
pub enum RuntimeError {
    #[error("Failed to build Tokio runtime: {0}")]
    TokioInitFailed(#[from] std::io::Error),

    #[error("Compute pool failure: {0}")]
    ComputeInitFailed(#[from] ComputeError),
}

/// Configuration settings for Tokio async runtime and Rayon compute pool.
#[derive(Debug, Clone)]
pub struct EngineRuntimeConfig {
    pub worker_threads: usize,
    pub max_blocking_threads: usize,
    pub compute_threads: usize,
    pub thread_name_prefix: String,
    pub thread_keep_alive: Duration,
    pub enable_io: bool,
    pub enable_time: bool,
}

impl Default for EngineRuntimeConfig {
    fn default() -> Self {
        let logical_cpus = num_cpus::get().max(2);
        let physical_cpus = num_cpus::get_physical().max(2);
        Self {
            worker_threads: logical_cpus,
            max_blocking_threads: 512,
            compute_threads: physical_cpus,
            thread_name_prefix: "mcp-worker".to_string(),
            thread_keep_alive: Duration::from_secs(10),
            enable_io: true,
            enable_time: true,
        }
    }
}

impl EngineRuntimeConfig {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn worker_threads(mut self, count: usize) -> Self {
        self.worker_threads = count.max(1);
        self
    }

    pub fn compute_threads(mut self, count: usize) -> Self {
        self.compute_threads = count.max(1);
        self
    }

    pub fn max_blocking_threads(mut self, count: usize) -> Self {
        self.max_blocking_threads = count.max(1);
        self
    }

    pub fn thread_name_prefix(mut self, prefix: impl Into<String>) -> Self {
        self.thread_name_prefix = prefix.into();
        self
    }
}

/// Rayon work-stealing compute thread pool for heavy CPU-bound tasks.
pub struct ComputePool {
    pool: rayon::ThreadPool,
    num_threads: usize,
}

impl ComputePool {
    /// Initializes a new Rayon compute thread pool with designated worker names.
    pub fn new(num_threads: usize) -> Result<Self, ComputeError> {
        let num_threads = num_threads.max(1);
        let pool = rayon::ThreadPoolBuilder::new()
            .num_threads(num_threads)
            .thread_name(|idx| format!("mcp-compute-{}", idx))
            .build()
            .map_err(ComputeError::ThreadPoolInit)?;

        Ok(Self {
            pool,
            num_threads,
        })
    }

    /// Spawns a CPU-intensive closure onto the Rayon pool, returning a non-blocking Tokio future via oneshot channel.
    pub async fn spawn_compute<F, R>(&self, f: F) -> Result<R, ComputeError>
    where
        F: FnOnce() -> R + Send + 'static,
        R: Send + 'static,
    {
        let (tx, rx) = oneshot::channel();
        self.pool.spawn(move || {
            let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(f));
            let send_res = match result {
                Ok(val) => tx.send(Ok(val)),
                Err(err) => {
                    let msg = if let Some(s) = err.downcast_ref::<&str>() {
                        s.to_string()
                    } else if let Some(s) = err.downcast_ref::<String>() {
                        s.clone()
                    } else {
                        "Unknown panic in compute worker".to_string()
                    };
                    tx.send(Err(ComputeError::ComputePanicked(msg)))
                }
            };
            let _ = send_res;
        });

        rx.await.map_err(|_| ComputeError::ComputeDropped)?
    }

    /// Executes a closure directly on the Rayon pool blocking the current thread until completion.
    pub fn install<OP, R>(&self, op: OP) -> R
    where
        OP: FnOnce() -> R + Send,
        R: Send,
    {
        self.pool.install(op)
    }

    /// Returns the number of threads in the compute pool.
    pub fn current_num_threads(&self) -> usize {
        self.num_threads
    }
}

/// Unified execution runtime managing Tokio asynchronous event loops and Rayon compute workers.
pub struct EngineRuntime {
    tokio_runtime: Option<Runtime>,
    handle: Handle,
    compute_pool: Arc<ComputePool>,
}

impl EngineRuntime {
    /// Builds a new EngineRuntime with dedicated Tokio runtime and Rayon compute pool.
    pub fn new(config: EngineRuntimeConfig) -> Result<Self, RuntimeError> {
        let compute_pool = Arc::new(ComputePool::new(config.compute_threads)?);

        let mut builder = Builder::new_multi_thread();
        builder
            .worker_threads(config.worker_threads)
            .max_blocking_threads(config.max_blocking_threads)
            .thread_name_fn(move || {
                static ATOMIC_ID: std::sync::atomic::AtomicUsize = std::sync::atomic::AtomicUsize::new(0);
                let id = ATOMIC_ID.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                format!("mcp-worker-{}", id)
            })
            .thread_keep_alive(config.thread_keep_alive);

        if config.enable_io {
            builder.enable_io();
        }
        if config.enable_time {
            builder.enable_time();
        }

        let tokio_runtime = builder.build().map_err(RuntimeError::TokioInitFailed)?;
        let handle = tokio_runtime.handle().clone();

        Ok(Self {
            tokio_runtime: Some(tokio_runtime),
            handle,
            compute_pool,
        })
    }

    /// Creates an EngineRuntime attaching to an existing Tokio Handle.
    pub fn from_handle(handle: Handle, compute_threads: usize) -> Result<Self, RuntimeError> {
        let compute_pool = Arc::new(ComputePool::new(compute_threads)?);
        Ok(Self {
            tokio_runtime: None,
            handle,
            compute_pool,
        })
    }

    /// Spawns an asynchronous future onto the Tokio reactor.
    pub fn spawn<F>(&self, future: F) -> tokio::task::JoinHandle<F::Output>
    where
        F: Future + Send + 'static,
        F::Output: Send + 'static,
    {
        self.handle.spawn(future)
    }

    /// Spawns a blocking I/O task onto Tokio's blocking thread pool.
    pub fn spawn_blocking<F, R>(&self, f: F) -> tokio::task::JoinHandle<R>
    where
        F: FnOnce() -> R + Send + 'static,
        R: Send + 'static,
    {
        self.handle.spawn_blocking(f)
    }

    /// Spawns a CPU-intensive compute task onto the Rayon pool and returns a Tokio future.
    pub async fn spawn_compute<F, R>(&self, f: F) -> Result<R, ComputeError>
    where
        F: FnOnce() -> R + Send + 'static,
        R: Send + 'static,
    {
        self.compute_pool.spawn_compute(f).await
    }

    /// Blocks on an async future (only valid when running on outer main thread, not inside async context).
    pub fn block_on<F: Future>(&self, future: F) -> F::Output {
        self.handle.block_on(future)
    }

    /// Returns a reference to the Tokio Handle.
    pub fn handle(&self) -> &Handle {
        &self.handle
    }

    /// Returns a clone of the ComputePool Arc.
    pub fn compute_pool(&self) -> Arc<ComputePool> {
        self.compute_pool.clone()
    }

    /// Shuts down the Tokio runtime gracefully with timeout.
    pub fn shutdown(mut self, timeout: Duration) {
        if let Some(rt) = self.tokio_runtime.take() {
            rt.shutdown_timeout(timeout);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_compute_pool_parallel_computation() {
        let pool = ComputePool::new(4).unwrap();
        let rt = Builder::new_current_thread().enable_all().build().unwrap();

        rt.block_on(async {
            let mut handles = Vec::new();
            for i in 0..10 {
                let pool_ref = &pool;
                handles.push(pool_ref.spawn_compute(move || {
                    // Heavy CPU work: sum of squares
                    (0..10_000).map(|x| x * i).sum::<u64>()
                }));
            }

            let results = futures::future::join_all(handles).await;
            for (i, res) in results.into_iter().enumerate() {
                let val = res.unwrap();
                let expected: u64 = (0..10_000).map(|x| x * (i as u64)).sum();
                assert_eq!(val, expected);
            }
        });
    }

    #[test]
    fn test_compute_pool_panic_handling() {
        let pool = ComputePool::new(2).unwrap();
        let rt = Builder::new_current_thread().enable_all().build().unwrap();

        rt.block_on(async {
            let res = pool
                .spawn_compute(|| {
                    panic!("intentional test panic in compute worker");
                })
                .await;

            assert!(res.is_err());
            match res.unwrap_err() {
                ComputeError::ComputePanicked(msg) => {
                    assert!(msg.contains("intentional test panic"));
                }
                other => panic!("Expected ComputePanicked, got {:?}", other),
            }
        });
    }

    #[test]
    fn test_engine_runtime_creation_and_spawn() {
        let config = EngineRuntimeConfig::new()
            .worker_threads(2)
            .compute_threads(2);
        let runtime = EngineRuntime::new(config).unwrap();

        let handle = runtime.spawn(async {
            tokio::time::sleep(Duration::from_millis(10)).await;
            42
        });

        let res = runtime.block_on(handle).unwrap();
        assert_eq!(res, 42);

        let compute_res = runtime.block_on(runtime.spawn_compute(|| 100 + 200)).unwrap();
        assert_eq!(compute_res, 300);
    }
}
