"""Tests for the MCP server entry point."""

from fastmcp import FastMCP

from server import mcp


def test_server_is_fastmcp_instance() -> None:
    assert isinstance(mcp, FastMCP)
