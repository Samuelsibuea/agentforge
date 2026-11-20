# agent/core.py — agent loop: LLM call (Kei), tool-call parse, memory, skill injection.
# Fallback chain, budget gate, approval ladder, hooks, stream rules, veritas.
import httpx, json, os, re, time
from datetime import datetime
from zoneinfo import ZoneInfo
from tools.router import ToolRouter
from agent.hooks import HookEngine
from agent.rules import RuleEngine
from agent.veritas import Veritas
from agent.keyring import KeyRing
from agent.mcp import MCPRegistry
from agent.compaction import ContextCompactor
from agent.subagent import SubagentSwarm, make_subagent_tool
from agent.modes import ModeEngine, encode_image_to_data_uri

WIB = ZoneInfo("Asia/Jakarta")

class Agent:
    def __init__(self, config_path="config.json"):
        with open(config_path) as f:
            cfg = json.load(f)
        self.api_key = cfg["api_key"]
        self.base_url = cfg["base_url"].rstrip("/")
        self.model = cfg.get("model", "glm-5.3-flash")
        self.max_turns = cfg.get("max_turns", 15)
        self.workspace = cfg.get("workspace", "workspace")
        self.router = ToolRouter(self.workspace)
        os.makedirs(f"{self.workspace}/output", exist_ok=True)
        os.makedirs(f"{self.workspace}/log", exist_ok=True)
        self.memory = []          # conversation buffer
        self.run_log = []         # tool-call trace (audit trail)
        self.skill = "research"   # active skill (loader: skills/<name>.md)
        # --- config turunan ---
        mcfg = cfg.get("models", {})
        self.model_chain = mcfg.get("chain", [self.model]) or [self.model]
        self.token_budget = int(cfg.get("token_budget", 80_000))
        self.tokens_used = 0
        self.approval_mode = cfg.get("approval_mode", "ask")  # ask|write|yolo
        self.auto_approve = cfg.get("auto_approve", False)
        # --- execution modes ---
        self.modes = ModeEngine(cfg.get("mode", "auto"))
        self.hooks = HookEngine(cfg.get("hooks", {}))
        self.rules = RuleEngine(cfg.get("stream_rules", []))
        self.veritas = Veritas(cfg.get("veritas", {}))
        self.keyring = KeyRing(self.workspace)
        self.run_stats = {"tool_calls": 0, "hooks_fired": 0, "rules_fired": 0,
                          "veratas_checks": 0}
        # --- MCP (Model Context Protocol) ---
        self.mcp = MCPRegistry(cfg.get("mcpServers", {}))
        if cfg.get("mcpServers"):
            self.mcp.start_all(strict=False)
            self.mcp.register_into_router(self.router)
        # --- Context Compaction & Subagent Swarm ---
        self.compactor = ContextCompactor(token_threshold=int(cfg.get("compaction_threshold", 40_000)))
        self.swarm = SubagentSwarm(self)
        self.router.register(make_subagent_tool(self.swarm))
        # --- BYOK (credential pool) ---
        self.active_key_name, self.active_key = self._resolve_key()

    # ---------- BYOK: bring your own key ----------
    def _resolve_key(self):
        """Key dari keyring (priority) atau config fallback."""
        prov = self._provider_of(self.base_url)
        name, key = self.keyring.pick(prov)
        if key:
            return name, key
        return None, self.api_key

    @staticmethod
    def _provider_of(url):
        for prov, marker in {"kei": "kei-inference", "kei_je": "jerouter",
                             "openrouter": "openrouter",
                             "deepseek": "deepseek", "groq": "groq",
                             "openai": "api.openai",
                             "anthropic": "api.anthropic"}.items():
            if marker in url:
                return "kei" if prov.startswith("kei") else prov
        return "custom"

    def rotate_key(self):
        """Ganti key aktif setelah 429/quota wall. Return nama baru atau None."""
        new = self.keyring.rotate(self._provider_of(self.base_url))
        if new:
            self.active_key_name = new
            self.active_key = self.keyring.get(new)
        return new

    # ---------- fallback chain (retry chain) ----------
    def llm(self, system: str, messages, tools=True):
        payload_base = {
            "messages": [{"role": "system", "content": system}] + messages,
            "max_tokens": 1500, "temperature": 0.4, "stream": True,
        }
        if tools:
            payload_base["tools"] = self.router.schemas()
            payload_base["tool_choice"] = "auto"
        last_err = None
        for model in self.model_chain:
            payload = dict(payload_base, model=model)
            for attempt in range(2):
                try:
                    r = httpx.post(f"{self.base_url}/chat/completions",
                                   headers={"Authorization": f"Bearer {self.active_key}",
                                            "Content-Type": "application/json"},
                                   json=payload, timeout=180)
                    if r.status_code >= 500 or r.status_code == 429:
                        # credential pool: 429 → rotate key dulu, retry
                        self.keyring.mark_fail(self.active_key_name) if self.active_key_name else None
                        rotated = self.rotate_key()
                        last_err = httpx.HTTPStatusError(
                            f"upstream {r.status_code}" +
                            (f" → rotated ke {rotated}" if rotated else " (pool habis)"),
                            request=r.request, response=r)
                        raise last_err
                    r.raise_for_status()
                    self._account_tokens(model, r)
                    return self._parse_stream(r, model)
                except (httpx.HTTPStatusError, httpx.TimeoutException,
                        httpx.TransportError) as e:
                    last_err = e
                    time.sleep(1 + attempt * 3)
        raise RuntimeError(f"semua model di chain gagal: {last_err}")

    # ---------- skill loader ----------
    def load_skill(self, name: str) -> str:
        p = f"skills/{name}.md"
        if os.path.exists(p):
            return open(p, encoding="utf-8").read()
        return ""

    # ---------- token accounting (budget gate) ----------
    def _account_tokens(self, model: str, r) -> None:
        try:
            j = r.json()
            self.tokens_used += int((j.get("usage") or {}).get("total_tokens", 0))
        except Exception:
            pass

    # ---------- SSE parser (dari method llm lama, murni) ----------
    def _parse_stream(self, r, model: str):
        content, tcs, finish = "", {}, None
        for line in r.text.split("\n"):
            line = line.strip()
            if not line.startswith("data: ") or "DONE" in line:
                continue
            try:
                ch = json.loads(line[6:])
            except json.JSONDecodeError:
                continue
            for c in ch.get("choices", []):
                d = c.get("delta") or {}
                finish = c.get("finish_reason") or finish
                content += d.get("content") or ""
                for tc in d.get("tool_calls") or []:
                    i = tc.get("index", 0)
                    slot = tcs.setdefault(i, {"id": "", "name": "", "arguments": ""})
                    if tc.get("id"):
                        slot["id"] = tc["id"]
                    f = tc.get("function") or {}
                    if f.get("name"):
                        slot["name"] = f["name"]
                    slot["arguments"] += f.get("arguments") or ""
        msg = {"role": "assistant", "content": content or None, "_model": model}
        if tcs:
            msg["tool_calls"] = [
                {"id": s["id"] or f"call_{i}", "type": "function",
                 "function": {"name": s["name"], "arguments": s["arguments"]}}
                for i, s in sorted(tcs.items())
            ]
        msg["_finish"] = finish
        return msg

    # ---------- enforce artefak ----------
    def _enforce_artefak(self, task, last_content, wrote_file):
        """Jamin ada artefak .md di workspace/output meski agent tidak file_write."""
        if wrote_file:
            return None
        slug = re.sub(r"[^a-z0-9-]+", "-", task.lower())[:40].strip("-") or "output"
        path = f"{self.workspace}/output/{slug}.md"
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# {task}\n\n{last_content}\n")
        return path

    # ---------- budget gate (internal --max-cost, varian token) ----------
    def _budget_left(self) -> int:
        return self.token_budget - self.tokens_used

    # ---------- approval ladder (approval ladder) ----------
    def _needs_approval(self, tool_name: str) -> bool:
        if self.approval_mode == "yolo":
            return False
        if self.approval_mode == "write":
            return tool_name in ("file_write", "file_patch")
        return True  # ask

    # ---------- main loop ----------
    def run(self, task: str, skill: str = "research", verbose=True):
        sys_prompt = self.load_skill(skill) or (
            "Kamu agent produktif. Pakai tool bila perlu, jawab final pakai bahasa "
            "Indonesia padat. Setiap tool call kamu catat.")
        if hasattr(self, "modes") and self.modes:
            sys_prompt = self.modes.apply_to_prompt(sys_prompt)
        self.hooks.fire("session_start", agent=self, task=task)
        self.memory = [{"role": "user", "content": task}]
        trace = []
        tool_count = 0
        wrote_file = False
        last_content = ""
        consec_fail = 0
        for i in range(self.max_turns):
            # context compaction: pangkas riwayat lama bila melebihi threshold
            if hasattr(self, "compactor") and self.compactor:
                self.memory, comp_stats = self.compactor.compact(self.memory)
                if comp_stats.get("compacted"):
                    trace.append({"turn": i, "type": "context_compaction", **comp_stats})
            # budget gate: habis → final sekarang
            if self._budget_left() <= 0:
                trace.append({"turn": i, "type": "budget_stop",
                              "tokens": self.tokens_used})
                break
            # forcing prompt: tool call terlalu banyak → suruh menulis laporan sekarang
            if tool_count >= 6:
                self.memory.append({"role": "user",
                    "content": "STOP. Riset cukup. SEKARANG kirim Laporan markdown LENGKAP sebagai jawaban final (content biasa, bukan tool call). Jangan panggil tool lagi."})
            msg = self.llm(sys_prompt, self.memory)
            # stream rules (stream rules): regex pada content → inject
            if msg.get("content"):
                for rule in self.rules.match(msg["content"]):
                    self.run_stats["rules_fired"] += 1
                    self.memory.append({"role": "user", "content": rule["inject"]})
                    trace.append({"turn": i, "type": "rule", "rule": rule["name"]})
            tcs = msg.get("tool_calls") or []
            if not tcs:
                final = msg.get("content") or ""
                last_content = final
                saved = self._enforce_artefak(task, final, wrote_file)
                trace.append({"turn": i, "type": "final", "len": len(final),
                              "artefak": saved})
                self.hooks.fire("session_end", agent=self, answer=final)
                self._persist(task, final, trace)
                return {"ok": True, "answer": final, "trace": trace,
                        "artefak": saved, "stats": self.run_stats}
            self.memory.append(msg)
            for tc in tcs:
                tool_count += 1
                self.run_stats["tool_calls"] += 1
                fn = tc["function"]
                raw_args = fn["arguments"] or "{}"
                try:
                    args = json.loads(raw_args)
                except json.JSONDecodeError:
                    # arguments terpotong server/model → perbaiki terbaik, else kosong
                    fixed = raw_args
                    for closer in ('"', "}", "]"):
                        fixed += closer
                    try:
                        args = json.loads(fixed)
                    except json.JSONDecodeError:
                        args = {}
                if fn["name"] == "file_write":
                    wrote_file = True
                    if not args.get("path") or not args.get("content"):
                        # arguments besar terpotong server → abaikan, harness auto-save nanti
                        args = {"path": "", "content": ""}
                        res = {"ok": False,
                               "error": "args terpotong; kirim laporan lewat jawaban final"}
                        trace.append({"turn": i, "type": "tool", "name": fn["name"],
                                      "args": args, "ok": False,
                                      "note": "truncated-args-ignored"})
                        self.run_log.append(trace[-1])
                        self.memory.append({"role": "tool", "tool_call_id": tc["id"],
                                            "content": json.dumps(res, ensure_ascii=False)})
                        continue
                # approval ladder: hook boleh menolak tool sebelum jalan
                if self._needs_approval(fn["name"]):
                    verdict = self.hooks.fire("tool_approve", tool=fn["name"], args=args)
                    if verdict.get("deny"):
                        res = {"ok": False,
                               "error": f"ditolak hook: {verdict.get('reason','')}"}
                        trace.append({"turn": i, "type": "tool", "name": fn["name"],
                                      "args": args, "ok": False, "deny": True})
                        self.run_log.append(trace[-1])
                        self.memory.append({"role": "tool", "tool_call_id": tc["id"],
                                            "content": json.dumps(res, ensure_ascii=False)})
                        continue
                # pre-tool hook (PreToolUse)
                pre = self.hooks.fire("pre_tool", tool=fn["name"], args=args)
                self.run_stats["hooks_fired"] += 1
                if pre.get("block"):
                    res = {"ok": False,
                           "error": f"diblokir hook: {pre.get('reason','')}"}
                    trace.append({"turn": i, "type": "tool", "name": fn["name"],
                                  "args": args, "ok": False, "blocked": True})
                    self.run_log.append(trace[-1])
                    self.memory.append({"role": "tool", "tool_call_id": tc["id"],
                                        "content": json.dumps(res, ensure_ascii=False)})
                    continue
                if verbose:
                    print(f"  [tool] {fn['name']}({json.dumps(args, ensure_ascii=False)[:120]})")
                res = self.router.call(fn["name"], args)
                # post-tool hook + veritas layer (gamechanger)
                self.hooks.fire("post_tool", tool=fn["name"], result=res)
                self.run_stats["hooks_fired"] += 1
                vcheck = self.veritas.check(fn["name"], args, res)
                if vcheck:
                    self.run_stats["veratas_checks"] += 1
                    trace.append({"turn": i, "type": "veritas",
                                  "tool": fn["name"], **vcheck})
                trace.append({"turn": i, "type": "tool", "name": fn["name"],
                              "args": args, "ok": res.get("ok", False)})
                self.run_log.append(trace[-1])
                self.memory.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": json.dumps(res, ensure_ascii=False)[:6000],
                })
                # HARD STOP: 2 kegagalan tool berturut-turut → recovery final tanpa tools
                if not res.get("ok", False):
                    consec_fail += 1
                    if consec_fail >= 2:
                        self.memory.append({"role": "user",
                            "content": "BERHENTI memanggil tool. Sekarang tulis Laporan markdown LENGKAP sebagai jawaban final langsung, tanpa tool call."})
                        msg2 = self.llm(sys_prompt, self.memory, tools=False)
                        final2 = msg2.get("content") or ""
                        if final2.strip():
                            saved = self._enforce_artefak(task, final2, wrote_file)
                            self._persist(task, final2, trace)
                            return {"ok": True, "answer": final2, "trace": trace, "artefak": saved}
                        consec_fail = 0
                else:
                    consec_fail = 0
        # ENFORCE ARTEFAK: agent tidak pernah file_write → harness simpan jawaban final sendiri
        if not wrote_file:
            saved = self._enforce_artefak(task, last_content, wrote_file)
            if saved:
                trace.append({"turn": "harness", "type": "enforce",
                              "note": "agent tidak file_write; harness auto-save", "path": saved})
        self.hooks.fire("session_end", agent=self, answer=last_content)
        return {"ok": False, "error": "max_turns habis", "trace": trace,
                "stats": self.run_stats}

    def _persist(self, task, answer, trace):
        ts = datetime.now(WIB).strftime("%Y%m%d_%H%M%S")
        with open(f"{self.workspace}/state.json", "w") as f:
            json.dump({"task": task, "answer": answer, "trace": trace,
                       "ts_wib": ts, "model": self.model,
                       "stats": self.run_stats}, f, ensure_ascii=False, indent=1)
        with open(f"{self.workspace}/log/runs.jsonl", "a") as f:
            f.write(json.dumps({"ts_wib": ts, "task": task, "trace": trace}, ensure_ascii=False) + "\n")
