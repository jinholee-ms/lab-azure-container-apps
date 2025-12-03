from capabilities.mcp import init_module as init_mcp_module
from common import console, init_ms_foundry_monitoring_module
from cmds.common import execute_interactive_shell

async def main():
    try:
        await init_ms_foundry_monitoring_module()
        await init_mcp_module()
        await execute_interactive_shell(input_cb=lambda: console.input("[blue]😊 User> "))
    except KeyboardInterrupt:
        console.print("\n[red]Interrupted by user. Exiting...[/]")
