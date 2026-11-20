# tools/files.py — file IO scoped ke workspace sendiri.
import os, json

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _safe(rel: str) -> str:
    p = os.path.normpath(os.path.join(BASE, rel))
    if not p.startswith(BASE):
        raise ValueError("path di luar workspace ditolak")
    return p

def file_read(path: str) -> dict:
    """Baca file di workspace (relatif terhadap root repo)."""
    try:
        with open(_safe(path), encoding="utf-8", errors="ignore") as f:
            content = f.read()
        return {"ok": True, "path": path, "chars": len(content), "content": content[:8000]}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def file_write(path: str, content: str) -> dict:
    """Tulis file ke workspace. Bikin folder parent kalau belum ada."""
    try:
        full = _safe(path)
        os.makedirs(os.path.dirname(full) or BASE, exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            f.write(content)
        return {"ok": True, "path": path, "bytes": len(content.encode())}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def file_list(dir: str = "workspace") -> dict:
    """List isi folder workspace."""
    try:
        p = _safe(dir)
        items = os.listdir(p) if os.path.isdir(p) else []
        return {"ok": True, "dir": dir, "items": sorted(items)}
    except Exception as e:
        return {"ok": False, "error": str(e)}
