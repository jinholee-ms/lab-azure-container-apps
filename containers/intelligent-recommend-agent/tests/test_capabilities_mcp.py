import os
import types
import pytest
from typing import Any

from capabilities import mcp


def test_handle_mcp_servers():
    mcp.start_mcp_servers()
    assert len(mcp._mcp_processes) == len(mcp._mcp_cmds)
    assert all(proc.poll() is None for proc in mcp._mcp_processes.values())

    mcp.cleanup_mcp_servers()


@pytest.mark.asyncio
async def test_init_mcp_module():
    await mcp.init_module()
    assert isinstance(mcp.mcp_client, mcp.MultiServerMCPClient)
    assert mcp.mcp_client.connections is not None
