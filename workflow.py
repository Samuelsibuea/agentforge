# workflow.py — end-to-end: topik -> riset live -> laporan .md di workspace/output.
import sys, json
from agent.core import Agent

def main():
    topic = sys.argv[1] if len(sys.argv) > 1 else \
        "Bandingkan framework agent Python: LangGraph vs CrewAI vs AutoGen"
    print(f"[workflow] topik: {topic}")
    a = Agent()
    out = a.run(topic, skill="research")
    print("[workflow] trace:")
    for t in out.get("trace", []):
        print("  ", json.dumps(t, ensure_ascii=False)[:160])
    ans = out.get("answer") or out.get("error")
    print("[workflow] answer:\n" + (ans or ""))
    # artefak output
    import os
    d = "workspace/output"
    if os.path.isdir(d):
        print("[workflow] workspace/output:")
        for f in sorted(os.listdir(d)):
            p = os.path.join(d, f)
            print(f"   {p}  {os.path.getsize(p)} bytes")

if __name__ == "__main__":
    main()
