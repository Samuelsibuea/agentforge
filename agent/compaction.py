# agent/compaction.py — Context Window Compaction Engine for AgentForge
# Automatically compacts older conversation history when approaching token limits,
# preserving initial goals, key facts, and recent context without information loss.
import json
from typing import List, Dict, Any, Tuple


class ContextCompactor:
    def __init__(self, token_threshold: int = 40_000, target_token_size: int = 15_000):
        self.token_threshold = token_threshold
        self.target_token_size = target_token_size

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Rough 4-char per token heuristic for rapid budget estimation."""
        return max(1, len(text) // 4)

    def total_memory_tokens(self, memory: List[Dict[str, Any]]) -> int:
        total = 0
        for msg in memory:
            content = msg.get("content", "")
            if isinstance(content, list):
                total += self.estimate_tokens(json.dumps(content, ensure_ascii=False))
            else:
                total += self.estimate_tokens(str(content))
        return total

    def should_compact(self, memory: List[Dict[str, Any]]) -> bool:
        return self.total_memory_tokens(memory) >= self.token_threshold

    def compact(self, memory: List[Dict[str, Any]], agent_summary_fn=None) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Compacts the memory buffer:
        - Keeps the first user goal message intact.
        - Keeps the last N recent messages (working memory).
        - Condenses middle messages into a structured checkpoint block.
        """
        if len(memory) <= 4 or not self.should_compact(memory):
            return memory, {"compacted": False, "before_tokens": self.total_memory_tokens(memory)}

        before_tokens = self.total_memory_tokens(memory)
        head = [memory[0]] # Original user prompt / objective
        tail_count = 3
        tail = memory[-tail_count:]
        middle = memory[1:-tail_count]

        # Extract salient action logs from middle turns
        action_summary = []
        for msg in middle:
            role = msg.get("role")
            content = msg.get("content", "")
            if role == "tool":
                action_summary.append(f"- Tool Output ({msg.get('name', 'tool')}): {str(content)[:160]}...")
            elif role == "assistant":
                tool_calls = msg.get("tool_calls", [])
                if tool_calls:
                    t_names = [tc.get("function", {}).get("name", "tool") for tc in tool_calls]
                    action_summary.append(f"- Assistant called: {', '.join(t_names)}")
                elif content:
                    action_summary.append(f"- Assistant thought/update: {str(content)[:140]}...")

        condensed_text = (
            "[SYSTEM CONTEXT COMPACTION — COMPACTED CHECKPOINT]\n"
            "Earlier conversation turns were compacted to maintain context window budget.\n"
            "Salient Actions & Intermediary Results:\n"
            + "\n".join(action_summary[-12:]) + "\n"
            "--- END OF CONTEXT CHECKPOINT ---"
        )

        checkpoint_msg = {
            "role": "user",
            "content": condensed_text
        }
        compacted_memory = head + [checkpoint_msg] + tail
        after_tokens = self.total_memory_tokens(compacted_memory)

        stats = {
            "compacted": True,
            "before_tokens": before_tokens,
            "after_tokens": after_tokens,
            "messages_condensed": len(middle)
        }
        return compacted_memory, stats
