# test_cli_wireframe.py — Automated Test Suite for AgentForge CLI v2.0.0
# Verifies 1:1 mapping with Prototype & Wireframe Spec (WF-01 to WF-12)

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from agent.core import Agent
from agent.tui import TUI, LOGO_ROWS, DEFAULT_FILES


class TestAgentForgeCLIWireframe(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.agent = Agent("config.json")

    def setUp(self):
        self.tui = TUI(self.agent)

    def test_T01_logo_mark_rendered_in_header(self):
        """WF-01: AgentForge RGB Logo rendered with proper half-block resolution and geometry"""
        self.assertEqual(len(LOGO_ROWS), 4, "Logo mark must have 4 half-block rows")
        hdr_frag = self.tui._header_frag()
        self.assertTrue(len(hdr_frag) > 30, "Header must contain logo and telemetry tokens")
        # Check title and version in header
        tokens_text = "".join(txt for _, txt in hdr_frag)
        self.assertIn("AGENT FORGE", tokens_text)
        self.assertIn("v2.0.0", tokens_text)
        self.assertIn("4 active", tokens_text)
        self.assertIn("12ms", tokens_text)

    def test_T02_live_session_and_coder_agent_code(self):
        """WF-04: Live session screen shows CoderAgent active file and Pipeline() call"""
        self.tui.active_screen = "live"
        self.tui.active_file = "redis.go"
        code_frag = self.tui._code_card_frag()
        code_text = "".join(txt for _, txt in code_frag)
        self.assertIn("CoderAgent", code_text)
        self.assertIn("internal/cache/redis.go", code_text)
        self.assertIn("Pipeline()", code_text)

    def test_T03_file_tabs_switch(self):
        """WF-04: File switching between redis.go -> session.proto -> session_server.go"""
        self.assertEqual(self.tui.active_file, "redis.go")
        self.tui.cycle_file()
        self.assertEqual(self.tui.active_file, "session.proto")
        proto_frag = self.tui._code_card_frag()
        self.assertIn("proto/session.proto", "".join(txt for _, txt in proto_frag))

        self.tui.cycle_file()
        self.assertEqual(self.tui.active_file, "session_server.go")
        server_frag = self.tui._code_card_frag()
        self.assertIn("internal/grpc/session_server.go", "".join(txt for _, txt in server_frag))

        self.tui.cycle_file()
        self.assertEqual(self.tui.active_file, "redis.go")

    def test_T04_review_and_apply_screen_and_staging(self):
        """WF-11: Review & Apply screen displays 3 staged files with diffs"""
        self.tui.handle_command("/diff")
        self.assertEqual(self.tui.active_screen, "review")
        rev_frag = self.tui._review_screen_frag()
        rev_text = "".join(txt for _, txt in rev_frag)
        self.assertIn("internal/cache/redis.go", rev_text)
        self.assertIn("proto/session.proto", rev_text)
        self.assertIn("internal/grpc/session_server.go", rev_text)
        self.assertIn("STAGED", rev_text)

    def test_T05_cluster_screen_pause_resume_and_prompt_inspect(self):
        """WF-12: Cluster screen allows pausing/resuming agents and inspecting prompt"""
        self.tui.handle_command("/cluster")
        self.assertEqual(self.tui.active_screen, "cluster")

        # Toggle researcher pause
        self.assertFalse(self.tui.agents[0]["paused"])
        self.tui.agents[0]["paused"] = True
        self.assertTrue(self.tui.agents[0]["paused"])
        self.tui.agents[0]["paused"] = False
        self.assertFalse(self.tui.agents[0]["paused"])

        # Inspect prompt for Coder
        self.tui.inspected_prompt_agent_id = "coder"
        clust_frag = self.tui._cluster_screen_frag()
        clust_text = "".join(txt for _, txt in clust_frag)
        self.assertIn("SYSTEM [CoderAgent]", clust_text)

    def test_T06_command_palette_command(self):
        """WF-09: Quick command palette commands handle help and actions"""
        self.tui.handle_command("/help")
        chat_text = "".join(txt for _, txt in self.tui.chat_log)
        self.assertIn("/diff", chat_text)
        self.assertIn("/apply", chat_text)
        self.assertIn("/test", chat_text)
        self.assertIn("/agents", chat_text)

    def test_T07_cli_diff_command(self):
        """WF-09/11: /diff switches to review screen"""
        self.tui.active_screen = "live"
        self.tui.handle_command("/diff")
        self.assertEqual(self.tui.active_screen, "review")

    def test_T08_cli_apply_writes_staged_files(self):
        """WF-11: /apply commits staged files and records log"""
        self.assertFalse(self.tui.applied)
        self.tui.handle_command("/apply")
        self.assertTrue(self.tui.applied)
        self.assertEqual(self.tui.active_screen, "review")
        rev_text = "".join(txt for _, txt in self.tui._review_screen_frag())
        self.assertIn("APPLIED TO DISK", rev_text)

    def test_T09_cli_test_runs_go_tests(self):
        """WF-07/11: /test runs unit and benchmark suites and marks task 4 done"""
        self.assertEqual(self.tui.tasks[3]["status"], "PENDING")
        self.tui.handle_command("/test")
        self.assertEqual(self.tui.tasks[3]["status"], "DONE")
        self.assertEqual(self.tui.tasks[3]["progress"], 100)
        self.assertTrue(len(self.tui.test_output) > 0)
        self.assertIn("PASS", self.tui.test_output[-1])

    def test_T10_cli_agents_cycle(self):
        """WF-06: /agents cycles focused agent through swarm"""
        self.assertEqual(self.tui.focused_agent_id, "coder")
        self.tui.handle_command("/agents")
        self.assertEqual(self.tui.focused_agent_id, "reviewer")
        self.tui.cycle_agent()
        self.assertEqual(self.tui.focused_agent_id, "researcher")
        self.tui.cycle_agent()
        self.assertEqual(self.tui.focused_agent_id, "architect")
        self.tui.cycle_agent()
        self.assertEqual(self.tui.focused_agent_id, "coder")

    def test_T11_pause_command_toggles_state(self):
        """WF-01: /pause toggles global session pause state"""
        self.assertFalse(self.tui.is_paused)
        self.tui.handle_command("/pause")
        self.assertTrue(self.tui.is_paused)
        self.tui.handle_command("/pause")
        self.assertFalse(self.tui.is_paused)

    def test_T12_custom_task_prompt_updates_metrics(self):
        """WF-08/10: Natural language task updates token counter, cost, and live log"""
        tok_before = self.tui.tokens_used
        cost_before = self.tui.cost
        self.tui.handle_command("Add Redis connection retry backoff")
        self.assertGreater(self.tui.tokens_used, tok_before)
        self.assertGreater(self.tui.cost, cost_before)
        log_bodies = [l["body"] for l in self.tui.live_logs]
        self.assertTrue(any("retry backoff" in b for b in log_bodies))


if __name__ == "__main__":
    unittest.main()
