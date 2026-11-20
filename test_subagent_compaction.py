# test_subagent_compaction.py — Test Suite for Subagent Swarm Delegation and Context Compaction
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from agent.core import Agent
from agent.compaction import ContextCompactor
from agent.subagent import SubagentSwarm


class TestSubagentAndCompaction(unittest.TestCase):
    def setUp(self):
        self.agent = Agent("config.json")

    def test_01_context_compactor(self):
        """Test compaction preserves user goal, summarizes intermediary messages, and keeps tail."""
        compactor = ContextCompactor(token_threshold=500, target_token_size=200)
        
        # Build memory exceeding threshold
        memory = [{"role": "user", "content": "INITIAL_GOAL: Design a scalable microservice architecture"}]
        for i in range(15):
            memory.append({"role": "assistant", "content": f"Working turn {i}: calling tools and analyzing dependencies. " * 8})
            memory.append({"role": "tool", "name": "web_search", "content": f"Search result data payload for step {i}. " * 12})
        memory.append({"role": "user", "content": "RECENT_PROMPT: Please finalize Redis session caching"})
        memory.append({"role": "assistant", "content": "RECENT_REPLY: Here is the redis struct implementation"})

        self.assertTrue(compactor.should_compact(memory))
        compacted, stats = compactor.compact(memory)

        self.assertTrue(stats["compacted"])
        self.assertLess(stats["after_tokens"], stats["before_tokens"])
        
        # Ensure initial goal preserved
        self.assertEqual(compacted[0]["content"], "INITIAL_GOAL: Design a scalable microservice architecture")
        # Ensure compaction notice in middle
        self.assertIn("SYSTEM CONTEXT COMPACTION", compacted[1]["content"])
        # Ensure recent tail message preserved
        self.assertIn("RECENT_REPLY: Here is the redis struct implementation", compacted[-1]["content"])

    def test_02_subagent_swarm_delegation(self):
        """Test subagent delegation execution with mock LLM response."""
        swarm = SubagentSwarm(self.agent)
        
        # Test delegation dispatch logic with a mock LLM return to avoid remote API rate-limit
        def mock_llm(system: str, messages: list, tools: bool = True):
            return {
                "role": "assistant",
                "content": "ResearcherAgent: Connection pool benchmark complete: 8.4ms average latency across 100k requests.",
                "tool_calls": []
            }
        setattr(self.agent, "_mock_llm", mock_llm)
        try:
            res = swarm.delegate_task(
                role="researcher",
                goal="Analyze go-redis connection pooling latency",
                context="System constraint: sub-10ms latency required"
            )
            self.assertEqual(res["role"], "researcher")
            self.assertEqual(res["goal"], "Analyze go-redis connection pooling latency")
            self.assertTrue(res["ok"])
            self.assertIn("Connection pool benchmark complete", res["answer"])
        finally:
            delattr(self.agent, "_mock_llm")

    def test_03_tool_router_has_delegate_task(self):
        """Ensure delegate_task tool is registered in ToolRouter schemas."""
        schemas = self.agent.router.schemas()
        t_names = [s["function"]["name"] for s in schemas]
        self.assertIn("delegate_task", t_names)

        # Test schema attributes
        d_schema = next(s for s in schemas if s["function"]["name"] == "delegate_task")
        props = d_schema["function"]["parameters"]["properties"]
        self.assertIn("role", props)
        self.assertIn("goal", props)


if __name__ == "__main__":
    unittest.main()
