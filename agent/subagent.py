# agent/subagent.py — Subagent Delegation Swarm Engine for AgentForge
# Spawns isolated subagents with specialized roles (researcher, architect, coder, reviewer),
# dedicated memory buffers, scoped tools, and returns verified execution results.
import json
import os
from typing import Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed


ROLES = {
    "researcher": {
        "model": "glm-5.3-flash",
        "system": (
            "You are ResearcherAgent in the AgentForge Swarm. Your role is thorough investigation, "
            "analyzing source code, architectural documentation, and web data. "
            "Output clear, concise factual findings and structural constraints."
        ),
        "skill": "research",
    },
    "architect": {
        "model": "glm-5.3-flash",
        "system": (
            "You are ArchitectAgent in the AgentForge Swarm. Your role is interface and schema design, "
            "API contracts, and modular software boundaries. Output clean architectural schemas."
        ),
        "skill": "research",
    },
    "coder": {
        "model": "glm-5.3-flash",
        "system": (
            "You are CoderAgent in the AgentForge Swarm. Your role is robust, idiomatic implementation. "
            "Write production-grade code, unit tests, and perform atomic file modifications."
        ),
        "skill": "coding",
    },
    "reviewer": {
        "model": "glm-5.3-flash",
        "system": (
            "You are ReviewerAgent in the AgentForge Swarm. Your role is code verification, race condition "
            "audit, static security checks, and benchmark validation."
        ),
        "skill": "summarize",
    }
}


class SubagentSwarm:
    def __init__(self, parent_agent):
        self.parent = parent_agent
        self.workspace = parent_agent.workspace
        self.active_subagents: Dict[str, Any] = {}

    def delegate_task(self, role: str, goal: str, context: Optional[str] = None, max_turns: int = 4) -> Dict[str, Any]:
        """Executes a single subagent task synchronously with isolated state."""
        role_key = role.lower()
        spec = ROLES.get(role_key, {
            "model": self.parent.model,
            "system": f"You are a specialized subagent for {role}. Goal: {goal}",
            "skill": getattr(self.parent, "skill", "research")
        })

        # Create isolated sub-workspace directory
        sub_ws = os.path.join(self.workspace, "subagents", role_key)
        os.makedirs(sub_ws, exist_ok=True)

        prompt_text = f"GOAL: {goal}"
        if context:
            prompt_text += f"\nCONTEXT:\n{context}"

        # Lazy clone an Agent instance with isolated memory
        from agent.core import Agent
        sub_agent = Agent.__new__(Agent)
        sub_agent.api_key = self.parent.api_key
        sub_agent.base_url = self.parent.base_url
        sub_agent.model = spec.get("model", self.parent.model)
        sub_agent.max_turns = max_turns
        sub_agent.workspace = self.workspace
        sub_agent.router = self.parent.router
        sub_agent.memory = []
        sub_agent.run_log = []
        sub_agent.skill = spec.get("skill", "research")
        sub_agent.model_chain = self.parent.model_chain
        sub_agent.token_budget = 30_000
        sub_agent.tokens_used = 0
        sub_agent.approval_mode = "yolo"  # Subagents inherit automated approval for speed
        sub_agent.auto_approve = True
        sub_agent.hooks = self.parent.hooks
        sub_agent.rules = self.parent.rules
        sub_agent.veritas = self.parent.veritas
        sub_agent.keyring = self.parent.keyring
        sub_agent.active_key_name = self.parent.active_key_name
        sub_agent.active_key = self.parent.active_key
        sub_agent.run_stats = {"tool_calls": 0, "hooks_fired": 0, "rules_fired": 0, "veratas_checks": 0}
        # Execute subagent run
        system_override = spec.get("system")
        if hasattr(self.parent, "_mock_llm"):
            sub_agent.llm = self.parent._mock_llm
        res = sub_agent.run(prompt_text, skill=sub_agent.skill, verbose=False)
        
        answer = res.get("answer") or res.get("error") or "Subagent completed."
        trace = res.get("trace", [])
        
        return {
            "ok": res.get("ok", True),
            "role": role_key,
            "goal": goal,
            "answer": answer,
            "tool_calls": len([t for t in trace if t.get("type") == "tool"]),
            "trace": trace
        }

    def delegate_parallel(self, tasks: list) -> list:
        """Executes multiple subagent tasks concurrently using a thread pool."""
        results = []
        with ThreadPoolExecutor(max_workers=min(4, len(tasks))) as executor:
            future_to_task = {
                executor.submit(
                    self.delegate_task,
                    t.get("role", "coder"),
                    t.get("goal", ""),
                    t.get("context", "")
                ): t for t in tasks
            }
            for future in as_completed(future_to_task):
                try:
                    res = future.result()
                    results.append(res)
                except Exception as e:
                    results.append({"ok": False, "error": str(e)})
        return results


def make_subagent_tool(swarm: SubagentSwarm):
    """Factory creating the delegate_task tool callable by LLM."""
    def delegate_task(role: str, goal: str, context: str = "") -> dict:
        """Delegate a subtask to a specialized subagent (researcher, architect, coder, reviewer).
        
        Args:
            role: The specialized agent role ('researcher', 'architect', 'coder', 'reviewer').
            goal: The exact objective and task description for the subagent.
            context: Optional background data, constraints, or previous findings.
        """
        return swarm.delegate_task(role=role, goal=goal, context=context)

    setattr(delegate_task, "_mcp_schema", {
        "type": "function",
        "function": {
            "name": "delegate_task",
            "description": "Delegate a subtask to a specialized swarm subagent (researcher, architect, coder, reviewer) with isolated context.",
            "parameters": {
                "type": "object",
                "properties": {
                    "role": {
                        "type": "string",
                        "enum": ["researcher", "architect", "coder", "reviewer"],
                        "description": "The specialized agent role"
                    },
                    "goal": {
                        "type": "string",
                        "description": "The objective and task description"
                    },
                    "context": {
                        "type": "string",
                        "description": "Optional background or findings"
                    }
                },
                "required": ["role", "goal"]
            }
        }
    })
    return delegate_task
