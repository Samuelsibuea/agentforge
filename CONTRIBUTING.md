# Contributing

Thanks for wanting to improve AgentForge. Small, focused PRs only.

## Setup

```bash
git clone https://github.com/Samuelsibuea/agentforge.git
cd agentforge
pip install httpx
cp config.example.json config.json   # add your own api_key
```

## Ground rules

- `config.json`, `workspace/`, `.env`, `*.key` are git-ignored. Never commit
  keys, tokens, or session state.
- One PR = one concern (a tool, a skill, a harness fix).
- New tools must: live in `tools/`, register in `tools/router.py` with a JSON
  schema, respect the per-task quota, and log every call via the router.
- Keep the harness framework-free. The point of this repo is a self-written
  agent loop on the Inference API — no LangChain/CrewAI/AutoGen imports.
- English for code, docs, and commit messages.

## Verify before you PR

```bash
python test_consistency.py      # harness suite must pass
python workflow.py "<topic>"    # end-to-end run must produce an .md artefact
```

A PR without a passing suite and a fresh artefact will not be reviewed.

## Reporting issues

Open an issue with: the exact command, the full stderr/stdout, your
`config.example.json`-shaped config (keys redacted), and the contents of
`workspace/log/runs.jsonl` for the failing run.
