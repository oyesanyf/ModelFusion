use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::time::Duration;
use dashmap::DashMap;
use serde::{Deserialize, Serialize};
use tokio_util::sync::CancellationToken as TokioToken;
use uuid::Uuid;

/// Unique identifier for a cancellation token.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct TokenId(pub Uuid);

impl TokenId {
    /// Generates a new time-ordered UUID v7 token ID.
    pub fn new() -> Self {
        Self(Uuid::now_v7())
    }
}

impl Default for TokenId {
    fn default() -> Self {
        Self::new()
    }
}

impl std::fmt::Display for TokenId {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.0)
    }
}

/// Internal shared state for a hierarchical cancellation token node.
struct TokenInner {
    id: TokenId,
    name: String,
    parent_id: Option<TokenId>,
    tokio_token: TokioToken,
    is_cancelled: AtomicBool,
    children: DashMap<TokenId, HierarchicalCancellationToken>,
}

/// Hierarchical, cooperative cancellation token with deterministic tree propagation and cleanup.
///
/// Properties:
/// - Cancelling a parent automatically propagates cancellation down to all children and descendants.
/// - Cancelling a child token does NOT affect its parent or siblings.
/// - Deterministic child registration and detachment prevents memory leaks across long sessions.
#[derive(Clone)]
pub struct HierarchicalCancellationToken {
    inner: Arc<TokenInner>,
}

impl std::fmt::Debug for HierarchicalCancellationToken {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("HierarchicalCancellationToken")
            .field("id", &self.inner.id)
            .field("name", &self.inner.name)
            .field("parent_id", &self.inner.parent_id)
            .field("is_cancelled", &self.is_cancelled())
            .field("active_children", &self.inner.children.len())
            .finish()
    }
}

impl HierarchicalCancellationToken {
    /// Creates a new root cancellation token.
    pub fn new_root(name: impl Into<String>) -> Self {
        let id = TokenId::new();
        let tokio_token = TokioToken::new();
        let inner = Arc::new(TokenInner {
            id,
            name: name.into(),
            parent_id: None,
            tokio_token,
            is_cancelled: AtomicBool::new(false),
            children: DashMap::new(),
        });
        Self { inner }
    }

    /// Returns the unique token identifier.
    pub fn id(&self) -> TokenId {
        self.inner.id
    }

    /// Returns the token descriptive name.
    pub fn name(&self) -> &str {
        &self.inner.name
    }

    /// Returns the parent token ID, if any.
    pub fn parent_id(&self) -> Option<TokenId> {
        self.inner.parent_id
    }

    /// Checks if this token (or any of its ancestors) has been cancelled.
    pub fn is_cancelled(&self) -> bool {
        self.inner.is_cancelled.load(Ordering::Acquire) || self.inner.tokio_token.is_cancelled()
    }

    /// Asynchronously waits until this token or any ancestor is cancelled.
    pub async fn cancelled(&self) {
        if self.is_cancelled() {
            return;
        }
        self.inner.tokio_token.cancelled().await;
    }

    /// Triggers cancellation on this token and all its active descendants.
    pub fn cancel(&self) {
        self.inner.is_cancelled.store(true, Ordering::Release);
        self.inner.tokio_token.cancel();
        // Propagate explicitly to all registered children
        for child in self.inner.children.iter() {
            child.value().cancel();
        }
    }

    /// Creates a child cancellation token linked to this parent.
    pub fn child_token(&self) -> Self {
        self.child_token_with_name(format!("child-{}", Uuid::new_v4()))
    }

    /// Creates a child cancellation token with a descriptive name.
    pub fn child_token_with_name(&self, name: impl Into<String>) -> Self {
        let child_id = TokenId::new();
        let child_tokio_token = self.inner.tokio_token.child_token();
        if self.is_cancelled() {
            child_tokio_token.cancel();
        }
        
        let child_inner = Arc::new(TokenInner {
            id: child_id,
            name: name.into(),
            parent_id: Some(self.inner.id),
            tokio_token: child_tokio_token,
            is_cancelled: AtomicBool::new(self.is_cancelled()),
            children: DashMap::new(),
        });

        let child = Self { inner: child_inner };
        self.inner.children.insert(child_id, child.clone());
        child
    }

    /// Detaches a child token from this parent's registry to allow immediate memory cleanup.
    pub fn detach_child(&self, child_id: &TokenId) -> Option<HierarchicalCancellationToken> {
        self.inner.children.remove(child_id).map(|(_, v)| v)
    }

    /// Returns the number of direct active child tokens.
    pub fn active_child_count(&self) -> usize {
        self.inner.children.len()
    }

    /// Returns the total number of active descendants in the subtree.
    pub fn active_descendant_count(&self) -> usize {
        let mut count = self.inner.children.len();
        for child in self.inner.children.iter() {
            count += child.value().active_descendant_count();
        }
        count
    }

    /// Computes the maximum depth of active child nodes below this token.
    pub fn tree_depth(&self) -> usize {
        if self.inner.children.is_empty() {
            0
        } else {
            let max_sub_depth = self
                .inner
                .children
                .iter()
                .map(|child| child.value().tree_depth())
                .max()
                .unwrap_or(0);
            1 + max_sub_depth
        }
    }

    /// Creates a child token that will automatically cancel after `timeout` duration.
    pub fn child_with_timeout(&self, timeout: Duration) -> Self {
        let child = self.child_token_with_name(format!("timeout-{}ms", timeout.as_millis()));
        let child_clone = child.clone();
        tokio::spawn(async move {
            tokio::select! {
                _ = tokio::time::sleep(timeout) => {
                    child_clone.cancel();
                }
                _ = child_clone.cancelled() => {}
            }
        });
        child
    }

    /// Returns a drop guard that will trigger cancellation when dropped.
    pub fn drop_guard(self) -> CancellationDropGuard {
        CancellationDropGuard {
            token: Some(self),
        }
    }
}

/// A RAII drop guard that cancels the wrapped token when it goes out of scope.
pub struct CancellationDropGuard {
    token: Option<HierarchicalCancellationToken>,
}

impl CancellationDropGuard {
    /// Disarms the guard so it will not cancel when dropped.
    pub fn disarm(mut self) -> HierarchicalCancellationToken {
        self.token.take().expect("token present")
    }
}

impl Drop for CancellationDropGuard {
    fn drop(&mut self) {
        if let Some(token) = self.token.take() {
            token.cancel();
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::AtomicUsize;
    use tokio::time::{sleep, Duration};

    #[tokio::test]
    async fn test_root_cancellation_propagates_to_descendants() {
        let root = HierarchicalCancellationToken::new_root("root");
        let child1 = root.child_token_with_name("child1");
        let child2 = root.child_token_with_name("child2");
        let grandchild = child1.child_token_with_name("grandchild");

        assert_eq!(root.active_child_count(), 2);
        assert_eq!(root.active_descendant_count(), 3);
        assert_eq!(root.tree_depth(), 2);

        assert!(!root.is_cancelled());
        assert!(!child1.is_cancelled());
        assert!(!child2.is_cancelled());
        assert!(!grandchild.is_cancelled());

        root.cancel();

        assert!(root.is_cancelled());
        assert!(child1.is_cancelled());
        assert!(child2.is_cancelled());
        assert!(grandchild.is_cancelled());
    }

    #[tokio::test]
    async fn test_child_cancellation_isolation() {
        let root = HierarchicalCancellationToken::new_root("root");
        let child1 = root.child_token_with_name("child1");
        let child2 = root.child_token_with_name("child2");
        let grandchild1 = child1.child_token_with_name("grandchild1");

        child1.cancel();

        assert!(child1.is_cancelled());
        assert!(grandchild1.is_cancelled());

        // Root and sibling must NOT be cancelled
        assert!(!root.is_cancelled());
        assert!(!child2.is_cancelled());
    }

    #[tokio::test]
    async fn test_deterministic_detach() {
        let root = HierarchicalCancellationToken::new_root("root");
        let child = root.child_token_with_name("child");
        let child_id = child.id();

        assert_eq!(root.active_child_count(), 1);
        let detached = root.detach_child(&child_id);
        assert!(detached.is_some());
        assert_eq!(root.active_child_count(), 0);

        // Detached child can still cancel independently
        assert!(!child.is_cancelled());
        child.cancel();
        assert!(child.is_cancelled());
    }

    #[tokio::test]
    async fn test_cancellation_timeout() {
        let root = HierarchicalCancellationToken::new_root("root");
        let timeout_token = root.child_with_timeout(Duration::from_millis(50));

        assert!(!timeout_token.is_cancelled());
        sleep(Duration::from_millis(100)).await;
        assert!(timeout_token.is_cancelled());
        assert!(!root.is_cancelled());
    }

    #[tokio::test]
    async fn test_concurrent_cancellation_stress() {
        let root = HierarchicalCancellationToken::new_root("stress_root");
        let mut tokens = Vec::new();

        for i in 0..100 {
            tokens.push(root.child_token_with_name(format!("child-{}", i)));
        }

        let counter = Arc::new(AtomicUsize::new(0));
        let mut handles = Vec::new();

        for token in tokens.clone() {
            let counter_clone = counter.clone();
            handles.push(tokio::spawn(async move {
                token.cancelled().await;
                counter_clone.fetch_add(1, Ordering::SeqCst);
            }));
        }

        // Cancel root
        root.cancel();

        for handle in handles {
            handle.await.unwrap();
        }

        assert_eq!(counter.load(Ordering::SeqCst), 100);
    }

    #[tokio::test]
    async fn test_drop_guard() {
        let root = HierarchicalCancellationToken::new_root("root");
        let child = root.child_token();
        
        {
            let guard = child.clone().drop_guard();
            assert!(!child.is_cancelled());
            drop(guard);
        }

        assert!(child.is_cancelled());
    }
}
