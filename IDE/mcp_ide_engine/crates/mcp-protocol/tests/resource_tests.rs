use std::collections::HashMap;
use std::sync::Arc;
use async_trait::async_trait;
use mcp_protocol::client::McpClient;
use mcp_protocol::resources::{DynamicResourceProvider, ResourceError};
use mcp_protocol::server::McpServer;
use mcp_protocol::transport::ChannelTransport;
use mcp_protocol::types::*;

struct DynamicWorkspaceProvider;

#[async_trait]
impl DynamicResourceProvider for DynamicWorkspaceProvider {
    fn template(&self) -> ResourceTemplate {
        ResourceTemplate {
            uri_template: "workspace://files/{path}".to_string(),
            name: "Dynamic Workspace File Provider".to_string(),
            description: Some("Provides content for workspace files".to_string()),
            mime_type: Some("text/plain".to_string()),
        }
    }

    async fn read(
        &self,
        uri: &str,
        variables: HashMap<String, String>,
    ) -> Result<Vec<ResourceContents>, ResourceError> {
        let path = variables
            .get("path")
            .ok_or_else(|| ResourceError::InvalidUri(uri.to_string(), "Missing path".to_string()))?;

        Ok(vec![ResourceContents::Text(TextResourceContents {
            uri: uri.to_string(),
            mime_type: Some("text/plain".to_string()),
            text: format!("Content of file at '{}'", path),
        })])
    }
}

#[tokio::test]
async fn test_resources_static_and_dynamic_provider() {
    let server = McpServer::new("resource-server", "1.0.0");

    // Static resource
    server.resources().register_static_text(
        "sysinfo://cpu",
        "CPU Metrics",
        Some("Live CPU metrics".to_string()),
        Some("application/json".to_string()),
        "{\"cores\": 16, \"usage\": 12.5}",
    );

    // Dynamic resource provider
    server.resources().register_dynamic(Arc::new(DynamicWorkspaceProvider));

    let (client_transport, server_transport) = ChannelTransport::pair(32);
    let server_clone = server.clone();
    tokio::spawn(async move {
        let _ = server_clone.serve(server_transport).await;
    });

    let client = McpClient::connect(client_transport, "resource-client", "1.0.0");
    client.initialize(ClientCapabilities::default()).await.unwrap();

    // 1. List static resources
    let res_list = client.list_resources(None).await.unwrap();
    assert_eq!(res_list.resources.len(), 1);
    assert_eq!(res_list.resources[0].uri, "sysinfo://cpu");

    // 2. List resource templates
    let tmpl_list = client.list_resource_templates(None).await.unwrap();
    assert_eq!(tmpl_list.resource_templates.len(), 1);
    assert_eq!(
        tmpl_list.resource_templates[0].uri_template,
        "workspace://files/{path}"
    );

    // 3. Read static resource
    let static_read = client.read_resource("sysinfo://cpu").await.unwrap();
    assert_eq!(static_read.contents.len(), 1);
    match &static_read.contents[0] {
        ResourceContents::Text(t) => assert!(t.text.contains("\"cores\": 16")),
        _ => panic!("Expected text resource contents"),
    }

    // 4. Read dynamic resource
    let dynamic_read = client
        .read_resource("workspace://files/src/main.rs")
        .await
        .unwrap();
    assert_eq!(dynamic_read.contents.len(), 1);
    match &dynamic_read.contents[0] {
        ResourceContents::Text(t) => {
            assert_eq!(t.text, "Content of file at 'src/main.rs'");
        }
        _ => panic!("Expected text resource contents"),
    }

    // 5. Read non-existent resource
    let missing_read = client.read_resource("unknown://uri").await;
    assert!(missing_read.is_err());

    // 6. Subscriptions
    client.subscribe_resource("sysinfo://cpu").await.unwrap();
    assert!(server.resources().subscriptions().is_subscribed("sysinfo://cpu"));

    client.unsubscribe_resource("sysinfo://cpu").await.unwrap();
    assert!(!server.resources().subscriptions().is_subscribed("sysinfo://cpu"));

    client.close().await.unwrap();
}
