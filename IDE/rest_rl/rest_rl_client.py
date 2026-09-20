#!/usr/bin/env python3
"""
HugOS ReST-RL / GRPO Client Shim (rest_rl_client.py)

Manages:
1. JSON-RPC 2.0 communication over TCP / Windows Named Pipe.
2. IdleActivityTracker: 45-second debounced state tracking (ACTIVE <-> IDLE)
   with instant preemption on user keystrokes / events.
3. Task enqueueing, status reporting, and diff/resolution extraction for IDE diff viewer.
"""

from __future__ import annotations

import os
import sys
import json
import time
import socket
import logging
import threading
from typing import Optional, Dict, Any, Callable, List

logger = logging.getLogger("rest_rl.client")


class RestRLClient:
    """Robust client communicating with rest_rl_daemon via JSON-RPC 2.0."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 45454,
        pipe_name: str = r"\\.\pipe\hugos_rest_rl_ipc",
        transport: str = "tcp",
        timeout: float = 10.0,
    ):
        self.host = host
        self.port = port
        self.pipe_name = pipe_name
        self.transport = transport
        self.timeout = timeout
        self._req_counter = 0
        self._lock = threading.Lock()

    def _next_id(self) -> int:
        with self._lock:
            self._req_counter += 1
            return self._req_counter

    def call(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Dispatches a JSON-RPC 2.0 call and returns the result."""
        req_id = self._next_id()
        payload = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params or {},
        }
        raw_req = json.dumps(payload) + "\n"

        if self.transport == "named_pipe" and sys.platform == "win32":
            return self._call_named_pipe(raw_req, req_id)
        else:
            return self._call_tcp(raw_req, req_id)

    def _call_tcp(self, raw_req: str, req_id: int) -> Dict[str, Any]:
        """Executes request over TCP socket."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(self.timeout)
                s.connect((self.host, self.port))
                s.sendall(raw_req.encode("utf-8"))

                buf = ""
                while "\n" not in buf:
                    chunk = s.recv(4096)
                    if not chunk:
                        break
                    buf += chunk.decode("utf-8", errors="replace")

                lines = buf.strip().splitlines()
                if not lines:
                    raise ConnectionError("Empty response from daemon")

                resp = json.loads(lines[0])
                if "error" in resp:
                    raise RuntimeError(f"RPC Error ({resp['error'].get('code')}): {resp['error'].get('message')}")
                return resp.get("result", {})
        except Exception as e:
            logger.debug("TCP RPC failed: %s", e)
            raise

    def _call_named_pipe(self, raw_req: str, req_id: int) -> Dict[str, Any]:
        """Executes request over Windows Named Pipe if configured with automatic fallback."""
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            GENERIC_READ = 0x80000000
            GENERIC_WRITE = 0x40000000
            OPEN_EXISTING = 3
            ERROR_PIPE_BUSY = 231

            h_pipe = kernel32.CreateFileW(
                self.pipe_name,
                GENERIC_READ | GENERIC_WRITE,
                0,
                None,
                OPEN_EXISTING,
                0,
                None,
            )
            if h_pipe == -1:
                err = kernel32.GetLastError()
                if err == ERROR_PIPE_BUSY:
                    if kernel32.WaitNamedPipeW(self.pipe_name, 3000):
                        h_pipe = kernel32.CreateFileW(
                            self.pipe_name,
                            GENERIC_READ | GENERIC_WRITE,
                            0,
                            None,
                            OPEN_EXISTING,
                            0,
                            None,
                        )
                if h_pipe == -1:
                    # Fallback to TCP if pipe creation fails
                    return self._call_tcp(raw_req, req_id)

            try:
                bytes_written = ctypes.c_ulong(0)
                bytes_read = ctypes.c_ulong(0)
                req_bytes = raw_req.encode("utf-8")

                kernel32.WriteFile(
                    h_pipe,
                    req_bytes,
                    len(req_bytes),
                    ctypes.byref(bytes_written),
                    None,
                )

                buf = ctypes.create_string_buffer(65536)
                success = kernel32.ReadFile(
                    h_pipe,
                    buf,
                    ctypes.sizeof(buf),
                    ctypes.byref(bytes_read),
                    None,
                )
                if not success or bytes_read.value == 0:
                    raise ConnectionError("Empty read from named pipe")

                raw_resp = buf.raw[:bytes_read.value].decode("utf-8", errors="replace").strip()
                resp = json.loads(raw_resp)
                if "error" in resp:
                    raise RuntimeError(f"Pipe RPC Error: {resp['error']}")
                return resp.get("result", {})
            finally:
                kernel32.CloseHandle(h_pipe)
        except Exception as e:
            logger.debug("Named pipe RPC failed, attempting TCP fallback: %s", e)
            return self._call_tcp(raw_req, req_id)

    # -------------------------------------------------------------------------
    # High-Level API Methods
    # -------------------------------------------------------------------------

    def notify_idle_start(self) -> Dict[str, Any]:
        """Informs daemon that the user has stopped typing (debounced idle)."""
        return self.call("ide/idle_start")

    def notify_idle_stop(self) -> Dict[str, Any]:
        """Instantly informs daemon that user resumed typing (active event)."""
        return self.call("ide/idle_stop")

    def enqueue_task(
        self,
        task_id: str,
        target_file: str,
        test_target: str,
        workspace_root: str,
        instruction: str = "",
        original_code: str = "",
        max_iterations: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Submits a failing test or code optimization job to the daemon."""
        return self.call(
            "agent/enqueue_task",
            {
                "task_id": task_id,
                "target_file": target_file,
                "test_target": test_target,
                "workspace_root": workspace_root,
                "instruction": instruction,
                "original_code": original_code,
                "max_iterations": max_iterations,
            },
        )

    def get_status(self) -> Dict[str, Any]:
        """Queries daemon state, hardware profile, queue length, and running task."""
        return self.call("agent/status")

    def get_result(self, task_id: str) -> Dict[str, Any]:
        """Retrieves candidate patch and verification reward for a completed task."""
        return self.call("agent/get_result", {"task_id": task_id})

    def poll_resolutions(self) -> List[Dict[str, Any]]:
        """Retrieves and acknowledges newly completed task resolutions for diff review."""
        res = self.call("agent/poll_resolutions")
        return res.get("resolutions", [])

    def shutdown_daemon(self) -> Dict[str, Any]:
        """Requests graceful daemon termination."""
        return self.call("system/shutdown")


class IdleActivityTracker:
    """
    Monitors user input activity (keystrokes, mouse, focus) and transitions
    between ACTIVE and IDLE states with debounced idle notifications.
    Optionally polls for resolved tasks to notify IDE resolution review.
    """

    def __init__(
        self,
        client: RestRLClient,
        debounce_seconds: float = 45.0,
        on_state_change: Optional[Callable[[str], None]] = None,
        on_resolution_available: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        self.client = client
        self.debounce_seconds = debounce_seconds
        self.on_state_change = on_state_change
        self.on_resolution_available = on_resolution_available

        self.is_idle = False
        self.last_activity_time = time.time()
        self._timer: Optional[threading.Timer] = None
        self._poll_timer: Optional[threading.Timer] = None
        self._lock = threading.Lock()
        self.running = False

    def start(self):
        """Starts the idle watcher and resolution poll."""
        self.running = True
        self._schedule_debounce()
        self._schedule_poll()

    def stop(self):
        """Stops the idle watcher."""
        self.running = False
        with self._lock:
            if self._timer:
                self._timer.cancel()
                self._timer = None
            if self._poll_timer:
                self._poll_timer.cancel()
                self._poll_timer = None

    def on_user_activity(self):
        """
        MUST be called on every keystroke, file change, or mouse event.
        Instantly preempts idle computation if previously idle.
        """
        now = time.time()
        with self._lock:
            self.last_activity_time = now

            if self.is_idle:
                self.is_idle = False
                logger.info("IDE Activity detected! Immediately notifying daemon to PAUSE.")
                try:
                    self.client.notify_idle_stop()
                except Exception as e:
                    logger.debug("Failed to send idle_stop: %s", e)

                if self.on_state_change:
                    try:
                        self.on_state_change("ACTIVE")
                    except Exception:
                        pass

            # Reset debounce timer
            self._schedule_debounce_locked()

    def _schedule_debounce(self):
        with self._lock:
            self._schedule_debounce_locked()

    def _schedule_debounce_locked(self):
        if not self.running:
            return
        if self._timer:
            self._timer.cancel()
        self._timer = threading.Timer(self.debounce_seconds, self._on_debounce_fired)
        self._timer.daemon = True
        self._timer.start()

    def _on_debounce_fired(self):
        with self._lock:
            if not self.running:
                return
            now = time.time()
            elapsed = now - self.last_activity_time
            if elapsed >= self.debounce_seconds and not self.is_idle:
                self.is_idle = True
                logger.info("IDE Inactive for %.1fs. Notifying daemon: IDLE_START", elapsed)
                try:
                    self.client.notify_idle_start()
                except Exception as e:
                    logger.debug("Failed to send idle_start: %s", e)

                if self.on_state_change:
                    try:
                        self.on_state_change("IDLE")
                    except Exception:
                        pass

    def _schedule_poll(self):
        if not self.running:
            return
        self._poll_timer = threading.Timer(2.0, self._poll_resolutions)
        self._poll_timer.daemon = True
        self._poll_timer.start()

    def _poll_resolutions(self):
        if not self.running:
            return
        try:
            resolutions = self.client.poll_resolutions()
            for r in resolutions:
                if self.on_resolution_available:
                    try:
                        self.on_resolution_available(r)
                    except Exception as e:
                        logger.debug("Error in resolution callback: %s", e)
        except Exception:
            pass
        finally:
            with self._lock:
                if self.running:
                    self._schedule_poll()


def main():
    import argparse
    import subprocess
    import sys

    parser = argparse.ArgumentParser(description="HugOS ReST-RL Client CLI")
    parser.add_argument("--host", default="127.0.0.1", help="TCP Host")
    parser.add_argument("--port", type=int, default=45454, help="TCP Port")
    parser.add_argument("--transport", choices=["tcp", "named_pipe"], default="tcp", help="IPC transport")

    subparsers = parser.add_subparsers(dest="action", help="Subcommand to execute")
    subparsers.add_parser("status", help="Query daemon status")
    subparsers.add_parser("start", help="Start the ReST-RL daemon if not running")
    subparsers.add_parser("stop", help="Stop the running ReST-RL daemon")

    eq = subparsers.add_parser("enqueue", help="Enqueue a task")
    eq.add_argument("--task-id", default="", help="Unique task ID")
    eq.add_argument("--target-file", default="", help="Target file path")
    eq.add_argument("--test-target", default="", help="Test target or command")
    eq.add_argument("--workspace-root", default=".", help="Workspace root directory")
    eq.add_argument("--instruction", default="", help="Task instruction")
    eq.add_argument("--original-code", default="", help="Original file code")
    eq.add_argument("--max-iterations", type=int, default=None, help="Max iterations")

    args, remaining = parser.parse_known_args()
    action = args.action or "status"

    client = RestRLClient(host=args.host, port=args.port, transport=args.transport, timeout=5.0)

    if action == "status":
        try:
            status = client.get_status()
            print(json.dumps({"running": True, "data": status}, indent=2))
        except Exception:
            print(json.dumps({"running": False, "status": "STOPPED", "message": "ReST-RL daemon is not running."}, indent=2))

    elif action == "start":
        try:
            status = client.get_status()
            print(json.dumps({"running": True, "status": "ALREADY_RUNNING", "data": status}, indent=2))
            return
        except Exception:
            pass

        script_dir = os.path.dirname(os.path.abspath(__file__))
        daemon_path = os.path.join(script_dir, "rest_rl_daemon.py")
        if not os.path.isfile(daemon_path):
            print(json.dumps({"error": f"Daemon script not found at {daemon_path}"}, indent=2))
            sys.exit(1)

        creationflags = 0
        if sys.platform == "win32":
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | 0x00000008  # DETACHED_PROCESS

        proc = subprocess.Popen(
            [sys.executable, daemon_path],
            cwd=script_dir,
            creationflags=creationflags,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # Wait up to 10 seconds for daemon to start listening
        ready = False
        status_data = None
        for _ in range(20):
            time.sleep(0.5)
            try:
                status_data = client.get_status()
                ready = True
                break
            except Exception:
                continue

        if ready:
            print(json.dumps({"running": True, "status": "STARTED", "pid": proc.pid, "data": status_data}, indent=2))
        else:
            print(json.dumps({"running": False, "status": "START_TIMEOUT", "message": "Daemon process started but did not respond to status probe within 10s."}, indent=2))
            sys.exit(1)

    elif action == "stop":
        try:
            res = client.shutdown_daemon()
            print(json.dumps({"running": False, "status": "STOPPED", "result": res}, indent=2))
        except Exception:
            print(json.dumps({"running": False, "status": "ALREADY_STOPPED", "message": "Daemon was not running."}, indent=2))

    elif action == "enqueue":
        task_id = args.task_id or f"task_{int(time.time())}"
        target_file = args.target_file or (remaining[0] if remaining else "solution.py")
        test_target = args.test_target or (remaining[1] if len(remaining) > 1 else "test_solution.py")
        workspace_root = args.workspace_root or "."
        instruction = args.instruction
        original_code = args.original_code

        if not original_code and os.path.isfile(os.path.join(workspace_root, target_file)):
            try:
                with open(os.path.join(workspace_root, target_file), "r", encoding="utf-8") as f:
                    original_code = f.read()
            except Exception:
                pass

        try:
            res = client.enqueue_task(
                task_id=task_id,
                target_file=target_file,
                test_target=test_target,
                workspace_root=workspace_root,
                instruction=instruction,
                original_code=original_code,
                max_iterations=args.max_iterations,
            )
            print(json.dumps({"success": True, "task_id": task_id, "result": res}, indent=2))
        except Exception as e:
            print(json.dumps({"success": False, "error": str(e)}, indent=2))
            sys.exit(1)


if __name__ == "__main__":
    main()
