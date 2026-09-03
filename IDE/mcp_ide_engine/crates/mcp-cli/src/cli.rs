//! Clap v4 Command-Line Interface definitions and argument specifications

use clap::{Args, Parser, Subcommand, ValueEnum};
use mcp_core::registry::TaskPriority;
use std::net::SocketAddr;
use std::path::PathBuf;

/// Root command-line structure for MCP IDE Engine
#[derive(Debug, Parser)]
#[command(
    name = "mcp-ide",
    about = "High-Performance Multithreaded Rust CLI & IDE Engine with Native MCP and Dynamic Resource Allocation",
    version = "0.1.0",
    author = "MCP IDE Engine Contributors"
)]
pub struct Cli {
    /// Emit structured JSON output for all commands
    #[arg(long, global = true)]
    pub json: bool,

    /// Increase logging verbosity (-v, -vv)
    #[arg(short, long, action = clap::ArgAction::Count, global = true)]
    pub verbose: u8,

    /// Number of async worker threads (defaults to num_cpus)
    #[arg(short = 'w', long, global = true)]
    pub workers: Option<usize>,

    /// Number of CPU compute worker threads in Rayon pool
    #[arg(long, global = true)]
    pub compute_workers: Option<usize>,

    #[command(subcommand)]
    pub command: Option<Commands>,
}

#[derive(Debug, Subcommand)]
pub enum Commands {
    /// Execute a command or workflow through the multithreaded priority engine
    Run(RunArgs),

    /// Model Context Protocol (MCP) server, client, tools, resources, and prompts
    Mcp(McpArgs),

    /// Hardware telemetry inspection, GPU detection, and model memory allocation
    Resource(ResourceArgs),

    /// Launch interactive 5-tab Ratatui Terminal IDE
    Tui(TuiArgs),

    /// Launch embedded Axum REST API, SSE, WebSocket, and Web UI server
    Serve(ServeArgs),

    /// Start interactive Reedline REPL shell
    Repl(ReplArgs),

    /// Run quick internal microbenchmark and latency verification
    Bench(BenchArgs),
}

#[derive(Debug, Args)]
pub struct RunArgs {
    /// Name of registered command to execute
    pub name: String,

    /// Command arguments in JSON format
    #[arg(short, long, default_value = "{}")]
    pub args: String,

    /// Task execution priority
    #[arg(short, long, value_enum, default_value_t = PriorityArg::Normal)]
    pub priority: PriorityArg,

    /// Do not wait for completion; return immediately with task ID
    #[arg(short, long)]
    pub detach: bool,

    /// Maximum timeout in seconds
    #[arg(short, long)]
    pub timeout: Option<u64>,
}

#[derive(Debug, Copy, Clone, PartialEq, Eq, ValueEnum)]
pub enum PriorityArg {
    Critical,
    High,
    Normal,
    Low,
    Background,
}

impl From<PriorityArg> for TaskPriority {
    fn from(p: PriorityArg) -> Self {
        match p {
            PriorityArg::Critical => TaskPriority::Critical,
            PriorityArg::High => TaskPriority::High,
            PriorityArg::Normal => TaskPriority::Normal,
            PriorityArg::Low => TaskPriority::Low,
            PriorityArg::Background => TaskPriority::Background,
        }
    }
}

#[derive(Debug, Args)]
pub struct McpArgs {
    #[command(subcommand)]
    pub action: McpSubcommands,
}

#[derive(Debug, Subcommand)]
pub enum McpSubcommands {
    /// List, inspect, or invoke MCP tools
    Tools(McpToolsArgs),

    /// List, inspect, or read MCP static and dynamic resources
    Resources(McpResourcesArgs),

    /// List or render MCP prompt templates
    Prompts(McpPromptsArgs),

    /// Run engine as an MCP Server exposing tools over Stdio or SSE
    Serve(McpServeArgs),

    /// Connect to an external MCP server as a client
    Client(McpClientArgs),
}

#[derive(Debug, Args)]
pub struct McpToolsArgs {
    #[command(subcommand)]
    pub action: McpToolsAction,
}

#[derive(Debug, Subcommand)]
pub enum McpToolsAction {
    /// List all registered MCP tools
    List,

    /// Call an MCP tool by name
    Call {
        /// Name of tool
        name: String,
        /// JSON input parameters
        #[arg(short, long, default_value = "{}")]
        args: String,
    },
}

#[derive(Debug, Args)]
pub struct McpResourcesArgs {
    #[command(subcommand)]
    pub action: McpResourcesAction,
}

#[derive(Debug, Subcommand)]
pub enum McpResourcesAction {
    /// List all registered resources
    List,

    /// Read resource content at specified URI
    Read {
        /// Resource URI (e.g. metrics://engine/status)
        uri: String,
    },
}

#[derive(Debug, Args)]
pub struct McpPromptsArgs {
    #[command(subcommand)]
    pub action: McpPromptsAction,
}

#[derive(Debug, Subcommand)]
pub enum McpPromptsAction {
    /// List all registered prompt templates
    List,

    /// Render a prompt template with arguments
    Get {
        /// Name of prompt
        name: String,
        /// JSON arguments for prompt interpolation
        #[arg(short, long, default_value = "{}")]
        args: String,
    },
}

#[derive(Debug, Args)]
pub struct McpServeArgs {
    /// Run in Stdio line-delimited mode (standard MCP transport)
    #[arg(long, default_value_t = true)]
    pub stdio: bool,

    /// Port for SSE transport server (if not stdio)
    #[arg(long)]
    pub sse_port: Option<u16>,
}

#[derive(Debug, Args)]
pub struct McpClientArgs {
    /// Command line to launch external MCP server process over stdio
    #[arg(short, long)]
    pub command: Option<String>,

    /// SSE URL to connect to external MCP server
    #[arg(short, long)]
    pub url: Option<String>,
}

#[derive(Debug, Args)]
pub struct ResourceArgs {
    #[command(subcommand)]
    pub action: ResourceSubcommands,
}

#[derive(Debug, Subcommand)]
pub enum ResourceSubcommands {
    /// View real-time CPU, RAM, and GPU hardware metrics
    Status,

    /// Recommend optimal model tier (Small, Medium, Large, Cloud) based on available RAM/VRAM
    Recommend {
        /// Context length in tokens (default: 4096)
        #[arg(short, long, default_value_t = 4096)]
        context: usize,
    },

    /// Calculate layer offload distribution for given model and available VRAM
    Offload {
        /// Available VRAM in gigabytes
        #[arg(long)]
        vram_gb: Option<f64>,

        /// Model ID to calculate (e.g. llama-3-8b-instruct-q4)
        #[arg(long, default_value = "llama-3-8b-instruct-q4")]
        model: String,
    },
}

#[derive(Debug, Args)]
pub struct TuiArgs {
    /// TUI refresh rate in milliseconds (default: 100ms)
    #[arg(short, long, default_value_t = 100)]
    pub tick_rate_ms: u64,
}

#[derive(Debug, Args)]
pub struct ServeArgs {
    /// Listening address for HTTP server
    #[arg(short, long, default_value = "127.0.0.1:3000")]
    pub addr: SocketAddr,
}

#[derive(Debug, Args)]
pub struct ReplArgs {
    /// Optional command history file path
    #[arg(long)]
    pub history_file: Option<PathBuf>,
}

#[derive(Debug, Args)]
pub struct BenchArgs {
    /// Number of iterations for internal dispatch benchmark
    #[arg(short, long, default_value_t = 1000)]
    pub iterations: usize,
}
