# test_checkpoint.py — Unit Test Suite for Workspace Checkpoint and Instant Rollback Engine
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from agent.core import Agent
from agent.checkpoint import CheckpointEngine
from agent.commands import cmd_checkpoint


class TestCheckpointEngine(unittest.TestCase):
    def setUp(self):
        self.workspace = "workspace"
        os.makedirs(self.workspace, exist_ok=True)
        self.engine = CheckpointEngine(self.workspace)
        self.agent = Agent("config.json")

    def test_01_create_snapshot_and_rollback(self):
        """Verify snapshot creation, file mutation, and clean rollback."""
        test_file = os.path.join(self.workspace, "state_test.txt")
        with open(test_file, "w") as f:
            f.write("ORIGINAL_CONTENT_V1")

        # 1. Create snapshot
        snap = self.engine.create_snapshot("test_v1")
        self.assertTrue(snap["ok"])
        self.assertIn("ckpt_", snap["id"])

        # 2. Mutate file
        with open(test_file, "w") as f:
            f.write("CORRUPTED_OR_CHANGED_CONTENT_V2")

        # 3. Rollback
        res = self.engine.rollback(snap["id"])
        self.assertTrue(res["ok"])

        # 4. Verify original content restored
        with open(test_file, "r") as f:
            restored = f.read()
        self.assertEqual(restored, "ORIGINAL_CONTENT_V1")

        # Clean up
        if os.path.exists(test_file):
            os.remove(test_file)

    def test_02_cmd_checkpoint_cli(self):
        """Test slash command /checkpoint create and rollback."""
        res_create = cmd_checkpoint(self.agent, ["create", "cli_test"])
        self.assertIn("[✓] Checkpoint snapshot dibuat", res_create)

        res_ls = cmd_checkpoint(self.agent, ["ls"])
        self.assertIn("Daftar Snapshots:", res_ls)

        res_undo = cmd_checkpoint(self.agent, ["rollback"])
        self.assertIn("[✓] Workspace berhasil di-rollback", res_undo)


if __name__ == "__main__":
    unittest.main()
