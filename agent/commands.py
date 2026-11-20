
# Tiap command: name · desc · run(agent, args) -> str. /help dirender dari registry ini.
import os
from tools.router import ToolRouter

WIB_FMT = "%Y-%m-%d %H:%M:%S WIB"


def _model_info(a):
    short = a.model.split("/")[-1]
    return f"{short} @ {a.base_url.replace('https://','').replace('http://','')}"


def cmd_help(agent, args):
    lines = ["perintah tersedia:", ""]
    for name, c in COMMANDS.items():
        lines.append(f"  /{name:<10} {c['desc']}")
    lines.append("")
    lines.append("  <teks bebas>    kirim ke agent (skill aktif: riset/coding/summarize)")
    return "\n".join(lines)


def cmd_doctor(agent, args):
    import httpx, os, json
    from datetime import datetime
    from zoneinfo import ZoneInfo
    lines = [f"doctor — {datetime.now(ZoneInfo('Asia/Jakarta')).strftime(WIB_FMT)}", ""]
    # 1 config
    lines.append(f"  config        ok   model={agent.model} max_turns={agent.max_turns}")
    lines.append(f"  workspace     {'ok' if os.path.isdir(agent.workspace) else 'MISSING'}   {agent.workspace}/")
    lines.append(f"  output dir    {'ok' if os.path.isdir(f'{agent.workspace}/output') else 'MISSING'}   {agent.workspace}/output/")
    # 2 endpoint live
    try:
        r = httpx.get(f"{agent.base_url}/models",
                      headers={"Authorization": f"Bearer {agent.api_key}"}, timeout=10)
        names = [m.get("id", "?") for m in r.json().get("data", [])] if r.status_code < 400 else []
        lines.append(f"  endpoint      {r.status_code}   {len(names)} model — {agent.base_url}")
        if agent.model.split("/")[-1] in names:
            lines.append(f"  model pin     ok   {agent.model} ada di daftar")
        else:
            lines.append(f"  model pin     ??   {agent.model} tidak ada di daftar endpoint")
    except Exception as e:
        lines.append(f"  endpoint      FAIL {type(e).__name__}: {e}")
    # 3 skills
    skills = [f[:-3] for f in os.listdir("skills") if f.endswith(".md")] if os.path.isdir("skills") else []
    lines.append(f"  skills        {len(skills)}    {', '.join(skills) or '-'}")
    # 4 tools
    lines.append(f"  tools         {len(ToolRouter(agent.workspace).schemas())}   "
                 + ", ".join(s["function"]["name"] for s in ToolRouter(agent.workspace).schemas()))
    # 5 runs log (run persist + tool audit)
    log = f"{agent.workspace}/log/runs.jsonl"
    rows = [json.loads(l) for l in open(log) if l.strip()] if os.path.exists(log) else []
    runs = sum(1 for r in rows if "task" in r)
    audits = sum(1 for r in rows if "tool" in r)
    lines.append(f"  runs.jsonl    {runs} run · {audits} tool audit   {log}")
    return "\n".join(lines)


def cmd_skills(agent, args):
    import os
    out = ["skill aktif + loader:", ""]
    for f in sorted(os.listdir("skills")):
        if not f.endswith(".md"):
            continue
        body = open(f"skills/{f}", encoding="utf-8").read()
        first = next((l for l in body.splitlines() if l.startswith("#")), "")
        out.append(f"  /{f[:-3]:<12} {first.lstrip('# ').strip()[:60]}")
    out.append("")
    out.append("  pakai /skill <nama> untuk ganti skill aktif (default: research)")
    return "\n".join(out)


def cmd_skill(agent, args):
    name = (args or "").strip().lstrip("/")
    if not name:
        return f"skill aktif sekarang: {agent.skill}\npakai: /skill <nama>"
    body = agent.load_skill(name)
    if not body:
        return f"skill '{name}' tidak ditemukan. /skills untuk daftar."
    agent.skill = name
    return f"skill aktif → {name} ({len(body)} char ter-load)"


def cmd_clear(agent, args):
    agent.memory = []
    agent.run_log = []
    return "memory + run_log dibersihkan. sesi baru dimulai."


def cmd_history(agent, args):
    import os
    log = f"{agent.workspace}/log/runs.jsonl"
    if not os.path.exists(log):
        return "belum ada run."
    import json
    rows = [json.loads(l) for l in open(log) if l.strip()]
    runs = [r for r in rows if "task" in r]           # run persist (Agent._persist)
    audits = [r for r in rows if "tool" in r]          # tool-call audit (router)
    out = [f"run history ({len(runs)} run · {len(audits)} tool audit) — {len(runs[-8:])} run terakhir:", ""]
    for r in runs[-8:]:
        tools = sum(1 for t in r.get("trace", []) if t.get("type") == "tool")
        final = next((t for t in reversed(r.get("trace", [])) if t.get("type") == "final"), {})
        ok = "final" if final else ("tools-only" if tools else "?")
        out.append(f"  {r.get('ts_wib','?')}  tools={tools:<2} {ok:<10}  {r.get('task','?')[:40]}")
    return "\n".join(out)


def cmd_status(agent, args):
    import os
    out = [f"model    {agent.model}", f"endpoint {agent.base_url}",
           f"skill    {getattr(agent, 'skill', 'research')}",
           f"memory   {len(agent.memory)} pesan", f"run_log  {len(agent.run_log)} tool call",
           f"turns    max {agent.max_turns}"]
    out_path = f"{agent.workspace}/output"
    n = len(os.listdir(out_path)) if os.path.isdir(out_path) else 0
    out.append(f"artefak  {n} file di {out_path}/")
    return "\n".join(out)


def cmd_exit(agent, args):
    raise SystemExit(0)


def cmd_init(agent, args):
    """/init → scan repo → generate AGENTS.md memory file."""
    import subprocess
    tree = subprocess.run(["find", ".", "-type", "f", "-not", "-path", "./.git/*",
                           "-not", "-path", "./workspace/*", "-not", "-path", "./research/*",
                           "-not", "-name", "*.pyc", "-not", "-path", "*/__pycache__/*"],
                          capture_output=True, text=True).stdout.split()
    readme = open("README.md", encoding="utf-8").read() if os.path.exists("README.md") else ""
    core = open("agent/core.py", encoding="utf-8").read() if os.path.exists("agent/core.py") else ""
    brief = (f"Struktur file repo:\n" + "\n".join(tree[:60]) +
             f"\n\nREADME (potongan):\n{readme}\n\nagent/core.py (potongan):\n{core}")
    task = ("Buat AGENTS.md untuk repo ini — dokumen memori proyek: identitas, "
            "cara jalan (perintah pasti dari README), struktur file, konvensi kode, "
            "dan aturan kontribusi. Hanya fakta dari data ini, nol karangan. "
            "Bahasa Indonesia padat. Format markdown. Data:\n\n" + brief)
    out = agent.run(task, skill="coding", verbose=False)
    # artefak file_write murni lebih baik dari jawaban (jawaban bisa bungkus preamble)
    art = out.get("artefak") or f"{agent.workspace}/output/AGENTS.md"
    text = ""
    if os.path.exists(art) and os.path.getsize(art) > 200:
        text = open(art, encoding="utf-8").read()
    if not text.strip():
        text = out.get("answer") or ""
        # kalau jawaban bungkus laporan, ambil bagian setelah pembatas "---"
        if "\n---\n" in text:
            text = text.split("\n---\n", 1)[1]
    if not text.strip():
        return f"/init gagal: {out.get('error')}"
    with open("AGENTS.md", "w", encoding="utf-8") as f:
        f.write(text if text.startswith("#") else f"# AGENTS.md\n\n{text}")
    return f"/init selesai — AGENTS.md ({len(text)} char) dari scan {len(tree)} file. Edit manual untuk poles."


def cmd_keys(agent, args):
    """/keys add <nama> <key> [provider] | /keys ls | /keys rm <nama> | /keys rotate
    BYOK — key milik BOZ, disimpan chmod 600 di workspace/keys/, nol plaintext di chat."""
    from agent.keyring import PROVIDER_DEFAULTS
    kr = agent.keyring
    if not args:
        return ("/keys add <nama> <key> [provider] · /keys ls · /keys rm <nama> · "
                "/keys rotate · provider: " + ", ".join(PROVIDER_DEFAULTS))
    op = args[0]
    if op == "add" and len(args) >= 3:
        r = kr.add(args[1], args[2], args[3] if len(args) > 3 else "custom")
        return f"key {args[1]} ({r.get('provider')}) fingerprint {r.get('fingerprint')} — aktif" if r["ok"] else f"gagal: {r['error']}"
    if op == "ls":
        ks = kr.list()
        if not ks:
            return "keyring kosong — /keys add <nama> <key> <provider>"
        return "\n".join(f"• {k['name']} [{k['provider']}] {k['fingerprint']} "
                         f"models={len(k.get('models', []))} aktif={k['active']}" for k in ks)
    if op == "rm" and len(args) > 1:
        r = kr.remove(args[1])
        return f"hapus {args[1]}" if r["ok"] else r["error"]
    if op == "rotate":
        new = agent.rotate_key()
        return f"rotasi → {new}" if new else "pool habis — /keys add dulu"
    return "usage: /keys add|ls|rm|rotate"


def cmd_models(agent, args):
    """/models — daftar model chain + provider aktif ."""
    lines = [f"provider: {agent._provider_of(agent.base_url)}",
             f"endpoint: {agent.base_url}",
             f"chain: {', '.join(agent.model_chain)}",
             f"key aktif: {agent.active_key_name or 'config-fallback'} "
             f"({agent.keyring.idx['keys'].get(agent.active_key_name, {}).get('fingerprint', '…')})"]
    return "\n".join(lines)


def cmd_serve(agent, args):
    """/serve [port] — headless HTTP + SSE. Jalan di thread."""
    port = int(args[0]) if args else 8787
    import threading
    from agent.serve import serve
    t = threading.Thread(target=serve, kwargs={"port": port}, daemon=True)
    t.start()
    return f"serve hidup di http://127.0.0.1:{port} (POST /v1/chat, GET /v1/models, /health)"


def cmd_export(agent, args):
    """/export [path] — session → JSON file."""
    from agent.store import export_session, session_stats
    path = export_session(agent, args[0] if args else None)
    st = session_stats(agent)
    return f"session → {path}\nstats: runs={st['total_runs']} tools={st['tool_use']} tokens={st['used_tokens']}/{st['budget_tokens']}"


def cmd_import(agent, args):
    """/import <file> — JSON session → memory balik."""
    from agent.store import import_session
    if not args:
        return "usage: /import <file.json>"
    r = import_session(agent, args[0])
    return (f"import OK: {r['turns']} turns dari {r['path']}" if r["ok"]
            else f"gagal: {r['error']}")


def cmd_stats(agent, args):
    """/stats — pakai tool, quota, veritas verdict."""
    from agent.store import session_stats
    st = session_stats(agent)
    v = agent.run_stats
    return (f"runs={st['total_runs']} · tools={st['tool_use']} · "
            f"tokens={st['used_tokens']}/{st['budget_tokens']} · "
            f"veratas={v['veratas_checks']} hooks={v['hooks_fired']} rules={v['rules_fired']}")


def cmd_cron(agent, args):
    """/cron add <nama> <cron5> <task> | ls | rm <nama> | pause|resume <nama> | tick
    jadwal → agent jalan otomatis → hasil ke runs.jsonl."""
    from agent.cron import CronEngine
    c = CronEngine(agent.workspace)
    if not args:
        return ("/cron add <nama> <'*/15 * * * *'> <task> · /cron ls · "
                "/cron rm <nama> · /cron pause <nama> · /cron resume <nama> · /cron tick")
    op = args[0]
    if op == "add" and len(args) >= 4:
        r = c.add(args[1], args[2], " ".join(args[3:]))
        return f"cron {args[1]} jadwal {args[2]} — aktif" if r["ok"] else f"gagal: {r['error']}"
    if op == "ls":
        js = c.list()
        return "\n".join(f"• {j['name']} [{j['schedule']}] runs={j['runs']} "
                         f"paused={j['paused']} last={j['last_run'] or '-'}" for j in js) or "kosong"
    if op == "rm" and len(args) > 1:
        return f"hapus {args[1]}" if c.remove(args[1])["ok"] else "tidak ada"
    if op == "pause" and len(args) > 1:
        return f"pause {args[1]}" if c.pause(args[1], True)["ok"] else "tidak ada"
    if op == "resume" and len(args) > 1:
        return f"resume {args[1]}" if c.pause(args[1], False)["ok"] else "tidak ada"
    if op == "tick":
        fired = c.tick()
        return f"tick: {len(fired)} job jalan — " + "; ".join(
            f"{f['name']} ok={f.get('ok')}" for f in fired) if fired else "tick: tak ada job jatuh sekarang"
    return "usage: /cron add|ls|rm|pause|resume|tick"


def cmd_learn(agent, args):
    """/learn <trigger> — run terakhir → skill otomatis."""
    from agent.learn import extract_skill, learned_index
    if args and args[0] == "ls":
        li = learned_index()
        return "\n".join(f"• {l['file']} trigger='{l['trigger']}' {l['steps']} langkah"
                         for l in li) or "belum ada learned skill"
    if not args:
        return "usage: /learn <trigger kata> | /learn ls"
    seq = [t.get("name") for t in agent.run_log if t.get("type") == "tool"]
    if not seq:
        return "belum ada tool call di sesi ini — jalan task dulu, lalu /learn"
    path = extract_skill(agent, " ".join(args), seq,
                         agent.run_log[-1].get("result", "")[:200] if agent.run_log else "")
    return f"skill dipelajari → {path} (sequence: {' → '.join(seq)})" if path else "gagal ekstrak"


COMMANDS = {
    "help":    {"desc": "daftar perintah + signature", "run": cmd_help},
    "doctor":  {"desc": "cek config, endpoint, skills, tools, log", "run": cmd_doctor},
    "skills":  {"desc": "daftar skill + loader", "run": cmd_skills},
    "skill":   {"desc": "<nama> — ganti skill aktif", "run": cmd_skill},
    "clear":   {"desc": "bersihkan memory sesi", "run": cmd_clear},
    "history": {"desc": "8 run terakhir dari runs.jsonl", "run": cmd_history},
    "status":  {"desc": "model, endpoint, memory, artefak", "run": cmd_status},
    "init":    {"desc": "scan repo → generate AGENTS.md memory file", "run": cmd_init},
    "keys":    {"desc": "BYOK — add/ls/rm/rotate API key (chmod 600)", "run": cmd_keys},
    "models":  {"desc": "model chain + provider + key aktif", "run": cmd_models},
    "serve":   {"desc": "[port] — headless HTTP + SSE ((HTTP + SSE))", "run": cmd_serve},
    "export":  {"desc": "[path] — session → JSON file", "run": cmd_export},
    "import":  {"desc": "<file> — JSON session → memory", "run": cmd_import},
    "stats":   {"desc": "tool use, quota, veritas verdict", "run": cmd_stats},
    "cron":    {"desc": "add/ls/rm/pause/resume/tick — scheduler", "run": cmd_cron},
    "learn":   {"desc": "<trigger> | ls — self-improving skill extraction", "run": cmd_learn},
    "exit":    {"desc": "keluar", "run": cmd_exit},
}
