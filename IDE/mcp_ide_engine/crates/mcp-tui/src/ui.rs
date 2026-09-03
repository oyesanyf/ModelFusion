//! Rendering engine and layout widgets for Ratatui TUI

use crate::app::{App, AppTab, LogLevel};
use mcp_resource::selector::calculate_layer_offload;
use ratatui::{
    layout::{Alignment, Constraint, Direction, Layout, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{
        Block, BorderType, Borders, Cell, Clear, Gauge, List, ListItem, Paragraph, Row,
        Sparkline, Table, Tabs, Wrap,
    },
    Frame,
};

/// Main draw dispatcher for Frame
pub fn draw(f: &mut Frame, app: &mut App) {
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(3), // Top tab header
            Constraint::Min(0),    // Main workspace
            Constraint::Length(3), // Bottom status / command bar
        ])
        .split(f.area());

    render_header(f, app, chunks[0]);

    match app.tab {
        AppTab::Dashboard => render_dashboard(f, app, chunks[1]),
        AppTab::Tasks => render_tasks(f, app, chunks[1]),
        AppTab::Telemetry => render_telemetry(f, app, chunks[1]),
        AppTab::McpCatalog => render_mcp_catalog(f, app, chunks[1]),
        AppTab::Logs => render_logs(f, app, chunks[1]),
    }

    render_status_bar(f, app, chunks[2]);

    // Modals
    if app.show_help {
        render_help_popup(f, f.area());
    }
    if app.show_tool_popup {
        render_tool_popup(f, app, f.area());
    }
}

/// Render Top Navigation Bar
fn render_header(f: &mut Frame, app: &App, area: Rect) {
    let titles: Vec<Line> = AppTab::all()
        .iter()
        .map(|t| {
            let (first, rest) = t.title().split_at(3);
            Line::from(vec![
                Span::styled(first, Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
                Span::styled(rest, Style::default().fg(Color::White)),
            ])
        })
        .collect();

    let tabs = Tabs::new(titles)
        .block(
            Block::default()
                .borders(Borders::ALL)
                .title(" MCP IDE ENGINE v0.1.0 ")
                .title_alignment(Alignment::Left)
                .border_type(BorderType::Rounded)
                .border_style(Style::default().fg(Color::Cyan)),
        )
        .select(app.tab as usize)
        .style(Style::default().fg(Color::DarkGray))
        .highlight_style(
            Style::default()
                .fg(Color::Green)
                .add_modifier(Modifier::BOLD)
                .bg(Color::Rgb(30, 40, 50)),
        );

    f.render_widget(tabs, area);
}

/// Render Tab 0: Dashboard
fn render_dashboard(f: &mut Frame, app: &App, area: Rect) {
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(8),  // System Gauges
            Constraint::Length(7),  // Core Metrics & Sizing
            Constraint::Min(0),     // Active Tasks Preview & Logs Preview
        ])
        .split(area);

    // 1. Gauges Row
    let gauge_chunks = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([
            Constraint::Percentage(33),
            Constraint::Percentage(33),
            Constraint::Percentage(34),
        ])
        .split(chunks[0]);

    // CPU Gauge
    let cpu_pct = app.system_snapshot.cpu.global_cpu_usage_pct.clamp(0.0, 100.0) as u16;
    let cpu_gauge = Gauge::default()
        .block(
            Block::default()
                .title(format!(
                    " CPU Usage ({:.1}%) - {} Cores ",
                    app.system_snapshot.cpu.global_cpu_usage_pct,
                    app.system_snapshot.cpu.logical_core_count
                ))
                .borders(Borders::ALL)
                .border_type(BorderType::Rounded)
                .border_style(Style::default().fg(Color::Cyan)),
        )
        .gauge_style(
            Style::default()
                .fg(if cpu_pct > 80 {
                    Color::Red
                } else if cpu_pct > 50 {
                    Color::Yellow
                } else {
                    Color::Green
                })
                .bg(Color::Rgb(25, 25, 35)),
        )
        .percent(cpu_pct);
    f.render_widget(cpu_gauge, gauge_chunks[0]);

    // RAM Gauge
    let ram_total = app.system_snapshot.memory.total_ram_bytes.max(1);
    let ram_used = app.system_snapshot.memory.used_ram_bytes;
    let ram_pct = ((ram_used as f64 / ram_total as f64) * 100.0).clamp(0.0, 100.0) as u16;
    let ram_used_gb = ram_used as f64 / (1024.0 * 1024.0 * 1024.0);
    let ram_total_gb = ram_total as f64 / (1024.0 * 1024.0 * 1024.0);

    let ram_gauge = Gauge::default()
        .block(
            Block::default()
                .title(format!(" System RAM ({:.1}/{:.1} GB) ", ram_used_gb, ram_total_gb))
                .borders(Borders::ALL)
                .border_type(BorderType::Rounded)
                .border_style(Style::default().fg(Color::Magenta)),
        )
        .gauge_style(
            Style::default()
                .fg(if ram_pct > 85 { Color::Red } else { Color::Magenta })
                .bg(Color::Rgb(25, 25, 35)),
        )
        .percent(ram_pct);
    f.render_widget(ram_gauge, gauge_chunks[1]);

    // GPU / VRAM Gauge
    if let Some(gpu) = app.system_snapshot.gpus.first() {
        let vram_total = gpu.total_vram_bytes.max(1);
        let vram_used = gpu.used_vram_bytes;
        let vram_pct = ((vram_used as f64 / vram_total as f64) * 100.0).clamp(0.0, 100.0) as u16;
        let vram_used_gb = vram_used as f64 / (1024.0 * 1024.0 * 1024.0);
        let vram_total_gb = vram_total as f64 / (1024.0 * 1024.0 * 1024.0);

        let vram_gauge = Gauge::default()
            .block(
                Block::default()
                    .title(format!(" GPU VRAM: {} ({:.1}/{:.1} GB) ", gpu.name, vram_used_gb, vram_total_gb))
                    .borders(Borders::ALL)
                    .border_type(BorderType::Rounded)
                    .border_style(Style::default().fg(Color::Yellow)),
            )
            .gauge_style(
                Style::default()
                    .fg(Color::Yellow)
                    .bg(Color::Rgb(25, 25, 35)),
            )
            .percent(vram_pct);
        f.render_widget(vram_gauge, gauge_chunks[2]);
    } else {
        let no_gpu = Paragraph::new("No dedicated GPU detected (Running CPU compute)")
            .block(
                Block::default()
                    .title(" GPU Telemetry ")
                    .borders(Borders::ALL)
                    .border_type(BorderType::Rounded),
            )
            .style(Style::default().fg(Color::DarkGray));
        f.render_widget(no_gpu, gauge_chunks[2]);
    }

    // 2. Metrics & Engine Stats
    let stats_chunks = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([Constraint::Percentage(50), Constraint::Percentage(50)])
        .split(chunks[1]);

    let tasks = app.get_tasks();
    let pending_count = tasks.iter().filter(|t| matches!(t.state, mcp_core::scheduler::TaskState::Queued)).count();
    let running_count = tasks.iter().filter(|t| matches!(t.state, mcp_core::scheduler::TaskState::Running)).count();

    let stats_text = vec![
        Line::from(vec![
            Span::styled("Active Worker Threads: ", Style::default().fg(Color::White)),
            Span::styled(format!("{}", app.system_snapshot.cpu.logical_core_count), Style::default().fg(Color::Green).add_modifier(Modifier::BOLD)),
            Span::raw(" | "),
            Span::styled("Running Tasks: ", Style::default().fg(Color::White)),
            Span::styled(format!("{}", running_count), Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)),
            Span::raw(" | "),
            Span::styled("Pending Queue: ", Style::default().fg(Color::White)),
            Span::styled(format!("{}", pending_count), Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
        ]),
        Line::from(vec![
            Span::styled("MCP Tools Registered: ", Style::default().fg(Color::White)),
            Span::styled(format!("{}", app.get_tools().len()), Style::default().fg(Color::LightBlue).add_modifier(Modifier::BOLD)),
            Span::raw(" | "),
            Span::styled("Engine Concurrency Mode: ", Style::default().fg(Color::White)),
            Span::styled("Tokio Work-Stealing + Rayon", Style::default().fg(Color::LightGreen)),
        ]),
    ];

    let stats_para = Paragraph::new(stats_text).block(
        Block::default()
            .title(" Engine Concurrency & Dispatch Status ")
            .borders(Borders::ALL)
            .border_type(BorderType::Rounded)
            .border_style(Style::default().fg(Color::Blue)),
    );
    f.render_widget(stats_para, stats_chunks[0]);

    // Model Sizing recommendation preview
    let model_fit_text = vec![
        Line::from(vec![
            Span::styled("Recommended Local Model: ", Style::default().fg(Color::White)),
            Span::styled(
                if ram_total_gb > 28.0 { "70B Q4_K_M (Large)" } else if ram_total_gb > 12.0 { "8B Q4_K_M (Medium)" } else { "3B Q4_K_M (Small)" },
                Style::default().fg(Color::Green).add_modifier(Modifier::BOLD)
            ),
        ]),
        Line::from(vec![
            Span::styled("Layer Offload Strategy: ", Style::default().fg(Color::White)),
            Span::styled("Dynamic VRAM Aware with 15% Headroom", Style::default().fg(Color::Yellow)),
        ]),
    ];
    let model_para = Paragraph::new(model_fit_text).block(
        Block::default()
            .title(" Dynamic Model Allocator ")
            .borders(Borders::ALL)
            .border_type(BorderType::Rounded)
            .border_style(Style::default().fg(Color::LightYellow)),
    );
    f.render_widget(model_para, stats_chunks[1]);

    // 3. Lower Row: Live Activity Summary
    let lower_chunks = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([Constraint::Percentage(50), Constraint::Percentage(50)])
        .split(chunks[2]);

    // Task table snippet
    let rows: Vec<Row> = tasks
        .iter()
        .take(6)
        .map(|t| {
            let state_color = match t.state {
                mcp_core::scheduler::TaskState::Running => Color::Cyan,
                mcp_core::scheduler::TaskState::Queued | mcp_core::scheduler::TaskState::Scheduled => Color::Yellow,
                mcp_core::scheduler::TaskState::Completed => Color::Green,
                mcp_core::scheduler::TaskState::Failed | mcp_core::scheduler::TaskState::TimedOut => Color::Red,
                mcp_core::scheduler::TaskState::Cancelled => Color::DarkGray,
            };
            Row::new(vec![
                Cell::from(t.task_id.to_string()),
                Cell::from(t.command_name.clone()),
                Cell::from(format!("{:?}", t.priority)),
                Cell::from(Span::styled(format!("{:?}", t.state), Style::default().fg(state_color))),
            ])
        })
        .collect();

    let task_table = Table::new(
        rows,
        [
            Constraint::Length(8),
            Constraint::Percentage(40),
            Constraint::Percentage(25),
            Constraint::Percentage(25),
        ],
    )
    .header(
        Row::new(vec!["Task ID", "Command / Name", "Priority", "State"])
            .style(Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
    )
    .block(
        Block::default()
            .title(" Active Tasks Preview ")
            .borders(Borders::ALL)
            .border_type(BorderType::Rounded),
    );
    f.render_widget(task_table, lower_chunks[0]);

    // Recent logs snippet
    let log_items: Vec<ListItem> = app
        .log_entries
        .iter()
        .rev()
        .take(6)
        .map(|l| {
            let col = match l.level {
                LogLevel::Error => Color::Red,
                LogLevel::Warn => Color::Yellow,
                LogLevel::Info => Color::Green,
                LogLevel::Debug => Color::Cyan,
                LogLevel::Trace => Color::DarkGray,
            };
            ListItem::new(Line::from(vec![
                Span::styled(format!("[{}] ", l.timestamp), Style::default().fg(Color::DarkGray)),
                Span::styled(format!("[{}] ", l.level.as_str()), Style::default().fg(col)),
                Span::raw(l.message.clone()),
            ]))
        })
        .collect();

    let logs_list = List::new(log_items).block(
        Block::default()
            .title(" Recent Engine Logs ")
            .borders(Borders::ALL)
            .border_type(BorderType::Rounded),
    );
    f.render_widget(logs_list, lower_chunks[1]);
}

/// Render Tab 1: Tasks & Threads
fn render_tasks(f: &mut Frame, app: &App, area: Rect) {
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([Constraint::Min(0), Constraint::Length(6)])
        .split(area);

    let tasks = app.get_tasks();
    let rows: Vec<Row> = tasks
        .iter()
        .enumerate()
        .map(|(idx, t)| {
            let is_selected = idx == app.selected_task_index;
            let state_color = match t.state {
                mcp_core::scheduler::TaskState::Running => Color::Cyan,
                mcp_core::scheduler::TaskState::Queued | mcp_core::scheduler::TaskState::Scheduled => Color::Yellow,
                mcp_core::scheduler::TaskState::Completed => Color::Green,
                mcp_core::scheduler::TaskState::Failed | mcp_core::scheduler::TaskState::TimedOut => Color::Red,
                mcp_core::scheduler::TaskState::Cancelled => Color::DarkGray,
            };

            let duration_str = format!("{:.2?}", std::time::Duration::from_micros(t.total_duration_us.unwrap_or(0)));
            let row = Row::new(vec![
                Cell::from(if is_selected { ">" } else { " " }),
                Cell::from(t.task_id.to_string()),
                Cell::from(t.command_name.clone()),
                Cell::from(format!("{:?}", t.priority)),
                Cell::from(Span::styled(format!("{:?}", t.state), Style::default().fg(state_color))),
                Cell::from("-".to_string()),
                Cell::from(duration_str.clone()),
            ]);

            if is_selected {
                row.style(Style::default().bg(Color::Rgb(40, 50, 60)).fg(Color::White).add_modifier(Modifier::BOLD))
            } else {
                row
            }
        })
        .collect();

    let table = Table::new(
        rows,
        [
            Constraint::Length(2),
            Constraint::Length(10),
            Constraint::Percentage(25),
            Constraint::Percentage(15),
            Constraint::Percentage(15),
            Constraint::Percentage(15),
            Constraint::Percentage(15),
        ],
    )
    .header(
        Row::new(vec!["", "Task ID", "Name / Command", "Priority", "Status", "Worker", "Elapsed"])
            .style(Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
    )
    .block(
        Block::default()
            .title(format!(" Task Registry (Total: {}) - [c]: Cancel Selected Task ", tasks.len()))
            .borders(Borders::ALL)
            .border_type(BorderType::Rounded)
            .border_style(Style::default().fg(Color::Cyan)),
    );
    f.render_widget(table, chunks[0]);

    // Detail box for selected task
    let detail_text = if let Some(t) = tasks.get(app.selected_task_index) {
        let duration_str = format!("{:.2?}", std::time::Duration::from_micros(t.total_duration_us.unwrap_or(0)));
        vec![
            Line::from(vec![
                Span::styled("Selected Task: ", Style::default().fg(Color::White).add_modifier(Modifier::BOLD)),
                Span::styled(format!("ID {} ({})", t.task_id, t.command_name), Style::default().fg(Color::Green)),
            ]),
            Line::from(vec![
                Span::styled("Status: ", Style::default().fg(Color::White)),
                Span::styled(format!("{:?}", t.state), Style::default().fg(Color::Yellow)),
                Span::raw(" | "),
                Span::styled("Priority Lane: ", Style::default().fg(Color::White)),
                Span::styled(format!("{:?}", t.priority), Style::default().fg(Color::Cyan)),
                Span::raw(" | "),
                Span::styled("Elapsed: ", Style::default().fg(Color::White)),
                Span::raw(duration_str),
            ]),
            Line::from(vec![
                Span::styled("Action: ", Style::default().fg(Color::White)),
                Span::styled("Press 'c' to send cooperative cancellation signal to this task.", Style::default().fg(Color::Red)),
            ]),
        ]
    } else {
        vec![Line::from("No tasks currently in scheduler queue.")]
    };

    let detail_para = Paragraph::new(detail_text).block(
        Block::default()
            .title(" Task Inspection ")
            .borders(Borders::ALL)
            .border_type(BorderType::Rounded),
    );
    f.render_widget(detail_para, chunks[1]);
}

/// Render Tab 2: Telemetry
fn render_telemetry(f: &mut Frame, app: &App, area: Rect) {
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(10), // CPU History sparkline
            Constraint::Min(0),     // Memory & GPU stats
        ])
        .split(area);

    // CPU Sparkline
    let sparkline = Sparkline::default()
        .block(
            Block::default()
                .title(format!(
                    " Real-Time CPU Load History (Last {} samples) ",
                    app.cpu_history.len()
                ))
                .borders(Borders::ALL)
                .border_type(BorderType::Rounded)
                .border_style(Style::default().fg(Color::Cyan)),
        )
        .data(&app.cpu_history)
        .style(Style::default().fg(Color::Green))
        .max(100);
    f.render_widget(sparkline, chunks[0]);

    let lower_chunks = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([Constraint::Percentage(50), Constraint::Percentage(50)])
        .split(chunks[1]);

    // Memory Breakdown
    let mem = &app.system_snapshot.memory;
    let total_gb = mem.total_ram_bytes as f64 / (1024.0 * 1024.0 * 1024.0);
    let used_gb = mem.used_ram_bytes as f64 / (1024.0 * 1024.0 * 1024.0);
    let free_gb = mem.available_ram_bytes as f64 / (1024.0 * 1024.0 * 1024.0);
    let swap_total_gb = mem.total_swap_bytes as f64 / (1024.0 * 1024.0 * 1024.0);
    let swap_used_gb = mem.used_swap_bytes as f64 / (1024.0 * 1024.0 * 1024.0);

    let mem_text = vec![
        Line::from(vec![
            Span::styled("Total Physical RAM: ", Style::default().fg(Color::White)),
            Span::styled(format!("{:.2} GB", total_gb), Style::default().fg(Color::Magenta).add_modifier(Modifier::BOLD)),
        ]),
        Line::from(vec![
            Span::styled("Used RAM: ", Style::default().fg(Color::White)),
            Span::styled(format!("{:.2} GB ({:.1}%)", used_gb, (used_gb / total_gb.max(0.1)) * 100.0), Style::default().fg(Color::Yellow)),
        ]),
        Line::from(vec![
            Span::styled("Available / Free: ", Style::default().fg(Color::White)),
            Span::styled(format!("{:.2} GB", free_gb), Style::default().fg(Color::Green)),
        ]),
        Line::from(vec![
            Span::styled("Swap Memory: ", Style::default().fg(Color::White)),
            Span::styled(format!("{:.2} / {:.2} GB", swap_used_gb, swap_total_gb), Style::default().fg(Color::DarkGray)),
        ]),
        Line::from(vec![
            Span::styled("Process RSS Memory: ", Style::default().fg(Color::White)),
            Span::styled(format!("{:.2} MB", app.system_snapshot.process.process_memory_bytes as f64 / (1024.0 * 1024.0)), Style::default().fg(Color::Cyan)),
        ]),
    ];

    let mem_para = Paragraph::new(mem_text).block(
        Block::default()
            .title(" Memory Telemetry & Pressure ")
            .borders(Borders::ALL)
            .border_type(BorderType::Rounded)
            .border_style(Style::default().fg(Color::Magenta)),
    );
    f.render_widget(mem_para, lower_chunks[0]);

    // GPU & Model Offloading
    let gpu_text = if let Some(gpu) = app.system_snapshot.gpus.first() {
        let v_total = gpu.total_vram_bytes as f64 / (1024.0 * 1024.0 * 1024.0);
        let v_used = gpu.used_vram_bytes as f64 / (1024.0 * 1024.0 * 1024.0);
        let v_free = gpu.free_vram_bytes as f64 / (1024.0 * 1024.0 * 1024.0);

        let plan_8b = calculate_layer_offload(
            &mcp_resource::selector::ModelSpec::llama_3_1_8b(),
            gpu.free_vram_bytes,
            4096,
            0.15,
        );

        vec![
            Line::from(vec![
                Span::styled("Primary GPU: ", Style::default().fg(Color::White)),
                Span::styled(gpu.name.clone(), Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
            ]),
            Line::from(vec![
                Span::styled("Backend Prober: ", Style::default().fg(Color::White)),
                Span::styled(format!("{:?}", gpu.detection_backend), Style::default().fg(Color::Cyan)),
                Span::raw(" | "),
                Span::styled("Driver: ", Style::default().fg(Color::White)),
                Span::styled(gpu.driver_version.clone().unwrap_or_else(|| "N/A".to_string()), Style::default().fg(Color::White)),
            ]),
            Line::from(vec![
                Span::styled("VRAM Total: ", Style::default().fg(Color::White)),
                Span::styled(format!("{:.2} GB", v_total), Style::default().fg(Color::Yellow)),
                Span::raw(" | "),
                Span::styled("Used: ", Style::default().fg(Color::White)),
                Span::styled(format!("{:.2} GB", v_used), Style::default().fg(Color::Red)),
                Span::raw(" | "),
                Span::styled("Free: ", Style::default().fg(Color::White)),
                Span::styled(format!("{:.2} GB", v_free), Style::default().fg(Color::Green)),
            ]),
            Line::from(vec![
                Span::styled("8B Model Offload Fit: ", Style::default().fg(Color::White)),
                Span::styled(format!("{}/{} layers offloaded to GPU", plan_8b.gpu_layers, plan_8b.total_layers), Style::default().fg(Color::LightGreen).add_modifier(Modifier::BOLD)),
            ]),
        ]
    } else {
        vec![
            Line::from("No hardware GPU acceleration detected."),
            Line::from("Model inference will utilize multithreaded CPU Rayon work-stealing pool."),
        ]
    };

    let gpu_para = Paragraph::new(gpu_text).block(
        Block::default()
            .title(" GPU Telemetry & VRAM Offloading ")
            .borders(Borders::ALL)
            .border_type(BorderType::Rounded)
            .border_style(Style::default().fg(Color::Yellow)),
    );
    f.render_widget(gpu_para, lower_chunks[1]);
}

/// Render Tab 3: MCP Catalog
fn render_mcp_catalog(f: &mut Frame, app: &App, area: Rect) {
    let chunks = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([Constraint::Percentage(40), Constraint::Percentage(60)])
        .split(area);

    let tools = app.get_tools();
    let items: Vec<ListItem> = tools
        .iter()
        .enumerate()
        .map(|(idx, t)| {
            let is_selected = idx == app.selected_tool_index;
            let style = if is_selected {
                Style::default()
                    .fg(Color::Yellow)
                    .bg(Color::Rgb(30, 45, 60))
                    .add_modifier(Modifier::BOLD)
            } else {
                Style::default().fg(Color::White)
            };

            let prefix = if is_selected { "> " } else { "  " };
            ListItem::new(Line::from(vec![
                Span::styled(prefix, Style::default().fg(Color::Yellow)),
                Span::styled(t.name.clone(), style),
            ]))
        })
        .collect();

    let list = List::new(items).block(
        Block::default()
            .title(format!(" Registered Tools ({}) - [Enter]: View Schema ", tools.len()))
            .borders(Borders::ALL)
            .border_type(BorderType::Rounded)
            .border_style(Style::default().fg(Color::LightBlue)),
    );
    f.render_widget(list, chunks[0]);

    // Tool Detail Inspector
    let detail_text = if let Some(tool) = tools.get(app.selected_tool_index) {
        let schema_str = serde_json::to_string_pretty(&tool.input_schema)
            .unwrap_or_else(|_| "Invalid schema".to_string());

        vec![
            Line::from(vec![
                Span::styled("Tool Name: ", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
                Span::styled(tool.name.clone(), Style::default().fg(Color::Green).add_modifier(Modifier::BOLD)),
            ]),
            Line::from(vec![
                Span::styled("Description: ", Style::default().fg(Color::White)),
                Span::styled(tool.description.clone().unwrap_or_else(|| "No description".to_string()), Style::default().fg(Color::LightCyan)),
            ]),
            Line::from(""),
            Line::from(Span::styled("Input JSON Schema:", Style::default().fg(Color::Magenta).add_modifier(Modifier::UNDERLINED))),
            Line::from(schema_str),
        ]
    } else {
        vec![Line::from("No MCP tools registered. Connect an MCP server or register internal tools.")]
    };

    let detail_para = Paragraph::new(detail_text)
        .wrap(Wrap { trim: false })
        .block(
            Block::default()
                .title(" Tool Specification & Schema Inspector ")
                .borders(Borders::ALL)
                .border_type(BorderType::Rounded),
        );
    f.render_widget(detail_para, chunks[1]);
}

/// Render Tab 4: Logs
fn render_logs(f: &mut Frame, app: &App, area: Rect) {
    let filtered_logs: Vec<&crate::app::LogEntry> = app
        .log_entries
        .iter()
        .filter(|l| {
            if let Some(filter) = app.log_level_filter {
                l.level == filter
            } else {
                true
            }
        })
        .collect();

    let items: Vec<ListItem> = filtered_logs
        .iter()
        .enumerate()
        .map(|(idx, l)| {
            let is_selected = idx == app.selected_log_index;
            let col = match l.level {
                LogLevel::Error => Color::Red,
                LogLevel::Warn => Color::Yellow,
                LogLevel::Info => Color::Green,
                LogLevel::Debug => Color::Cyan,
                LogLevel::Trace => Color::DarkGray,
            };

            let line = Line::from(vec![
                Span::styled(format!("[{}] ", l.timestamp), Style::default().fg(Color::DarkGray)),
                Span::styled(format!("[{:<5}] ", l.level.as_str()), Style::default().fg(col).add_modifier(Modifier::BOLD)),
                Span::styled(format!("{:<10} ", l.target), Style::default().fg(Color::LightBlue)),
                Span::raw(l.message.clone()),
            ]);

            let item = ListItem::new(line);
            if is_selected && !app.auto_scroll_logs {
                item.style(Style::default().bg(Color::Rgb(40, 40, 50)))
            } else {
                item
            }
        })
        .collect();

    let filter_label = app
        .log_level_filter
        .map(|l| l.as_str())
        .unwrap_or("ALL");

    let title = format!(
        " System Event Log (Total: {}) | Auto-Scroll: {} | Filter [l]: {} ",
        app.log_entries.len(),
        if app.auto_scroll_logs { "ON" } else { "OFF" },
        filter_label
    );

    let list = List::new(items).block(
        Block::default()
            .title(title)
            .borders(Borders::ALL)
            .border_type(BorderType::Rounded)
            .border_style(Style::default().fg(Color::Cyan)),
    );
    f.render_widget(list, area);
}

/// Render Bottom Status / Command Line Bar
fn render_status_bar(f: &mut Frame, app: &App, area: Rect) {
    let content = if app.is_input_mode {
        Line::from(vec![
            Span::styled(":", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
            Span::styled(&app.input_buffer, Style::default().fg(Color::White)),
            Span::styled("_", Style::default().fg(Color::Green).add_modifier(Modifier::SLOW_BLINK)),
        ])
    } else {
        let msg = app.status_message.as_deref().unwrap_or("Ready.");
        Line::from(vec![
            Span::styled(" [Tab] ", Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)),
            Span::raw("Next Tab | "),
            Span::styled("[1-5] ", Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)),
            Span::raw("Jump | "),
            Span::styled("[:] ", Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)),
            Span::raw("Command | "),
            Span::styled("[?] ", Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)),
            Span::raw("Help | "),
            Span::styled("[q] ", Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)),
            Span::raw("Quit  |  "),
            Span::styled(msg, Style::default().fg(Color::LightGreen)),
        ])
    };

    let p = Paragraph::new(content).block(
        Block::default()
            .borders(Borders::ALL)
            .border_type(BorderType::Rounded)
            .border_style(Style::default().fg(Color::DarkGray)),
    );
    f.render_widget(p, area);
}

/// Helper to render centered modal popup
fn centered_rect(percent_x: u16, percent_y: u16, r: Rect) -> Rect {
    let popup_layout = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Percentage((100 - percent_y) / 2),
            Constraint::Percentage(percent_y),
            Constraint::Percentage((100 - percent_y) / 2),
        ])
        .split(r);

    Layout::default()
        .direction(Direction::Horizontal)
        .constraints([
            Constraint::Percentage((100 - percent_x) / 2),
            Constraint::Percentage(percent_x),
            Constraint::Percentage((100 - percent_x) / 2),
        ])
        .split(popup_layout[1])[1]
}

/// Help Modal Popup
fn render_help_popup(f: &mut Frame, area: Rect) {
    let popup_area = centered_rect(60, 60, area);
    f.render_widget(Clear, popup_area);

    let text = vec![
        Line::from(Span::styled(" MCP IDE ENGINE KEYBOARD SHORTCUTS ", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD))),
        Line::from(""),
        Line::from("  Tab / Shift-Tab : Cycle through tabs"),
        Line::from("  1 - 5           : Direct jump to specific tab"),
        Line::from("  Up / Down (k/j) : Navigate tasks, tools, and log entries"),
        Line::from("  Enter           : Inspect details / trigger action"),
        Line::from("  c               : Cancel selected task (Tasks tab)"),
        Line::from("  a               : Toggle auto-scroll (Logs tab)"),
        Line::from("  l               : Cycle log severity filter (Logs tab)"),
        Line::from("  :               : Open CLI command prompt in TUI"),
        Line::from("  ?               : Toggle this help screen"),
        Line::from("  q / Ctrl-C      : Gracefully exit engine & TUI"),
        Line::from(""),
        Line::from(Span::styled("Press ESC, Enter, or '?' to close this dialog.", Style::default().fg(Color::Green))),
    ];

    let block = Block::default()
        .title(" Help & Keybindings ")
        .borders(Borders::ALL)
        .border_type(BorderType::Double)
        .border_style(Style::default().fg(Color::Yellow));

    let p = Paragraph::new(text).block(block).alignment(Alignment::Left);
    f.render_widget(p, popup_area);
}

/// Tool Detail Popup Modal
fn render_tool_popup(f: &mut Frame, app: &App, area: Rect) {
    let popup_area = centered_rect(70, 70, area);
    f.render_widget(Clear, popup_area);

    let tools = app.get_tools();
    let text = if let Some(tool) = tools.get(app.selected_tool_index) {
        let schema_str = serde_json::to_string_pretty(&tool.input_schema)
            .unwrap_or_else(|_| "Invalid schema".to_string());

        vec![
            Line::from(Span::styled(format!(" TOOL: {} ", tool.name), Style::default().fg(Color::Green).add_modifier(Modifier::BOLD))),
            Line::from(""),
            Line::from(format!("Description: {}", tool.description.as_deref().unwrap_or("None"))),
            Line::from(""),
            Line::from(Span::styled("Schema Definition:", Style::default().fg(Color::Yellow))),
            Line::from(schema_str),
            Line::from(""),
            Line::from(Span::styled("Press ESC or Enter to close", Style::default().fg(Color::DarkGray))),
        ]
    } else {
        vec![Line::from("No tool selected.")]
    };

    let block = Block::default()
        .title(" MCP Tool Specification ")
        .borders(Borders::ALL)
        .border_type(BorderType::Double)
        .border_style(Style::default().fg(Color::LightBlue));

    let p = Paragraph::new(text).wrap(Wrap { trim: false }).block(block);
    f.render_widget(p, popup_area);
}
