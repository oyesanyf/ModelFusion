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
