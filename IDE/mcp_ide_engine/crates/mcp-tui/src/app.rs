//! TUI Application state machine and business logic

use crossterm::event::{KeyCode, KeyEvent, KeyModifiers};
use mcp_core::registry::{TaskDispatcher, TaskRecord};
use mcp_core::scheduler::TaskId;
use mcp_core::telemetry::EngineEvent;
use mcp_protocol::server::McpServer;
use mcp_protocol::types::Tool;
use mcp_resource::telemetry::{ResourceMonitor, SystemSnapshot};
use std::sync::Arc;
use std::time::SystemTime;

/// 5 Tab Navigation
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AppTab {
    Dashboard = 0,
    Tasks = 1,
    Telemetry = 2,
    McpCatalog = 3,
    Logs = 4,
}

impl AppTab {
    pub fn all() -> &'static [AppTab] {
        &[
            AppTab::Dashboard,
            AppTab::Tasks,
            AppTab::Telemetry,
            AppTab::McpCatalog,
            AppTab::Logs,
        ]
    }

    pub fn title(&self) -> &'static str {
        match self {
            AppTab::Dashboard => "1: Dashboard",
            AppTab::Tasks => "2: Tasks & Threads",
            AppTab::Telemetry => "3: Telemetry",
            AppTab::McpCatalog => "4: MCP Tools & Prompts",
            AppTab::Logs => "5: Logs & Output",
        }
    }

    pub fn next(&self) -> Self {
        match self {
            AppTab::Dashboard => AppTab::Tasks,
            AppTab::Tasks => AppTab::Telemetry,
            AppTab::Telemetry => AppTab::McpCatalog,
            AppTab::McpCatalog => AppTab::Logs,
            AppTab::Logs => AppTab::Dashboard,
        }
    }

    pub fn prev(&self) -> Self {
        match self {
            AppTab::Dashboard => AppTab::Logs,
            AppTab::Tasks => AppTab::Dashboard,
            AppTab::Telemetry => AppTab::Tasks,
            AppTab::McpCatalog => AppTab::Telemetry,
            AppTab::Logs => AppTab::McpCatalog,
        }
    }

    pub fn from_index(index: usize) -> Self {
        match index {
            0 => AppTab::Dashboard,
            1 => AppTab::Tasks,
            2 => AppTab::Telemetry,
            3 => AppTab::McpCatalog,
            4 => AppTab::Logs,
            _ => AppTab::Dashboard,
        }
    }
}

/// Log severity level
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LogLevel {
    Trace,
    Debug,
    Info,
    Warn,
    Error,
}

impl LogLevel {
    pub fn as_str(&self) -> &'static str {
        match self {
            LogLevel::Trace => "TRACE",
            LogLevel::Debug => "DEBUG",
            LogLevel::Info => "INFO",
            LogLevel::Warn => "WARN",
            LogLevel::Error => "ERROR",
        }
    }
}

/// Log buffer entry
#[derive(Debug, Clone)]
pub struct LogEntry {
    pub timestamp: String,
    pub level: LogLevel,
    pub target: String,
    pub message: String,
}

/// Main TUI Application State
pub struct App {
    /// Active selected tab
    pub tab: AppTab,
    /// Whether the TUI application is active
    pub running: bool,
    /// Core task dispatcher
    pub dispatcher: Option<Arc<TaskDispatcher>>,
    /// Resource telemetry monitor
    pub resource_monitor: Option<Arc<ResourceMonitor>>,
    /// MCP protocol server
    pub mcp_server: Option<Arc<McpServer>>,
    /// Cached latest system snapshot
    pub system_snapshot: SystemSnapshot,
    /// Historical CPU percentage (for sparkline / graphs)
    pub cpu_history: Vec<u64>,
    /// Historical RAM bytes used (MB/GB)
    pub ram_history: Vec<u64>,
    /// Historical VRAM bytes used
    pub vram_history: Vec<u64>,
    /// Stored log entries
    pub log_entries: Vec<LogEntry>,
    /// Selected index in Task list
    pub selected_task_index: usize,
    /// Selected index in MCP Tools list
    pub selected_tool_index: usize,
    /// Selected index in Logs list
    pub selected_log_index: usize,
    /// Whether log view auto-scrolls to bottom
    pub auto_scroll_logs: bool,
    /// Filter for log level (None = show all)
    pub log_level_filter: Option<LogLevel>,
    /// Show help popup modal
    pub show_help: bool,
    /// Show tool detail popup modal
    pub show_tool_popup: bool,
    /// Status message displayed at bottom bar
    pub status_message: Option<String>,
    /// Input mode or command buffer
    pub input_buffer: String,
    pub is_input_mode: bool,
}

impl App {
    /// Create new App instance with default state
    pub fn new() -> Self {
        Self {
            tab: AppTab::Dashboard,
            running: true,
            dispatcher: None,
            resource_monitor: None,
            mcp_server: None,
            system_snapshot: SystemSnapshot::default(),
            cpu_history: Vec::with_capacity(120),
            ram_history: Vec::with_capacity(120),
            vram_history: Vec::with_capacity(120),
            log_entries: Vec::new(),
            selected_task_index: 0,
            selected_tool_index: 0,
            selected_log_index: 0,
            auto_scroll_logs: true,
            log_level_filter: None,
            show_help: false,
            show_tool_popup: false,
            status_message: Some("Ready. Press '?' for help, Tab to switch views.".to_string()),
            input_buffer: String::new(),
            is_input_mode: false,
        }
    }

    /// Attach Core Dispatcher
    pub fn with_dispatcher(mut self, dispatcher: Arc<TaskDispatcher>) -> Self {
        self.dispatcher = Some(dispatcher);
        self
    }

    /// Attach Resource Monitor
    pub fn with_resource_monitor(mut self, monitor: Arc<ResourceMonitor>) -> Self {
        let snap = monitor.snapshot();
        self.system_snapshot = snap;
        self.resource_monitor = Some(monitor);
        self
    }

    /// Attach MCP Server
    pub fn with_mcp_server(mut self, server: Arc<McpServer>) -> Self {
        self.mcp_server = Some(server);
        self
    }

    /// Add a log entry
    pub fn add_log(&mut self, level: LogLevel, target: &str, message: &str) {
        let now = SystemTime::now()
            .duration_since(SystemTime::UNIX_EPOCH)
            .unwrap_or_default()
            .as_millis();
        let secs = now / 1000;
        let millis = now % 1000;
        let timestamp = format!("{}.{:03}", secs % 86400, millis);

        self.log_entries.push(LogEntry {
            timestamp,
            level,
            target: target.to_string(),
            message: message.to_string(),
        });

        if self.log_entries.len() > 1000 {
            self.log_entries.remove(0);
        }

        if self.auto_scroll_logs && !self.log_entries.is_empty() {
            self.selected_log_index = self.log_entries.len() - 1;
        }
    }

    /// Update resource snapshot and append history points
    pub fn update_resource_snapshot(&mut self, snap: SystemSnapshot) {
        self.cpu_history.push(snap.cpu.global_cpu_usage_pct as u64);
        if self.cpu_history.len() > 100 {
            self.cpu_history.remove(0);
        }

        let ram_used_mb = snap.memory.used_ram_bytes / (1024 * 1024);
        self.ram_history.push(ram_used_mb);
        if self.ram_history.len() > 100 {
            self.ram_history.remove(0);
        }

        if let Some(gpu) = snap.gpus.first() {
            let vram_used_mb = gpu.used_vram_bytes / (1024 * 1024);
            self.vram_history.push(vram_used_mb);
            if self.vram_history.len() > 100 {
                self.vram_history.remove(0);
            }
        }

        self.system_snapshot = snap;
    }

    /// Process engine event
    pub fn handle_engine_event(&mut self, event: EngineEvent) {
        match event {
            EngineEvent::TaskQueued { task_id, name, priority, .. } => {
                self.add_log(
                    LogLevel::Info,
                    "engine",
                    &format!("Task created: {} [{}] ({})", name, priority, task_id),
                );
            }
            EngineEvent::TaskStarted { task_id, dispatch_latency_us } => {
                self.add_log(
                    LogLevel::Debug,
                    "engine",
                    &format!("Task started in {}µs: ({})", dispatch_latency_us, task_id),
                );
            }
            EngineEvent::TaskCompleted { task_id, run_duration_us, total_duration_us: _ } => {
                self.add_log(
                    LogLevel::Info,
                    "engine",
                    &format!("Task completed in {}µs: ({})", run_duration_us, task_id),
                );
            }
            EngineEvent::TaskFailed { task_id, error, run_duration_us: _ } => {
                self.add_log(
                    LogLevel::Error,
                    "engine",
                    &format!("Task failed: ({}): {}", task_id, error),
                );
            }
            EngineEvent::TaskCancelled { task_id, stage } => {
                self.add_log(
                    LogLevel::Warn,
                    "engine",
                    &format!("Task cancelled at stage {}: ({})", stage, task_id),
                );
            }
            _ => {}
        }
    }

    /// Retrieve active task records from scheduler
    pub fn get_tasks(&self) -> Vec<TaskRecord> {
        if let Some(ref disp) = self.dispatcher {
            disp.list_task_records()
        } else {
            Vec::new()
        }
    }

    /// Retrieve registered MCP tools
    pub fn get_tools(&self) -> Vec<Tool> {
        if let Some(ref srv) = self.mcp_server {
            srv.tools().list()
        } else {
            Vec::new()
        }
    }

    /// Cancel selected task if possible
    pub fn cancel_selected_task(&mut self) {
        let tasks = self.get_tasks();
        if let Some(task) = tasks.get(self.selected_task_index) {
            let id = task.task_id;
            if let Some(ref disp) = self.dispatcher {
                let _ = disp.cancel_task(&id);
                self.status_message = Some(format!("Cancelled task {}", id));
                self.add_log(LogLevel::Warn, "user", &format!("User requested cancellation for task {}", id));
            }
        }
    }

    /// Handle key event
    pub fn handle_key(&mut self, key: KeyEvent) {
        if self.is_input_mode {
            match key.code {
                KeyCode::Esc => {
                    self.is_input_mode = false;
                    self.input_buffer.clear();
                }
                KeyCode::Enter => {
                    self.is_input_mode = false;
                    let input = std::mem::take(&mut self.input_buffer);
                    if !input.is_empty() {
                        self.execute_user_command(&input);
                    }
                }
                KeyCode::Backspace => {
                    self.input_buffer.pop();
                }
                KeyCode::Char(c) => {
                    self.input_buffer.push(c);
                }
                _ => {}
            }
            return;
        }

        // Popup dismiss
        if self.show_help {
            if matches!(key.code, KeyCode::Esc | KeyCode::Char('?') | KeyCode::Char('q') | KeyCode::Enter) {
                self.show_help = false;
            }
            return;
        }

        if self.show_tool_popup {
            if matches!(key.code, KeyCode::Esc | KeyCode::Char('q') | KeyCode::Enter) {
                self.show_tool_popup = false;
            }
            return;
        }

        match key.code {
            KeyCode::Char('q') | KeyCode::Esc => {
                self.running = false;
            }
            KeyCode::Char('c') if key.modifiers.contains(KeyModifiers::CONTROL) => {
                self.running = false;
            }
            KeyCode::Tab => {
                self.tab = self.tab.next();
            }
            KeyCode::BackTab => {
                self.tab = self.tab.prev();
            }
            KeyCode::Char('1') => self.tab = AppTab::Dashboard,
            KeyCode::Char('2') => self.tab = AppTab::Tasks,
            KeyCode::Char('3') => self.tab = AppTab::Telemetry,
            KeyCode::Char('4') => self.tab = AppTab::McpCatalog,
            KeyCode::Char('5') => self.tab = AppTab::Logs,
            KeyCode::Char('?') => {
                self.show_help = true;
            }
            KeyCode::Char(':') => {
                self.is_input_mode = true;
                self.input_buffer.clear();
            }
            KeyCode::Up | KeyCode::Char('k') => match self.tab {
                AppTab::Tasks => {
                    if self.selected_task_index > 0 {
                        self.selected_task_index -= 1;
                    }
                }
                AppTab::McpCatalog => {
                    if self.selected_tool_index > 0 {
                        self.selected_tool_index -= 1;
                    }
                }
                AppTab::Logs => {
                    self.auto_scroll_logs = false;
                    if self.selected_log_index > 0 {
                        self.selected_log_index -= 1;
                    }
                }
                _ => {}
            },
            KeyCode::Down | KeyCode::Char('j') => match self.tab {
                AppTab::Tasks => {
                    let count = self.get_tasks().len();
                    if count > 0 && self.selected_task_index + 1 < count {
                        self.selected_task_index += 1;
                    }
                }
                AppTab::McpCatalog => {
                    let count = self.get_tools().len();
                    if count > 0 && self.selected_tool_index + 1 < count {
                        self.selected_tool_index += 1;
                    }
                }
                AppTab::Logs => {
                    if !self.log_entries.is_empty() && self.selected_log_index + 1 < self.log_entries.len() {
                        self.selected_log_index += 1;
                    }
                }
                _ => {}
            },
            KeyCode::Char('c') if self.tab == AppTab::Tasks => {
                self.cancel_selected_task();
            }
            KeyCode::Enter if self.tab == AppTab::McpCatalog => {
                let tools = self.get_tools();
                if !tools.is_empty() && self.selected_tool_index < tools.len() {
                    self.show_tool_popup = true;
                }
            }
            KeyCode::Char('a') if self.tab == AppTab::Logs => {
                self.auto_scroll_logs = !self.auto_scroll_logs;
                self.status_message = Some(format!(
                    "Auto-scroll logs: {}",
                    if self.auto_scroll_logs { "ON" } else { "OFF" }
                ));
            }
            KeyCode::Char('l') if self.tab == AppTab::Logs => {
                self.log_level_filter = match self.log_level_filter {
                    None => Some(LogLevel::Info),
                    Some(LogLevel::Info) => Some(LogLevel::Warn),
                    Some(LogLevel::Warn) => Some(LogLevel::Error),
                    Some(LogLevel::Error) => Some(LogLevel::Debug),
                    Some(LogLevel::Debug) => None,
                    Some(LogLevel::Trace) => None,
                };
                self.status_message = Some(format!(
                    "Log filter: {:?}",
                    self.log_level_filter.map(|l| l.as_str()).unwrap_or("ALL")
                ));
            }
            _ => {}
        }
    }

    /// Execute a CLI command typed via ':'
    pub fn execute_user_command(&mut self, input: &str) {
        let parts: Vec<&str> = input.split_whitespace().collect();
        if parts.is_empty() {
            return;
        }

        let cmd = parts[0];
        match cmd {
            "quit" | "q" | "exit" => {
                self.running = false;
            }
            "clear" => {
                self.log_entries.clear();
                self.status_message = Some("Logs cleared".to_string());
            }
            "tab" if parts.len() > 1 => {
                if let Ok(idx) = parts[1].parse::<usize>() {
                    self.tab = AppTab::from_index(idx.saturating_sub(1));
                }
            }
            "run" if parts.len() > 1 => {
                let tool_name = parts[1];
                if let Some(ref disp) = self.dispatcher {
                    match disp.dispatch(tool_name, serde_json::json!({}), None) {
                        Ok(handle) => {
                            self.status_message = Some(format!("Dispatched task {}", handle.id()));
                            self.add_log(LogLevel::Info, "user", &format!("Dispatched command '{}' with task ID {}", tool_name, handle.id()));
                        }
                        Err(e) => {
                            self.status_message = Some(format!("Dispatch error: {}", e));
                            self.add_log(LogLevel::Error, "user", &format!("Failed to dispatch '{}': {}", tool_name, e));
                        }
                    }
                }
            }
            _ => {
                self.status_message = Some(format!("Unknown command: {}", cmd));
            }
        }
    }
}

impl Default for App {
    fn default() -> Self {
        Self::new()
    }
}
