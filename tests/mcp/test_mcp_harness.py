"""
Test Model Context Protocol (MCP) Server and Tool Implementations
=================================================================
Validates protocol handshake, schema definitions, and execution for all 91 MCP tools.
"""

import os
import sys
import pytest

# Add IDE directory to path
ide_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "IDE"))
if ide_dir not in sys.path:
    sys.path.insert(0, ide_dir)

from test_mcp_full_harness import (
    find_default_cli_path,
    find_default_db_path,
    ModelFusionMcpClient,
    McpFullHarness,
    get_tool_payload_matrix
)


@pytest.fixture(scope="module")
def cli_path():
    path = find_default_cli_path()
    assert os.path.exists(path), f"CLI binary not found at {path}"
    return path


@pytest.fixture(scope="module")
def db_path():
    path = find_default_db_path()
    return path


@pytest.fixture(scope="module")
def mcp_client(cli_path, db_path):
    client = ModelFusionMcpClient(cli_path, db_path, timeout=15.0)
    client.start()
    yield client
    client.close()


def test_mcp_handshake(mcp_client):
    resp = mcp_client.send_request("initialize")
    assert "result" in resp, f"Initialize failed: {resp}"
    result = resp["result"]
    assert result.get("protocolVersion") == "2024-11-05"
    assert "capabilities" in result and "tools" in result["capabilities"]
    assert result.get("serverInfo", {}).get("name") == "ModelFusion MCP Server"


def test_mcp_tools_list_count_and_schema(mcp_client):
    resp = mcp_client.send_request("tools/list")
    assert "result" in resp, f"tools/list failed: {resp}"
    tools = resp["result"].get("tools", [])
    assert len(tools) == 91, f"Expected 91 tools, found {len(tools)}"
    
    for tool in tools:
        assert "name" in tool and len(tool["name"]) > 0
        assert "description" in tool and len(tool["description"]) > 0
        assert "inputSchema" in tool
        schema = tool["inputSchema"]
        assert schema.get("type") == "object"
        assert "properties" in schema


def test_mcp_invalid_method_error(mcp_client):
    resp = mcp_client.send_request("non_existent_method_xyz")
    assert "error" in resp
    assert resp["error"].get("code") == -32601


def test_mcp_full_harness_execution(cli_path, db_path):
    harness = McpFullHarness(cli_path, db_path, timeout=15.0, verbose=False)
    summary = harness.run_all()
    
    assert summary["total_registered_tools"] == 91
    assert summary["total_tested_tools"] == 91
    assert summary["passed"] == 91
    assert summary["failed"] == 0
    assert summary["pass_rate_pct"] == 100.0
