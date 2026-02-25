import json
from anthropic import Anthropic
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from .config import get_api_key, get_model, SYNTHETIC_BASE_URL, MAX_TOKENS, SUBAGENT_MAX_TURNS
from .tools import get_tool_definitions, execute_tool

console = Console()

SUBAGENT_SYSTEM = """You are a focused subagent working on a specific task. Complete the task using the tools available to you, then provide a clear summary of what you did and the results.

Be efficient: use the minimum number of tool calls needed. When done, respond with a final summary."""


def get_subagent_tools():
    return [t for t in get_tool_definitions() if t["name"] != "spawn_subagent"]


def run_subagent(task, context=None, model=None, max_turns=None):
    api_key = get_api_key()
    resolved_model = get_model(model)
    turns = max_turns or SUBAGENT_MAX_TURNS

    client = Anthropic(api_key=api_key, base_url=SYNTHETIC_BASE_URL)
    tools = get_subagent_tools()

    system_prompt = SUBAGENT_SYSTEM
    if context:
        system_prompt += f"\n\nAdditional context:\n{context}"

    messages = [{"role": "user", "content": f"Task: {task}"}]

    console.print(
        Panel(
            f"[bold]Task:[/bold] {task}",
            title="[bold dark_orange]Subagent Started[/bold dark_orange]",
            border_style="dark_orange",
        )
    )

    final_text = ""
    turns_used = 0

    for turn in range(turns):
        turns_used += 1
        try:
            response = client.messages.create(
                model=resolved_model,
                max_tokens=MAX_TOKENS,
                system=system_prompt,
                tools=tools,
                messages=messages,
            )
        except Exception as e:
            return {"status": "error", "error": str(e), "turns_used": turns_used}

        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for block in response.content:
            block_type = getattr(block, "type", None)

            if block_type == "text" and block.text.strip():
                final_text = block.text
                console.print(
                    Panel(
                        Markdown(block.text),
                        title="[dim dark_orange]Subagent[/dim dark_orange]",
                        border_style="dim dark_orange",
                    )
                )

            elif block_type == "tool_use":
                name = block.name
                inp = block.input
                summary = json.dumps(inp)
                if len(summary) > 200:
                    summary = summary[:200] + "..."
                console.print(f"  [dim dark_orange]Subagent tool:[/dim dark_orange] [yellow]{name}[/yellow] {summary}")

                result = execute_tool(name, inp)
                result_str = json.dumps(result)
                if len(result_str) > 50000:
                    result_str = result_str[:50000] + "... [truncated]"
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result_str,
                })

        if response.stop_reason == "end_turn" or not tool_results:
            break

        messages.append({"role": "user", "content": tool_results})

    console.print(
        Panel(
            f"Completed in {turns_used} turn(s)",
            title="[bold dark_orange]Subagent Finished[/bold dark_orange]",
            border_style="dark_orange",
        )
    )

    return {
        "status": "completed",
        "summary": final_text,
        "turns_used": turns_used,
    }
