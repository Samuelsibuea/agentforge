# agent/mcp.py — Model Context Protocol (MCP) Stdio Client for AgentForge
# Implements JSON-RPC 2.0 transport over stdin/stdout for external MCP tool servers.
import json
import os
import subprocess
import threading
from typing import Any, Dict, List, Optional


class MCPError(Exception):
    pass


class MCPClient:
    """Manages connection and JSON-RPC lifecycle with an MCP server running as a subprocess."""
    def __init__(self, name: str, command: str, args: Optional[List[str]] = None, env: Optional[Dict[str, str]] = None):
        self.name = name
        self.command = command
        self.args = args or []
        self.env = env or {}
        
        self.process: Optional[subprocess.Popen] = None
        self._request_id = 0
        self._pending_requests: Dict[int, threading.Event] = {}
        self._responses: Dict[int, Any] = {}
        self._lock = threading.Lock()
        self._reader_thread: Optional[threading.Thread] = None
        self._running = False
        self.server_info: Dict[str, Any] = {}
        self.tools: List[Dict[str, Any]] = []

    def start(self, timeout: float = 10.0) -> bool:
        """Spawn server process, start IO thread, and perform handshake."""
        full_env = os.environ.copy()
        full_env.update(self.env)
        cmd = [self.command] + self.args

        try:
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                env=full_env,
            )
        except Exception as e:
            raise MCPError(f"Gagal menjalankan server MCP '{self.name}' ({cmd}): {e}")

        self._running = True
        self._reader_thread = threading.Thread(target=self._read_loop, daemon=True)
        self._reader_thread.start()

        # MCP Handshake: initialize
        init_res = self.send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "clientInfo": {
                "name": "agentforge",
                "version": "2.0.0"
            }
        }, timeout=timeout)

        self.server_info = init_res.get("serverInfo", {})

        # MCP Handshake: notifications/initialized
        self.send_notification("notifications/initialized", {})

        # Fetch tools catalog
        tools_res = self.send_request("tools/list", {}, timeout=timeout)
        self.tools = tools_res.get("tools", [])
        return True

    def _read_loop(self):
        """Reads newline-delimited JSON-RPC messages from stdout."""
        while self._running and self.process and self.process.stdout:
            line = self.process.stdout.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
                req_id = msg.get("id")
                if req_id is not None and req_id in self._pending_requests:
                    self._responses[req_id] = msg
                    self._pending_requests[req_id].set()
            except Exception:
                pass
        self._running = False

    def send_request(self, method: str, params: Optional[Dict[str, Any]] = None, timeout: float = 15.0) -> Any:
        """Sends a JSON-RPC request and synchronously waits for matching ID response."""
        if not self._running or not self.process or not self.process.stdin:
            raise MCPError(f"Server MCP '{self.name}' tidak berjalan.")

        with self._lock:
            self._request_id += 1
            req_id = self._request_id
            ev = threading.Event()
            self._pending_requests[req_id] = ev

        payload = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params or {}
        }

        try:
            self.process.stdin.write(json.dumps(payload) + "\n")
            self.process.stdin.flush()
        except Exception as e:
            raise MCPError(f"Gagal mengirim pesan ke MCP '{self.name}': {e}")

        if not ev.wait(timeout=timeout):
            raise MCPError(f"Timeout menunggu respons MCP '{self.name}' untuk method '{method}' (id={req_id}).")

        res = self._responses.pop(req_id, {})
        with self._lock:
            self._pending_requests.pop(req_id, None)

        if "error" in res:
            err = res["error"]
            raise MCPError(f"MCP error [{err.get('code')}]: {err.get('message')}")

        return res.get("result", {})

    def send_notification(self, method: str, params: Optional[Dict[str, Any]] = None):
        """Sends a JSON-RPC notification (no response expected)."""
        if not self._running or not self.process or not self.process.stdin:
            return

        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {}
        }
        try:
            self.process.stdin.write(json.dumps(payload) + "\n")
            self.process.stdin.flush()
        except Exception:
            pass

    def call_tool(self, name: str, arguments: Dict[str, Any], timeout: float = 30.0) -> Dict[str, Any]:
        """Calls a tool via MCP 'tools/call' protocol."""
        result = self.send_request("tools/call", {
            "name": name,
            "arguments": arguments
        }, timeout=timeout)

        # Convert MCP content array into unified output
        content_items = result.get("content", [])
        text_outputs = []
        for item in content_items:
            if item.get("type") == "text":
                text_outputs.append(item.get("text", ""))
        
        output_str = "\n".join(text_outputs) if text_outputs else json.dumps(result, ensure_ascii=False)
        return {
            "ok": not result.get("isError", False),
            "output": output_str,
            "raw": result
        }

    def close(self):
        """Gracefully terminate server process."""
        self._running = False
        if self.process:
            try:
                if self.process.stdin:
                    self.process.stdin.close()
                if self.process.stdout:
                    self.process.stdout.close()
                if self.process.stderr:
                    self.process.stderr.close()
                self.process.terminate()
                self.process.wait(timeout=2.0)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
            self.process = None


class MCPRegistry:
    """Manages multiple MCP server instances defined in configuration."""
    def __init__(self, config_servers: Optional[Dict[str, Any]] = None):
        self.servers: Dict[str, MCPClient] = {}
        if config_servers:
            self.load_from_config(config_servers)

    def load_from_config(self, config_servers: Dict[str, Any]):
        for name, spec in config_servers.items():
            cmd = spec.get("command")
            args = spec.get("args", [])
            env = spec.get("env", {})
            if cmd:
                client = MCPClient(name=name, command=cmd, args=args, env=env)
                self.servers[name] = client

    def start_all(self, strict: bool = False) -> Dict[str, bool]:
        status = {}
        for name, client in self.servers.items():
            try:
                client.start()
                status[name] = True
            except Exception as e:
                status[name] = False
                if strict:
                    raise e
        return status

    def register_into_router(self, router: Any):
        """Registers all tools exposed by running MCP servers into AgentForge's ToolRouter."""
        for sname, client in self.servers.items():
            for tool_spec in client.tools:
                tname = str(tool_spec.get("name", ""))
                if not tname:
                    continue
                desc = str(tool_spec.get("description", ""))
                schema = tool_spec.get("inputSchema", {})

                # Bind tool closure
                def make_handler(c=client, tn=tname):
                    def handler(**kwargs):
                        return c.call_tool(tn, kwargs)
                    return handler

                handler_fn = make_handler()
                fn_name = f"mcp__{sname}__{tname}"
                handler_fn.__name__ = fn_name
                handler_fn.__doc__ = desc

                # Inject custom schema attribute for ToolRouter
                setattr(handler_fn, "_mcp_schema", {
                    "type": "function",
                    "function": {
                        "name": fn_name,
                        "description": f"[MCP:{sname}] {desc}",
                        "parameters": schema
                    }
                })
                router.register(handler_fn)

    def close_all(self):
        for client in self.servers.values():
            client.close()
