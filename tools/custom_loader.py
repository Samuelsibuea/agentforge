# tools/custom_loader.py — Dynamic User-Created Tool Engine with Type Inference and Schema Generation
import inspect
import importlib.util
import os
import sys
from typing import get_type_hints, Any, Dict, Callable


TYPE_MAP = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
}


def function_to_schema(fn: Callable) -> Dict[str, Any]:
    """Inspects a Python function's docstring and type hints to generate OpenAI/MCP JSON schema."""
    sig = inspect.signature(fn)
    hints = get_type_hints(fn) if hasattr(fn, "__annotations__") else {}
    doc = (fn.__doc__ or "").strip()
    
    properties = {}
    required = []

    for name, param in sig.parameters.items():
        if name in ("self", "cls"):
            continue
        p_type = hints.get(name, str)
        json_type = TYPE_MAP.get(p_type, "string")
        
        properties[name] = {
            "type": json_type,
            "description": f"Parameter '{name}' ({json_type})"
        }
        if param.default is inspect.Parameter.empty:
            required.append(name)

    return {
        "type": "function",
        "function": {
            "name": fn.__name__,
            "description": doc or f"Custom user-created tool: {fn.__name__}",
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required
            }
        }
    }


def load_custom_tools_from_dir(custom_dir: str = "tools/custom") -> Dict[str, Callable]:
    """Discovers and imports user-defined Python tool files dynamically."""
    tools = {}
    if not os.path.exists(custom_dir):
        os.makedirs(custom_dir, exist_ok=True)
        return tools

    for fname in os.listdir(custom_dir):
        if fname.endswith(".py") and not fname.startswith("__"):
            fpath = os.path.join(custom_dir, fname)
            mod_name = f"custom_tool_{fname[:-3]}"
            try:
                spec = importlib.util.spec_from_file_location(mod_name, fpath)
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    sys.modules[mod_name] = mod
                    spec.loader.exec_module(mod)

                    # Look for functions exposed in module
                    for attr_name in dir(mod):
                        if not attr_name.startswith("_"):
                            attr = getattr(mod, attr_name)
                            if inspect.isfunction(attr) and attr.__module__ == mod_name:
                                schema = function_to_schema(attr)
                                setattr(attr, "_mcp_schema", schema)
                                tools[attr.__name__] = attr
            except Exception as e:
                print(f"[custom_loader] Gagal memuat {fname}: {e}")
    return tools
