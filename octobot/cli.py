import sys
import click
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table

from .agent import Agent
from .config import DEFAULT_MODEL
from .tools import TOOL_DEFINITIONS
from .browser import close_browser
from .octopus import is_awake, set_awake, OCTOPUS_FULL

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
    console.print("[dim]  Commands: /tools /skills /reset /model /models /tokens /stats /octo /help /quit[/dim]\n")


def print_help():
    help_text = """
[bold cyan]Available Commands:[/bold cyan]

  [cyan]/tools[/cyan]           List all available tools
  [cyan]/skills[/cyan]          List loaded skills
  [cyan]/reset[/cyan]           Clear conversation history
  [cyan]/model[/cyan] [name]    Show or switch model (add --default to persist)
  [cyan]/models[/cyan]          List all available models from the API
  [cyan]/tokens[/cyan]          Show token usage for this session
  [cyan]/stats[/cyan]           Show router stats (latency, health, failover)
  [cyan]/history[/cyan]         List past conversations
  [cyan]/history[/cyan] <#>     Resume a past conversation
  [cyan]/octo[/cyan]            Toggle the swimming octopus animation
  [cyan]/help[/cyan]            Show this help message
  [cyan]/quit[/cyan]            Exit octobot

[bold cyan]Tips:[/bold cyan]

  Just type your request and press Enter.
  Octobot can read, write, edit, and search files,
  run shell commands, fetch web pages, search the web,
  automate browsers, and spawn subagents for subtasks.
  It remembers things across sessions via persistent memory.
  Dangerous operations require your approval before executing.
"""
    console.print(help_text)


def print_tools():
    table = Table(title="Available Tools", border_style="cyan", title_style="bold cyan")
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
    table = Table(title="Loaded Skills", border_style="cyan", title_style="bold cyan")
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
        close_browser()
        return

    while True:
        try:
            console.print("[bold cyan]>[/bold cyan] ", end="")
            user_input = input().strip()
        except (KeyboardInterrupt, EOFError):
            close_browser()
            console.print("\n[dim]Goodbye![/dim]")
            break

        if not user_input:
            continue

        if user_input.startswith("/"):
            cmd = user_input.lower().split()[0]
            if cmd in ("/quit", "/exit", "/q"):
                close_browser()
                console.print("[dim]Goodbye![/dim]")
                break
            elif cmd == "/reset":
                agent.reset()
                close_browser()
                console.print("[green]Conversation reset.[/green]\n")
                continue
            elif cmd == "/model":
                parts = user_input.split(maxsplit=1)
                if len(parts) > 1:
                    model_arg = parts[1].strip()
                    persist = False
                    if model_arg.endswith(" --default"):
                        model_arg = model_arg[:-10].strip()
                        persist = True
                    elif model_arg == "--default":
                        from octobot.config import load_config, save_config
                        config = load_config()
                        config["model"] = agent.model
                        save_config(config)
                        console.print(f"[green]Saved {agent.model} as default.[/green]\n")
                        continue
                    agent.model = model_arg
                    agent.reset()
                    if persist:
                        from octobot.config import load_config, save_config
                        config = load_config()
                        config["model"] = model_arg
                        save_config(config)
                        console.print(f"[green]Switched to model: {agent.model} (saved as default)[/green]\n")
                    else:
                        console.print(f"[green]Switched to model: {agent.model} (session only)[/green]\n")
                else:
                    console.print(f"[dim]Current model: {agent.model}[/dim]")
                    console.print(f"[dim]Use /model <name> to switch (session) or /model <name> --default to persist[/dim]\n")
                continue
            elif cmd == "/models":
                import httpx
                from octobot.config import get_api_key
                from rich.table import Table
                console.print("[dim]Fetching available models...[/dim]")
                try:
                    r = httpx.get(
                        "https://api.synthetic.new/openai/v1/models",
                        headers={"Authorization": f"Bearer {get_api_key()}"},
                        timeout=10,
                    )
                    data = r.json()
                    table = Table(title="Available Models", border_style="cyan", title_style="bold cyan")
                    table.add_column("Model ID", style="cyan")
                    table.add_column("Context", justify="right")
                    table.add_column("Provider")
                    table.add_column("Tools", justify="center")
                    for m in sorted(data.get("data", []), key=lambda x: x.get("id", "")):
                        mid = m.get("id", "")
                        ctx = f"{m.get('context_length', 0) // 1024}K"
                        prov = m.get("provider", "")
                        feats = m.get("supported_features", [])
                        tools = "[green]Yes[/green]" if "tools" in feats else "[red]No[/red]"
                        current = " *" if mid == agent.model else ""
                        table.add_row(mid + current, ctx, prov, tools)
                    console.print(table)
                except Exception as e:
                    console.print(f"[red]Error fetching models: {e}[/red]")
                console.print()
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
            elif cmd == "/octo":
                if is_awake():
                    set_awake(False)
                    console.print(OCTOPUS_FULL, style="dim")
                    console.print("[dim]Octobot is sleeping... zzz[/dim]\n")
                else:
                    set_awake(True)
                    console.print(OCTOPUS_FULL, style="bold cyan")
                    console.print("[bold cyan]Octobot is awake![/bold cyan]\n")
                continue
            elif cmd == "/stats":
                from octobot.router import get_model_stats, FALLBACK_ORDER, is_model_healthy
                from rich.table import Table
                stats = get_model_stats()
                table = Table(title="Router Stats", border_style="cyan", title_style="bold cyan")
                table.add_column("Model", style="cyan")
                table.add_column("Requests", justify="right")
                table.add_column("Avg Latency", justify="right")
                table.add_column("Avg In Tokens", justify="right")
                table.add_column("Avg Out Tokens", justify="right")
                table.add_column("Healthy", justify="center")
                for m in FALLBACK_ORDER:
                    s = stats.get(m, {})
                    healthy = "[green]Yes[/green]" if is_model_healthy(m) else "[red]No[/red]"
                    short = m.split("/")[-1] if "/" in m else m
                    primary = " *" if m == agent.model else ""
                    table.add_row(
                        short + primary,
                        str(s.get("requests", 0)),
                        f"{s.get('avg_latency', 0):.1f}s",
                        str(s.get("avg_input_tokens", 0)),
                        str(s.get("avg_output_tokens", 0)),
                        healthy,
                    )
                console.print(table)
                console.print()
                continue
            elif cmd == "/history":
                from octobot.history import list_sessions
                from rich.table import Table
                sessions = list_sessions()
                if not sessions:
                    console.print("[dim]No conversation history.[/dim]\n")
                    continue
                table = Table(title="Conversation History", border_style="cyan", title_style="bold cyan")
                table.add_column("#", style="dim", justify="right")
                table.add_column("Preview", style="white", max_width=50)
                table.add_column("Messages", justify="right")
                table.add_column("Tokens", justify="right")
                table.add_column("Model", style="dim")
                import time as _t
                for i, s in enumerate(sessions, 1):
                    age = _t.time() - s["updated_at"]
                    if age < 3600:
                        when = f"{int(age/60)}m ago"
                    elif age < 86400:
                        when = f"{int(age/3600)}h ago"
                    else:
                        when = f"{int(age/86400)}d ago"
                    current = " *" if s["session_id"] == agent.session_id else ""
                    short_model = s["model"].split("/")[-1] if "/" in s["model"] else s["model"]
                    table.add_row(
                        str(i) + current,
                        s["preview"],
                        str(s["message_count"]),
                        f"{s['input_tokens']:,}+{s['output_tokens']:,}",
                        f"{short_model} ({when})",
                    )
                console.print(table)
                console.print("[dim]Use /history <number> to resume a conversation[/dim]\n")
                continue
            elif cmd.startswith("/history") and len(user_input.split()) > 1:
                from octobot.history import list_sessions
                parts = user_input.split()
                try:
                    idx = int(parts[1]) - 1
                    sessions = list_sessions()
                    if 0 <= idx < len(sessions):
                        sid = sessions[idx]["session_id"]
                        if agent.load_history(sid):
                            console.print(f"[green]Resumed conversation ({len(agent.messages)} messages, {agent.total_input_tokens:,}+{agent.total_output_tokens:,} tokens)[/green]\n")
                        else:
                            console.print("[red]Failed to load session.[/red]\n")
                    else:
                        console.print("[red]Invalid session number.[/red]\n")
                except ValueError:
                    console.print("[red]Usage: /history <number>[/red]\n")
                continue
            elif cmd == "/help":
                print_help()
                continue
            else:
                console.print(f"[yellow]Unknown command: {cmd}[/yellow]\n")
                continue

        console.print()
        agent.chat(user_input)
        agent.save_history()
        console.print()
