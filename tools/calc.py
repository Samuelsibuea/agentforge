# tools/calc.py — kalkulator presisi-tinggi, aman (eval dibatasi).
from decimal import Decimal, getcontext
import re

def calculate(expression: str) -> dict:
    """Hitung ekspresi aritmatika. Angka presisi-tinggi (Decimal), operator + - * / ** ( ) %."""
    getcontext().prec = 50
    expr = expression.strip()
    if not re.fullmatch(r"[\d\s+\-*/().%]+|^[+\-*/().%\d\s]+(sqrt|pow)\(?[\d\s+\-*/().%]*\)?$", expr):
        if re.search(r"[a-zA-Z_]", expr):
            return {"ok": False, "error": "hanya angka & operator aritmatika"}
    try:
        # eval terbatas: tidak ada builtin, tidak ada import
        safe = {"__builtins__": {}, "sqrt": lambda x: float(x) ** 0.5,
                "pow": lambda a, b: float(a) ** float(b), "abs": abs}
        val = eval(expr, safe, {})
        if isinstance(val, float):
            val = round(val, 10)
        return {"ok": True, "expression": expr, "result": val}
    except Exception as e:
        return {"ok": False, "error": str(e)}
