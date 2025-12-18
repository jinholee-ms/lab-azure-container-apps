import asyncio
from uuid import uuid4

from rich.markup import escape
from rich.rule import Rule
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from agents.base import agent_manager
from agents.triage import TriageAgentGraph
from capabilities.mcp import get_mcp_client
from common import console, settings


async def _execute_agent_prompts_interactive_shell(agent_class, input_cb: callable):
    while True:
        console.print(f"Choose a prompt: {escape('[s]')}ystem, {escape('[u]')}ser, {escape('[q]')}uit")
        prompt = await input_cb() if asyncio.iscoroutinefunction(input_cb) else input_cb()
        if not prompt.strip():
            continue
        elif prompt.lower() == "q":
            break
        elif prompt.lower() == "s":
            role = "system"
            prompts = agent_class.profile.prompts.system
        elif prompt.lower() == "u":
            role = "user"
            prompts = agent_class.profile.prompts.user
        else:
            console.print("[red]❌ Invalid prompt type. Please try again.[/]")
            continue

        while True:
            table = Table(title=f"Select {role} prompt (or 'q' to quit)", show_lines=False)
            table.add_column("#", style="cyan", justify="right")
            table.add_column("Type", style="magenta")
            table.add_column("Filename", style="cyan")
            table.add_column("Selected", style="green")
            for idx, p in enumerate(prompts):
                table.add_row(str(idx + 1), p.type, p.filename, str(p.selected))
            console.print(table)

            number = await input_cb() if asyncio.iscoroutinefunction(input_cb) else input_cb()
            if not number.strip():
                continue
            elif number.lower() == "q":
                break
            elif not number.isdigit() or int(number) < 1 or int(number) > len(prompts):
                console.print("[red]❌ Invalid prompt number. Please try again.[/]")
                continue

            for p in prompts:
                p.selected = False
            var = prompts[int(number) - 1]
            var.selected = True
            console.print(f"[green]✅ {role} prompt '{var.filename}' has been selected.[/]")
            continue

async def _execute_agent_chat_interactive_shell(agent_class, input_cb: callable):
    agent = agent_class()
    await agent.initialize()
    while True:
        console.print("")
        console.print("Type '/quit' to exit the shell.")

        user_input = await input_cb() if asyncio.iscoroutinefunction(input_cb) else input_cb()
        if not user_input.strip():
            continue
        elif user_input.startswith("/quit"):
            break

        with console.status(f"[blue] {agent.profile.name} is processing...[/]"):
            start_time = console.get_datetime()
            response = await agent.run(
                agent.generate_user_prompt(question=user_input),
            )
            answer = agent.extract_answer(response)
            elapsed_time = console.get_datetime() - start_time
        console.print(f"[yellow]🤖 Assistant({elapsed_time.total_seconds():.2f}s)> {answer}[/]")


def _control_mcp_properties():
    for key, value in get_mcp_client().connections.items():
        console.print(f"[cyan]{key}[/]: [yellow]{value}[/]")


async def _control_agent_properties(input_cb: callable):
    while True:
        console.print("\n\n")
        table = Table(title="Select agent (or 'q' to quit)", show_lines=False)
        table.add_column("#", style="cyan", justify="right")
        table.add_column("Name", style="magenta")
        table.add_column("Interactive", style="green")
        table.add_column("Activated", style="yellow")
        table.add_column("Deployment Name", style="blue")
        table.add_column("Enable Debugging", style="red")
        for idx, agent in enumerate(agent_manager.all_agents):
            table.add_row(
                str(idx + 1),
                agent.profile.name,
                str(agent.profile.interactive),
                str(agent.profile.activated),
                agent.profile.deployment_name,
                str(agent.profile.enable_debugging),
            )
        console.print(table)

        number = await input_cb() if asyncio.iscoroutinefunction(input_cb) else input_cb()
        if not number.strip():
            continue
        elif number.lower() == "q":
            break
        elif not number.isdigit() or int(number) < 1 or int(number) > len(agent_manager.all_agents):
            console.print("[red]❌ Invalid agent number. Please try again.[/]")
            continue

        agent_class = agent_manager.get_agent(int(number) - 1)
        console.print(
            "Choose a command: "
            "(c)chat, "
            "(a)activate, "
            "(d)deactivate, "
            "(p)prompts, "
            "(pd)deployment name, "
            "(de)enable debugging, "
            "(dd)disable debugging, "
            "(q)quit"
        )
        cmd = await input_cb() if asyncio.iscoroutinefunction(input_cb) else input_cb()
        if not cmd.strip():
            continue
        elif cmd.lower() == "q":
            continue
        elif cmd.lower() == "a":
            agent_class.profile.activated = True
            console.print(f"[green]✅ {agent_class.profile.name} has been activated.[/]")
        elif cmd.lower() == "d":
            agent_class.profile.activated = False
            console.print(f"[green]✅ {agent_class.profile.name} has been deactivated.[/]")
        elif cmd.lower() == "pd":
            available_deployments = settings.get_available_model_deployments()
            prompt = "Enter deployment_name: "
            for i in range(len(available_deployments)):
                prompt += f"{i + 1}. {available_deployments[i]}"
                if i != len(available_deployments) - 1:
                    prompt += ", "

            console.print(prompt)
            deployment_number = await input_cb() if asyncio.iscoroutinefunction(input_cb) else input_cb()
            if deployment_number.strip():
                deployment_name = available_deployments[int(deployment_number) - 1].strip()
                agent_class.profile.deployment_name = deployment_name
                console.print(f"[green]✅ deployment name has been updated to '{deployment_name}'[/]")
            else:
                console.print("[red]❌ deployment name cannot be empty.[/]")
        elif cmd.lower() == "de":
            agent_class.profile.enable_debugging = True
            console.print(
                f"[green]✅ enable_debugging has been set to '{agent_class.profile.enable_debugging}'[/]"
            )
        elif cmd.lower() == "dd":
            agent_class.profile.enable_debugging = False
            console.print(
                f"[green]✅ enable_debugging has been set to '{agent_class.profile.enable_debugging}'[/]"
            )
        elif cmd.lower() == "p":
            if not agent_class.profile.prompts:
                console.print("[red]❌ This agent does not have any prompts.[/]")
                continue

            await _execute_agent_prompts_interactive_shell(agent_class, input_cb)
            continue
        elif cmd.lower() == "c":
            if not agent_class.profile.interactive:
                console.print("[red]❌ This agent cannot be interactive.[/]")
                continue

            await _execute_agent_chat_interactive_shell(agent_class, input_cb)
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