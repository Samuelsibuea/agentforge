# test_selfheal_replay.py — Comprehensive Test Suite for Autonomous Self-Healing and HTML Session Replay Visualizer
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from agent.core import Agent
from agent.self_heal import SelfHealingEngine
from agent.visualizer import export_session_replay_html
from agent.commands import cmd_replay


class TestSelfHealAndReplay(unittest.TestCase):
    def setUp(self):
        self.agent = Agent("config.json")
        self.agent.run_log = [
            {"type": "tool", "name": "file_read", "args": {"path": "main.py"}, "result": "content ok"},
            {"type": "veritas", "name": "dual_check", "args": {}, "result": "PASS"},
            {"type": "tool", "name": "calculate", "args": {"expr": "40 + 2"}, "result": "42"}
        ]

    def test_01_traceback_diagnosis(self):
        """Verify self-healing engine parses stack traces accurately."""
        healer = SelfHealingEngine(self.agent)
        sample_error = """
Traceback (most recent call last):
  File "agent/core.py", line 142, in call_model
    resp = httpx.post(url, headers=headers)
ZeroDivisionError: division by zero
"""
        diag = healer.diagnose_error(sample_error)
        self.assertTrue(diag["is_error"])
        self.assertEqual(diag["file"], "agent/core.py")
        self.assertEqual(diag["line"], 142)
        self.assertEqual(diag["error_type"], "ZeroDivisionError")
        self.assertIn("division by zero", diag["message"])

        res = healer.attempt_heal("test_tool", sample_error)
        self.assertTrue(res["healed"])
        self.assertEqual(res["attempt"], 1)

    def test_02_export_session_replay_html(self):
        """Verify HTML visualizer exports dark-themed self-contained dashboard."""
        out_html = "workspace/test_replay.html"
        res_file = export_session_replay_html(self.agent, out_html)
        self.assertTrue(os.path.exists(res_file))

        content = open(res_file, "r", encoding="utf-8").read()
        self.assertIn("AGENTFORGE v2.0.0", content)
        self.assertIn("glm-5.3-flash", content)
        self.assertIn("file_read", content)
        self.assertIn("calculate", content)
        self.assertIn("100% PASS", content)

        # Clean up
        if os.path.exists(res_file):
            os.remove(res_file)

    def test_03_cmd_replay_cli(self):
        """Test slash command /replay."""
        res = cmd_replay(self.agent, ["workspace/test_cli_replay.html"])
        self.assertIn("[✓] Session Replay HTML berhasil diekspor", res)
        self.assertTrue(os.path.exists("workspace/test_cli_replay.html"))
        if os.path.exists("workspace/test_cli_replay.html"):
            os.remove("workspace/test_cli_replay.html")


if __name__ == "__main__":
    unittest.main()
