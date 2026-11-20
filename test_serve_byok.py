# test_serve_byok.py — verifikasi unit: serve/export/import/models/stats
# + BYOK keyring, credential pool rotation + commands registry.
import json, os, sys, tempfile, threading, time, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agent.core import Agent
from agent.keyring import KeyRing
from agent.store import export_session, import_session, session_stats

PASS = FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    s = "PASS" if cond else "FAIL"
    if cond:
        PASS += 1
    else:
        FAIL += 1
    print(f"  [{s}] {name}" + (f" — {detail}" if detail and not cond else ""))


print("=== serve + byok feature tests ===")
cfg = json.load(open("config.json"))
cfg.setdefault("models", {})["chain"] = ["glm-5.3-flash"]
cfg["approval_mode"] = "write"
cfg["auto_approve"] = True
cfg["hooks"] = {}
cfg["stream_rules"] = []
cfg["veritas"] = {"enabled": True}
json.dump(cfg, open("config.json", "w"))

# BYOK dulu — Agent baca keyring pas init
pre = KeyRing("workspace")
pre.add("boot1", "sk-bootkey-0123456789abcdef", "kei")
a = Agent("config.json")

# --- BYOK keyring ---
print("-- BYOK keyring --")
a.keyring.remove("boot1")
r = a.keyring.add("test1", "sk-testkey-abcdefghij123456", "kei")
check("add key", r["ok"] and r["fingerprint"] == "sk-t…3456", str(r))
r2 = a.keyring.add("test2", "sk-otherkey-qrstuvwxyz789012", "kei")
check("add key 2", r2["ok"])
name, key = a.keyring.pick("kei")
check("pick affinity", name == "test1" and key.startswith("sk-testkey"), f"{name}")
a.keyring.mark_fail("test1")
name2, key2 = a.keyring.pick("kei")
check("fail → next key", name2 == "test2", f"got {name2}")
rot = a.keyring.rotate("kei")
check("rotate", rot is not None)
check("remove key", a.keyring.remove("test1")["ok"])
check("key file chmod 600",
      oct(os.stat("workspace/keys/test2.key").st_mode)[-3:] == "600")
check("nol plaintext di index.json",
      "sk-otherkey" not in open("workspace/keys/index.json").read())

# --- Agent resolve key (keyring sudah berisi test1/test2 di atas) ---
print("-- Agent BYOK resolve --")
a2 = Agent("config.json")  # init ulang, keyring sudah terisi
check("agent aktif key dari keyring", a2.active_key_name in ("test1", "test2"),
      f"{a2.active_key_name}")
check("agent key == keyring key", a2.active_key == a2.keyring.get(a2.active_key_name))

# --- commands registry ---
print("-- commands --")
from agent.commands import COMMANDS
for c in ["keys", "models", "serve", "export", "import", "stats"]:
    check(f"/{c} terdaftar", c in COMMANDS)
check("total commands >= 14", len(COMMANDS) >= 14, f"{len(COMMANDS)}")

# --- /keys ls output ---
out = COMMANDS["keys"]["run"](a, ["ls"])
check("/keys ls listing", "test2" in out and "fingerprint" not in out.replace("sk-o…", ""))
out = COMMANDS["keys"]["run"](a, ["rotate"])
check("/keys rotate jalan", "rotasi" in out)

# --- /models ---
out = COMMANDS["models"]["run"](a, [])
check("/models provider+chain", "provider" in out and "chain" in out, out[:80])

# --- session export/import (pola sendiri) ---
print("-- session export/import --")
a.memory = [{"role": "user", "content": "tes"}, {"role": "assistant", "content": "balasan"}]
p = export_session(a)
check("export file exists", os.path.exists(p), p)
d = json.load(open(p))
check("export isi memory", len(d["memory"]) == 2)
b = Agent("config.json")
r = import_session(b, p)
check("import balik", r["ok"] and r["turns"] == 2)
check("memory sama", b.memory[1]["content"] == "balasan")

# --- stats ---
st = session_stats(a)
check("stats shape", "total_runs" in st and "tool_use" in st and "budget_tokens" in st)
out = COMMANDS["stats"]["run"](a, [])
check("/stats output", "runs=" in out and "tokens=" in out)

# --- serve mode (pola sendiri) ---
print("-- serve HTTP --")
from agent.serve import serve
t = threading.Thread(target=serve, kwargs={"port": 8787}, daemon=True)
t.start()
time.sleep(1.0)
try:
    h = urllib.request.urlopen("http://127.0.0.1:8787/health", timeout=5)
    check("GET /health 200", h.status == 200)
    body = json.loads(h.read())
    check("health body", body["ok"] is True)
    m = urllib.request.urlopen("http://127.0.0.1:8787/v1/models", timeout=5)
    mj = json.loads(m.read())
    check("GET /v1/models chain", "glm-5.3-flash" in mj["models"])
    req = urllib.request.Request(
        "http://127.0.0.1:8787/v1/chat",
        data=json.dumps({"task": "jawab satu kata: siapa", "skill": "research"}).encode(),
        headers={"Content-Type": "application/json"})
    try:
        resp = urllib.request.urlopen(req, timeout=90)
        sse = resp.read().decode()
    except Exception as e:
        # Handler.run gagal → baca log untuk sebab asli
        import traceback
        log = open("workspace/log/agentforge.log").read()[-400:]
        check("POST /v1/chat SSE", False, f"{e} | log: {log}")
        sse = ""
    check("POST /v1/chat SSE", "data: " in sse and '"event": "final"' in sse, sse[:100])
    fin = json.loads(sse.strip().split("data: ")[-1])
    ans = fin.get("answer") or fin.get("artefak") or ""
    check("SSE jawab ada", bool(ans), str(fin)[:120])
except Exception as e:
    check("serve end-to-end", False, str(e)[:120])

# --- /export command ---
print("-- /export command --")
out = COMMANDS["export"]["run"](a, [])
check("/export command", "session →" in out and "stats:" in out, out[:80])

# cleanup
for n in ["test1", "test2"]:
    a.keyring.remove(n)
print(f"\n=== serve+byok: PASSED {PASS} / FAILED {FAIL} ===")
sys.exit(1 if FAIL else 0)
