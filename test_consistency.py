# test_consistency.py — run the agent on N diverse tasks, verify each one
# produces a real deliverable:
#   PASS kalau (a) jawaban final ada, (b) file output *.md ada di workspace/output,
#   (c) jawaban mengandung "Sumber" atau "sumber".
# Exit 0 kalau semua task PASS, selain itu exit 1.
import json, os, sys, time
from agent.core import Agent

TASKS = [
    "Apa itu AI agent harness? Bandingkan pendekatan utama 2026",
    "Jelaskan teknik prompt injection pada LLM agent dan mitigasinya",
    "Apa itu MCP (Model Context Protocol)? Kegunaan utamanya",
    "Bandingkan SQLite vs PostgreSQL untuk aplikasi skala kecil",
    "Apa itu RAG? Jelaskan pipeline retrieval-augmented generation",
]

def main():
    a = Agent()
    results = []
    for i, task in enumerate(TASKS, 1):
        t0 = time.time()
        print(f"[{i}/5] {task}", flush=True)
        out = a.run(task, skill="research", verbose=False)
        ans = out.get("answer") or ""
        files = os.listdir("workspace/output") if os.path.isdir("workspace/output") else []
        md = [f for f in files if f.endswith(".md")]
        has_src = ("sumber" in ans.lower()) or any("sumber" in open(f"workspace/output/{f}", encoding="utf-8", errors="ignore").read().lower() for f in md)
        ok = bool(ans.strip()) and len(md) > 0 and has_src
        dur = round(time.time() - t0, 1)
        results.append({"task": task[:40], "ok": ok, "answer_len": len(ans),
                        "md_files": md, "dur_s": dur, "tools": len(out.get("trace", []))})
        print(f"    -> {'PASS' if ok else 'FAIL'} ans={len(ans)}ch files={md} dur={dur}s", flush=True)
    passed = sum(1 for r in results if r["ok"])
    print(f"\n=== 5x CONSISTENCY: {passed}/5 PASS ===")
    with open("workspace/test_results.json", "w") as f:
        json.dump({"passed": passed, "total": 5, "results": results}, f, ensure_ascii=False, indent=1)
    sys.exit(0 if passed == 5 else 1)

if __name__ == "__main__":
    main()
