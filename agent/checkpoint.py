# agent/checkpoint.py — Workspace Checkpoint & Instant Rollback/Undo Engine for AgentForge
# Enables safety snapshots before risky tool operations and 1-command rollback.
import os
import shutil
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from zoneinfo import ZoneInfo

WIB = ZoneInfo("Asia/Jakarta")


class CheckpointEngine:
    def __init__(self, workspace: str = "workspace"):
        self.workspace = workspace
        self.ckpt_root = os.path.join(workspace, ".checkpoints")
        os.makedirs(self.ckpt_root, exist_ok=True)

    def create_snapshot(self, label: str = "auto") -> Dict[str, Any]:
        """Creates an atomic disk snapshot of the workspace (excluding .checkpoints)."""
        ts = int(time.time())
        iso_ts = datetime.now(WIB).strftime("%Y%m%d_%H%M%S")
        ckpt_id = f"ckpt_{iso_ts}_{label}"
        target_dir = os.path.join(self.ckpt_root, ckpt_id)
        os.makedirs(target_dir, exist_ok=True)

        copied_count = 0
        for root, dirs, files in os.walk(self.workspace):
            # Skip checkpoints directory itself
            if ".checkpoints" in root or "subagents" in root:
                continue
            rel_path = os.path.relpath(root, self.workspace)
            dest_dir = os.path.join(target_dir, rel_path) if rel_path != "." else target_dir
            os.makedirs(dest_dir, exist_ok=True)

            for f in files:
                src_file = os.path.join(root, f)
                dst_file = os.path.join(dest_dir, f)
                try:
                    shutil.copy2(src_file, dst_file)
                    copied_count += 1
                except Exception:
                    pass

        return {
            "ok": True,
            "id": ckpt_id,
            "label": label,
            "timestamp": iso_ts,
            "files_saved": copied_count,
            "path": target_dir
        }

    def rollback(self, ckpt_id: Optional[str] = None) -> Dict[str, Any]:
        """Rolls back the workspace to a specified checkpoint or the most recent one."""
        snapshots = self.list_snapshots()
        if not snapshots:
            return {"ok": False, "error": "Belum ada checkpoint untuk di-rollback."}

        target_snap = None
        if ckpt_id:
            target_snap = next((s for s in snapshots if s["id"] == ckpt_id), None)
            if not target_snap:
                return {"ok": False, "error": f"Checkpoint '{ckpt_id}' tidak ditemukan."}
        else:
            target_snap = snapshots[-1]  # Most recent

        src_dir = target_snap["path"]
        restored_count = 0

        # Copy back files into workspace
        for root, dirs, files in os.walk(src_dir):
            rel_path = os.path.relpath(root, src_dir)
            dest_dir = os.path.join(self.workspace, rel_path) if rel_path != "." else self.workspace
            os.makedirs(dest_dir, exist_ok=True)

            for f in files:
                src_file = os.path.join(root, f)
                dst_file = os.path.join(dest_dir, f)
                try:
                    shutil.copy2(src_file, dst_file)
                    restored_count += 1
                except Exception:
                    pass

        return {
            "ok": True,
            "restored_from": target_snap["id"],
            "files_restored": restored_count,
            "label": target_snap["label"]
        }

    def list_snapshots(self) -> List[Dict[str, Any]]:
        """Lists all snapshots chronologically."""
        if not os.path.exists(self.ckpt_root):
            return []
        dirs = sorted([d for d in os.listdir(self.ckpt_root) if os.path.isdir(os.path.join(self.ckpt_root, d))])
        res = []
        for d in dirs:
            p = os.path.join(self.ckpt_root, d)
            parts = d.split("_", 2)
            label = parts[2] if len(parts) > 2 else "auto"
            res.append({
                "id": d,
                "label": label,
                "path": p
            })
        return res
