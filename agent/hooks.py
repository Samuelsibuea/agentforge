# agent/hooks.py — event hooks (hooks: PreToolUse/PostToolUse/SessionStart).
# Config: hooks = {"session_start": [...], "pre_tool": [...], "post_tool": [...],
#                  "tool_approve": [...], "session_end": [...]}
# Tiap entry: {"type": "log"|"deny"|"block"|"allow", "match": "<tool>", "reason": "..."}
# "log" = catat saja. "deny"/"block" = tolak tool (match boleh kosong = semua tool).

class HookEngine:
    def __init__(self, cfg):
        self.cfg = cfg or {}
        self.fired = []

    def _entries(self, event):
        return self.cfg.get(event, []) or []

    def fire(self, event, **ctx):
        """Return verdict dict. deny/block True berarti tool ditolak."""
        verdict = {"deny": False, "block": False, "reason": ""}
        for entry in self._entries(event):
            match = entry.get("match")
            tool = ctx.get("tool")
            if match and tool and match not in tool and tool not in match:
                continue
            typ = entry.get("type", "log")
            rec = {"event": event, "type": typ, "tool": tool,
                   "reason": entry.get("reason", "")}
            self.fired.append(rec)
            if typ == "deny":
                verdict["deny"] = True
                verdict["reason"] = entry.get("reason", "denied by hook")
            elif typ == "block":
                verdict["block"] = True
                verdict["reason"] = entry.get("reason", "blocked by hook")
        return verdict

    def summary(self):
        return {"fired": len(self.fired), "events": self.fired[-10:]}
