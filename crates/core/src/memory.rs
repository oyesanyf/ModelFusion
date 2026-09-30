//! SQLite-backed Conversation Memory Subsystem for ModelFusion & HugOS.
//!
//! Provides high-throughput asynchronous memory persistence via `sqlx` in WAL mode
//! with busy timeouts and cl100k_base BPE tokenization.
//!
//! Features:
//! - Connection pooling with Write-Ahead Logging (WAL) and busy timeout.
//! - Foreign-key cascading session and message tables.
//! - Accurate cl100k_base BPE token counting with tiktoken-rs.
//! - Budgeted ContextManager for recent turn assembly and semantic memory packing.

use async_trait::async_trait;
use chrono::Utc;
use serde::{Deserialize, Serialize};
use sqlx::{sqlite::SqliteConnectOptions, FromRow, SqlitePool};
use std::str::FromStr;
use thiserror::Error;
use tiktoken_rs::cl100k_base;
use uuid::Uuid;

#[derive(Error, Debug)]
pub enum MemoryError {
    #[error("Database error: {0}")]
    Database(#[from] sqlx::Error),
    #[error("Tokenization error: {0}")]
    Tokenization(String),
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum MessageRole {
    System,
    User,
    Assistant,
}

impl MessageRole {
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::System => "system",
            Self::User => "user",
            Self::Assistant => "assistant",
        }
    }

    pub fn from_str(s: &str) -> Self {
        match s.to_lowercase().as_str() {
            "system" => Self::System,
            "assistant" => Self::Assistant,
            _ => Self::User,
        }
    }
}

impl std::fmt::Display for MessageRole {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.as_str())
    }
}

#[derive(Clone, Debug, FromRow, Serialize, Deserialize, PartialEq, Eq)]
pub struct ConversationSession {
    pub id: String,
    pub user_id: String,
    pub created_at: i64,
    pub updated_at: i64,
}

#[derive(Clone, Debug, FromRow, Serialize, Deserialize, PartialEq, Eq)]
pub struct StoredMessage {
    pub id: String,
    pub session_id: String,
    pub role: String,
    pub content: String,
    pub token_count: i64,
    pub created_at: i64,
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
pub struct ChatMessage {
    pub role: MessageRole,
    pub content: String,
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
pub struct AssemblyContext {
    pub system_prompt: Option<String>,
    pub retrieved_memories: Vec<String>,
    pub recent_turns: Vec<ChatMessage>,
    pub total_tokens: usize,
}

#[async_trait]
pub trait MemoryRepository: Send + Sync {
    async fn ensure_session(&self, user_id: &str, session_id: Option<&str>) -> Result<String, MemoryError>;
    async fn append_message(&self, session_id: &str, role: MessageRole, content: &str) -> Result<StoredMessage, MemoryError>;
    async fn get_recent_messages(&self, session_id: &str, limit: i64) -> Result<Vec<StoredMessage>, MemoryError>;
}

#[async_trait]
impl<R: MemoryRepository + ?Sized + Sync> MemoryRepository for &R {
    async fn ensure_session(&self, user_id: &str, session_id: Option<&str>) -> Result<String, MemoryError> {
        (**self).ensure_session(user_id, session_id).await
    }
    async fn append_message(&self, session_id: &str, role: MessageRole, content: &str) -> Result<StoredMessage, MemoryError> {
        (**self).append_message(session_id, role, content).await
    }
    async fn get_recent_messages(&self, session_id: &str, limit: i64) -> Result<Vec<StoredMessage>, MemoryError> {
        (**self).get_recent_messages(session_id, limit).await
    }
}

#[async_trait]
impl<R: MemoryRepository + ?Sized + Sync> MemoryRepository for std::sync::Arc<R> {
    async fn ensure_session(&self, user_id: &str, session_id: Option<&str>) -> Result<String, MemoryError> {
        (**self).ensure_session(user_id, session_id).await
    }
    async fn append_message(&self, session_id: &str, role: MessageRole, content: &str) -> Result<StoredMessage, MemoryError> {
        (**self).append_message(session_id, role, content).await
    }
    async fn get_recent_messages(&self, session_id: &str, limit: i64) -> Result<Vec<StoredMessage>, MemoryError> {
        (**self).get_recent_messages(session_id, limit).await
    }
}

#[derive(Clone)]
pub struct SqliteMemoryRepository {
    pool: SqlitePool,
}

impl SqliteMemoryRepository {
    pub async fn new(database_path: &str) -> Result<Self, sqlx::Error> {
        let connection_options = match SqliteConnectOptions::from_str(database_path) {
            Ok(opts) => opts,
            Err(_) => {
                let prefixed = format!("sqlite://{}", database_path);
                SqliteConnectOptions::from_str(&prefixed)
                    .unwrap_or_else(|_| SqliteConnectOptions::new().filename(database_path))
            }
        }
        .create_if_missing(true)
        .journal_mode(sqlx::sqlite::SqliteJournalMode::Wal)
        .busy_timeout(std::time::Duration::from_secs(5))
        .foreign_keys(true);

        let pool = SqlitePool::connect_with(connection_options).await?;

        Self::init_tables(&pool).await?;

        Ok(Self { pool })
    }

    pub fn from_pool(pool: SqlitePool) -> Self {
        Self { pool }
    }

    pub fn pool(&self) -> &SqlitePool {
        &self.pool
    }

    pub async fn init_tables(pool: &SqlitePool) -> Result<(), sqlx::Error> {
        sqlx::query(
            r#"
            PRAGMA foreign_keys = ON;

            CREATE TABLE IF NOT EXISTS conversation_sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS conversation_messages (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL REFERENCES conversation_sessions(id) ON DELETE CASCADE,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                token_count INTEGER NOT NULL DEFAULT 0,
                created_at INTEGER NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_messages_session_time 
            ON conversation_messages(session_id, created_at DESC);
            "#,
        )
        .execute(pool)
        .await?;

        Ok(())
    }

    pub fn calculate_tokens(content: &str) -> Result<i64, MemoryError> {
        let bpe = cl100k_base().map_err(|e| MemoryError::Tokenization(e.to_string()))?;
        Ok(bpe.encode_with_special_tokens(content).len() as i64)
    }

    pub async fn list_sessions(&self, user_id: &str) -> Result<Vec<ConversationSession>, MemoryError> {
        let sessions = sqlx::query_as::<_, ConversationSession>(
            "SELECT id, user_id, created_at, updated_at FROM conversation_sessions WHERE user_id = ?1 ORDER BY updated_at DESC"
        )
        .bind(user_id)
        .fetch_all(&self.pool)
        .await?;
        Ok(sessions)
    }

    pub async fn delete_session(&self, session_id: &str) -> Result<(), MemoryError> {
        sqlx::query("DELETE FROM conversation_sessions WHERE id = ?1")
            .bind(session_id)
            .execute(&self.pool)
            .await?;
        Ok(())
    }

    pub async fn count_messages(&self, session_id: &str) -> Result<i64, MemoryError> {
        let count = sqlx::query_scalar::<_, i64>(
            "SELECT COUNT(1) FROM conversation_messages WHERE session_id = ?1"
        )
        .bind(session_id)
        .fetch_one(&self.pool)
        .await?;
        Ok(count)
    }
}

#[async_trait]
impl MemoryRepository for SqliteMemoryRepository {
    async fn ensure_session(&self, user_id: &str, session_id: Option<&str>) -> Result<String, MemoryError> {
        if let Some(id) = session_id {
            let row = sqlx::query_scalar::<_, i64>(
                "SELECT COUNT(1) FROM conversation_sessions WHERE id = ?1",
            )
            .bind(id)
            .fetch_one(&self.pool)
            .await?;

            if row > 0 {
                return Ok(id.to_string());
            }
        }

        let new_id = session_id
            .filter(|s| !s.trim().is_empty())
            .map(|s| s.to_string())
            .unwrap_or_else(|| Uuid::new_v4().to_string());
        let now = Utc::now().timestamp_millis();

        sqlx::query(
            "INSERT INTO conversation_sessions (id, user_id, created_at, updated_at) VALUES (?1, ?2, ?3, ?4)",
        )
        .bind(&new_id)
        .bind(user_id)
        .bind(now)
        .bind(now)
        .execute(&self.pool)
        .await?;

        Ok(new_id)
    }

    async fn append_message(
        &self,
        session_id: &str,
        role: MessageRole,
        content: &str,
    ) -> Result<StoredMessage, MemoryError> {
        let tokens = Self::calculate_tokens(content)?;
        let msg_id = Uuid::new_v4().to_string();

        let max_time: Option<i64> = sqlx::query_scalar(
            "SELECT MAX(created_at) FROM conversation_messages WHERE session_id = ?1"
        )
        .bind(session_id)
        .fetch_optional(&self.pool)
        .await?
        .flatten();

        let mut now = Utc::now().timestamp_micros();
        if let Some(prev) = max_time {
            if now <= prev {
                now = prev + 1;
            }
        }

        sqlx::query(
            r#"
            INSERT INTO conversation_messages (id, session_id, role, content, token_count, created_at)
            VALUES (?1, ?2, ?3, ?4, ?5, ?6)
            "#,
        )
        .bind(&msg_id)
        .bind(session_id)
        .bind(role.as_str())
        .bind(content)
        .bind(tokens)
        .bind(now)
        .execute(&self.pool)
        .await?;

        sqlx::query(
            "UPDATE conversation_sessions SET updated_at = ?1 WHERE id = ?2",
        )
        .bind(now)
        .bind(session_id)
        .execute(&self.pool)
        .await?;

        Ok(StoredMessage {
            id: msg_id,
            session_id: session_id.to_string(),
            role: role.as_str().to_string(),
            content: content.to_string(),
            token_count: tokens,
            created_at: now,
        })
    }

    async fn get_recent_messages(&self, session_id: &str, limit: i64) -> Result<Vec<StoredMessage>, MemoryError> {
        let mut messages = sqlx::query_as::<_, StoredMessage>(
            r#"
            SELECT id, session_id, role, content, token_count, created_at
            FROM conversation_messages
            WHERE session_id = ?1
            ORDER BY created_at DESC
            LIMIT ?2
            "#,
        )
        .bind(session_id)
        .bind(limit)
        .fetch_all(&self.pool)
        .await?;

        messages.reverse();
        Ok(messages)
    }
}

pub struct ContextManager<R: MemoryRepository> {
    repo: R,
    max_context_tokens: usize,
    reserved_completion_tokens: usize,
}

impl<R: MemoryRepository> ContextManager<R> {
    pub fn new(repo: R, max_context_tokens: usize, reserved_completion_tokens: usize) -> Self {
        Self {
            repo,
            max_context_tokens,
            reserved_completion_tokens,
        }
    }

    pub fn repo(&self) -> &R {
        &self.repo
    }

    pub fn max_context_tokens(&self) -> usize {
        self.max_context_tokens
    }

    pub fn reserved_completion_tokens(&self) -> usize {
        self.reserved_completion_tokens
    }

    pub async fn assemble_context(
        &self,
        session_id: &str,
        system_prompt: Option<&str>,
        semantic_memories: Vec<String>,
    ) -> Result<AssemblyContext, MemoryError> {
        let bpe = cl100k_base().map_err(|e| MemoryError::Tokenization(e.to_string()))?;
        let mut used_tokens = 0;

        if let Some(sys) = system_prompt {
            used_tokens += bpe.encode_with_special_tokens(sys).len();
        }

        let mut included_memories = Vec::new();
        for memory in semantic_memories {
            let cost = bpe.encode_with_special_tokens(&memory).len();
            if used_tokens + cost + self.reserved_completion_tokens <= self.max_context_tokens {
                used_tokens += cost;
                included_memories.push(memory);
            }
        }

        let raw_history = self.repo.get_recent_messages(session_id, 30).await?;
        let mut selected_turns = Vec::new();

        for msg in raw_history.into_iter().rev() {
            let msg_cost = msg.token_count as usize;
            if used_tokens + msg_cost + self.reserved_completion_tokens > self.max_context_tokens {
                break;
            }
            used_tokens += msg_cost;
            selected_turns.push(ChatMessage {
                role: MessageRole::from_str(&msg.role),
                content: msg.content,
            });
        }

        selected_turns.reverse();

        Ok(AssemblyContext {
            system_prompt: system_prompt.map(|s| s.to_string()),
            retrieved_memories: included_memories,
            recent_turns: selected_turns,
            total_tokens: used_tokens,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_sqlite_memory_repository_lifecycle() {
        let repo = SqliteMemoryRepository::new("sqlite::memory:")
            .await
            .expect("Failed to initialize in-memory SQLite");

        // 1. Ensure new session
        let session_id = repo
            .ensure_session("user-123", None)
            .await
            .expect("Failed to create session");
        assert!(!session_id.is_empty());

        // 2. Ensure session idempotency
        let same_id = repo
            .ensure_session("user-123", Some(&session_id))
            .await
            .expect("Failed to ensure existing session");
        assert_eq!(session_id, same_id);

        // 3. Append messages
        let msg1 = repo
            .append_message(&session_id, MessageRole::User, "Hello ModelFusion!")
            .await
            .expect("Failed to append user message");
        assert_eq!(msg1.role, "user");
        assert!(msg1.token_count > 0);

        let msg2 = repo
            .append_message(&session_id, MessageRole::Assistant, "Hello! How can I assist you today?")
            .await
            .expect("Failed to append assistant message");
        assert_eq!(msg2.role, "assistant");
        assert!(msg2.token_count > 0);

        // 4. Retrieve recent messages
        let history = repo
            .get_recent_messages(&session_id, 10)
            .await
            .expect("Failed to get recent messages");
        assert_eq!(history.len(), 2);
        assert_eq!(history[0].content, "Hello ModelFusion!");
        assert_eq!(history[1].content, "Hello! How can I assist you today?");

        // 5. Test message count
        let count = repo.count_messages(&session_id).await.expect("Failed to count");
        assert_eq!(count, 2);

        // 6. Test session listing
        let sessions = repo.list_sessions("user-123").await.expect("Failed to list");
        assert_eq!(sessions.len(), 1);
        assert_eq!(sessions[0].id, session_id);
    }

    #[tokio::test]
    async fn test_context_manager_assembly() {
        let repo = SqliteMemoryRepository::new("sqlite::memory:")
            .await
            .expect("Failed to initialize in-memory SQLite");

        let session_id = repo
            .ensure_session("test-user", Some("test-session"))
            .await
            .expect("Failed to ensure session");

        repo.append_message(&session_id, MessageRole::User, "What is Rust?")
            .await
            .unwrap();
        repo.append_message(
            &session_id,
            MessageRole::Assistant,
            "Rust is a systems programming language focused on safety and speed.",
        )
        .await
        .unwrap();

        let ctx_manager = ContextManager::new(repo, 1000, 200);
        let assembled = ctx_manager
            .assemble_context(
                &session_id,
                Some("You are an expert systems engineer."),
                vec!["Memory note: user prefers concise answers.".to_string()],
            )
            .await
            .expect("Failed to assemble context");

        assert_eq!(
            assembled.system_prompt.as_deref(),
            Some("You are an expert systems engineer.")
        );
        assert_eq!(assembled.retrieved_memories.len(), 1);
        assert_eq!(assembled.recent_turns.len(), 2);
        assert_eq!(assembled.recent_turns[0].role, MessageRole::User);
        assert_eq!(assembled.recent_turns[1].role, MessageRole::Assistant);
        assert!(assembled.total_tokens > 0);
    }

    #[tokio::test]
    async fn test_context_manager_token_budget_truncation() {
        let repo = SqliteMemoryRepository::new("sqlite::memory:")
            .await
            .expect("Failed to initialize in-memory SQLite");

        let session_id = repo
            .ensure_session("budget-user", None)
            .await
            .expect("Failed to ensure session");

        // Add 5 long turns
        for i in 1..=5 {
            repo.append_message(
                &session_id,
                MessageRole::User,
                &format!("User query {} with some additional text to take up tokens in the context window.", i),
            )
            .await
            .unwrap();
        }

        // Set tight token budget
        let ctx_manager = ContextManager::new(repo, 80, 20);
        let assembled = ctx_manager
            .assemble_context(&session_id, None, Vec::new())
            .await
            .expect("Failed to assemble context");

        // Truncation should allow only turns that fit
        assert!(assembled.recent_turns.len() < 5);
        assert!(assembled.total_tokens + ctx_manager.reserved_completion_tokens() <= ctx_manager.max_context_tokens());
    }
}
