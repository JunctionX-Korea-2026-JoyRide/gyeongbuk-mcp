"""FastMCP server entry point."""

from fastmcp import FastMCP

mcp = FastMCP(name="Gyeongbuk MCP")


if __name__ == "__main__":
    mcp.run()
