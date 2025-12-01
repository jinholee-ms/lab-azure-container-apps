from capabilities.mcp import mcp_client


class GooglePlaces:
    async def get_tools(self):
        tools = await mcp_client.get_tools(server_name="google-places")
        return tools
