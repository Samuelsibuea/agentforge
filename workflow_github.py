# workflow_github.py — Autonomous GitHub Issue & Repository Maintenance Workflow
# Reads an issue/PR description or user repo query, inspects the codebase using tools,
# and generates a complete patch analysis report with verification trace.
import sys
import os
import json

from agent.core import Agent


def run_github_workflow(issue_or_task: str):
    print("=" * 72)
    print("  AGENTFORGE — AUTONOMOUS GITHUB REPOSITORY MAINTAINER WORKFLOW")
    print("=" * 72)
    print(f"[github-workflow] Target Task / Issue: {issue_or_task}\n")

    agent = Agent("config.json")
    agent.skill = "coding"

    task_prompt = (
        f"You are the autonomous repository maintainer for this project.\n"
        f"Issue / Request: {issue_or_task}\n\n"
        f"Instructions:\n"
        f"1. Inspect relevant files using file_read or file_list.\n"
        f"2. Formulate a verified solution and describe changes.\n"
        f"3. Generate a structured Markdown report in workspace/output/.\n"
    )

    out = agent.run(task_prompt, skill="coding", verbose=True)
    ans = out.get("answer") or out.get("error") or ""
    print("\n" + "=" * 72)
    print("  WORKFLOW EXECUTION COMPLETE")
    print("=" * 72)
    print(f"Artefact: {out.get('artefak')}")
    print(f"Tool calls executed: {out.get('stats', {}).get('tool_calls', 0)}")
    return out


if __name__ == "__main__":
    query = sys.argv[1] if len(sys.argv) > 1 else "Audit repository structure, check tool definitions, and verify coding standards."
    run_github_workflow(query)
