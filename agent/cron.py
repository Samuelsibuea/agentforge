# agent/cron.py — jadwalkan task → jalan otomatis → kirim hasil.
# Format jadwal: menit jam tanggal.bulan hari (cron 5-field) + nama + task + skill.
# Penyimpanan: workspace/cron/jobs.json + runs.jsonl. Jalar: `python -m agent.cron tick`.
# job = schedule + prompt + delivery; hasil → log + file, nol duplikasi.
import json, os, subprocess, sys
from datetime import datetime
from zoneinfo import ZoneInfo

WIB = ZoneInfo("Asia/Jakarta")


class CronEngine:
    def __init__(self, workspace="workspace"):
        self.dir = f"{workspace}/cron"
        os.makedirs(self.dir, exist_ok=True)
        os.chmod(self.dir, 0o700)
        self.jf = os.path.join(self.dir, "jobs.json")
        self.jobs = json.load(open(self.jf)) if os.path.exists(self.jf) else []

    def _save(self):
        with open(self.jf, "w") as f:
            json.dump(self.jobs, f, indent=1)
        os.chmod(self.jf, 0o600)

    def add(self, name, schedule, task, skill="research"):
        """schedule = cron 5-field string, mis. "*/15 * * * *" atau "0 9 * * 1"."""
        fields = schedule.split()
        if len(fields) != 5:
            return {"ok": False, "error": "schedule harus 5 field cron: menit jam tanggal.bulan hari"}
        self.jobs.append({"name": name, "schedule": schedule, "task": task,
                          "skill": skill, "added_wib": _now(), "paused": False,
                          "last_run": None, "runs": 0})
        self._save()
        return {"ok": True, "name": name, "schedule": schedule, "task": task[:60]}

    def remove(self, name):
        before = len(self.jobs)
        self.jobs = [j for j in self.jobs if j["name"] != name]
        self._save()
        return {"ok": len(self.jobs) < before, "removed": name}

    def pause(self, name, paused=True):
        for j in self.jobs:
            if j["name"] == name:
                j["paused"] = paused
                self._save()
                return {"ok": True, "name": name, "paused": paused}
        return {"ok": False, "error": f"job {name} tidak ada"}

    def list(self):
        return [{"name": j["name"], "schedule": j["schedule"],
                 "task": j["task"][:70], "skill": j["skill"],
                 "paused": j["paused"], "runs": j["runs"],
                 "last_run": j["last_run"]} for j in self.jobs]

    # ---------- cron field matcher ----------
    @staticmethod
    def _match(field, value, maximum):
        if field == "*":
            return True
        for part in field.split(","):
            if "/" in part:
                base, step = part.split("/", 1)
                start = 0 if base == "*" else int(base)
                if value >= start and (value - start) % int(step) == 0:
                    return True
            elif "-" in part:
                lo, hi = map(int, part.split("-"))
                if lo <= value <= hi:
                    return True
            elif int(part) == value:
                return True
        return False

    def due(self, now=None):
        """Job yang jatuh pada waktu now (default: sekarang WIB)."""
        now = now or datetime.now(WIB)
        return [j for j in self.jobs if not j["paused"]
                and self._match(j["schedule"].split()[0], now.minute, 59)
                and self._match(j["schedule"].split()[1], now.hour, 23)
                and self._match(j["schedule"].split()[2], now.day, 31)
                and self._match(j["schedule"].split()[3], now.month, 12)
                and self._match(j["schedule"].split()[4], now.weekday(), 6)]

    def tick(self, verbose=False):
        """tick: jalan semua job yang jatuh sekarang."""
        fired = []
        for j in self.due():
            if verbose:
                print(f"[cron] {j['name']} → {j['task'][:50]}")
            # jalar lewat Agent.run di subprocess biar isolated + idempotent
            r = subprocess.run([sys.executable, "-c", f"""
import sys, json
sys.path.insert(0, '.')
from agent.core import Agent
a = Agent('config.json')
res = a.run({json.dumps(j['task'])!r}, skill={json.dumps(j['skill'])!r}, verbose=False)
print(json.dumps({{'ok': res['ok'], 'answer': (res.get('answer') or '')[:500],
                   'artefak': res.get('artefak'), 'stats': res.get('stats')}},
                  ensure_ascii=False))
"""], capture_output=True, text=True, timeout=300, cwd=os.getcwd())
            outcome = {"name": j["name"], "ran_wib": _now(), "ok": False}
            try:
                line = [l for l in r.stdout.strip().splitlines() if l.startswith("{")][-1]
                outcome = json.loads(line)
                outcome["ok"] = bool(outcome.get("ok"))
            except Exception:
                outcome["error"] = r.stderr.strip()[-200:]
            fired.append(outcome)
            j["last_run"] = _now()
            j["runs"] += 1
            self._append_run(j["name"], outcome)
        self._save()
        return fired

    def _append_run(self, name, outcome):
        with open(os.path.join(self.dir, "runs.jsonl"), "a") as f:
            f.write(json.dumps({"job": name, **outcome}, ensure_ascii=False) + "\n")


def _now():
    return datetime.now(WIB).strftime("%Y-%m-%d %H:%M:%S")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="AgentForge cron")
    p.add_argument("op", choices=["add", "ls", "rm", "pause", "resume", "tick"])
    p.add_argument("--name"); p.add_argument("--schedule"); p.add_argument("--task")
    p.add_argument("--skill", default="research")
    a = p.parse_args()
    c = CronEngine()
    if a.op == "add":
        print(json.dumps(c.add(a.name, a.schedule, a.task, a.skill), ensure_ascii=False))
    elif a.op == "ls":
        print(json.dumps(c.list(), ensure_ascii=False, indent=1))
    elif a.op == "rm":
        print(json.dumps(c.remove(a.name), ensure_ascii=False))
    elif a.op == "pause":
        print(json.dumps(c.pause(a.name, True), ensure_ascii=False))
    elif a.op == "resume":
        print(json.dumps(c.pause(a.name, False), ensure_ascii=False))
    elif a.op == "tick":
        print(json.dumps(c.tick(verbose=True), ensure_ascii=False, indent=1))
