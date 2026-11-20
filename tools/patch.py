# tools/patch.py — hashline edit (feature 11): edit by content hash.
# Model sebut anchor hash, bukan mengetik ulang baris. Stale anchor → reject
# sebelum korupsi. Mekanisme: sha256(isi file)[:8] jadi anchor; argumen
# old_hash + new_content. Kalau hash file != old_hash → tolak (file berubah).
import hashlib


def file_patch(path: str, old_hash: str, new_content: str) -> dict:
    """Patch file dengan anchor hash. old_hash = sha256(file)[:8] saat baca.

    Stale anchor (file berubah sejak baca) → reject, nol corrupt."""
    try:
        cur = open(path, encoding="utf-8").read()
    except FileNotFoundError:
        return {"ok": False, "error": f"file tidak ada: {path}"}
    cur_hash = hashlib.sha256(cur.encode()).hexdigest()[:8]
    if cur_hash != old_hash:
        return {"ok": False, "error": "stale anchor",
                "expected": old_hash, "actual": cur_hash,
                "note": "file berubah sejak dibaca; baca ulang lalu patch"}
    open(path, "w", encoding="utf-8").write(new_content)
    new_hash = hashlib.sha256(new_content.encode()).hexdigest()[:8]
    return {"ok": True, "path": path, "old_hash": old_hash,
            "new_hash": new_hash, "bytes": len(new_content)}
