import asyncio
from uuid import uuid4

from rich.rule import Rule
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from agents.base import agent_manager
from agents.orchestrator import Orchestrator
from capabilities.mcp import get_mcp_client
from common import console, settings


def _control_mcp_properties():
    for key, value in get_mcp_client().connections.items():
        console.print(f"[cyan]{key}[/]: [yellow]{value}[/]")


async def _control_agent_properties(input_cb: callable):
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

        number = await input_cb() if asyncio.iscoroutinefunction(input_cb) else input_cb()
        if number.lower() == "q":
            break

        if not number.isdigit() or int(number) < 1 or int(number) > len(agent_manager.all_agents):
            console.print("[red]❌ Invalid agent number. Please try again.[/]")
            continue
        if agent_manager.get_agent(int(number) - 1).locked:
            console.print("[red]❌ This agent is locked and cannot be modified.[/]")
            continue

        property = Prompt.ask(
            "\nEnter property to toggle: (a)ctivated/(d)eactivated/(c)hat", choices=["a", "d", "c"]
        )
        if property.lower() == "a":
            agent_manager.activate_agent(int(number) - 1)
        elif property.lower() == "d":
            agent_manager.deactivate_agent(int(number) - 1)
        elif property.lower() == "c":
            user_input = await input_cb() if asyncio.iscoroutinefunction(input_cb) else input_cb()
            console.print(Rule(style="bold blue", characters="-"))
            console.print("")
            console.print(
                Rule(
                    "Assistant Utterance",
                    align="center",
                    style="bold yellow",
                    characters="-",
                )
            )

            if agent := agent_manager.get_agent(int(number) - 1):
                with console.status(
                    f"[blue] {agent.name} is processing...[/]", spinner="aesthetic"
                ):
                    response = await agent.run_langchain_agent(
                        agent.generate_system_prompt(),
                        agent.generate_user_prompt(question=user_input),
                        session_id=uuid4().hex,
                    )
                    answer = agent.extract_langchain_agent_answer(response)

            console.print(Panel(f"[yellow]🤖 Assistant> {answer}[/]"))
            console.print(Rule(style="bold yellow", characters="-"))


async def execute_interactive_shell(input_cb: callable):
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
            user_input = await input_cb() if asyncio.iscoroutinefunction(input_cb) else input_cb()
            console.print(Rule(style="bold blue", characters="-"))

            if not user_input.strip():
                continue
            elif user_input.startswith("/quit"):
                console.print("👋 ByeBye ~")
                break
            elif user_input.startswith("/agents"):
                await _control_agent_properties(input_cb=input_cb)
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
                answer = await orchestrator.run(user_input)

                console.print(Panel(f"[yellow]🤖 Assistant> {answer}[/]"))
                console.print(Rule(style="bold yellow", characters="-"))
        except (EOFError, KeyboardInterrupt):
            break