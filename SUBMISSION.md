# AgentForge — Submission

**Author:** Samuel — samuel.early@students.mikroskil.ac.id
**Repo:** https://github.com/Samuelsibuea/agentforge
**Stack:** Python 3.11+ · single dependency `httpx` · zero agent frameworks

AgentForge is a self-written AI agent harness: a ~300-line agent loop with
SSE-native tool calling, a tool router with JSON-schema validation, quota
enforcement and a run audit trail, three modular skills, and an end-to-end
workflow that turns one topic into a real markdown research report built
from live internet data.

## Reproduction

```bash
pip install httpx
cp config.example.json config.json   # add your api_key (event key via @KeiInferenceBot)
python workflow.py "<any topic>"     # live research → report .md in workspace/output/
python -m agent.cli                  # interactive mode
python test_consistency.py           # harness suite, 5/5 tasks PASS
```

## Architecture

```
workflow.py  ──topic──▶  agent/core.py  (agent loop)
                            │  SSE stream ──▶ Inference API (glm-5.3-flash)
                            │  tool_call ──▶ tools/router.py
                            │                 │ schema validate + quota + audit
                            │                 ├─▶ tools/web.py    web_search · web_fetch
                            │                 ├─▶ tools/files.py file_read · file_write · file_list
                            │                 └─▶ tools/calc.py  calc
                            ├─▶ skills/*.md  research · coding · summarize
                            └─▶ workspace/   output/ · state.json · log/runs.jsonl
```

## Tool inventory (6, all live)

| Tool | Mechanism | Quota/task |
|---|---|---|
| `web_search` | Live HTTP: HN Algolia + GitHub API + Wikipedia API, dedup | 3 |
| `web_fetch` | HTTP GET + text extraction (title + paragraphs) | 3 |
| `file_read` | Read files inside workspace | — |
| `file_write` | Write files inside workspace | 2 |
| `file_list` | List workspace directory | — |
| `calc` | High-precision calculator (decimal) | — |

## Skills (3)

`skills/research.md` · `skills/coding.md` · `skills/summarize.md` — markdown
frontmatter + body, loaded on demand by the router, zero cost while idle.

## Test evidence (measured, 19 Nov 2026 WIB)

`test_consistency.py` runs 5 diverse tasks end-to-end. A task passes only if
(a) final answer exists, (b) artefact `.md` exists in `workspace/output/`,
(c) answer contains a citation ("sumber").

```json
{ "passed": 5, "total": 5 }
```

Sample row from `workspace/test_results.json`:

```json
{ "task": "Apa itu AI agent harness? Bandingkan pendekatan utama 2026",
  "ok": true, "answer_len": 5439, "dur_s": 61.3, "tools": 8 }
```

Full log: `workspace/log/runs.jsonl` — 177 entries, each with WIB timestamp,
tool, args, ok/error, duration.

## Run evidence (live, 19 Nov 2026 09:49 WIB)

```console
$ python workflow.py "Apa itu RAG? Jelaskan dalam 3 paragraf"

[workflow] topik: Apa itu RAG? Jelaskan dalam 3 paragraf
  [tool] web_search  ok   {"query": "Retrieval-Augmented Generation RAG definition how it works"}
  [tool] web_search  ok   {"query": "RAG retrieval augmented generation kelebihan kekurangan LLM"}
  [tool] web_fetch   ok   {"url": "https://en.wikipedia.org/wiki/Retrieval-augmented_generation"}
[workflow] trace:
   {"turn": 0, "type": "tool", "name": "web_search",  "ok": true}
   {"turn": 0, "type": "tool", "name": "web_search",  "ok": true}
   {"turn": 1, "type": "tool", "name": "web_fetch",   "ok": true}
   {"turn": 2, "type": "final", "len": 3524, "artefak": "workspace/output/apa-itu-rag-jelaskan-dalam-3-paragraf.md"}
```

Artefak: `workspace/output/apa-itu-rag-jelaskan-dalam-3-paragraf.md`
(3589 bytes, 19 lines) — sha256 `ec10b86db6293df2e074ac5ba404247d70b41115e1b49da8403cbdcdc1b990f0`,
sitasi live ke en.wikipedia.org.

## Design goals

| Goal | How it is met |
|---|---|
| Self-written | No LangChain/CrewAI/AutoGen — loop, router, skills are own code |
| Tool discipline | JSON-schema args, per-tool quota, hard stop at `max_turns` |
| Artefact enforcement | Harness auto-saves final answer to `.md` if agent forgets |
| Provenance | Every tool call in `runs.jsonl` with WIB ts + ok/error + duration |
| Resilience | SSE stream parsed incrementally; partial output never silently dropped |

## Scope notes

All tools operate on local reads/writes inside `workspace/`; search goes
through public keyless APIs (HN Algolia, GitHub, Wikipedia). No remote
administration, no credential access, no exfiltration, no download-and-execute.

## Roadmap
 
 - [x] Interactive CLI upgrade: prompt-toolkit UI with history + autocomplete (shipped: banner, statusline, 8 slash commands, stderr progress, cancellation)
 - [x] Execution Modes Suite: `plan`, `auto`, `fast` (flash), `reasoning` (thinking), `vision`, `workflow`
 - [x] Model Context Protocol (MCP) Client stdio JSON-RPC 2.0 integration
 - [x] Subagent Swarm Delegation runtime (`delegate_task`)
 - [x] User-Created Custom Tools & Dynamic Loader (`/tool create`)
 - [x] User-Created Custom Skills & Ecosystem Marketplace (`/skill create`, `/skill catalog`)
 - [x] GitHub Automation Workflow (`workflow_github.py`) & CI/CD Action (`.github/workflows/ci.yml`)
 - [x] Context Compaction Window Pruner
 - [x] Benchmark Suite & Evaluation Harness (`benchmark.py`)
