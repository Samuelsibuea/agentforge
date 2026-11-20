# Buat AGENTS.md untuk repo ini — dokumen memori proyek: identitas, cara jalan (perintah pasti dari README), struktur file, konvensi kode, dan aturan kontribusi. Hanya fakta dari data ini, nol karangan. Bahasa Indonesia padat. Format markdown. Data:

Struktur file repo:
./test_consistency.py
./SUBMISSION.md
./README.md
./.gitignore
./workflow.py
./skills/coding.md
./skills/summarize.md
./skills/research.md
./skills/__init__.py
./tools/calc.py
./tools/web.py
./tools/router.py
./tools/files.py
./tools/__init__.py
./CONTRIBUTING.md
./agent/core.py
./agent/cli.py
./agent/commands.py
./agent/__init__.py
./config.example.json
./config.json
./LICENSE

README (potongan):
# AgentForge

![python](https://img.shields.io/badge/python-3.11+-3670A0)
![llm](https://img.shields.io/badge/LLM-Inference%20API-2563EB)
![tools](https://img.shields.io/badge/tools-6%20native-0E9F6E)
![deps](https://img.shields.io/badge/deps-1%20%28httpx%29-9333EA)
![status](https://img.shields.io/badge/status-stable-brightgreen)

> End-to-end AI agent ecosystem on the Inference API: a self-written harness
> (agent loop + SSE parser + tool router), modular skills, a scoped workspace,
> and a research workflow that turns a topic into a real markdown report —
> with live internet data, tool-call audit log, and provenance.

```
                    ┌───────────────────────────────────┐
   topic / task ───►│  agent/core.py  — the harness     │
                    │  ├─ SSE streaming parser          │
                    │  ├─ tool-call decode + dispatch   │
                    │  ├─ memory + loop control         │
                    │  ├─ quota + hard-stop recovery    │
                    │  └─ artefact enforcement          │
                    └────────────────┬──────────────────┘
                                     │ tool_calls (JSON over SSE)
                    ┌────────────────▼──────────────────┐
                    │  tools/router.py — registry       │
                    │  schema · quota · runs.jsonl log  │
                    ├───────────┬──────────┬────────────┤
                    ▼           ▼          ▼            ▼
              web_search    web_fetch  file_read/     calc
              HN Algolia    HTTP live  write/list     decimal
              +GitHub+Wiki             workspace-     (high
                                       scoped         precision)
                                     │
                    ┌────────────────▼──────────────────┐
                    │  workspace/output/<slug>.md       │
                    │  final report + sources + trace   │
                    └───────────────────────────────────┘
```

## Live demo

Real run, 19 Nov 2026 09:49 WIB — one command, topic in, report out:

```console
$ python workflow.py "Apa itu RAG? Jelaskan dalam 3 paragraf"

[workflow] topik: Apa itu RAG? Jelaskan dalam 3 paragraf
  [tool] web_search({"count": 6, "query": "Retrieval-Augmented Generation RAG definition how it works"})
  [tool] web_search({"count": 6, "query": "RAG retrieval augmented generation kelebihan kekurangan LLM"})
  [tool] web_fetch({"max_chars": 6000, "url": "https://en.wikipedia.org/wiki/Retrieval-augmented_generation"})
[workflow] trace:
   {"turn": 0, "type": "tool", "name": "web_search",  "ok": true}
   {"turn": 0, "type": "tool", "name": "web_search",  "ok": true}
   {"turn": 1, "type": "tool", "name": "web_fetch",   "ok": true}
   {"turn": 2, "type": "final", "len": 3524, "artefak": "workspace/output/apa-itu-rag-jelaskan-dalam-3-paragraf.md"}
[workflow] answer:
# RAG (Retrieval-Augmented Generation)
...
[workflow] workspace/output:
   workspace/output/apa-itu-rag-jelaskan-dalam-3-paragraf.md  3589 bytes
```

Artefak sha256 `ec10b86d…c1b990f0`, 19 lines, sitasi sumber live
(en.wikipedia.org/wiki/Retrieval-augmented_generation).
Every tool call lands in `workspace/log/runs.jsonl` — WIB timestamp, tool,
args, ok/error, duration. Full provenance, replayable.

## Layout

```
agentforge/
├── agent/
│   ├── core.py          # Agent loop: SSE parser, tool-call decode, memory, enforcement
│   └── cli.py           # Interactive CLI + single-shot mode
├── tools/
│   ├── router.py        # Tool registry, dispatcher, JSON schema, run log
│   ├── web.py           # web_search (HN Algolia + GitHub + Wikipedia, dedup), web_fetch
│   ├── files.py         # file_read / file_write / file_list (workspace-scoped)
│   └── calc.py          # High-precision calculator (decimal)
├── skills/
│   ├── research.md      # Research skill: search → fetch → synthesize → report
│   ├── coding.md        # Coding skill: draft → verify → polish
│   └── summarize.md     # Summarization skill: fetch → extract → bullet
├── workflow.py          # End-to-end workflow: research topic → report .md
├── test_consistency.py  # Harness consistency suite (loop · quota · SSE parse · artefact)
├── config.example.json  # Config template (config.json is git-ignored, add your api_key)
└── README.md
```

## Tools (6, all live)

| Tool | Mechanism | Quota/task |
|---|---|---|
| `web_search` | Live HTTP: HN Algolia + GitHub API + Wikipedia API, dedup | 3 |
| `web_fetch` | HTTP GET + text extraction (title + paragraphs) | 3 |
| `file_read` | Read files inside workspace | — |
| `file_write` | Write files inside workspace | 2 |
| `file_list` | List workspace directory | — |
| `calc` | High-precision calculator (decimal) | — |

Every tool call is logged to `workspace/log/runs.jsonl` — each entry carries a
WIB timestamp, tool, args, ok/error, and duration.

## Quick start

```bash
pip install httpx            # single dependency
cp config.example.json config.json
# add your api_key (event key via @KeiInferenceBot)

# single-shot research
python workflow.py "Compare Python agent frameworks: LangGraph vs CrewAI vs AutoGen"

# interactive shell
python -m agent.cli
```

Interactive shell (`/help` untuk daftar lengkap):

| Perintah | Fungsi |
|---|---|
| `/doctor` | cek config, endpoint live, skills, tools, runs log |
| `/status` | model, endpoint, memory, artefak |
| `/skills` · `/skill <nama>` | daftar + ganti skill aktif |
| `/history` | 8 run terakhir dari `runs.jsonl` |
| `/clear` | bersihkan memory sesi |
| `/exit` | keluar |

Prompt: `➜ agentforge:<skill> ❯` dengan history (FileHistory), slash-command
autocomplete, statusline bawah, progress tool-call ke stderr, dan Ctrl+C
yang membatalkan tool call tanpa mematikan sesi.

## Configuration

`config.json`:
```json
{
  "api_key": "sk-...",
  "base_url": "https://ai.kei-inference.web.id/v1",
  "model": "glm-5.3-flash",
  "max_turns": 15,
  "workspace": "workspace"
}
```

## Workflow (end-to-end)

1. Agent receives the topic from CLI/argument.
2. The `research` skill activates → agent calls `web_search` (live HTTP).
3. For each relevant result: `web_fetch` → extract text.
4. Agent synthesizes → markdown report becomes the **final answer**.
5. The harness enforces the artefact: if the agent did not `file_write`, the
   harness auto-saves the answer to `workspace/output/<slug>.md`.
6. Prints summary + file path + provenance (tool-call log + HTTP status).

## Harness resilience

- The Inference API server always responds with SSE → the client parses SSE chunks
  (`data:` lines), accumulating `delta.content` + `delta.tool_calls[index]`
  (OpenAI-compatible format).
- 4× retry on 5xx/429/timeout; tool quota (3 search / 3 fetch / 2 write).
- Long JSON arguments can be truncated server-side → harness fallback parse +
  **hard-stop**: 2 consecutive tool failures → final recovery without tools.
- **Artefact enforcement**: if the agent never calls `file_write`, the harness
  auto-saves the final answer.
- Bing/DDG/Google/Mojeek/SearxNG/Ecosia wall datacenter IPs → the search chain
  uses stable open API endpoints (HN Algolia, GitHub, Wikipedia), keyless.

## Design notes

- Tools are read/write-local only: search, fetch, files in your own workspace,
  calculator. No remote administration, no credential access, no exfiltration.
- All written data stays inside `workspace/` on your machine.
- One dependency: `httpx`. No external services beyond the Inference API
  and the open search endpoints listed above.

---

**AgentForge** — a self-written harness, six live tools, real reports from
real data. Built on the Inference API.


agent/core.py (potongan):
# agent/core.py — agent loop: LLM call (Kei), tool-call parse, memory, skill injection.
import httpx, json, os, re, time
from datetime import datetime
from zoneinfo import ZoneInfo
from tools.router import ToolRouter

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

    # ---------- skill loader ----------
    def load_skill(self, name: str) -> str:
        p = f"skills/{name}.md"
        if os.path.exists(p):
            return open(p, encoding="utf-8").read()
        return ""

    # ---------- LLM (SSE — server kei paksa stream meski stream:false) ----------
    def llm(self, system: str, messages, tools=True):
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}] + messages,
            "max_tokens": 1500,
            "temperature": 0.4,
            "stream": True,
        }
        if tools:
            payload["tools"] = self.router.schemas()
            payload["tool_choice"] = "auto"
        r = None
        for attempt in range(4):
            try:
                r = httpx.post(f"{self.base_url}/chat/completions",
                               headers={"Authorization": f"Bearer {self.api_key}",
                                        "Content-Type": "application/json"},
                               json=payload, timeout=180)
                if r.status_code >= 500 or r.status_code == 429:
                    raise httpx.HTTPStatusError(f"upstream {r.status_code}", request=r.request, response=r)
                r.raise_for_status()
                break
            except (httpx.HTTPStatusError, httpx.TimeoutException, httpx.TransportError) as e:
                if attempt == 3:
                    raise
                time.sleep(2 + attempt * 4)
        if r is None:
            raise RuntimeError("no response from Kei API")
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
        msg = {"role": "assistant", "content": content or None}
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

    # ---------- main loop ----------
    def run(self, task: str, skill: str = "research", verbose=True):
        sys_prompt = self.load_skill(skill) or (
            "Kamu agent produktif. Pakai tool bila perlu, jawab final pakai bahasa "
            "Indonesia padat. Setiap tool call kamu catat.")
        self.memory = [{"role": "user", "content": task}]
        trace = []
        tool_count = 0
        wrote_file = False
        last_content = ""
        consec_fail = 0
        for i in range(self.max_turns):
            # forcing prompt: tool call terlalu banyak → suruh menulis laporan sekarang
            if tool_count >= 6:
                self.memory.append({"role": "user",
                    "content": "STOP. Riset cukup. SEKARANG kirim Laporan markdown LENGKAP sebagai jawaban final (content biasa, bukan tool call). Jangan panggil tool lagi."})
            msg = self.llm(sys_prompt, self.memory)
            tcs = msg.get("tool_calls") or []
            if not tcs:
                final = msg.get("content") or ""
                last_content = final
                saved = self._enforce_artefak(task, final, wrote_file)
                trace.append({"turn": i, "type": "final", "len": len(final),
                              "artefak": saved})
                self._persist(task, final, trace)
                return {"ok": True, "answer": final, "trace": trace, "artefak": saved}
            self.memory.append(msg)
            for tc in tcs:
                tool_count += 1
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
                        res = {"ok": False, "error": "args terpotong; kirim laporan lewat jawaban final"}
                        trace.append({"turn": i, "type": "tool", "name": fn["name"],
                                      "args": args, "ok": False, "note": "truncated-args-ignored"})
                        self.run_log.append(trace[-1])
                        self.memory.append({"role": "tool", "tool_call_id": tc["id"],
                                            "content": json.dumps(res, ensure_ascii=False)})
                        continue
                if verbose:
                    print(f"  [tool] {fn['name']}({json.dumps(args, ensure_ascii=False)[:120]})")
                res = self.router.call(fn["name"], args)
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
        return {"ok": False, "error": "max_turns habis", "trace": trace}

    def _persist(self, task, answer, trace):
        ts = datetime.now(WIB).strftime("%Y%m%d_%H%M%S")
        with open(f"{self.workspace}/state.json", "w") as f:
            json.dump({"task": task, "answer": answer, "trace": trace,
                       "ts_wib": ts, "model": self.model}, f, ensure_ascii=False, indent=1)
        with open(f"{self.workspace}/log/runs.jsonl", "a") as f:
            f.write(json.dumps({"ts_wib": ts, "task": task, "trace": trace}, ensure_ascii=False) + "\n")



