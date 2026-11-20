# test_cron_learn.py — verifikasi unit: cron, learn + serve E2E + BYOK rotation.
import json, os, sys, threading, time, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agent.core import Agent
from agent.cron import CronEngine
from agent.learn import extract_skill, learned_index

PASS = FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    s = "PASS" if cond else "FAIL"
    if cond:
        PASS += 1
    else:
        FAIL += 1
    print(f"  [{s}] {name}" + (f" — {detail}" if detail and not cond else ""))


print("=== cron + learn + serve E2E ===")
cfg = json.load(open("config.json"))
cfg.setdefault("models", {})["chain"] = ["glm-5.3-flash"]
cfg["approval_mode"] = "write"
cfg["auto_approve"] = True
cfg["hooks"] = {}
cfg["stream_rules"] = []
cfg["veritas"] = {"enabled": True}
json.dump(cfg, open("config.json", "w"))

a = Agent("config.json")

# --- cron ---
print("-- cron --")
c = CronEngine(a.workspace)
r = c.add("ping", "* * * * *", "jawab satu kata: hidup")
check("cron add", r["ok"] and r["schedule"] == "* * * * *")
check("cron ls", len(c.list()) == 1 and c.list()[0]["name"] == "ping")
check("cron matcher now", len(c.due()) == 1, f"due={[j['name'] for j in c.due()]}")
check("cron bad schedule", not c.add("x", "* * *", "t")["ok"])
c.pause("ping", True)
check("cron pause", len(c.due()) == 0)
c.pause("ping", False)
fired = c.tick()
check("cron tick jalan", len(fired) == 1 and fired[0].get("ok") is True,
      json.dumps(fired)[:150])
check("cron runs.jsonl", os.path.exists("workspace/cron/runs.jsonl"))
c.remove("ping")
check("cron rm", len(c.list()) == 0)

# --- learn ---
print("-- learn --")
a.run_log = [{"type": "tool", "name": "web_search", "result": "ok"},
             {"type": "tool", "name": "file_write", "result": "ok"}]
p = extract_skill(a, "cari lalu tulis", ["web_search", "file_write"], "hasil 2 file")
check("learn extract", p is not None and os.path.exists(p), str(p))
li = learned_index()
check("learn index", len(li) == 1 and li[0]["steps"] == 2, str(li))

# --- BYOK rotation under 401 (credential pool) ---
print("-- BYOK rotation --")
kr = a.keyring
kr.add("k1", "sk-dummy-key-0000000000000001", "kei")
kr.add("k2", "sk-dummy-key-0000000000000002", "kei")
n1, key1 = kr.pick("kei")
check("pick k1 first", n1 == "k1")
kr.mark_fail("k1")
n2, key2 = kr.pick("kei")
check("fail → k2", n2 == "k2")
rot = kr.rotate("kei")
check("rotate dari k2 (k1 mati) → k2", rot == "k2", f"got {rot}")
kr.idx["keys"]["k1"]["active"] = True  # hidupkan lagi
rot2 = kr.rotate("kei")
check("rotate k2 → k1 hidup", rot2 == "k1", f"got {rot2}")
kr.remove("k1"); kr.remove("k2")
kr.idx["rotation"] = {}  # bersihkan pointer rotation sisa
kr._save()
check("pool kosong → fallback config",
      Agent("config.json").active_key_name is None)

# --- serve E2E (pola sendiri) ---
print("-- serve E2E --")
from agent.serve import serve
t = threading.Thread(target=serve, kwargs={"port": 8788}, daemon=True)
t.start()
time.sleep(1.0)
h = urllib.request.urlopen("http://127.0.0.1:8788/health", timeout=5)
check("health 200", h.status == 200)
req = urllib.request.Request(
    "http://127.0.0.1:8788/v1/chat",
    data=json.dumps({"task": "hitung 6*7 lalu tulis ke workspace/output/v4.txt",
                     "skill": "research"}).encode(),
    headers={"Content-Type": "application/json"})
resp = urllib.request.urlopen(req, timeout=120)
sse = resp.read().decode()
fin = json.loads(sse.strip().split("data: ")[-1])
check("serve calculate+write", fin.get("ok") is True, str(fin)[:150])
check("serve artefak di disk", os.path.exists("workspace/output/v4.txt")
      and "42" in open("workspace/output/v4.txt").read(),
      open("workspace/output/v4.txt").read() if os.path.exists("workspace/output/v4.txt") else "no file")

print(f"\n=== cron+learn: PASSED {PASS} / FAILED {FAIL} ===")
sys.exit(1 if FAIL else 0)
