from capabilities.mcp import mcp_client

class NaverWeb:        
    async def get_tools(self):
        tools = await mcp_client.get_tools(server_name="naver-web")
        return tools
