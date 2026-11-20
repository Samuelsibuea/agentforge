# test_chain_budget.py — verifikasi unit: fallback chain, budget gate,
# approval ladder, hooks, stream rules, veritas, hashline patch.
# Jalan: python test_chain_budget.py  (nol dependensi eksternal, nol network.)
import json, os, sys, tempfile, types

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

passed, failed = [], []

def check(name, cond, detail=""):
    (passed if cond else failed).append(f"{name} {detail}".strip())

# ---- 1. HookEngine ----
from agent.hooks import HookEngine
h = HookEngine({"pre_tool": [{"type": "block", "match": "bash", "reason": "no bash"}],
                "post_tool": [{"type": "log"}]})
v = h.fire("pre_tool", tool="bash")
check("hook_block_bash", v.get("block") is True and "no bash" in v.get("reason", ""))
res = h.fire("pre_tool", tool="web_search")
check("hook_allow_other", res.get("block") is False)
h.fire("post_tool", tool="web_search")
check("hook_log_fired", len(h.fired) == 2)

# ---- 2. RuleEngine (stream rules) ----
from agent.rules import RuleEngine
r = RuleEngine([{"name": "no-fence", "pattern": "berhenti|stop",
                 "inject": "REMINDER: lanjutkan."}])
hits = r.match("ayo berhenti dulu")
check("rule_hit", len(hits) == 1 and hits[0]["name"] == "no-fence")
check("rule_miss", r.match("semua baik saja") == [])

# ---- 3. Veritas ----
from agent.veritas import Veritas
vt = Veritas({"enabled": True})
c = vt.check("calculate", {"expression": "2+2*3"}, {"ok": True, "data": {"result": "8"}})
check("veritas_calc_ok", c is not None and c["verdict"] == "verified", str(c))
c2 = vt.check("calculate", {"expression": "2+2*3"}, {"ok": True, "data": {"result": "9"}})
check("veritas_calc_mismatch", c2 is not None and "mismatch" in c2["verdict"], str(c2))
c3 = vt.check("file_write", {"path": "/definitely/not/exist/x", "content": "abc"},
              {"ok": True})
check("veritas_file_drift", c3 is not None and c3["verdict"] == "drift", str(c3))
c4 = vt.check("web_search", {}, {"ok": True, "data": {"items": [1, 2, 3]}})
check("veritas_search_count", c4 is not None and c4["count"] == 3, str(c4))

# ---- 4. file_patch hashline ----
from tools.patch import file_patch
tmp = tempfile.mkdtemp()
fp = os.path.join(tmp, "a.txt")
open(fp, "w").write("v1")
import hashlib
h1 = hashlib.sha256(b"v1").hexdigest()[:8]
ok1 = file_patch(fp, h1, "alpha")
check("patch_ok", ok1["ok"] is True and ok1["new_hash"] ==
      hashlib.sha256(b"alpha").hexdigest()[:8], str(ok1))
ok2 = file_patch(fp, h1, "beta")  # stale: file sudah alpha
check("patch_stale_reject", ok2["ok"] is False and ok2["error"] == "stale anchor",
      str(ok2))
ok3 = file_patch(fp, ok1["new_hash"], "beta")
check("patch_after_refresh", ok3["ok"] is True and
      open(fp).read() == "beta", str(ok3))

# ---- 5. budget gate math ----
from agent.core import Agent
class FakeRouter:
    def schemas(self): return []
a = object.__new__(Agent)
a.token_budget = 1000
a.tokens_used = 950
check("budget_left", a._budget_left() == 50)
a.tokens_used = 1000
check("budget_zero", a._budget_left() == 0)

# ---- 6. approval ladder ----
a.approval_mode = "write"
check("approval_write_skips_read", a._needs_approval("web_search") is False)
check("approval_write_gates_write", a._needs_approval("file_write") is True)
a.approval_mode = "yolo"
check("approval_yolo_all", a._needs_approval("file_write") is False)

# ---- 7. model chain config ----
cfg = json.load(open("config.example.json"))
check("config_chain", len(cfg["models"]["chain"]) == 2 and
      cfg["models"]["chain"][0] == "glm-5.3-flash")
check("config_rules", len(cfg["stream_rules"]) == 1)
check("config_veritas", cfg["veritas"]["enabled"] is True)

# ---- 8. router muat file_patch ----
from tools.router import ToolRouter
tr = ToolRouter(tempfile.mkdtemp())
check("router_has_patch", "file_patch" in tr.tools, str(list(tr.tools)))
check("router_7_tools", len(tr.tools) == 7, str(len(tr.tools)))

print(f"\nPASSED {len(passed)} / FAILED {len(failed)}")
for p in passed: print(f"  [OK] {p}")
for f in failed: print(f"  [FAIL] {f}")
sys.exit(1 if failed else 0)
