import sys
import click
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table

from .agent import Agent
from .config import DEFAULT_MODEL
from .tools import TOOL_DEFINITIONS

console = Console()

OCTOBOT_TOP = """ \u2584\u2588\u2588\u2588\u2588\u2588\u2588\u2584   \u2584\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588     \u2588\u2588\u2588      \u2584\u2588\u2588\u2588\u2588\u2588\u2588\u2584
\u2588\u2588\u2588    \u2588\u2588\u2588 \u2588\u2588\u2588    \u2588\u2588\u2588 \u2580\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2584 \u2588\u2588\u2588    \u2588\u2588\u2588
\u2588\u2588\u2588    \u2588\u2588\u2588 \u2588\u2588\u2588    \u2588\u2580     \u2580\u2588\u2588\u2588\u2580\u2580\u2588\u2588 \u2588\u2588\u2588    \u2588\u2588\u2588
\u2588\u2588\u2588    \u2588\u2588\u2588 \u2588\u2588\u2588            \u2588\u2588\u2588   \u2580 \u2588\u2588\u2588    \u2588\u2588\u2588
\u2588\u2588\u2588    \u2588\u2588\u2588 \u2588\u2588\u2588            \u2588\u2588\u2588     \u2588\u2588\u2588    \u2588\u2588\u2588
\u2588\u2588\u2588    \u2588\u2588\u2588 \u2588\u2588\u2588    \u2588\u2584      \u2588\u2588\u2588     \u2588\u2588\u2588    \u2588\u2588\u2588
\u2588\u2588\u2588    \u2588\u2588\u2588 \u2588\u2588\u2588    \u2588\u2588\u2588     \u2588\u2588\u2588     \u2588\u2588\u2588    \u2588\u2588\u2588
 \u2580\u2588\u2588\u2588\u2588\u2588\u2588\u2580  \u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2580     \u2584\u2588\u2588\u2588\u2588\u2580    \u2580\u2588\u2588\u2588\u2588\u2588\u2588\u2580"""

OCTOBOT_BOT = """\u2580\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2584   \u2584\u2588\u2588\u2588\u2588\u2588\u2588\u2584      \u2588\u2588\u2588
  \u2588\u2588\u2588    \u2588\u2588\u2588 \u2588\u2588\u2588    \u2588\u2588\u2588 \u2580\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2584
  \u2588\u2588\u2588    \u2588\u2588\u2588 \u2588\u2588\u2588    \u2588\u2588\u2588    \u2580\u2588\u2588\u2588\u2580\u2580\u2588\u2588
 \u2584\u2588\u2588\u2588\u2584\u2584\u2584\u2588\u2588\u2580  \u2588\u2588\u2588    \u2588\u2588\u2588     \u2588\u2588\u2588   \u2580
\u2580\u2580\u2588\u2588\u2588\u2580\u2580\u2580\u2588\u2588\u2584  \u2588\u2588\u2588    \u2588\u2588\u2588     \u2588\u2588\u2588
  \u2588\u2588\u2588    \u2588\u2588\u2584 \u2588\u2588\u2588    \u2588\u2588\u2588     \u2588\u2588\u2588
  \u2588\u2588\u2588    \u2588\u2588\u2588 \u2588\u2588\u2588    \u2588\u2588\u2588     \u2588\u2588\u2588
\u2584\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2580   \u2580\u2588\u2588\u2588\u2588\u2588\u2588\u2580     \u2584\u2588\u2588\u2588\u2588\u2580"""


def print_banner(model):
    console.print(OCTOBOT_TOP, style="bold cyan")
    console.print(OCTOBOT_BOT, style="white")
    console.print()
    info = Text()
    info.append("  Model: ", style="dim")
    info.append(model, style="bold cyan")
    info.append("  |  ", style="dim")
    info.append("v0.1.0", style="dim")
    info.append("  |  ", style="dim")
    info.append(f"{len(TOOL_DEFINITIONS)} tools", style="dim cyan")
    console.print(info)
    console.print("[dim]  Commands: /tools /skills /reset /model /tokens /help /quit[/dim]\n")


def print_help():
    help_text = """
[bold cyan]Available Commands:[/bold cyan]

  [cyan]/tools[/cyan]           List all available tools
  [cyan]/skills[/cyan]          List loaded skills
  [cyan]/reset[/cyan]           Clear conversation history
  [cyan]/model[/cyan] [name]    Show or switch the current model
  [cyan]/tokens[/cyan]          Show token usage for this session
  [cyan]/help[/cyan]            Show this help message
  [cyan]/quit[/cyan]            Exit octobot

[bold cyan]Tips:[/bold cyan]

  Just type your request and press Enter.
  Octobot can read, write, edit, and search files,
  run shell commands, fetch web pages, and search the web.
  It remembers things across sessions via persistent memory.
"""
    console.print(help_text)


def print_tools():
    table = Table(title="Available Tools", border_style="cyan")
    table.add_column("Tool", style="bold cyan", no_wrap=True)
    table.add_column("Description", style="white")
    for t in TOOL_DEFINITIONS:
        desc = t["description"]
        if len(desc) > 80:
            desc = desc[:77] + "..."
        table.add_row(t["name"], desc)
    console.print(table)
    console.print()


def print_skills(agent):
    skills = agent.skills_manager.get_skills_metadata()
    if not skills:
        console.print("[dim]No skills loaded. Add skills to ~/.octobot/skills/ or ./skills/[/dim]\n")
        return
    table = Table(title="Loaded Skills", border_style="cyan")
    table.add_column("Skill", style="bold cyan", no_wrap=True)
    table.add_column("Description", style="white")
    for s in skills:
        table.add_row(s["name"], s.get("description", ""))
    console.print(table)
    console.print()


@click.command()
@click.option("--model", "-m", default=None, help=f"Model to use (default: {DEFAULT_MODEL})")
@click.option("--single", "-s", default=None, help="Run a single prompt and exit")
def main(model, single):
    try:
        agent = Agent(model=model)
    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)

    console.print()
    print_banner(agent.model)

    if single:
        agent.chat(single)
        return

    while True:
        try:
            console.print("[bold cyan]>[/bold cyan] ", end="")
            user_input = input().strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Goodbye![/dim]")
            break

        if not user_input:
            continue

        if user_input.startswith("/"):
            cmd = user_input.lower().split()[0]
            if cmd in ("/quit", "/exit", "/q"):
                console.print("[dim]Goodbye![/dim]")
                break
            elif cmd == "/reset":
                agent.reset()
                console.print("[green]Conversation reset.[/green]\n")
                continue
            elif cmd == "/model":
                parts = user_input.split(maxsplit=1)
                if len(parts) > 1:
                    agent.model = parts[1]
                    agent.reset()
                    console.print(f"[green]Switched to model: {agent.model}[/green]\n")
                else:
                    console.print(f"[dim]Current model: {agent.model}[/dim]\n")
                continue
            elif cmd == "/tokens":
                console.print(
                    f"[dim]Session tokens: {agent.total_input_tokens:,} in / "
                    f"{agent.total_output_tokens:,} out[/dim]\n"
                )
                continue
            elif cmd == "/tools":
                print_tools()
                continue
            elif cmd == "/skills":
                print_skills(agent)
                continue
            elif cmd == "/help":
                print_help()
                continue
            else:
                console.print(f"[yellow]Unknown command: {cmd}[/yellow]\n")
                continue

        console.print()
        agent.chat(user_input)
        console.print()
