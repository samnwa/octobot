import sys
import click
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from .agent import Agent
from .config import DEFAULT_MODEL

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
    console.print(OCTOBOT_TOP, style="bold blue")
    console.print(OCTOBOT_BOT, style="white")
    console.print()
    info = Text()
    info.append("  Model: ", style="dim")
    info.append(model, style="bold cyan")
    info.append("  |  ", style="dim")
    info.append("v0.1.0", style="dim")
    console.print(info)
    console.print("[dim]  Commands: /reset /model /tokens /help /quit[/dim]\n")


def print_help():
    help_text = """
[bold cyan]Available Commands:[/bold cyan]

  [cyan]/reset[/cyan]           Clear conversation history
  [cyan]/model[/cyan] [name]    Show or switch the current model
  [cyan]/tokens[/cyan]          Show token usage for this session
  [cyan]/help[/cyan]            Show this help message
  [cyan]/quit[/cyan]            Exit octobot

[bold cyan]Tips:[/bold cyan]

  Just type your request and press Enter.
  Octobot can read, write, edit, and search files,
  and run shell commands on your behalf.
"""
    console.print(help_text)


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
            elif cmd == "/help":
                print_help()
                continue
            else:
                console.print(f"[yellow]Unknown command: {cmd}[/yellow]\n")
                continue

        console.print()
        agent.chat(user_input)
        console.print()
