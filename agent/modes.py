# agent/modes.py — Execution Modes Engine for AgentForge
# Supports Plan, Auto, Fast (Flash), Reasoning (Thinking), Vision, and Workflow modes.
import base64
import os
import mimetypes
from typing import Dict, Any, Optional, Tuple


MODES = {
    "auto": {
        "name": "Auto Mode",
        "description": "Standard balanced autonomous agent loop with auto tool execution and Veritas checks.",
        "model_pref": "glm-5.3-flash",
        "approval": "yolo",
        "system_prefix": "Mode: AUTO (Autonomous execution). Execute necessary tools decisively to fulfill the task.",
    },
    "plan": {
        "name": "Plan Mode",
        "description": "Drafts structured step-by-step architectural execution plans before taking actions (read-only safe).",
        "model_pref": "glm-5.3-flash",
        "approval": "ask",
        "system_prefix": (
            "Mode: PLAN (Read-Only Planning). Formulate a comprehensive, phased execution plan. "
            "Do NOT perform state-mutating actions (file writes, deletes) until explicitly approved. "
            "Inspect files and outline architectural steps."
        ),
    },
    "fast": {
        "name": "Fast (Flash) Mode",
        "description": "Ultra-low latency execution mode prioritizing speed and concise output without heavy subagent steps.",
        "model_pref": "glm-5.3-flash",
        "approval": "yolo",
        "system_prefix": "Mode: FAST (Flash Low-Latency). Respond with extreme brevity, zero fluff, and minimal tool overhead.",
    },
    "reasoning": {
        "name": "Reasoning (Thinking) Mode",
        "description": "Deep thinking mode with explicit multi-step chain-of-thought verification and edge-case probing.",
        "model_pref": "glm-5.3-flash",
        "approval": "write",
        "system_prefix": (
            "Mode: REASONING (Deep Thinking). Before providing any final answer or executing critical tools, "
            "generate explicit internal chain-of-thought reasoning inside <thinking>...</thinking> tags: "
            "evaluate assumptions, hypothesize edge cases, and verify mathematical/logical invariants."
        ),
    },
    "vision": {
        "name": "Vision Mode",
        "description": "Multimodal image understanding and inspection mode (PNG, JPG, WEBP base64 encoding).",
        "model_pref": "glm-5.3-flash",
        "approval": "ask",
        "system_prefix": "Mode: VISION (Multimodal Inspection). Analyze visual artifacts, screenshots, layout geometries, and UI tokens.",
    },
    "workflow": {
        "name": "Workflow Mode",
        "description": "Structured multi-stage pipeline: Research -> Architecture Contract -> Implementation -> Verification Report.",
        "model_pref": "glm-5.3-flash",
        "approval": "write",
        "system_prefix": (
            "Mode: WORKFLOW (End-to-End Pipeline). Coordinate sequentially: "
            "1. Gather requirements. 2. Design schema. 3. Execute implementation. 4. Write full verified report in workspace/output/."
        ),
    }
}


class ModeEngine:
    def __init__(self, default_mode: str = "auto"):
        self.current_mode: str = default_mode.lower() if default_mode.lower() in MODES else "auto"

    def set_mode(self, mode: str) -> Tuple[bool, str]:
        m = mode.lower().strip()
        if m not in MODES:
            return False, f"Mode '{mode}' tidak dikenal. Pilihan: {', '.join(MODES.keys())}"
        self.current_mode = m
        return True, f"[✓] Execution Mode diganti ke: {MODES[m]['name']} ({MODES[m]['description']})"

    def get_mode_spec(self) -> Dict[str, Any]:
        return MODES.get(self.current_mode, MODES["auto"])

    def apply_to_prompt(self, base_prompt: str) -> str:
        spec = self.get_mode_spec()
        return f"{spec['system_prefix']}\n\n{base_prompt}"

    def list_modes(self) -> str:
        lines = ["Daftar Execution Modes di AgentForge:"]
        for k, v in MODES.items():
            mark = "★ (Aktif)" if k == self.current_mode else " "
            lines.append(f"{mark} • {k:<10} — {v['name']}: {v['description']}")
        return "\n".join(lines)


def encode_image_to_data_uri(image_path: str) -> str:
    """Encodes a local image file to a base64 Data URI for multimodal LLM vision payloads."""
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Gambar tidak ditemukan: {image_path}")
    
    mime_type, _ = mimetypes.guess_type(image_path)
    if not mime_type:
        mime_type = "image/png"

    with open(image_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")
    return f"data:{mime_type};base64,{encoded}"
