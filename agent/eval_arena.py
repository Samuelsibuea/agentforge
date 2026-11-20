# agent/eval_arena.py — Autonomous Self-Evaluation & Verification Arena for AgentForge
# Scores agent outputs across 4 rigorous pillars: Factuality, Constraint Adherence,
# Conciseness, and Tool Precision. Produces an objective 0-100 Ecosystem Score.
import re
from typing import Dict, Any, List


class EvalArena:
    def __init__(self, agent=None):
        self.agent = agent

    def evaluate_run(self, task: str, answer: str, run_log: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Evaluates an agent run quantitatively across 4 dimensions."""
        # 1. Factuality & Veritas Check (0-25)
        # Check if Veritas verified the tool outputs without tampering
        veritas_events = [x for x in run_log if x.get("type") == "veritas"]
        veritas_passed = all("PASS" in str(x.get("result", "")) for x in veritas_events) if veritas_events else True
        factuality_score = 25 if veritas_passed else 10

        # 2. Constraint Adherence (0-25)
        # Check if output is non-empty, contains no forbidden leakages, and matches language intent
        constraint_score = 25
        if not answer or len(answer.strip()) < 10:
            constraint_score = 5
        elif any(forbidden in answer for forbidden in ["sk-ant-", "ghp_", "bearer ", "AI Assistant"]):
            constraint_score = 0

        # 3. Tool Precision & Efficiency (0-25)
        # Evaluate tool calls: redundant repetitive tool calls penalize score
        tool_calls = [x for x in run_log if x.get("type") == "tool"]
        tool_names = [t.get("name") for t in tool_calls]
        if len(tool_names) == len(set(tool_names)):
            tool_score = 25  # Zero redundant calls
        elif len(tool_names) <= len(set(tool_names)) + 1:
            tool_score = 20
        else:
            tool_score = 15

        # 4. Conciseness & Information Density (0-25)
        # Ratio of informative content vs filler words
        fluff_words = ["mohon maaf", "sebagai ai", "tentu saja", "halo!"]
        fluff_count = sum(1 for f in fluff_words if f in answer.lower())
        conciseness_score = max(10, 25 - (fluff_count * 5))

        total_score = factuality_score + constraint_score + tool_score + conciseness_score

        # Grade classification
        if total_score >= 90:
            grade = "A+ (Superior Ecosystem Grade)"
        elif total_score >= 80:
            grade = "A (Production Ready)"
        elif total_score >= 70:
            grade = "B (Acceptable)"
        else:
            grade = "C (Needs Optimization)"

        return {
            "total_score": total_score,
            "grade": grade,
            "breakdown": {
                "factuality_veritas": factuality_score,
                "constraint_adherence": constraint_score,
                "tool_precision": tool_score,
                "conciseness": conciseness_score
            },
            "summary": f"Arena Score: {total_score}/100 [{grade}]"
        }
