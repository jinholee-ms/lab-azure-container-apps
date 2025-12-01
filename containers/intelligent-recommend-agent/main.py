import asyncio

from rich.rule import Rule
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from agents.base import agent_manager
from agents.orchestrator import Orchestrator
from capabilities.mcp import get_mcp_client
from capabilities.mcp import init_module as init_mcp_module
from common import console, settings, init_ms_foundry_monitoring_module


def _control_mcp_properties():
    for key, value in get_mcp_client().connections.items():
        console.print(f"[cyan]{key}[/]: [yellow]{value}[/]")


def _control_agent_properties():
    while True:
        console.print("\n\n")
        table = Table(title="Select agent (or 'q' to quit)", show_lines=False)
        table.add_column("#", style="cyan", justify="right")
        table.add_column("Name", style="magenta")
        table.add_column("Locked", style="green")
        table.add_column("Activated", style="cyan")
        for idx, agent in enumerate(agent_manager.all_agents):
            table.add_row(
                str(idx + 1), agent.name, str(agent.locked), str(agent.activated)
            )
        console.print(table)

        number = Prompt.ask(
            "\nEnter number",
            choices=[str(i) for i in range(1, len(agent_manager.all_agents) + 1)]
            + ["q"],
        )
        if number.lower() == "q":
            break

        if agent_manager.get_agent(int(number) - 1).locked:
            console.print("[red]❌ This agent is locked and cannot be modified.[/]")
            continue

        property = Prompt.ask(
            "\nEnter property to toggle: (a)ctivated/(d)eactivated", choices=["a", "d"]
        )
        if property == "a":
            agent_manager.activate_agent(int(number) - 1)
        elif property == "d":
            agent_manager.deactivate_agent(int(number) - 1)


async def execute_interactive_shell():
    orchestrator = Orchestrator()
    while True:
        try:
            console.print(
                Rule(
                    " AI Agent Interactive Shell",
                    align="center",
                    style="bold green",
                    characters="=",
                )
            )
            console.print("[bold green]Welcome to the AI Agent Interactive Shell![/]")
            console.print("Type your messages below to interact with the AI agent.")
            console.print("Type '/quit' to exit the shell.")
            console.print("Type '/agents' to list available sub-agents.")
            console.print("Type '/mcp' to view MCP server properties.")
            console.print("Type '/settings' to view or change settings.")
            console.print("")
            console.print(
                Rule(
                    "User Utterance", align="center", style="bold blue", characters="-"
                )
            )
            user_input = console.input("[blue]😊 User> ")
            console.print(Rule(style="bold blue", characters="-"))

            if not user_input.strip():
                continue
            elif user_input.startswith("/quit"):
                console.print("👋 ByeBye ~")
                break
            elif user_input.startswith("/agents"):
                _control_agent_properties()
            elif user_input.startswith("/mcp"):
                _control_mcp_properties()
            elif user_input.startswith("/settings"):
                settings.show()
            else:
                console.print("")
                console.print(
                    Rule(
                        "Assistant Utterance",
                        align="center",
                        style="bold yellow",
                        characters="-",
                    )
                )
                with console.status("[yellow]Thinking...[/]", spinner="bouncingBar"):
                    answer = await orchestrator.run(user_input)

                console.print(Panel(f"[yellow]🤖 Assistant> {answer}[/]"))
                console.print(Rule(style="bold yellow", characters="-"))
        except (EOFError, KeyboardInterrupt):
            break


async def main():
    await init_ms_foundry_monitoring_module()
    await init_mcp_module()
    await execute_interactive_shell()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[red]Interrupted by user. Exiting...[/]")
