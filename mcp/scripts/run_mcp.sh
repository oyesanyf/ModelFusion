#!/usr/bin/env bash
# ModelFusion Universal MCP Server Bash Launcher
# Runs ModelFusion Master CLI in Model Context Protocol (MCP) stdio mode

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Discover ModelFusion Master CLI Binary
CLI_BIN=""
if [ -f "$REPO_ROOT/target/release/cli" ]; then
    CLI_BIN="$REPO_ROOT/target/release/cli"
elif command -v cli &>/dev/null; then
    CLI_BIN="$(command -v cli)"
elif [ -f "$HOME/.local/bin/cli" ]; then
    CLI_BIN="$HOME/.local/bin/cli"
fi

if [ -z "$CLI_BIN" ]; then
    echo "[ERROR] ModelFusion Master CLI (cli) not found. Compile with 'cargo build --release --bin cli'." >&2
    exit 1
fi

# Discover Database Path
DB_ARG=()
if [ -f "$REPO_ROOT/IDE/db/hf_models.db" ]; then
    DB_ARG=(--db-path "$REPO_ROOT/IDE/db/hf_models.db")
fi

exec "$CLI_BIN" --mcp "${DB_ARG[@]}" "$@"
