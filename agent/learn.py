# agent/learn.py — self-improving pattern: prosedur berhasil → simpan jadi skill.
# Mekanisme: kalau run menghasilkan artefak dengan pola tetap (tool sequence → hasil),
# engine simpan skill.md ke skills/learned/<nama>.md supaya run berikutnya pakai lagi.
# skill = trigger + prosedur, auto-load saat kata kunci cocok.
import json, os
from datetime import datetime
from zoneinfo import ZoneInfo

WIB = ZoneInfo("Asia/Jakarta")


def extract_skill(agent, trigger_words, tool_names, result_hint):
    """Simpan prosedur dari run terakhir jadi skill. Return path atau None."""
    seq = [t.get("name") for t in agent.run_log if t.get("type") == "tool"]
    if not seq:
        return None
    name = "_".join(w.lower().strip()[:12] for w in trigger_words.split()[:2]) or "learned"
    d = "skills/learned"
    os.makedirs(d, exist_ok=True)
    path = f"{d}/{name}.md"
    body = f"""# {name} — learned skill (auto)

Trigger: {trigger_words}

Prosedur (tool sequence dari run berhasil):
{chr(10).join(f'{i+1}. `{t}`' for i, t in enumerate(seq))}

Hasil terakhir: {result_hint[:200]}

Dipelajari: {datetime.now(WIB).strftime('%Y-%m-%d %H:%M:%S')} WIB
Sumber: AgentForge learn (self-improving pattern)
"""
    with open(path, "w") as f:
        f.write(body)
    return path


def learned_index():
    """Daftar skill yang dipelajari mesin, bukan ditulis tangan."""
    d = "skills/learned"
    if not os.path.isdir(d):
        return []
    out = []
    for fn in sorted(os.listdir(d)):
        if fn.endswith(".md"):
            txt = open(os.path.join(d, fn)).read()
            trig = txt.split("Trigger: ")[1].split("\n")[0] if "Trigger: " in txt else ""
            out.append({"file": fn, "trigger": trig,
                        "steps": txt.count(". `")})
    return out
