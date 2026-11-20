# tools/router.py — tool registry + dispatcher. Semua tool return dict {ok, data/error}.
import importlib, json, time
from datetime import datetime
from zoneinfo import ZoneInfo

WIB = ZoneInfo("Asia/Jakarta")

SCHEMAS = {
    "web_search": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Query pencarian"},
            "count": {"type": "integer", "description": "Jumlah hasil (default 8)"},
        },
        "required": ["query"],
    },
    "web_fetch": {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL halaman yang diambil"},
            "max_chars": {"type": "integer", "description": "Maksimal karakter teks (default 4000)"},
        },
        "required": ["url"],
    },
    "file_read": {
        "type": "object",
        "properties": {"path": {"type": "string", "description": "Path file relatif terhadap root repo"}},
        "required": ["path"],
    },
    "file_write": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path file relatif terhadap root repo"},
            "content": {"type": "string", "description": "Isi file (string penuh)"},
        },
        "required": ["path", "content"],
    },
    "file_patch": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path file relatif terhadap root repo"},
            "old_hash": {"type": "string", "description": "sha256(file)[:8] saat file dibaca (stale → reject)"},
            "new_content": {"type": "string", "description": "Isi baru file (string penuh)"},
        },
        "required": ["path", "old_hash", "new_content"],
    },
    "file_list": {
        "type": "object",
        "properties": {"dir": {"type": "string", "description": "Folder relatif (default workspace)"}},
    },
    "calculate": {
        "type": "object",
        "properties": {"expression": {"type": "string", "description": "Ekspresi aritmatika"}},
        "required": ["expression"],
    },
}

class ToolRouter:
    QUOTA = {"web_search": 3, "web_fetch": 3, "file_write": 2}

    def __init__(self, workspace="workspace"):
        self.workspace = workspace
        self.tools = {}
        self.used = {}
        self._load_builtin()
        self.log_path = f"{workspace}/log/runs.jsonl"

    def _load_builtin(self):
        from tools import web, files, calc, patch
        for fn in (web.web_search, web.web_fetch,
                   files.file_read, files.file_write, files.file_list,
                   calc.calculate, patch.file_patch):
            self.register(fn)

    def register(self, fn):
        name = fn.__name__
        mcp_schema = getattr(fn, "_mcp_schema", None)
        if mcp_schema:
            schema_params = mcp_schema["function"].get("parameters", {})
            desc = mcp_schema["function"].get("description", fn.__doc__ or "")
        else:
            schema_params = SCHEMAS[name]
            desc = (fn.__doc__ or "").strip()

        self.tools[name] = {
            "name": name,
            "description": desc,
            "parameters": schema_params,
            "fn": fn,
        }
        self.used[name] = 0

    def schemas(self):
        out = []
        for t in self.tools.values():
            out.append({
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t["parameters"],
                },
            })
        return out

    def call(self, name, args):
        t0 = time.time()
        entry = {"ts": datetime.now(WIB).isoformat(), "tool": name, "args": args}
        if name not in self.tools:
            entry.update(ok=False, error=f"unknown tool: {name}")
            self._log(entry); return {"ok": False, "error": entry["error"]}
        # QUOTA: cegah model search forever / file_write raksasa yang truncate
        q = self.QUOTA.get(name)
        if q is not None and self.used.get(name, 0) >= q:
            msg = f"quota {name} habis ({q}x). Lanjut ke sintesis + jawab final."
            entry.update(ok=False, error=msg)
            self._log(entry); return {"ok": False, "error": msg}
        self.used[name] = self.used.get(name, 0) + 1
        try:
            res = self.tools[name]["fn"](**args)
            dur = round(time.time() - t0, 2)
            entry.update(ok=True, dur_s=dur,
                         result_preview=json.dumps(res, ensure_ascii=False)[:300])
            self._log(entry)
            return res
        except Exception as e:
            entry.update(ok=False, error=str(e))
            self._log(entry)
            return {"ok": False, "error": str(e)}

    def _log(self, entry):
        import os
        os.makedirs(self.log_path.rsplit("/", 1)[0], exist_ok=True)
        with open(self.log_path, "a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
