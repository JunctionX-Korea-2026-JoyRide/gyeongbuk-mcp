"""FastMCP server entry point."""

from fastmcp import FastMCP

from tools import (
    get_age_population_ratio,
    get_safety_grade,
    recommend_car_free_neighborhoods,
    search_nearby_bus_stops,
    search_nearby_hospitals,
    search_nearby_markets,
    search_nearby_stores,
)

mcp = FastMCP(name="Gyeongbuk MCP")
mcp.tool(search_nearby_hospitals)
mcp.tool(search_nearby_bus_stops)
mcp.tool(search_nearby_markets)
mcp.tool(search_nearby_stores)
mcp.tool(recommend_car_free_neighborhoods)
mcp.tool(get_age_population_ratio)
mcp.tool(get_safety_grade)


if __name__ == "__main__":
    mcp.run()
