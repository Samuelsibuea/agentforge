# test_mcp.py — Comprehensive Test Suite for AgentForge MCP (Model Context Protocol)
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from agent.mcp import MCPClient, MCPRegistry
from tools.router import ToolRouter


class TestMCPIntegration(unittest.TestCase):
    def test_01_mcp_handshake_and_tool_call(self):
        """Verify full MCP JSON-RPC stdio handshake, tools/list, and tools/call using an inline mock server."""
        # Standalone Python script acting as a compliant MCP stdio server
        mock_server_code = """
import sys, json

def main():
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        req = json.loads(line.strip())
        method = req.get("method")
        req_id = req.get("id")

        if method == "initialize":
            res = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {"name": "mock-mcp-server", "version": "1.0.0"},
                    "capabilities": {"tools": {}}
                }
            }
            sys.stdout.write(json.dumps(res) + "\\n")
            sys.stdout.flush()
        elif method == "notifications/initialized":
            pass # Notification, no response
        elif method == "tools/list":
            res = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "tools": [
                        {
                            "name": "echo_metric",
                            "description": "Echo back diagnostic metrics",
                            "inputSchema": {
                                "type": "object",
                                "properties": {"msg": {"type": "string"}},
                                "required": ["msg"]
                            }
                        }
                    ]
                }
            }
            sys.stdout.write(json.dumps(res) + "\\n")
            sys.stdout.flush()
        elif method == "tools/call":
            params = req.get("params", {})
            tname = params.get("name")
            args = params.get("arguments", {})
            if tname == "echo_metric":
                res = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": f"MOCK_OK:{args.get('msg')}"}],
                        "isError": False
                    }
                }
            else:
                res = {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": "Method not found"}}
            sys.stdout.write(json.dumps(res) + "\\n")
            sys.stdout.flush()

if __name__ == '__main__':
    main()
"""
        client = MCPClient(name="test_srv", command=sys.executable, args=["-c", mock_server_code])
        self.assertTrue(client.start(timeout=5.0))
        self.assertEqual(client.server_info.get("name"), "mock-mcp-server")
        self.assertEqual(len(client.tools), 1)
        self.assertEqual(client.tools[0]["name"], "echo_metric")

        # Execute call_tool
        call_res = client.call_tool("echo_metric", {"msg": "benchmark_100"})
        self.assertTrue(call_res["ok"])
        self.assertIn("MOCK_OK:benchmark_100", call_res["output"])

        client.close()

    def test_02_mcp_registry_into_router(self):
        """Verify MCP tools are seamlessly registered into ToolRouter schemas and callable by the agent."""
        mock_server_code = """
import sys, json
while True:
    line = sys.stdin.readline()
    if not line: break
    req = json.loads(line.strip())
    method, req_id = req.get("method"), req.get("id")
    if method == "initialize":
        sys.stdout.write(json.dumps({"jsonrpc":"2.0", "id": req_id, "result": {"serverInfo":{"name":"db-mcp"}}}) + "\\n")
        sys.stdout.flush()
    elif method == "tools/list":
        sys.stdout.write(json.dumps({"jsonrpc":"2.0", "id": req_id, "result": {"tools":[{"name":"query_db","description":"Query SQL db","inputSchema":{"type":"object"}}]}}) + "\\n")
        sys.stdout.flush()
    elif method == "tools/call":
        sys.stdout.write(json.dumps({"jsonrpc":"2.0", "id": req_id, "result": {"content":[{"type":"text","text":"db_rows_42"}]}}) + "\\n")
        sys.stdout.flush()
"""
        registry = MCPRegistry({
            "database": {
                "command": sys.executable,
                "args": ["-c", mock_server_code]
            }
        })
        statuses = registry.start_all(strict=True)
        self.assertTrue(statuses.get("database"))

        router = ToolRouter("workspace")
        init_tool_count = len(router.tools)
        registry.register_into_router(router)

        # Tool name registered as mcp__<server>__<tool>
        mcp_tool_name = "mcp__database__query_db"
        self.assertIn(mcp_tool_name, router.tools)
        self.assertEqual(len(router.tools), init_tool_count + 1)

        # Check schemas() output conforms to OpenAI tool schema
        all_schemas = router.schemas()
        mcp_schema = next((s for s in all_schemas if s["function"]["name"] == mcp_tool_name), None)
        self.assertIsNotNone(mcp_schema)
        assert mcp_schema is not None
        self.assertIn("[MCP:database]", mcp_schema["function"]["description"])

        # Execute call via router
        res = router.call(mcp_tool_name, {})
        self.assertTrue(res.get("ok"))
        out_val = str(res.get("output", ""))
        self.assertIn("db_rows_42", out_val)

        registry.close_all()


if __name__ == "__main__":
    unittest.main()
