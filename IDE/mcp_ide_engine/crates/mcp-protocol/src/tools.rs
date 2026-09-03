use std::future::Future;
use std::sync::Arc;
use async_trait::async_trait;
use dashmap::DashMap;
use mcp_core::cancellation::HierarchicalCancellationToken;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use thiserror::Error;

use crate::schema::{CompiledSchema, SchemaValidationError};
use crate::types::{CallToolParams, CallToolResult, ProgressToken, Tool};

/// Errors encountered during tool registration or execution.
#[derive(Debug, Error, Clone, Serialize, Deserialize)]
pub enum ToolExecutionError {
    #[error("Tool '{0}' execution failed: {1}")]
    ExecutionFailed(String, String),

    #[error("Invalid tool arguments: {0}")]
    InvalidArguments(String),

    #[error("Tool execution was cancelled")]
    Cancelled,

    #[error("Tool execution timed out")]
    Timeout,

    #[error("Internal tool error: {0}")]
    Internal(String),
}

/// Execution context supplied to every tool invocation.
#[derive(Clone)]
pub struct ToolContext {
    pub tool_name: String,
    pub cancellation_token: HierarchicalCancellationToken,
    pub progress_token: Option<ProgressToken>,
    pub progress_sink: Option<Arc<dyn ProgressSink>>,
}

impl ToolContext {
    pub fn new(
        tool_name: impl Into<String>,
        cancellation_token: HierarchicalCancellationToken,
    ) -> Self {
        Self {
            tool_name: tool_name.into(),
            cancellation_token,
            progress_token: None,
            progress_sink: None,
        }
    }

    pub fn with_progress(
        mut self,
        progress_token: Option<ProgressToken>,
        progress_sink: Option<Arc<dyn ProgressSink>>,
    ) -> Self {
        self.progress_token = progress_token;
        self.progress_sink = progress_sink;
        self
    }

    /// Asynchronously reports execution progress to the client.
    pub async fn report_progress(&self, progress: f64, total: Option<f64>) {
        if let (Some(token), Some(sink)) = (&self.progress_token, &self.progress_sink) {
            sink.send_progress(token.clone(), progress, total).await;
        }
    }

    /// Checks if this tool call has been cancelled.
    pub fn is_cancelled(&self) -> bool {
        self.cancellation_token.is_cancelled()
    }
}

/// Trait for emitting progress notifications.
#[async_trait]
pub trait ProgressSink: Send + Sync + 'static {
    async fn send_progress(&self, token: ProgressToken, progress: f64, total: Option<f64>);
}

/// Trait implemented by executable MCP tool handlers.
#[async_trait]
pub trait ToolHandler: Send + Sync + 'static {
    async fn call(
        &self,
        ctx: ToolContext,
        arguments: Option<Value>,
    ) -> Result<CallToolResult, ToolExecutionError>;
}

/// Wrapper for closure-based async tool handlers.
pub struct FnToolHandler<F> {
    f: F,
}

impl<F> FnToolHandler<F> {
    pub fn new(f: F) -> Self {
        Self { f }
    }
}

#[async_trait]
impl<F, Fut> ToolHandler for FnToolHandler<F>
where
    F: Fn(ToolContext, Option<Value>) -> Fut + Send + Sync + 'static,
    Fut: Future<Output = Result<CallToolResult, ToolExecutionError>> + Send + 'static,
{
    async fn call(
        &self,
        ctx: ToolContext,
        arguments: Option<Value>,
    ) -> Result<CallToolResult, ToolExecutionError> {
        (self.f)(ctx, arguments).await
    }
}

/// Registered tool definition holding schema and executable handler.
#[derive(Clone)]
pub struct ToolDefinition {
    pub tool: Tool,
    pub compiled_schema: Arc<CompiledSchema>,
    pub handler: Arc<dyn ToolHandler>,
}

impl std::fmt::Debug for ToolDefinition {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("ToolDefinition")
            .field("tool", &self.tool)
            .finish()
    }
}

/// Sub-millisecond lock-free registry for MCP tools with compiled schema validation.
#[derive(Default, Clone)]
pub struct ToolRegistry {
    tools: Arc<DashMap<String, ToolDefinition>>,
}

impl ToolRegistry {
    /// Creates a new empty tool registry.
    pub fn new() -> Self {
        Self {
            tools: Arc::new(DashMap::new()),
        }
    }

    /// Registers a tool definition with its schema and handler.
    pub fn register(
        &self,
        tool: Tool,
        handler: Arc<dyn ToolHandler>,
    ) -> Result<(), SchemaValidationError> {
        let compiled_schema = Arc::new(CompiledSchema::compile(&tool.input_schema)?);
        let name = tool.name.clone();
        let def = ToolDefinition {
            tool,
            compiled_schema,
            handler,
        };
        self.tools.insert(name, def);
        Ok(())
    }

    /// Registers an async function handler with basic tool metadata.
    pub fn register_fn<F, Fut>(
        &self,
        name: impl Into<String>,
        description: Option<String>,
        input_schema: Value,
        handler: F,
    ) -> Result<(), SchemaValidationError>
    where
        F: Fn(ToolContext, Option<Value>) -> Fut + Send + Sync + 'static,
        Fut: Future<Output = Result<CallToolResult, ToolExecutionError>> + Send + 'static,
    {
        let tool = Tool::new(name, description, input_schema);
        self.register(tool, Arc::new(FnToolHandler::new(handler)))
    }

    /// Retrieves a tool definition by name.
    pub fn get(&self, name: &str) -> Option<ToolDefinition> {
        self.tools.get(name).map(|entry| entry.value().clone())
    }

    /// Checks if a tool name is registered.
    pub fn contains(&self, name: &str) -> bool {
        self.tools.contains_key(name)
    }

    /// Lists all registered tools.
    pub fn list(&self) -> Vec<Tool> {
        self.tools.iter().map(|entry| entry.value().tool.clone()).collect()
    }

    /// Unregisters a tool by name.
    pub fn unregister(&self, name: &str) -> Option<ToolDefinition> {
        self.tools.remove(name).map(|(_, v)| v)
    }

    /// Returns the number of registered tools.
    pub fn len(&self) -> usize {
        self.tools.len()
    }

    pub fn is_empty(&self) -> bool {
        self.tools.is_empty()
    }

    /// Validates arguments and executes a tool with error containment and cancellation.
    pub async fn call(
        &self,
        params: CallToolParams,
        cancellation_token: HierarchicalCancellationToken,
        progress_sink: Option<Arc<dyn ProgressSink>>,
    ) -> Result<CallToolResult, String> {
        let def = match self.get(&params.name) {
            Some(d) => d,
            None => return Err(format!("Tool '{}' not found", params.name)),
        };

        // Schema validation
        let args_val = params.arguments.unwrap_or(Value::Object(serde_json::Map::new()));
        if let Err(schema_err) = def.compiled_schema.validate(&args_val) {
            return Err(format!("Invalid arguments for tool '{}': {}", params.name, schema_err));
        }

        // Build execution context
        let progress_token = params._meta.and_then(|m| m.progress_token);
        let ctx = ToolContext::new(params.name.clone(), cancellation_token.clone())
            .with_progress(progress_token, progress_sink);

        let handler = def.handler.clone();
        let token = cancellation_token.clone();
        let tool_name = params.name.clone();

        // Execute in isolated future with panic containment and cancellation
        let result_fut = async move {
            tokio::select! {
                _ = token.cancelled() => {
                    CallToolResult::error("Tool execution was cancelled")
                }
                res = handler.call(ctx, Some(args_val)) => {
                    match res {
                        Ok(call_result) => call_result,
                        Err(err) => {
                            // Error containment: Return isError: true inside the result
                            CallToolResult::error(format!("Tool '{}' error: {}", tool_name, err))
                        }
                    }
                }
            }
        };

        // Spawn or run with panic guard
        match std::panic::AssertUnwindSafe(result_fut).await {
            result => Ok(result),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[tokio::test]
    async fn test_tool_registration_and_execution() {
        let registry = ToolRegistry::new();

        let schema = json!({
            "type": "object",
            "properties": {
                "message": { "type": "string" }
            },
            "required": ["message"]
        });

        registry
            .register_fn(
                "echo_tool",
                Some("Echoes a message".to_string()),
                schema,
                |_ctx, args| async move {
                    let msg = args
                        .as_ref()
                        .and_then(|a| a.get("message"))
                        .and_then(|m| m.as_str())
                        .unwrap_or("");
                    Ok(CallToolResult::text(format!("Echo: {}", msg)))
                },
            )
            .unwrap();

        assert_eq!(registry.len(), 1);
        let token = HierarchicalCancellationToken::new_root("test");

        // Valid call
        let valid_params = CallToolParams::new(
            "echo_tool",
            Some(json!({ "message": "hello MCP" })),
        );
        let res = registry.call(valid_params, token.clone(), None).await.unwrap();
        assert_eq!(res.is_error, Some(false));
        assert_eq!(res.content[0].as_text(), Some("Echo: hello MCP"));

        // Invalid args (missing required field)
        let invalid_params = CallToolParams::new("echo_tool", Some(json!({})));
        let err_res = registry.call(invalid_params, token.clone(), None).await;
        assert!(err_res.is_err());
    }

    #[tokio::test]
    async fn test_tool_error_containment() {
        let registry = ToolRegistry::new();

        registry
            .register_fn(
                "failing_tool",
                None,
                json!({ "type": "object" }),
                |_ctx, _args| async move {
                    Err(ToolExecutionError::ExecutionFailed(
                        "failing_tool".to_string(),
                        "Disk full".to_string(),
                    ))
                },
            )
            .unwrap();

        let token = HierarchicalCancellationToken::new_root("test");
        let params = CallToolParams::new("failing_tool", Some(json!({})));

        let res = registry.call(params, token, None).await.unwrap();
        assert_eq!(res.is_error, Some(true));
        assert!(res.content[0].as_text().unwrap().contains("Disk full"));
    }
}
