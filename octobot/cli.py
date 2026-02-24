import sys
import click
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from .agent import Agent
from .config import DEFAULT_MODEL

console = Console()


def print_banner():
    banner = Text()
    banner.append("  octobot ", style="bold cyan")
    banner.append("v0.1.0", style="dim")
    banner.append(" | ", style="dim")
    banner.append("Efficient AI Tool-Calling Agent", style="italic")
    console.print(Panel(banner, border_style="cyan"))
    console.print("[dim]Commands: /reset /model /tokens /quit[/dim]\n")


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
    print_banner()
    console.print(f"[dim]Model: {agent.model}[/dim]\n")

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
            else:
                console.print(f"[yellow]Unknown command: {cmd}[/yellow]\n")
                continue

        console.print()
        agent.chat(user_input)
        console.print()
