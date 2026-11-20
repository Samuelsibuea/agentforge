# test_user_extensibility.py — Test Suite for User-Created Tools, Custom Skills, and Marketplace Catalog
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from agent.core import Agent
from agent.commands import cmd_tool, cmd_skill_manage


class TestUserExtensibility(unittest.TestCase):
    def setUp(self):
        self.agent = Agent("config.json")
        os.makedirs("tools/custom", exist_ok=True)
        os.makedirs("skills", exist_ok=True)

    def test_01_create_custom_tool_live(self):
        """User creates a custom python tool live via /tool create and calls it through ToolRouter."""
        tool_code = """
def get_weather_forecast(city: str, days: int = 3) -> dict:
    '''Fetch weather forecast for a target city.'''
    return {"ok": True, "city": city, "forecast": f"Sunny {days} days ahead"}
"""
        res = cmd_tool(self.agent, ["create", "weather_tool", tool_code])
        self.assertIn("[✓] Tool 'weather_tool' berhasil dibuat", res)

        # Verify tool is loaded in ToolRouter
        self.assertIn("get_weather_forecast", self.agent.router.tools)
        
        # Call the user-created tool
        out = self.agent.router.call("get_weather_forecast", {"city": "Jakarta", "days": 5})
        self.assertTrue(out.get("ok"))
        self.assertIn("Sunny 5 days ahead", str(out.get("forecast")))

        # Clean up custom tool file
        if os.path.exists("tools/custom/weather_tool.py"):
            os.remove("tools/custom/weather_tool.py")

    def test_02_create_custom_skill_live(self):
        """User creates a custom skill via /skill create and immediately activates it."""
        skill_prompt = "You are an Elite Rust Systems Engineer. Enforce zero-cost abstractions."
        res = cmd_skill_manage(self.agent, ["create", "rust-guru", skill_prompt])
        self.assertIn("[✓] Skill 'rust-guru' berhasil dibuat", res)
        self.assertEqual(self.agent.skill, "rust-guru")

        # Verify file exists
        p = "skills/rust-guru.md"
        self.assertTrue(os.path.exists(p))
        content = open(p).read()
        self.assertIn("Elite Rust Systems Engineer", content)

        # Clean up
        if os.path.exists(p):
            os.remove(p)

    def test_03_skill_catalog_and_install(self):
        """User inspects ecosystem skill catalog and installs a preset."""
        cat = cmd_skill_manage(self.agent, ["catalog"])
        self.assertIn("Ecosystem Skill Marketplace", cat)
        self.assertIn("devops", cat)

        res = cmd_skill_manage(self.agent, ["install", "devops"])
        self.assertIn("[✓] Skill 'devops' terinstall", res)
        self.assertTrue(os.path.exists("skills/devops.md"))

        # Clean up
        if os.path.exists("skills/devops.md"):
            os.remove("skills/devops.md")


if __name__ == "__main__":
    unittest.main()
