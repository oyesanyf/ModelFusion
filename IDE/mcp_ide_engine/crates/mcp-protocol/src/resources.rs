use std::collections::{HashMap, HashSet};
use std::sync::Arc;
use async_trait::async_trait;
use dashmap::DashMap;
use parking_lot::RwLock;
use serde::{Deserialize, Serialize};
use thiserror::Error;

use crate::types::{
    Resource, ResourceContents, ResourceTemplate, TextResourceContents,
};

/// Errors arising during resource lookup, reading, or subscription.
#[derive(Debug, Error, Clone, Serialize, Deserialize)]
pub enum ResourceError {
    #[error("Resource not found for URI: '{0}'")]
    NotFound(String),

    #[error("Invalid resource URI: '{0}' ({1})")]
    InvalidUri(String, String),

    #[error("Resource read failed: '{0}'")]
    ReadFailed(String),

    #[error("Subscription not found for URI: '{0}'")]
    SubscriptionNotFound(String),

    #[error("Internal resource error: {0}")]
    Internal(String),
}

/// Helper for matching and extracting variables from RFC 6570 style URI templates (e.g. `workspace://files/{path}`).
#[derive(Debug, Clone)]
pub struct UriTemplate {
    pub raw_template: String,
    prefix_pattern: Vec<PatternSegment>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
enum PatternSegment {
    Literal(String),
    Variable(String),
}

impl UriTemplate {
    pub fn new(template: impl Into<String>) -> Self {
        let raw_template = template.into();
        let mut prefix_pattern = Vec::new();

        let mut rest = raw_template.as_str();
        while !rest.is_empty() {
            if let Some(open_idx) = rest.find('{') {
                if open_idx > 0 {
                    prefix_pattern.push(PatternSegment::Literal(rest[..open_idx].to_string()));
                }
                let after_open = &rest[open_idx + 1..];
                if let Some(close_idx) = after_open.find('}') {
                    let var_name = &after_open[..close_idx];
                    prefix_pattern.push(PatternSegment::Variable(var_name.to_string()));
                    rest = &after_open[close_idx + 1..];
                } else {
                    prefix_pattern.push(PatternSegment::Literal(rest[open_idx..].to_string()));
                    break;
                }
            } else {
                prefix_pattern.push(PatternSegment::Literal(rest.to_string()));
                break;
            }
        }

        Self {
            raw_template,
            prefix_pattern,
        }
    }

    /// Matches a concrete URI against this template and extracts variable values.
    pub fn match_uri(&self, uri: &str) -> Option<HashMap<String, String>> {
        let mut variables = HashMap::new();
        let mut current = uri;

        for (i, segment) in self.prefix_pattern.iter().enumerate() {
            match segment {
                PatternSegment::Literal(lit) => {
                    if let Some(stripped) = current.strip_prefix(lit) {
                        current = stripped;
                    } else {
                        return None;
                    }
                }
                PatternSegment::Variable(var) => {
                    // Look at the next literal segment, if any
                    let next_literal = self.prefix_pattern.get(i + 1).and_then(|seg| match seg {
                        PatternSegment::Literal(s) => Some(s.as_str()),
                        _ => None,
                    });

                    if let Some(next_lit) = next_literal {
                        if let Some(pos) = current.find(next_lit) {
                            let val = &current[..pos];
                            variables.insert(var.clone(), val.to_string());
                            current = &current[pos..];
                        } else {
                            return None;
                        }
                    } else {
                        // Last variable segment captures all remaining URI characters
                        variables.insert(var.clone(), current.to_string());
                        current = "";
                    }
                }
            }
        }

        if current.is_empty() {
            Some(variables)
        } else {
            None
        }
    }
}

/// Trait for dynamic resource providers (e.g., workspace files, live telemetry).
#[async_trait]
pub trait DynamicResourceProvider: Send + Sync + 'static {
    fn template(&self) -> ResourceTemplate;
    
    async fn read(
        &self,
        uri: &str,
        variables: HashMap<String, String>,
    ) -> Result<Vec<ResourceContents>, ResourceError>;
}

/// Subscription manager tracking clients subscribed to resource updates.
#[derive(Default)]
pub struct SubscriptionManager {
    subscriptions: DashMap<String, RwLock<HashSet<String>>>,
}

impl SubscriptionManager {
    pub fn new() -> Self {
        Self {
            subscriptions: DashMap::new(),
        }
    }

    /// Subscribes a subscriber ID to a resource URI.
    pub fn subscribe(&self, uri: &str, subscriber_id: &str) {
        let entry = self
            .subscriptions
            .entry(uri.to_string())
            .or_insert_with(|| RwLock::new(HashSet::new()));
        entry.write().insert(subscriber_id.to_string());
    }

    /// Unsubscribes a subscriber ID from a resource URI.
    pub fn unsubscribe(&self, uri: &str, subscriber_id: &str) -> bool {
        if let Some(entry) = self.subscriptions.get(uri) {
            let mut set = entry.write();
            let removed = set.remove(subscriber_id);
            removed
        } else {
            false
        }
    }

    /// Checks if a resource URI has active subscribers.
    pub fn is_subscribed(&self, uri: &str) -> bool {
        self.subscriptions
            .get(uri)
            .map(|entry| !entry.read().is_empty())
            .unwrap_or(false)
    }

    /// Returns all subscriber IDs for a given resource URI.
    pub fn get_subscribers(&self, uri: &str) -> Vec<String> {
        self.subscriptions
            .get(uri)
            .map(|entry| entry.read().iter().cloned().collect())
            .unwrap_or_default()
    }
}

/// Lock-free Resource Registry holding static resources and dynamic URI template providers.
#[derive(Default, Clone)]
pub struct ResourceRegistry {
    static_resources: Arc<DashMap<String, (Resource, ResourceContents)>>,
    dynamic_providers: Arc<RwLock<Vec<(UriTemplate, Arc<dyn DynamicResourceProvider>)>>>,
    subscriptions: Arc<SubscriptionManager>,
}

impl ResourceRegistry {
    pub fn new() -> Self {
        Self {
            static_resources: Arc::new(DashMap::new()),
            dynamic_providers: Arc::new(RwLock::new(Vec::new())),
            subscriptions: Arc::new(SubscriptionManager::new()),
        }
    }

    /// Registers a static in-memory resource.
    pub fn register_static(&self, resource: Resource, contents: ResourceContents) {
        self.static_resources.insert(resource.uri.clone(), (resource, contents));
    }

    /// Registers a static text resource helper.
    pub fn register_static_text(
        &self,
        uri: impl Into<String>,
        name: impl Into<String>,
        description: Option<String>,
        mime_type: Option<String>,
        text: impl Into<String>,
    ) {
        let uri_str = uri.into();
        let text_str = text.into();
        let mime = mime_type.clone().unwrap_or_else(|| "text/plain".to_string());

        let res = Resource {
            uri: uri_str.clone(),
            name: name.into(),
            description,
            mime_type: Some(mime.clone()),
            size: Some(text_str.len() as u64),
        };

        let content = ResourceContents::Text(TextResourceContents {
            uri: uri_str,
            mime_type: Some(mime),
            text: text_str,
        });

        self.register_static(res, content);
    }

    /// Registers a dynamic resource provider.
    pub fn register_dynamic(&self, provider: Arc<dyn DynamicResourceProvider>) {
        let tmpl = provider.template();
        let matcher = UriTemplate::new(tmpl.uri_template.clone());
        self.dynamic_providers.write().push((matcher, provider));
    }

    /// Lists all static resources.
    pub fn list_resources(&self) -> Vec<Resource> {
        self.static_resources
            .iter()
            .map(|entry| entry.value().0.clone())
            .collect()
    }

    /// Alias for list_resources.
    pub fn list(&self) -> Vec<Resource> {
        self.list_resources()
    }

    /// Lists all dynamic resource templates.
    pub fn list_templates(&self) -> Vec<ResourceTemplate> {
        self.dynamic_providers
            .read()
            .iter()
            .map(|(_, p)| p.template())
            .collect()
    }

    /// Reads a resource by URI (resolves static first, then matches dynamic templates).
    pub async fn read(&self, uri: &str) -> Result<Vec<ResourceContents>, ResourceError> {
        // 1. Check static resources
        if let Some(entry) = self.static_resources.get(uri) {
            return Ok(vec![entry.value().1.clone()]);
        }

        // 2. Check dynamic providers
        let providers = self.dynamic_providers.read().clone();
        for (matcher, provider) in providers {
            if let Some(vars) = matcher.match_uri(uri) {
                return provider.read(uri, vars).await;
            }
        }

        Err(ResourceError::NotFound(uri.to_string()))
    }

    /// Returns the subscription manager.
    pub fn subscriptions(&self) -> &Arc<SubscriptionManager> {
        &self.subscriptions
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_uri_template_matching() {
        let tmpl = UriTemplate::new("workspace://files/{path}");
        let vars = tmpl.match_uri("workspace://files/src/main.rs").unwrap();
        assert_eq!(vars.get("path").unwrap(), "src/main.rs");

        let tmpl2 = UriTemplate::new("sysinfo://{category}/{metric}");
        let vars2 = tmpl2.match_uri("sysinfo://cpu/usage").unwrap();
        assert_eq!(vars2.get("category").unwrap(), "cpu");
        assert_eq!(vars2.get("metric").unwrap(), "usage");

        assert!(tmpl2.match_uri("other://cpu/usage").is_none());
    }

    #[tokio::test]
    async fn test_resource_registry_static_and_subscriptions() {
        let registry = ResourceRegistry::new();
        registry.register_static_text(
            "test://sample.txt",
            "Sample Text",
            Some("A sample file".to_string()),
            Some("text/plain".to_string()),
            "Hello World Content",
        );

        assert_eq!(registry.list_resources().len(), 1);

        let contents = registry.read("test://sample.txt").await.unwrap();
        assert_eq!(contents.len(), 1);
        match &contents[0] {
            ResourceContents::Text(t) => assert_eq!(t.text, "Hello World Content"),
            _ => panic!("Expected Text contents"),
        }

        // Test subscriptions
        registry.subscriptions().subscribe("test://sample.txt", "client-1");
        assert!(registry.subscriptions().is_subscribed("test://sample.txt"));
        assert_eq!(registry.subscriptions().get_subscribers("test://sample.txt"), vec!["client-1"]);

        registry.subscriptions().unsubscribe("test://sample.txt", "client-1");
        assert!(!registry.subscriptions().is_subscribed("test://sample.txt"));
    }
}
