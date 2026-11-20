# test_modes.py — Comprehensive Test Suite for AgentForge Execution Modes
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from agent.core import Agent
from agent.modes import ModeEngine, MODES, encode_image_to_data_uri
from agent.commands import cmd_mode


class TestExecutionModes(unittest.TestCase):
    def setUp(self):
        self.agent = Agent("config.json")

    def test_01_mode_engine_registration_and_switching(self):
        """Verify all 6 execution modes are registered and switchable."""
        engine = ModeEngine()
        expected_modes = ["auto", "plan", "fast", "reasoning", "vision", "workflow"]
        for m in expected_modes:
            self.assertIn(m, MODES)
            ok, msg = engine.set_mode(m)
            self.assertTrue(ok)
            self.assertEqual(engine.current_mode, m)
            spec = engine.get_mode_spec()
            self.assertIn("name", spec)
            self.assertIn("system_prefix", spec)

        # Invalid mode handling
        ok, msg = engine.set_mode("unknown_mode")
        self.assertFalse(ok)

    def test_02_mode_prompt_injection(self):
        """Verify execution mode system prompt prefix is injected into agent run prompt."""
        engine = ModeEngine("reasoning")
        base = "You are a software engineer."
        injected = engine.apply_to_prompt(base)
        self.assertIn("REASONING (Deep Thinking)", injected)
        self.assertIn("<thinking>", injected)

        # Plan mode
        engine.set_mode("plan")
        plan_injected = engine.apply_to_prompt(base)
        self.assertIn("PLAN (Read-Only Planning)", plan_injected)

    def test_03_cmd_mode_in_agent_commands(self):
        """Test slash command /mode via agent command router."""
        # List modes
        listing = cmd_mode(self.agent, [])
        self.assertIn("Daftar Execution Modes", listing)
        self.assertIn("fast", listing)
        self.assertIn("reasoning", listing)

        # Switch to fast mode
        res = cmd_mode(self.agent, ["fast"])
        self.assertIn("[✓] Execution Mode diganti ke: Fast (Flash) Mode", res)
        self.assertEqual(self.agent.modes.current_mode, "fast")
        self.assertEqual(self.agent.approval_mode, "yolo")

        # Switch to plan mode
        res_plan = cmd_mode(self.agent, ["plan"])
        self.assertIn("[✓] Execution Mode diganti ke: Plan Mode", res_plan)
        self.assertEqual(self.agent.modes.current_mode, "plan")
        self.assertEqual(self.agent.approval_mode, "ask")

    def test_04_encode_image_to_data_uri(self):
        """Verify vision mode image encoder generates valid base64 data URI."""
        img_path = "assets/logo-mark.png"
        uri = encode_image_to_data_uri(img_path)
        self.assertTrue(uri.startswith("data:image/png;base64,"))
        self.assertGreater(len(uri), 1000)


if __name__ == "__main__":
    unittest.main()
