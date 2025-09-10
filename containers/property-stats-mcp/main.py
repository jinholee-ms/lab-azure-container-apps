# server.py
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("PropertyStatsMCP", host="0.0.0.0")

@mcp.tool()
def price_index(region: str) -> float:
    """지역별 매매지수(예시)"""
    return {"Seoul": 102.3, "Busan": 98.4}.get(region, 100.0)

if __name__ == "__main__":
    mcp.run(transport="streamable-http")  # 기본 /mcp 엔드포인트