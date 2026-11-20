# test_eval_arena.py — Test Suite for Autonomous Self-Evaluation & Verification Arena
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from agent.core import Agent
from agent.eval_arena import EvalArena
from agent.commands import cmd_eval


class TestEvalArena(unittest.TestCase):
    def setUp(self):
        self.agent = Agent("config.json")
        self.arena = EvalArena(self.agent)

    def test_01_evaluate_high_quality_run(self):
        """High quality run with Veritas PASS and clean tool calls should score >= 90 (Grade A+)."""
        run_log = [
            {"type": "tool", "name": "file_read", "args": {"path": "main.py"}, "result": "code content"},
            {"type": "veritas", "name": "dual_check", "args": {}, "result": "PASS"},
            {"type": "tool", "name": "calculate", "args": {"expr": "100 * 2"}, "result": "200"}
        ]
        task = "Hitung total memori dan baca konfigurasi."
        answer = "Analisis selesai. Total alokasi memori adalah 200MB berdasarkan verifikasi konfigurasi."

        res = self.arena.evaluate_run(task, answer, run_log)
        self.assertGreaterEqual(res["total_score"], 90)
        self.assertIn("A+", res["grade"])
        self.assertEqual(res["breakdown"]["factuality_veritas"], 25)
        self.assertEqual(res["breakdown"]["constraint_adherence"], 25)
        self.assertEqual(res["breakdown"]["tool_precision"], 25)

    def test_02_evaluate_fluffy_penalized_run(self):
        """Fluffy answers with redundant filler phrases receive conciseness penalty."""
        run_log = []
        task = "Jelaskan status sistem."
        answer = "Halo! Tentu saja, mohon maaf atas keterlambatan, sebagai ai saya laporkan sistem normal."

        res = self.arena.evaluate_run(task, answer, run_log)
        self.assertLess(res["breakdown"]["conciseness"], 25)

    def test_03_cmd_eval_cli(self):
        """Test slash command /eval in CLI environment."""
        self.agent.run_log = [
            {"type": "tool", "name": "calculate", "args": {"expr": "1+1"}, "result": "2"},
            {"type": "veritas", "name": "check", "args": {}, "result": "PASS"}
        ]
        self.agent.memory = [{"role": "user", "content": "Hitung 1+1"}]
        out = cmd_eval(self.agent, [])
        self.assertIn("AGENTFORGE SELF-EVALUATION ARENA SCORE", out)
        self.assertIn("Total Score :", out)
        self.assertIn("Factuality & Veritas", out)


if __name__ == "__main__":
    unittest.main()
