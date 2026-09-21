#!/usr/bin/env python3
"""
HugOS ReST-RL / GRPO Background Daemon (rest_rl_daemon.py)

Autonomous background daemon that executes code repair and self-training reasoning
using ReST-RL algorithms (VM-MCTS / GRPO / Minimal-GRPO) without degrading editor performance.

Key features:
1. Runs at low OS scheduling priority (psutil.IDLE_PRIORITY_CLASS / os.nice(15)).
2. Configures GPU memory caps (VLLM_GPU_MEMORY_UTILIZATION=0.4, torch memory fraction=0.5).
3. JSON-RPC 2.0 IPC over TCP (127.0.0.1:45454) and Windows Named Pipe (\\\\.\\pipe\\hugos_rest_rl_ipc).
4. Strict Idle-Driven Execution:
   - ide/idle_start: Resumes queue and spins up background reasoning tasks.
   - ide/idle_stop: Immediately halts computation and yields CPU/GPU to the IDE UI thread.
5. Task queue and resolution review streaming for developer diff inspection.
"""

from __future__ import annotations

import os
import sys
import json
import time
import socket
import select
import difflib
import logging
import threading
import traceback
from typing import Optional, Dict, Any, List

if not __package__:
    pkg_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(pkg_dir)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    __package__ = os.path.basename(pkg_dir)

import sqlite3
from .hardware_profiler import HardwareProfiler, HardwareTier, MemoryProfile
from .sandbox import VerificationSandbox, SandboxResult
from .adapters.base import RLTask, RolloutResult, BaseRLAdapter
from .adapters.factory import create_adapter
from .graduated_rewards import GraduatedRewardEvaluator
from .mutation_verifier import ASTMutator, AdversarialCertificationGate
from .compute_budgeter import ComputeBudgeter
from .lsp_diagnostic_repair import LSPDiagnosticHarvester, CompilerOracleRepairLoop, LSPDiagnostic
from .speculative_synthesis import SpeculativeSynthesizer, SpeculativeCache
from .dependency_migration import DependencyMigrationManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [rest_rl_daemon] %(message)s",
)
logger = logging.getLogger("rest_rl_daemon")


class TaskState:
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class DaemonTask:
    def __init__(self, task: RLTask, max_iterations: Optional[int] = None):
        self.task = task
        self.max_iterations = max_iterations
        self.state = TaskState.QUEUED
        self.enqueued_at = time.time()
        self.started_at: Optional[float] = None
        self.completed_at: Optional[float] = None
        self.result: Optional[RolloutResult] = None
        self.diff_patch: Optional[str] = None
        self.error: Optional[str] = None


class RestRLDaemon:
    """Core daemon managing JSON-RPC IPC, idle state controller, and background worker."""

    def __init__(self, config_path: Optional[str] = None):
        self.config = self._load_config(config_path)
        HardwareProfiler.apply_os_throttling()
        self.profiler = HardwareProfiler(
            tier1_min_ram_gb=self.config.get("resources", {}).get("tier1_min_available_ram_gb", 24.0),
            tier1_min_vram_gb=self.config.get("resources", {}).get("tier1_min_free_vram_gb", 14.0),
            tier2_min_ram_gb=self.config.get("resources", {}).get("tier2_min_available_ram_gb", 12.0),
            tier2_min_vram_gb=self.config.get("resources", {}).get("tier2_min_free_vram_gb", 4.5),
        )
        self.sandbox = VerificationSandbox(
            default_timeout=self.config.get("sandbox", {}).get("timeout_seconds", 5.0)
        )

        # Advanced reasoning, verification, and tooling modules
        self.reward_evaluator = GraduatedRewardEvaluator(sandbox=self.sandbox)
        self.mutator = ASTMutator()
        self.certification_gate = AdversarialCertificationGate(sandbox=self.sandbox, mutator=self.mutator)
        self.budgeter = ComputeBudgeter()
        self.harvester = LSPDiagnosticHarvester()
        self.repair_loop = CompilerOracleRepairLoop(harvester=self.harvester)
        self.speculative_cache = SpeculativeCache()
        self.speculative_synthesizer = SpeculativeSynthesizer(cache=self.speculative_cache)
        self.migration_mgr = DependencyMigrationManager()

        # Persistent SQLite storage (IDE/db/rest_rl.db)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        ide_dir = os.path.dirname(base_dir)
        self.db_path = self.config.get("database", {}).get("db_path", os.path.join(ide_dir, "db", "rest_rl.db"))
        self._init_sqlite()

        # Idle & Pause synchronization
        self.is_idle = False
        self.pause_event = threading.Event()
        self.pause_event.set()  # Initially paused until first ide/idle_start

        # Task queue, store, and completed resolution reviews
        self.task_lock = threading.Lock()
        self.task_queue: List[str] = []  # List of task_ids
        self.tasks: Dict[str, DaemonTask] = {}
        self.resolved_tasks: List[Dict[str, Any]] = []
        self.current_task_id: Optional[str] = None

        # Adapter lifecycle
        self.active_adapter: Optional[BaseRLAdapter] = None
        self.active_tier: HardwareTier = HardwareTier.TIER_3

        # Server state
        self.running = False
        self.tcp_server_sock: Optional[socket.socket] = None
        self.tcp_port = self.config.get("ipc", {}).get("tcp_port", 45454)
        self.tcp_host = self.config.get("ipc", {}).get("tcp_host", "127.0.0.1")
        self.pipe_name = self.config.get("ipc", {}).get("pipe_name", r"\\.\pipe\hugos_rest_rl_ipc")

        # Threads
        self.worker_thread: Optional[threading.Thread] = None
        self.tcp_thread: Optional[threading.Thread] = None
        self.pipe_thread: Optional[threading.Thread] = None

    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        if not config_path:
            default_path = os.path.join(os.path.dirname(__file__), "config.json")
            if os.path.isfile(default_path):
                config_path = default_path

        if config_path and os.path.isfile(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error("Failed to load config from %s: %s", config_path, e)
        return {}

    def _init_sqlite(self) -> None:
        """Ensures SQLite schema exists at IDE/db/rest_rl.db."""
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.cursor()
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS tasks (
                        task_id TEXT PRIMARY KEY,
                        target_file TEXT,
                        test_target TEXT,
                        workspace_root TEXT,
                        instruction TEXT,
                        state TEXT,
                        reward REAL,
                        created_at REAL,
                        updated_at REAL
                    )
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS resolutions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        task_id TEXT,
                        target_file TEXT,
                        candidate_code TEXT,
                        original_code TEXT,
                        diff_patch TEXT,
                        reward REAL,
                        passed INTEGER,
                        created_at REAL
                    )
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS diagnostics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        task_id TEXT,
                        file_path TEXT,
                        line_number INTEGER,
                        column INTEGER,
                        severity TEXT,
                        source TEXT,
                        code TEXT,
                        message TEXT,
                        created_at REAL
                    )
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS speculative_cache (
                        key TEXT PRIMARY KEY,
                        file_path TEXT,
                        func_name TEXT,
                        signature TEXT,
                        candidate_code TEXT,
                        reward REAL,
                        created_at REAL
                    )
                """)
                conn.commit()
            logger.info("Persistent SQLite database initialized at %s", self.db_path)
        except Exception as e:
            logger.warning("Failed to initialize SQLite database at %s: %s", self.db_path, e)

    def _save_task_to_db(self, task: RLTask, state: str, reward: float = 0.0) -> None:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.cursor()
                now = time.time()
                cur.execute("""
                    INSERT INTO tasks (task_id, target_file, test_target, workspace_root, instruction, state, reward, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(task_id) DO UPDATE SET
                        state=excluded.state,
                        reward=excluded.reward,
                        updated_at=excluded.updated_at
                """, (
                    task.task_id,
                    task.target_file,
                    task.test_target,
                    task.workspace_root,
                    task.instruction,
                    state,
                    reward,
                    now,
                    now,
                ))
                conn.commit()
        except Exception as e:
            logger.debug("SQLite save task error: %s", e)

    def _save_resolution_to_db(self, payload: Dict[str, Any]) -> None:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO resolutions (task_id, target_file, candidate_code, original_code, diff_patch, reward, passed, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    payload.get("task_id", ""),
                    payload.get("target_file", ""),
                    payload.get("candidate_code", ""),
                    payload.get("original_code", ""),
                    payload.get("diff_patch", ""),
                    payload.get("reward", 0.0),
                    1 if payload.get("passed") else 0,
                    time.time(),
                ))
                conn.commit()
        except Exception as e:
            logger.debug("SQLite save resolution error: %s", e)

    def initialize(self):
        """Initializes low process scheduling priority, memory caps, and hardware tier."""
        logger.info("Initializing HugOS ReST-RL Daemon...")

        # 1. Enforce low OS priority
        HardwareProfiler.apply_os_throttling()

        # 2. Apply GPU memory caps
        cuda_frac = self.config.get("resources", {}).get("max_cuda_memory_fraction", 0.5)
        vllm_util = self.config.get("resources", {}).get("vllm_gpu_memory_utilization", 0.4)
        HardwareProfiler.apply_gpu_memory_caps(cuda_fraction=cuda_frac, vllm_utilization=vllm_util)

        # 3. Dynamic Hardware Sizing via Available Runtime Memory Rule
        profile = self.profiler.classify()
        self.active_tier = profile.tier
        logger.info(
            "Hardware Profile: Tier %d (%s) | Avail RAM: %.1f GB | Free VRAM: %.1f MB | GPU: %s",
            int(profile.tier),
            profile.tier.name,
            profile.available_ram_gb,
            profile.free_vram_mb,
            profile.gpu_name,
        )

        # 4. Instantiate Adapter
        self.active_adapter = create_adapter(tier=self.active_tier, config=self.config, sandbox=self.sandbox)
        logger.info("Initialized RL reasoning adapter: %s", type(self.active_adapter).__name__)

    def start(self):
        """Starts IPC listeners and the background worker loop."""
        HardwareProfiler.apply_os_throttling()
        self.running = True

        # Start TCP JSON-RPC listener
        self.tcp_thread = threading.Thread(target=self._run_tcp_server, name="ReST-RL-TCP", daemon=True)
        self.tcp_thread.start()

        # Start Windows Named Pipe listener if on Windows
        if sys.platform == "win32":
            self.pipe_thread = threading.Thread(target=self._run_named_pipe_server, name="ReST-RL-Pipe", daemon=True)
            self.pipe_thread.start()

        # Start background worker thread
        self.worker_thread = threading.Thread(target=self._worker_loop, name="ReST-RL-Worker", daemon=True)
        self.worker_thread.start()

        logger.info("Daemon started successfully. Listening on %s:%d and %s", self.tcp_host, self.tcp_port, self.pipe_name)

    def stop(self):
        """Gracefully halts the daemon."""
        logger.info("Stopping ReST-RL Daemon...")
        self.running = False
        self.pause_event.set()

        if self.tcp_server_sock:
            try:
                self.tcp_server_sock.close()
            except Exception:
                pass

        if sys.platform == "win32":
            try:
                import ctypes
                # Unblock ConnectNamedPipe if server loop is waiting
                h = ctypes.windll.kernel32.CreateFileW(
                    self.pipe_name,
                    0x80000000 | 0x40000000,
                    0,
                    None,
                    3,
                    0,
                    None,
                )
                if h != -1:
                    ctypes.windll.kernel32.CloseHandle(h)
            except Exception:
                pass

        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=2.0)

        logger.info("Daemon shutdown complete.")

    # -------------------------------------------------------------------------
    # Worker Loop & Idle Controller
    # -------------------------------------------------------------------------

    def _is_paused_check(self) -> bool:
        """Returns True if the worker must yield computation."""
        return (not self.is_idle) or self.pause_event.is_set() or (not self.running)

    def _worker_loop(self):
        """Main background reasoning worker loop."""
        while self.running:
            # Yield if IDE is active (not idle) or paused
            if not self.is_idle or self.pause_event.is_set():
                time.sleep(0.5)
                continue

            # Check for queued tasks
            task_to_run: Optional[DaemonTask] = None
            with self.task_lock:
                if self.task_queue:
                    tid = self.task_queue[0]
                    task_to_run = self.tasks.get(tid)

            if not task_to_run:
                time.sleep(0.5)
                continue

            self.current_task_id = task_to_run.task.task_id
            task_to_run.state = TaskState.RUNNING
            if not task_to_run.started_at:
                task_to_run.started_at = time.time()
            self._save_task_to_db(task_to_run.task, TaskState.RUNNING, 0.0)

            logger.info("Worker starting/resuming task: %s (Target: %s)", task_to_run.task.task_id, task_to_run.task.target_file)

            try:
                rollout_result = self.active_adapter.run_rollout(
                    task=task_to_run.task,
                    is_paused=self._is_paused_check,
                    max_iterations=task_to_run.max_iterations,
                )
                task_to_run.result = rollout_result

                if rollout_result.status == "PAUSED":
                    task_to_run.state = TaskState.PAUSED
                    self._save_task_to_db(task_to_run.task, TaskState.PAUSED, rollout_result.best_reward)
                    logger.info("Task %s paused at iteration %d", task_to_run.task.task_id, rollout_result.iterations_completed)
                    time.sleep(0.1)
                else:
                    # Completed or failed
                    task_to_run.state = TaskState.COMPLETED
                    task_to_run.completed_at = time.time()

                    # Compute unified diff patch if candidate differs from original
                    diff_patch = self._generate_diff(
                        original=task_to_run.task.original_code,
                        candidate=rollout_result.best_candidate,
                        filename=task_to_run.task.target_file,
                    )
                    task_to_run.diff_patch = diff_patch

                    # Record resolution review payload
                    resolution_payload = {
                        "task_id": task_to_run.task.task_id,
                        "target_file": task_to_run.task.target_file,
                        "reward": rollout_result.best_reward,
                        "candidate_code": rollout_result.best_candidate,
                        "original_code": task_to_run.task.original_code,
                        "diff_patch": diff_patch,
                        "passed": rollout_result.best_reward >= 1.0,
                    }

                    with self.task_lock:
                        self.resolved_tasks.append(resolution_payload)
                        if self.task_queue and self.task_queue[0] == task_to_run.task.task_id:
                            self.task_queue.pop(0)
                        self.current_task_id = None

                    self._save_task_to_db(task_to_run.task, TaskState.COMPLETED, rollout_result.best_reward)
                    self._save_resolution_to_db(resolution_payload)

                    logger.info(
                        "Task %s finished with reward %.2f (status: %s)",
                        task_to_run.task.task_id,
                        rollout_result.best_reward,
                        rollout_result.status,
                    )

            except Exception as e:
                logger.error("Exception in worker execution for task %s: %s", task_to_run.task.task_id, e, exc_info=True)
                task_to_run.state = TaskState.FAILED
                task_to_run.error = str(e)
                self._save_task_to_db(task_to_run.task, TaskState.FAILED, 0.0)
                with self.task_lock:
                    if self.task_queue and self.task_queue[0] == task_to_run.task.task_id:
                        self.task_queue.pop(0)
                    self.current_task_id = None

    @staticmethod
    def _generate_diff(original: str, candidate: str, filename: str) -> str:
        """Generates unified diff between original and candidate code."""
        orig_lines = original.splitlines(keepends=True)
        cand_lines = candidate.splitlines(keepends=True)
        diff = difflib.unified_diff(
            orig_lines,
            cand_lines,
            fromfile=f"a/{os.path.basename(filename)}",
            tofile=f"b/{os.path.basename(filename)}",
            lineterm="",
        )
        return "".join(diff)

    # -------------------------------------------------------------------------
    # JSON-RPC 2.0 Dispatcher
    # -------------------------------------------------------------------------

    def dispatch_rpc(self, request_raw: str) -> str:
        """Dispatches incoming JSON-RPC 2.0 payload and returns formatted JSON-RPC response."""
        try:
            req = json.loads(request_raw)
        except json.JSONDecodeError as jde:
            return json.dumps({
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"Parse error: {jde}"},
            })

        req_id = req.get("id")
        method = req.get("method")
        params = req.get("params", {})

        if not method:
            return json.dumps({
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32600, "message": "Invalid Request: missing method"},
            })

        try:
            result = self._handle_method(method, params)
            return json.dumps({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": result,
            })
        except Exception as e:
            logger.error("RPC handler error on %s: %s", method, e)
            return json.dumps({
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32000, "message": str(e), "traceback": traceback.format_exc()},
            })

    def _handle_method(self, method: str, params: Dict[str, Any]) -> Any:
        if method == "ide/idle_start":
            self.is_idle = True
            self.pause_event.clear()  # Resume worker
            logger.info("State changed: IDE is IDLE -> Resumed background reasoning worker.")
            return {"status": "RESUMED", "is_idle": True}

        elif method == "ide/idle_stop":
            self.is_idle = False
            self.pause_event.set()  # Pause worker immediately
            self.sandbox.terminate_active_jobs()
            logger.info("State changed: IDE is ACTIVE -> Immediately paused background worker and terminated active jobs.")
            return {"status": "PAUSED", "is_idle": False}

        elif method == "agent/enqueue_task":
            task_id = params.get("task_id", f"task_{int(time.time()*1000)}")
            target_file = params.get("target_file", "")
            test_target = params.get("test_target", "")
            workspace_root = params.get("workspace_root", "")
            instruction = params.get("instruction", "")
            original_code = params.get("original_code", "")
            max_iterations = params.get("max_iterations")

            task = RLTask(
                task_id=task_id,
                target_file=target_file,
                test_target=test_target,
                workspace_root=workspace_root,
                instruction=instruction,
                original_code=original_code,
            )
            daemon_task = DaemonTask(task=task, max_iterations=max_iterations)

            with self.task_lock:
                self.tasks[task_id] = daemon_task
                self.task_queue.append(task_id)

            self._save_task_to_db(task, TaskState.QUEUED, 0.0)

            logger.info("Enqueued task %s for target %s (Queue length: %d)", task_id, target_file, len(self.task_queue))
            return {
                "task_id": task_id,
                "status": "QUEUED",
                "queue_position": len(self.task_queue),
            }

        elif method == "agent/status":
            mem_profile = self.profiler.classify()
            with self.task_lock:
                q_len = len(self.task_queue)
                curr_id = self.current_task_id
                resolved_count = len(self.resolved_tasks)

            current_task_info = None
            running_task_str = None
            if curr_id and curr_id in self.tasks:
                ct = self.tasks[curr_id]
                running_task_str = ct.task.target_file
                current_task_info = {
                    "task_id": curr_id,
                    "target_file": ct.task.target_file,
                    "state": ct.state,
                    "iterations": ct.result.iterations_completed if ct.result else 0,
                    "reward": ct.result.best_reward if ct.result else 0.0,
                }

            hw_dict = mem_profile.to_dict()
            ide_state_str = "IDLE" if self.is_idle else "ACTIVE"

            return {
                "daemon_running": self.running,
                "is_idle": self.is_idle,
                "is_paused": self.pause_event.is_set(),
                "ide_state": ide_state_str,
                "hardware_tier": int(mem_profile.tier),
                "hardware_tier_name": mem_profile.tier.name,
                "queue_length": q_len,
                "processed_tasks_count": resolved_count,
                "running_task": running_task_str,
                "current_task": current_task_info,
                "hardware": hw_dict,
                "hardware_profile": hw_dict,
                "adapter": type(self.active_adapter).__name__ if self.active_adapter else "None",
            }

        elif method == "agent/get_result":
            task_id = params.get("task_id")
            if not task_id:
                raise ValueError("Missing 'task_id' parameter")

            with self.task_lock:
                task_entry = self.tasks.get(task_id)

            if not task_entry:
                return {"task_id": task_id, "found": False}

            res_dict = None
            if task_entry.result:
                res_dict = task_entry.result.to_dict()

            return {
                "task_id": task_id,
                "found": True,
                "state": task_entry.state,
                "diff_patch": task_entry.diff_patch,
                "error": task_entry.error,
                "result": res_dict,
                "duration_sec": (task_entry.completed_at - task_entry.started_at) if (task_entry.completed_at and task_entry.started_at) else None,
            }

        elif method == "agent/poll_resolutions":
            with self.task_lock:
                resolutions = list(self.resolved_tasks)
                self.resolved_tasks.clear()
            return {"resolutions": resolutions}

        elif method == "diagnostics/report":
            diags = self.harvester.harvest_from_payload(params)
            count = len(diags)
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cur = conn.cursor()
                    now = time.time()
                    task_id = params.get("task_id", "")
                    for d in diags:
                        cur.execute("""
                            INSERT INTO diagnostics (task_id, file_path, line_number, column, severity, source, code, message, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (task_id, d.file_path, d.line_number, d.column, d.severity, d.source, d.code, d.message, now))
                    conn.commit()
            except Exception as e:
                logger.debug("Failed saving diagnostics to SQLite: %s", e)
            return {"recorded": count, "diagnostics": [d.to_dict() for d in diags]}

        elif method == "speculative/detect":
            code_str = params.get("code", "")
            file_path = params.get("file_path", "solution.py")
            callsites = self.speculative_synthesizer.detect_unwritten_callsites(code_str, target_file=file_path)
            return {"count": len(callsites), "callsites": [c.to_dict() for c in callsites]}

        elif method == "speculative/get_cache":
            file_path = params.get("file_path", "")
            func_name = params.get("func_name", "")
            if file_path and func_name:
                item = self.speculative_cache.get(file_path, func_name)
                return {"found": item is not None, "item": item.to_dict() if item else None}
            else:
                return {"items": self.speculative_cache.all_items()}

        elif method == "migration/detect":
            manifest_filename = params.get("manifest_filename", "")
            old_content = params.get("old_content", "")
            new_content = params.get("new_content", "")
            bumps = self.migration_mgr.detect_manifest_bumps(manifest_filename, old_content, new_content)
            return {"bumps": [b.to_dict() for b in bumps]}

        elif method == "agent/certify":
            code = params.get("code", "")
            test_code = params.get("test_code", "")
            target_filename = params.get("target_filename", "solution.py")
            workspace_root = params.get("workspace_root")
            cert_result = self.certification_gate.certify(
                candidate_code=code,
                test_source=test_code,
                target_filename=target_filename,
                workspace_root=workspace_root,
            )
            return cert_result.to_dict()

        elif method == "budget/complexity":
            code_str = params.get("code", "")
            score = self.budgeter.compute_complexity(code_str)
            return score.to_dict()

        elif method == "system/shutdown":
            threading.Thread(target=self.stop, daemon=True).start()
            return {"status": "SHUTTING_DOWN"}

        else:
            raise ValueError(f"Unknown RPC method: {method}")

    # -------------------------------------------------------------------------
    # IPC Network Transports (TCP & Named Pipe)
    # -------------------------------------------------------------------------

    def _run_tcp_server(self):
        """Runs the TCP JSON-RPC listener."""
        self.tcp_server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.tcp_server_sock.bind((self.tcp_host, self.tcp_port))
        self.tcp_server_sock.listen(10)
        self.tcp_server_sock.settimeout(1.0)
        logger.info("TCP JSON-RPC server listening on %s:%d", self.tcp_host, self.tcp_port)

        while self.running:
            try:
                conn, _ = self.tcp_server_sock.accept()
                threading.Thread(target=self._handle_socket_client, args=(conn,), daemon=True).start()
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    logger.debug("TCP accept loop exception: %s", e)
                break

    def _handle_socket_client(self, conn: socket.socket):
        """Handles framed newline-delimited JSON-RPC requests over TCP."""
        with conn:
            conn.settimeout(30.0)
            buf = ""
            while self.running:
                try:
                    data = conn.recv(4096)
                    if not data:
                        break
                    buf += data.decode("utf-8", errors="replace")
                    while "\n" in buf:
                        line, buf = buf.split("\n", 1)
                        line = line.strip()
                        if line:
                            resp = self.dispatch_rpc(line)
                            conn.sendall((resp + "\n").encode("utf-8"))
                except socket.timeout:
                    break
                except Exception as e:
                    logger.debug("Client handler error: %s", e)
                    break

    def _run_named_pipe_server(self):
        """Runs Windows Named Pipe server instance loop if on Windows."""
        try:
            import ctypes

            PIPE_ACCESS_DUPLEX = 0x00000003
            PIPE_TYPE_MESSAGE = 0x00000004
            PIPE_READMODE_MESSAGE = 0x00000002
            PIPE_WAIT = 0x00000000
            INVALID_HANDLE_VALUE = -1

            kernel32 = ctypes.windll.kernel32

            while self.running:
                h_pipe = kernel32.CreateNamedPipeW(
                    self.pipe_name,
                    PIPE_ACCESS_DUPLEX,
                    PIPE_TYPE_MESSAGE | PIPE_READMODE_MESSAGE | PIPE_WAIT,
                    255,  # Max instances
                    65536,  # Out buffer
                    65536,  # In buffer
                    50,  # Default timeout ms
                    None,
                )

                if h_pipe == INVALID_HANDLE_VALUE:
                    time.sleep(0.5)
                    continue

                connected = kernel32.ConnectNamedPipe(h_pipe, None)
                if not self.running:
                    kernel32.CloseHandle(h_pipe)
                    break

                if not connected and kernel32.GetLastError() != 535:  # ERROR_PIPE_CONNECTED
                    kernel32.CloseHandle(h_pipe)
                    continue

                # Handle client in worker thread
                threading.Thread(target=self._handle_named_pipe_client, args=(h_pipe,), daemon=True).start()

        except Exception as e:
            logger.debug("Windows Named Pipe server loop ended: %s", e)

    def _handle_named_pipe_client(self, h_pipe):
        """Reads and responds to messages on Windows Named Pipe handle."""
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            buf = ctypes.create_string_buffer(65536)
            bytes_read = ctypes.c_ulong(0)
            bytes_written = ctypes.c_ulong(0)

            while self.running:
                success = kernel32.ReadFile(
                    h_pipe,
                    buf,
                    ctypes.sizeof(buf),
                    ctypes.byref(bytes_read),
                    None,
                )
                if not success or bytes_read.value == 0:
                    break

                raw_req = buf.raw[:bytes_read.value].decode("utf-8", errors="replace").strip()
                if raw_req:
                    resp = self.dispatch_rpc(raw_req)
                    resp_bytes = (resp + "\n").encode("utf-8")
                    kernel32.WriteFile(
                        h_pipe,
                        resp_bytes,
                        len(resp_bytes),
                        ctypes.byref(bytes_written),
                        None,
                    )
        finally:
            try:
                import ctypes
                ctypes.windll.kernel32.DisconnectNamedPipe(h_pipe)
                ctypes.windll.kernel32.CloseHandle(h_pipe)
            except Exception:
                pass


if __name__ == "__main__":
    daemon = RestRLDaemon()
    daemon.initialize()
    daemon.start()

    logger.info("Daemon running. Press Ctrl+C to terminate.")
    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        daemon.stop()
