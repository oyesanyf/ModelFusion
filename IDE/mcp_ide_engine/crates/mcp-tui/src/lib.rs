//! # MCP TUI Dashboard
//!
//! High-performance interactive 5-tab terminal user interface for the MCP IDE Engine.
//!
//! Tabs:
//! 1. **Dashboard**: Live system gauges (CPU, RAM, VRAM), engine metrics, and active task overview.
//! 2. **Tasks & Threads**: Interactive task table, worker thread assignments, and cancellation controls.
//! 3. **Telemetry**: CPU load history sparkline, memory breakdown, and GPU layer offload calculator.
//! 4. **MCP Tools & Prompts**: Tool discovery catalog, JSON Schema inspector, and execution interface.
//! 5. **Logs & Output**: Real-time ANSI log stream with severity filtering and auto-scroll.

pub mod app;
pub mod event;
pub mod ui;

pub use app::{App, AppTab, LogEntry, LogLevel};
pub use event::{AppEvent, EventHandler};

use crossterm::{
    event::{DisableMouseCapture, EnableMouseCapture},
    execute,
    terminal::{disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen},
};
use ratatui::{backend::CrosstermBackend, Terminal};
use std::io::{self, stdout};
use std::sync::Arc;
use std::time::Duration;

/// Launch interactive TUI session with default terminal
pub async fn run_tui(mut app: App, tick_rate: Duration) -> io::Result<()> {
    // Setup terminal
    enable_raw_mode()?;
    let mut stdout = stdout();
    execute!(stdout, EnterAlternateScreen, EnableMouseCapture)?;
    let backend = CrosstermBackend::new(stdout);
    let mut terminal = Terminal::new(backend)?;

    // Setup event handler
    let event_bus_rx = if let Some(ref disp) = app.dispatcher {
        disp.telemetry().event_bus.subscribe()
    } else {
        tokio::sync::broadcast::channel(16).1
    };

    let resource_rx = if let Some(ref mon) = app.resource_monitor {
        mon.subscribe()
    } else {
        tokio::sync::watch::channel(mcp_resource::telemetry::SystemSnapshot::default()).1
    };

    let mut events = EventHandler::new(tick_rate, event_bus_rx, resource_rx);

    // Main event loop
    while app.running {
        terminal.draw(|f| ui::draw(f, &mut app))?;

        if let Some(event) = events.next().await {
            match event {
                AppEvent::Key(key) => app.handle_key(key),
                AppEvent::Tick => {}
                AppEvent::Engine(eng_ev) => app.handle_engine_event(eng_ev),
                AppEvent::Resource(snap) => app.update_resource_snapshot(snap),
                AppEvent::Log(msg) => app.add_log(LogLevel::Info, "app", &msg),
                AppEvent::Resize(..) => {}
                AppEvent::Mouse(..) => {}
            }
        }
    }

    // Restore terminal
    disable_raw_mode()?;
    execute!(
        terminal.backend_mut(),
        LeaveAlternateScreen,
        DisableMouseCapture
    )?;
    terminal.show_cursor()?;

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crossterm::event::{KeyCode, KeyEvent, KeyModifiers};
    use mcp_core::registry::{CommandRegistry, TaskDispatcher, TaskPriority};
    use mcp_core::runtime::{EngineRuntime, EngineRuntimeConfig};
    use mcp_core::scheduler::MultiLaneScheduler;
    use mcp_core::telemetry::EngineTelemetry;
    use mcp_protocol::server::McpServer;
    use mcp_protocol::types::CallToolResult;
    use ratatui::backend::TestBackend;
    use serde_json::json;

    fn setup_test_engine() -> (Arc<TaskDispatcher>, Arc<McpServer>) {
        let telemetry = Arc::new(EngineTelemetry::new());
        let config = EngineRuntimeConfig::new().worker_threads(2).compute_threads(1);
        let runtime = Arc::new(EngineRuntime::new(config).unwrap());
        let scheduler = Arc::new(MultiLaneScheduler::new(telemetry.clone()));
        let registry = Arc::new(CommandRegistry::new());

        registry
            .register_fn(
                "test_cmd",
                "Test command",
                "general",
                TaskPriority::Normal,
                |_ctx, _args| async move {
                    Ok(mcp_core::registry::TaskOutput::success(json!({"status": "ok"})))
                },
            )
            .unwrap();

        let dispatcher = TaskDispatcher::new(registry, scheduler, runtime, telemetry, 2);

        let server = McpServer::new("test-server", "1.0.0");
        server
            .tools()
            .register_fn(
                "echo",
                Some("Echo tool".to_string()),
                json!({ "type": "object" }),
                |_ctx, _args| async move { Ok(CallToolResult::text("echoed")) },
            )
            .unwrap();

        (dispatcher, Arc::new(server))
    }

    #[tokio::test]
    async fn test_tui_state_and_tab_navigation() {
        let mut app = App::new();
        assert_eq!(app.tab, AppTab::Dashboard);

        // Tab cycling
        app.handle_key(KeyEvent::new(KeyCode::Tab, KeyModifiers::NONE));
        assert_eq!(app.tab, AppTab::Tasks);

        app.handle_key(KeyEvent::new(KeyCode::Tab, KeyModifiers::NONE));
        assert_eq!(app.tab, AppTab::Telemetry);

        app.handle_key(KeyEvent::new(KeyCode::Tab, KeyModifiers::NONE));
        assert_eq!(app.tab, AppTab::McpCatalog);

        app.handle_key(KeyEvent::new(KeyCode::Tab, KeyModifiers::NONE));
        assert_eq!(app.tab, AppTab::Logs);

        app.handle_key(KeyEvent::new(KeyCode::Tab, KeyModifiers::NONE));
        assert_eq!(app.tab, AppTab::Dashboard);

        // Direct numeric jump
        app.handle_key(KeyEvent::new(KeyCode::Char('3'), KeyModifiers::NONE));
        assert_eq!(app.tab, AppTab::Telemetry);

        app.handle_key(KeyEvent::new(KeyCode::Char('1'), KeyModifiers::NONE));
        assert_eq!(app.tab, AppTab::Dashboard);
    }

    #[tokio::test]
    async fn test_tui_rendering_headless_all_tabs() {
        let (dispatcher, server) = setup_test_engine();
        let mut app = App::new()
            .with_dispatcher(dispatcher.clone())
            .with_mcp_server(server);

        // Dispatch a test command
        let _h = dispatcher.dispatch("test_cmd", json!({}), None).unwrap();

        app.add_log(LogLevel::Info, "test", "Initialization complete");
        app.add_log(LogLevel::Warn, "test", "Warning sample");
        app.add_log(LogLevel::Error, "test", "Error sample");

        let backend = TestBackend::new(120, 40);
        let mut terminal = Terminal::new(backend).unwrap();

        // Render each tab
        for tab in AppTab::all() {
            app.tab = *tab;
            terminal.draw(|f| ui::draw(f, &mut app)).unwrap();
        }

        // Render modals
        app.show_help = true;
        terminal.draw(|f| ui::draw(f, &mut app)).unwrap();
        app.show_help = false;

        app.show_tool_popup = true;
        terminal.draw(|f| ui::draw(f, &mut app)).unwrap();
        app.show_tool_popup = false;

        assert!(app.running);
        app.handle_key(KeyEvent::new(KeyCode::Char('q'), KeyModifiers::NONE));
        assert!(!app.running);
    }

    #[tokio::test]
    async fn test_tui_log_filtering_and_auto_scroll() {
        let mut app = App::new();
        app.add_log(LogLevel::Info, "kernel", "Booting kernel");
        app.add_log(LogLevel::Error, "kernel", "Failure occurred");

        assert_eq!(app.log_entries.len(), 2);
        assert!(app.auto_scroll_logs);

        // Toggle auto-scroll with 'a' on logs tab
        app.tab = AppTab::Logs;
        app.handle_key(KeyEvent::new(KeyCode::Char('a'), KeyModifiers::NONE));
        assert!(!app.auto_scroll_logs);

        // Cycle filter with 'l'
        app.handle_key(KeyEvent::new(KeyCode::Char('l'), KeyModifiers::NONE));
        assert_eq!(app.log_level_filter, Some(LogLevel::Info));
    }
}
