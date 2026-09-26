#!/usr/bin/env python3
"""
Integration tests for ReST-RL Daemon IPC (JSON-RPC 2.0), State Controller,
Idle Activity Debounce, Resolution Polling, Windows Named Pipe, and Worker Queue.
"""

import sys
import time
import socket
import unittest
from pathlib import Path

# Add root of rest_rl to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from rest_rl.rest_rl_daemon import RestRLDaemon
from rest_rl.rest_rl_client import RestRLClient, IdleActivityTracker


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


class TestIPCAndState(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import tempfile
        import os
        cls.test_port = find_free_port()
        cls.test_pipe = rf"\\.\pipe\test_hugos_rest_rl_{int(time.time()*1000)}"
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
            cls.temp_db = tf.name
        cls.daemon = RestRLDaemon()
        cls.daemon.db_path = cls.temp_db
        cls.daemon.tcp_port = cls.test_port
        cls.daemon.pipe_name = cls.test_pipe
        cls.daemon.initialize()
        cls.daemon.start()

        # Give server time to bind
        time.sleep(0.3)
        cls.client = RestRLClient(port=cls.test_port, pipe_name=cls.test_pipe, timeout=5.0)

    @classmethod
    def tearDownClass(cls):
        if cls.daemon:
            cls.daemon.stop()
        if hasattr(cls, "temp_db"):
            try:
                import os
                os.unlink(cls.temp_db)
            except Exception:
                pass

    def test_01_agent_status(self):
        status = self.client.get_status()
        self.assertTrue(status.get("daemon_running"))
        self.assertIn("hardware", status)
        self.assertIn("tier", status["hardware"])
        self.assertIn("queue_length", status)

    def test_02_idle_state_transitions(self):
        # 1. Trigger idle_start
        resp_idle = self.client.notify_idle_start()
        self.assertEqual(resp_idle.get("status"), "RESUMED")
        self.assertTrue(resp_idle.get("is_idle"))

        status = self.client.get_status()
        self.assertTrue(status.get("is_idle"))
        self.assertFalse(status.get("is_paused"))

        # 2. Trigger idle_stop (user activity)
        resp_active = self.client.notify_idle_stop()
        self.assertEqual(resp_active.get("status"), "PAUSED")
        self.assertFalse(resp_active.get("is_idle"))

        status = self.client.get_status()
        self.assertFalse(status.get("is_idle"))
        self.assertTrue(status.get("is_paused"))

    def test_03_enqueue_and_process_task(self):
        task_id = "test_integration_task_42"
        target_code = """
def multiply(a: int, b: int) -> int:
    pass
"""
        test_code = """
import unittest
from solution import multiply

class TestMult(unittest.TestCase):
    def test_mult(self):
        # If returns not None, passes
        res = multiply(3, 4)
        self.assertTrue(res is not None)
"""
        # Ensure worker is paused before enqueuing
        self.client.notify_idle_stop()

        enqueue_res = self.client.enqueue_task(
            task_id=task_id,
            target_file="solution.py",
            test_target=test_code,
            workspace_root="",
            instruction="Fix multiply function",
            original_code=target_code,
            max_iterations=2,
        )
        self.assertEqual(enqueue_res.get("task_id"), task_id)
        self.assertEqual(enqueue_res.get("status"), "QUEUED")

        # Now simulate IDE becoming IDLE
        self.client.notify_idle_start()

        # Wait for worker loop to pick up and process task
        max_wait = 20.0
        start = time.time()
        completed = False
        while time.time() - start < max_wait:
            res = self.client.get_result(task_id)
            if res.get("found") and res.get("state") in ["COMPLETED", "FAILED"]:
                completed = True
                break
            time.sleep(0.3)

        self.assertTrue(completed, f"Task did not complete in {max_wait}s")
        result_payload = self.client.get_result(task_id)
        self.assertTrue(result_payload.get("found"))
        self.assertEqual(result_payload.get("state"), "COMPLETED")
        self.assertIsNotNone(result_payload.get("diff_patch"))

        # Put back into paused state
        self.client.notify_idle_stop()

    def test_04_idle_activity_tracker_debounce(self):
        state_changes = []

        def on_change(new_state: str):
            state_changes.append(new_state)

        # Fast 0.5s debounce for test (prevents TCP RPC roundtrip race)
        tracker = IdleActivityTracker(
            client=self.client,
            debounce_seconds=0.5,
            on_state_change=on_change,
        )
        tracker.start()

        try:
            # Initially active
            self.assertFalse(tracker.is_idle)

            # Wait for debounce to fire
            time.sleep(0.65)
            self.assertTrue(tracker.is_idle)
            self.assertIn("IDLE", state_changes)

            # Simulate user keystroke
            tracker.on_user_activity()
            self.assertFalse(tracker.is_idle)
            self.assertIn("ACTIVE", state_changes)

            # Immediately check daemon status
            status = self.client.get_status()
            self.assertFalse(status.get("is_idle"))
            self.assertTrue(status.get("is_paused"))
        finally:
            tracker.stop()

    def test_05_resolution_polling(self):
        resolutions = self.client.poll_resolutions()
        self.assertIsInstance(resolutions, list)
        if resolutions:
            first = resolutions[0]
            self.assertIn("task_id", first)
            self.assertIn("reward", first)
            self.assertIn("diff_patch", first)

    def test_06_named_pipe_communication(self):
        if sys.platform != "win32":
            return
        pipe_client = RestRLClient(
            pipe_name=self.test_pipe,
            transport="named_pipe",
            timeout=3.0,
        )
        status = pipe_client.get_status()
        self.assertTrue(status.get("daemon_running"))
        self.assertIn("hardware", status)

    def test_07_multiple_consecutive_tasks(self):
        self.client.notify_idle_stop()

        # Enqueue Task A
        test_a = """
import unittest
from solution_a import f

class TestA(unittest.TestCase):
    def test_f(self):
        self.assertIsNotNone(f())
"""
        self.client.enqueue_task(
            task_id="seq_task_A",
            target_file="solution_a.py",
            test_target=test_a,
            workspace_root="",
            original_code="def f():\n    pass\n",
            max_iterations=2,
        )

        # Enqueue Task B
        test_b = """
import unittest
from solution_b import g

class TestB(unittest.TestCase):
    def test_g(self):
        self.assertIsNotNone(g())
"""
        self.client.enqueue_task(
            task_id="seq_task_B",
            target_file="solution_b.py",
            test_target=test_b,
            workspace_root="",
            original_code="def g():\n    pass\n",
            max_iterations=2,
        )

        # Let daemon run both
        self.client.notify_idle_start()

        max_wait = 25.0
        start = time.time()
        a_done, b_done = False, False
        while time.time() - start < max_wait:
            if not a_done:
                res_a = self.client.get_result("seq_task_A")
                if res_a.get("found") and res_a.get("state") in ["COMPLETED", "FAILED"]:
                    a_done = True
            if not b_done:
                res_b = self.client.get_result("seq_task_B")
                if res_b.get("found") and res_b.get("state") in ["COMPLETED", "FAILED"]:
                    b_done = True
            if a_done and b_done:
                break
            time.sleep(0.3)

        self.assertTrue(a_done, "seq_task_A did not complete")
        self.assertTrue(b_done, "seq_task_B did not complete")

        self.client.notify_idle_stop()


if __name__ == "__main__":
    unittest.main()
