
# Pola: credential pool rotate + providers/manage.
# Key disimpan DI DISK saja (chmod 600), nol plaintext di chat / config.json.
# Registry: workspace/keys/*.json  →  {name, provider, key, endpoint, models[], active}
# Rotation: key habis quota (429) → key berikutnya untuk provider yang sama,
# session affinity + backoff per credential (pola sendiri).
import json, os
from zoneinfo import ZoneInfo

WIB = ZoneInfo("Asia/Jakarta")

PROVIDER_DEFAULTS = {
    "kei":      "https://ai.kei-inference.web.id/v1",
    "openai":   "https://api.openai.com/v1",
    "anthropic": "https://api.anthropic.com/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "deepseek": "https://api.deepseek.com/v1",
    "groq":     "https://api.groq.com/openai/v1",
}


class KeyRing:
    def __init__(self, workspace="workspace"):
        self.dir = f"{workspace}/keys"
        os.makedirs(self.dir, exist_ok=True)
        os.chmod(self.dir, 0o700)
        self._idx = os.path.join(self.dir, "index.json")
        self.idx = self._load_idx()

    def _load_idx(self):
        if os.path.exists(self._idx):
            return json.load(open(self._idx))
        return {"keys": {}, "rotation": {}}

    def _save(self):
        with open(self._idx, "w") as f:
            json.dump(self.idx, f, indent=1)
        os.chmod(self._idx, 0o600)

    # ---------- manage ----------
    def add(self, name, key, provider, endpoint=None, models=None):
        """Tambah key. Nol plaintext di output — hash saja yang tercatat."""
        if not key or len(key) < 8:
            return {"ok": False, "error": "key terlalu pendek / kosong"}
        entry = {
            "name": name,
            "provider": provider,
            "endpoint": endpoint or PROVIDER_DEFAULTS.get(provider, ""),
            "models": models or [],
            "fingerprint": key[:4] + "…" + key[-4:],
            "added_wib": _now(),
            "active": True,
            "fails": 0,
        }
        self.idx["keys"][name] = entry
        with open(os.path.join(self.dir, f"{name}.key"), "w") as f:
            f.write(key)
        os.chmod(os.path.join(self.dir, f"{name}.key"), 0o600)
        self._save()
        return {"ok": True, "name": name, "fingerprint": entry["fingerprint"],
                "provider": provider}

    def remove(self, name):
        if name not in self.idx["keys"]:
            return {"ok": False, "error": f"key {name} tidak ada"}
        kp = os.path.join(self.dir, f"{name}.key")
        if os.path.exists(kp):
            os.remove(kp)
        self.idx["keys"].pop(name)
        self._save()
        return {"ok": True, "removed": name}

    def get(self, name):
        kp = os.path.join(self.dir, f"{name}.key")
        if name not in self.idx["keys"] or not os.path.exists(kp):
            return None
        return open(kp).read().strip()

    def list(self):
        return [{"name": n, **{k: v for k, v in e.items() if k != "fails"}}
                for n, e in self.idx["keys"].items()]

    # ---------- rotation (credential pool) ----------
    def mark_fail(self, name):
        if name in self.idx["keys"]:
            self.idx["keys"][name]["fails"] += 1
            self.idx["keys"][name]["active"] = False
            self._save()

    def pick(self, provider):
        """Pilih key aktif untuk provider, session affinity + ganti kalau mati."""
        cands = [(n, e) for n, e in self.idx["keys"].items()
                 if e.get("provider") == provider and e.get("active", True)]
        if not cands:
            return None, None
        pref = self.idx["rotation"].get(provider)
        if pref in dict(cands):
            return pref, self.get(pref)
        name, _ = cands[0]
        self.idx["rotation"][provider] = name
        self._save()
        return name, self.get(name)

    def rotate(self, provider):
        """Ganti key aktif ke key hidup berikutnya (setelah 429/quota wall).
        Cari di semua key provider, maju satu dari pointer, lompati yang mati."""
        allnames = [n for n, e in self.idx["keys"].items()
                    if e.get("provider") == provider]
        if not allnames:
            return None
        cur = self.idx["rotation"].get(provider)
        start = allnames.index(cur) if cur in allnames else -1
        for step in range(1, len(allnames) + 1):
            cand = allnames[(start + step) % len(allnames)]
            if self.idx["keys"][cand].get("active", True):
                self.idx["rotation"][provider] = cand
                self._save()
                return cand
        return None


def _now():
    from datetime import datetime
    return datetime.now(WIB).strftime("%Y-%m-%d %H:%M:%S")
