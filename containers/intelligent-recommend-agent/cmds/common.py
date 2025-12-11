import asyncio
from uuid import uuid4

from rich.rule import Rule
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from agents.base import agent_manager
from agents.triage import TriageAgentGraph
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
        table.add_column("Chat", style="green")
        for idx, agent in enumerate(agent_manager.all_agents):
            table.add_row(
                str(idx + 1), agent.profile.name, str(agent.profile.chat_in_settings)
            )
        console.print(table)

        number = await input_cb() if asyncio.iscoroutinefunction(input_cb) else input_cb()
        if number.lower() == "q":
            break

        if not number.isdigit() or int(number) < 1 or int(number) > len(agent_manager.all_agents):
            console.print("[red]❌ Invalid agent number. Please try again.[/]")
            continue
        if agent := agent_manager.get_agent(int(number) - 1):
            if not agent.profile.chat_in_settings:
                console.print("[red]❌ This agent cannot chat in settings.[/]")
            if agent_class := agent_manager.get_agent(int(number) - 1):
                agent = agent_class()
                await agent.initialize()

                while True:
                    console.print("")
                    console.print("Type '/quit' to exit the shell.")

                    user_input = await input_cb() if asyncio.iscoroutinefunction(input_cb) else input_cb()
                    if not user_input.strip():
                        continue
                    elif user_input.startswith("/quit"):
                        console.print("👋 ByeBye ~")
                        break

                    with console.status(f"[blue] {agent.profile.name} is processing...[/]"):
                        response = await agent.run(
                            agent.generate_user_prompt(question=user_input),
                        )
                        answer = agent.extract_answer(response)
                    console.print(f"[yellow]🤖 Assistant> {answer}[/]")
            continue


async def execute_interactive_shell(input_cb: callable):
    triage_agent = TriageAgentGraph()
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
            console.print("Type '/reset' to reset the conversation.\n")
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
            elif user_input.startswith("/reset"):
                triage_agent = TriageAgentGraph()
                console.print("[green]✅ Conversation has been reset.[/]")
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
                answer = await triage_agent.run(user_input)

                console.print(Panel(f"[yellow]🤖 Assistant> {answer}[/]"))
                console.print(Rule(style="bold yellow", characters="-"))
        except (EOFError, KeyboardInterrupt):
            break