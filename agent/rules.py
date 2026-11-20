# agent/rules.py — time-traveling stream rules (internal feature 04).
# Config: stream_rules = [{"name": "...", "pattern": "<regex>",
#                          "inject": "<system reminder bila pattern kena>"}]
# Mekanisme: regex dijalan pada content assistant TIAP turn. Kena → inject message
# user ke memory + catat trace. Beda dengan prompt biasa: aturan aktif hanya saat
# pola muncul (dormant sampai kecemat), nol context tax di turn normal.

import re


class RuleEngine:
    def __init__(self, rules):
        self.rules = []
        for r in rules or []:
            try:
                self.rules.append({"name": r["name"],
                                   "rx": re.compile(r["pattern"], re.I),
                                   "inject": r["inject"]})
            except (KeyError, re.error) as e:
                # rule rusak jangan matikan harness
                self.rules.append({"name": r.get("name", "?"), "rx": None,
                                   "inject": "", "error": str(e)})

    def match(self, text: str):
        hits = []
        if not text:
            return hits
        for r in self.rules:
            if r.get("rx") and r["rx"].search(text):
                hits.append({"name": r["name"], "inject": r["inject"]})
        return hits
