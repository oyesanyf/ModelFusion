#!/usr/bin/env python3
"""
ModelFusion MCP Test Client (JSON-RPC 2.0 stdio transport)
Tests the MCP server implementation by spawning `cli.exe --mcp`.
"""

import os
import sys
import json
import time
import subprocess
import threading

# Force UTF-8 output encoding for Windows terminal compatibility
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

CLI_BINARY = r"D:\harfile\ModelFusion\IDE\bin\cli.exe"
DB_PATH = r"C:\Users\oyesa\.hugos-ide\db\hf_models.db"

class MCPClient:
    def __init__(self, cli_path: str, db_path: str):
        self.cli_path = cli_path
        self.db_path = db_path
        self.process = None
        self.request_id = 0

    def start(self):
        cmd = [self.cli_path, "--mcp", "--db-path", self.db_path]
        print(f"[START] Spawning MCP Server: {' '.join(cmd)}")
        
        self.process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            bufsize=1
        )

        # Start stderr listener thread to avoid buffer blocking
        stderr_thread = threading.Thread(target=self._listen_stderr, daemon=True)
        stderr_thread.start()
        time.sleep(0.5)

    def _listen_stderr(self):
        if not self.process or not self.process.stderr:
            return
        for line in self.process.stderr:
            print(f"  [MCP Server stderr] {line.strip()}", file=sys.stderr)

    def send_request(self, method: str, params: dict = None) -> dict:
        self.request_id += 1
        req = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method,
            "params": params or {}
        }
        json_str = json.dumps(req)
        print(f"\n[REQ {self.request_id}] Sending Method: {method}")
        
        try:
            self.process.stdin.write(json_str + "\n")
            self.process.stdin.flush()
        except BrokenPipeError:
            print("[ERROR] Pipe broken. MCP server process exited.")
            return {}

        # Read response line from stdout
        response_line = self.process.stdout.readline()
        if not response_line:
            print("[WARN] Received empty response line from stdout.")
            return {}

        try:
            resp = json.loads(response_line)
            print(f"[RESP {self.request_id}] Result:")
            print(json.dumps(resp, indent=2))
            return resp
        except json.JSONDecodeError as e:
            print(f"[ERROR] JSON Decode Error: {e} | Raw line: {response_line.strip()}")
            return {}

    def stop(self):
        if self.process:
            print("\n[STOP] Terminating MCP Server process...")
            try:
                self.process.terminate()
                self.process.wait(timeout=3)
            except Exception:
                self.process.kill()
            print("[STOP] MCP Server process stopped.")

def main():
    if not os.path.exists(CLI_BINARY):
        print(f"[ERROR] CLI binary not found at {CLI_BINARY}")
        sys.exit(1)

    client = MCPClient(CLI_BINARY, DB_PATH)
    try:
        client.start()

        # Step 1: Handshake / Initialize
        print("\n--- Step 1: Initialize Handshake ---")
        client.send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "ModelFusion-TestClient", "version": "1.0.0"}
        })

        # Step 2: List Available Tools
        print("\n--- Step 2: List Tools ---")
        client.send_request("tools/list")

        # Step 3: Call Tool 'get_system_info'
        print("\n--- Step 3: Call Tool 'get_system_info' ---")
        client.send_request("tools/call", {
            "name": "get_system_info",
            "arguments": {}
        })

        # Step 4: Call Tool 'get_database_stats'
        print("\n--- Step 4: Call Tool 'get_database_stats' ---")
        client.send_request("tools/call", {
            "name": "get_database_stats",
            "arguments": {}
        })

        # Step 5: Call Tool 'text_classification'
        print("\n--- Step 5: Call Tool 'text_classification' ---")
        client.send_request("tools/call", {
            "name": "text_classification",
            "arguments": {"text": "ModelFusion provides high performance AI models."}
        })

    finally:
        client.stop()

if __name__ == "__main__":
    main()
