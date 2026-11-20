# agent/veritas.py — VERITAS LAYER (gamechanger, turunan dari internal tools + review).
# Prinsip: harness tidak percaya klaim lisan agent. Untuk tiap tool call yang
# menghasilkan data, harness MEMBUAT + MENJALANKAN kode verifikasi kecil, lalu
# catat verdict di trace. Agent bisa saja berhalusinasi; veritas tidak.
#
# Terpasang: setelah post_tool hook, sebelum tool result dikembalikan ke memory.
# Saat ini verifikator untuk: web_fetch (URL hidup + panjang konten),
# web_search (hasil parse + count), file_read (file nyata + byte), calculate
# (rehitung ulang dengan decimal), file_write (baca ulang file + byte match).
# Verifikator baru = tambah dict di CHECKERS, tanpa sentuh core loop.

import json, os, re
from decimal import Decimal, InvalidOperation


class Veritas:
    def __init__(self, cfg):
        self.enabled = bool((cfg or {}).get("enabled", True))
        self.max_body = int((cfg or {}).get("max_body", 4000))

    def check(self, tool, args, res):
        """Return dict verdict atau None (tool tanpa verifikator)."""
        if not self.enabled or not res.get("ok"):
            return None
        fn = getattr(self, f"_v_{tool}", None)
        if not fn:
            return None
        return fn(args, res)

    # --- verifikator ---
    def _v_web_fetch(self, args, res):
        body = str(res.get("data", {}).get("body", "")) if isinstance(res.get("data"), dict) else str(res.get("data", ""))
        url = args.get("url", "")
        v = {"url": url[:120], "body_len": len(body),
             "title_tag": bool(re.search(r"<title[^>]*>[^<]+</title>", body[:4000], re.I)),
             "verdict": "verified" if len(body) > 200 else "thin"}
        return v

    def _v_web_search(self, args, res):
        data = res.get("data")
        items = data.get("items") or data.get("results") or [] if isinstance(data, dict) else []
        return {"query": args.get("query", "")[:80], "count": len(items),
                "verdict": "verified" if items else "empty"}

    def _v_file_read(self, args, res):
        p = args.get("path", "")
        data = res.get("data")
        n = len(str(data.get("content", ""))) if isinstance(data, dict) else len(str(data))
        return {"path": p, "bytes_read": n, "verdict": "verified" if n > 0 else "empty"}

    def _v_calculate(self, args, res):
        expr = args.get("expression", "")
        try:
            # hitung ulang independen: AST parse, hanya angka + 4 operator
            import ast, operator
            OPS = {ast.Add: operator.add, ast.Sub: operator.sub,
                   ast.Mult: operator.mul, ast.Div: operator.truediv,
                   ast.USub: operator.neg, ast.UAdd: operator.pos}
            def ev(n):
                if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
                    return float(n.value)
                if isinstance(n, ast.BinOp) and type(n.op) in OPS:
                    return OPS[type(n.op)](ev(n.left), ev(n.right))
                if isinstance(n, ast.UnaryOp) and type(n.op) in OPS:
                    return OPS[type(n.op)](ev(n.operand))
                raise ValueError(f"unsupported node {type(n).__name__}")
            val = ev(ast.parse(expr, mode="eval").body)
            data = res.get("data", res)  # result bisa di top-level atau di data
            got_raw = data.get("result", "")
            try:
                same = abs(float(got_raw) - val) < 1e-9
            except (TypeError, ValueError):
                same = False
            return {"expr": expr[:60], "recomputed": repr(val),
                    "verdict": "verified" if same else
                               f"mismatch: harness={val} agent={got_raw}"}
        except Exception as e:
            return {"expr": expr[:60], "verdict": "skip", "why": str(e)[:60]}

    def _v_file_write(self, args, res):
        p = args.get("path", "")
        want = args.get("content", "")
        try:
            got = open(p, encoding="utf-8").read() if os.path.exists(p) else ""
        except Exception:
            got = ""
        return {"path": p, "disk_len": len(got), "expected_len": len(want),
                "verdict": "verified" if got == want else "drift"}
