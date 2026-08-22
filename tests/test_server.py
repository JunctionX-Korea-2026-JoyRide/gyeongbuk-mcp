"""Tests for the MCP server entry point."""

import asyncio

from fastmcp import FastMCP

from server import mcp


def test_server_is_fastmcp_instance() -> None:
    assert isinstance(mcp, FastMCP)


def test_server_registers_accessibility_tools() -> None:
    tools = asyncio.run(mcp.list_tools())

    assert {tool.name for tool in tools} == {
        "search_nearby_hospitals",
        "search_nearby_bus_stops",
        "search_nearby_markets",
        "recommend_car_free_neighborhoods",
        "get_age_population_ratio",
        "get_safety_grade",
    }
