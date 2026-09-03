use std::collections::HashMap;
use std::future::Future;
use std::sync::Arc;
use async_trait::async_trait;
use dashmap::DashMap;
use serde::{Deserialize, Serialize};
use thiserror::Error;

use crate::types::{
    Content, GetPromptResult, Prompt, PromptArgument, PromptMessage, Role,
};

/// Errors arising during prompt lookup, validation, or generation.
#[derive(Debug, Error, Clone, Serialize, Deserialize)]
pub enum PromptError {
    #[error("Prompt '{0}' not found in registry")]
    NotFound(String),

    #[error("Missing required prompt argument '{0}' for prompt '{1}'")]
    MissingRequiredArgument(String, String),

    #[error("Prompt execution failed: {0}")]
    ExecutionFailed(String),

    #[error("Internal prompt error: {0}")]
    Internal(String),
}

/// Trait implemented by executable prompt handlers.
#[async_trait]
pub trait PromptHandler: Send + Sync + 'static {
    async fn render(
        &self,
        arguments: Option<HashMap<String, String>>,
    ) -> Result<GetPromptResult, PromptError>;
}

/// Static template prompt handler that performs `{{var}}` parameter interpolation.
#[derive(Clone)]
pub struct TemplatePromptHandler {
    description: Option<String>,
    arguments_meta: Vec<PromptArgument>,
    template_messages: Vec<(Role, String)>,
}

impl TemplatePromptHandler {
    pub fn new(
        description: Option<String>,
        arguments_meta: Vec<PromptArgument>,
        template_messages: Vec<(Role, String)>,
    ) -> Self {
        Self {
            description,
            arguments_meta,
            template_messages,
        }
    }
}

#[async_trait]
impl PromptHandler for TemplatePromptHandler {
    async fn render(
        &self,
        arguments: Option<HashMap<String, String>>,
    ) -> Result<GetPromptResult, PromptError> {
        let args = arguments.unwrap_or_default();

        // 1. Validate required arguments
        for arg_meta in &self.arguments_meta {
            if arg_meta.required.unwrap_or(false) && !args.contains_key(&arg_meta.name) {
                return Err(PromptError::MissingRequiredArgument(
                    arg_meta.name.clone(),
                    self.description.clone().unwrap_or_default(),
                ));
            }
        }

        // 2. Interpolate template messages
        let mut messages = Vec::with_capacity(self.template_messages.len());
        for (role, template_text) in &self.template_messages {
            let mut interpolated = template_text.clone();
            for (key, val) in &args {
                let placeholder = format!("{{{{{}}}}}", key);
                interpolated = interpolated.replace(&placeholder, val);
            }
            messages.push(PromptMessage {
                role: *role,
                content: Content::text(interpolated),
            });
        }

        Ok(GetPromptResult {
            description: self.description.clone(),
            messages,
        })
    }
}

/// Dynamic closure-based prompt handler.
pub struct FnPromptHandler<F> {
    f: F,
}

impl<F> FnPromptHandler<F> {
    pub fn new(f: F) -> Self {
        Self { f }
    }
}

#[async_trait]
impl<F, Fut> PromptHandler for FnPromptHandler<F>
where
    F: Fn(Option<HashMap<String, String>>) -> Fut + Send + Sync + 'static,
    Fut: Future<Output = Result<GetPromptResult, PromptError>> + Send + 'static,
{
    async fn render(
        &self,
        arguments: Option<HashMap<String, String>>,
    ) -> Result<GetPromptResult, PromptError> {
        (self.f)(arguments).await
    }
}

/// Complete registered prompt definition.
#[derive(Clone)]
pub struct PromptDefinition {
    pub prompt: Prompt,
    pub handler: Arc<dyn PromptHandler>,
}

/// Lock-free registry for MCP prompt templates.
#[derive(Default, Clone)]
pub struct PromptRegistry {
    prompts: Arc<DashMap<String, PromptDefinition>>,
}

impl PromptRegistry {
    pub fn new() -> Self {
        Self {
            prompts: Arc::new(DashMap::new()),
        }
    }

    /// Registers a templated prompt with string message templates.
    pub fn register_template(
        &self,
        name: impl Into<String>,
        description: Option<String>,
        arguments: Vec<PromptArgument>,
        template_messages: Vec<(Role, String)>,
    ) {
        let name_str = name.into();
        let prompt = Prompt {
            name: name_str.clone(),
            description: description.clone(),
            arguments: Some(arguments.clone()),
        };

        let handler = Arc::new(TemplatePromptHandler::new(
            description,
            arguments,
            template_messages,
        ));

        let def = PromptDefinition { prompt, handler };
        self.prompts.insert(name_str, def);
    }

    /// Registers a custom prompt handler.
    pub fn register_handler(&self, prompt: Prompt, handler: Arc<dyn PromptHandler>) {
        let name = prompt.name.clone();
        let def = PromptDefinition { prompt, handler };
        self.prompts.insert(name, def);
    }

    /// Lists all registered prompts.
    pub fn list(&self) -> Vec<Prompt> {
        self.prompts
            .iter()
            .map(|entry| entry.value().prompt.clone())
            .collect()
    }

    /// Retrieves and renders a prompt by name.
    pub async fn get(
        &self,
        name: &str,
        arguments: Option<HashMap<String, String>>,
    ) -> Result<GetPromptResult, PromptError> {
        let def = self
            .prompts
            .get(name)
            .ok_or_else(|| PromptError::NotFound(name.to_string()))?;
        def.handler.render(arguments).await
    }

    /// Alias for get / render prompt
    pub async fn render(
        &self,
        name: &str,
        arguments: Option<HashMap<String, String>>,
    ) -> Result<GetPromptResult, PromptError> {
        self.get(name, arguments).await
    }

    /// Returns the number of registered prompts.
    pub fn len(&self) -> usize {
        self.prompts.len()
    }

    pub fn is_empty(&self) -> bool {
        self.prompts.is_empty()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_prompt_templating_and_validation() {
        let registry = PromptRegistry::new();

        registry.register_template(
            "code_review",
            Some("Review code snippet".to_string()),
            vec![
                PromptArgument {
                    name: "language".to_string(),
                    description: Some("Target programming language".to_string()),
                    required: Some(true),
                },
                PromptArgument {
                    name: "code".to_string(),
                    description: Some("Source code to review".to_string()),
                    required: Some(true),
                },
            ],
            vec![
                (Role::User, "Please review this {{language}} code:\n{{code}}".to_string()),
            ],
        );

        assert_eq!(registry.len(), 1);

        // Valid arguments
        let mut args = HashMap::new();
        args.insert("language".to_string(), "Rust".to_string());
        args.insert("code".to_string(), "fn main() {}".to_string());

        let res = registry.get("code_review", Some(args)).await.unwrap();
        assert_eq!(res.messages.len(), 1);
        assert_eq!(res.messages[0].role, Role::User);
        assert_eq!(
            res.messages[0].content.as_text(),
            Some("Please review this Rust code:\nfn main() {}")
        );

        // Missing required argument
        let mut invalid_args = HashMap::new();
        invalid_args.insert("language".to_string(), "Rust".to_string());
        let err = registry.get("code_review", Some(invalid_args)).await;
        assert!(err.is_err());
    }
}
