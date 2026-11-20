
import json, os
from datetime import datetime
from zoneinfo import ZoneInfo

WIB = ZoneInfo("Asia/Jakarta")


def export_session(agent, path=None):
    """Session → JSON file. Mekanisme: memory + trace + stats."""
    ts = datetime.now(WIB).strftime("%Y%m%d_%H%M%S")
    path = path or f"{agent.workspace}/sessions/session_{ts}.json"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    payload = {"exported_wib": ts, "model": agent.model,
               "model_chain": agent.model_chain, "memory": agent.memory,
               "run_log": agent.run_log, "stats": agent.run_stats}
    with open(path, "w") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    return path


def import_session(agent, path):
    """Session dari JSON file → memory balik. Mekanisme balik."""
    if not os.path.exists(path):
        return {"ok": False, "error": f"file tidak ada: {path}"}
    d = json.load(open(path))
    agent.memory = d.get("memory", [])
    agent.run_log = d.get("run_log", [])
    agent.run_stats = d.get("stats", agent.run_stats)
    return {"ok": True, "path": path, "turns": len(agent.memory),
            "exported_wib": d.get("exported_wib")}


def session_stats(agent):
    """Stats run: tool count, quota, duration, veritas verdict."""
    log = f"{agent.workspace}/log/runs.jsonl"
    runs = []
    if os.path.exists(log):
        for line in open(log):
            line = line.strip()
            if line:
                runs.append(json.loads(line))
    tools = {}
    for r in runs:
        for t in r.get("trace", []):
            if t.get("type") == "tool":
                tools[t.get("name", "?")] = tools.get(t.get("name", "?"), 0) + 1
    return {"total_runs": len(runs), "tool_use": tools,
            "model": agent.model, "chain": agent.model_chain,
            "budget_tokens": agent.token_budget, "used_tokens": agent.tokens_used}
