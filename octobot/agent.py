import json
from anthropic import Anthropic
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax

from .config import get_api_key, get_model, SYNTHETIC_BASE_URL, MAX_TOKENS, MAX_TURNS
from .tools import get_tool_definitions, execute_tool
from .identity import load_identity
from .skills import SkillsManager
from .memory import load_memory_context

console = Console()


class Agent:
    def __init__(self, model=None):
        self.api_key = get_api_key()
        self.model = get_model(model)
        self.client = Anthropic(
            api_key=self.api_key,
            base_url=SYNTHETIC_BASE_URL,
        )
        self.messages = []
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.skills_manager = SkillsManager()
        self._tool_call_history = []

    def _build_system_prompt(self):
        parts = [load_identity()]

        memory_ctx = load_memory_context()
        if memory_ctx:
            parts.append("\n\n## Memory\n\nThe following is your persistent memory from previous sessions:\n\n" + memory_ctx)

        skills_ctx = self.skills_manager.get_skills_context()
        if skills_ctx:
            parts.append("\n\n" + skills_ctx)

        return "\n".join(parts)

    def _build_tools(self):
        return get_tool_definitions()

    def _display_text(self, text):
        try:
            md = Markdown(text)
            console.print(md)
        except Exception:
            console.print(text)

    def _display_thinking(self, text):
        if text and text.strip():
            preview = text.strip()
            if len(preview) > 200:
                preview = preview[:200] + "..."
            console.print(f"[dim italic]Thinking: {preview}[/dim italic]")

    def _display_tool_use(self, block):
        name = block.name
        inp = block.input if hasattr(block, "input") else {}
        summary = json.dumps(inp, indent=2)
        if len(summary) > 500:
            summary = summary[:500] + "..."
        console.print(
            Panel(
                summary,
                title=f"[bold yellow]Tool: {name}[/bold yellow]",
                border_style="yellow",
            )
        )

    def _display_tool_result(self, name, result):
        result_str = json.dumps(result, indent=2)
        if len(result_str) > 1000:
            result_str = result_str[:1000] + "\n... [truncated]"
        console.print(
            Panel(
                result_str,
                title=f"[dim]Result: {name}[/dim]",
                border_style="dim",
            )
        )

    def _check_loop(self, tool_name, tool_input):
        call_key = f"{tool_name}:{json.dumps(tool_input, sort_keys=True)}"
        self._tool_call_history.append(call_key)

        recent = self._tool_call_history[-6:]
        if len(recent) >= 3:
            if recent[-1] == recent[-2] == recent[-3]:
                console.print(
                    "[bold red]Loop detected:[/bold red] Same tool call repeated 3 times. Stopping.",
                )
                return True

        no_text_calls = 0
        for entry in reversed(self._tool_call_history):
            if entry == "__TEXT__":
                break
            no_text_calls += 1
        if no_text_calls >= 8:
            console.print(
                "[bold red]Loop detected:[/bold red] 8+ tool calls with no text output. Stopping.",
            )
            return True

        return False

    def _process_response(self, response):
        self.total_input_tokens += response.usage.input_tokens
        self.total_output_tokens += response.usage.output_tokens

        tool_results = []
        loop_detected = False

        for block in response.content:
            block_type = getattr(block, "type", None)

            if block_type == "thinking":
                self._display_thinking(getattr(block, "thinking", ""))

            elif block_type == "text" and block.text.strip():
                self._display_text(block.text)
                self._tool_call_history.append("__TEXT__")

            elif block_type == "tool_use":
                if self._check_loop(block.name, block.input):
                    loop_detected = True
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps({"error": "Loop detected - please try a different approach or respond to the user."}),
                    })
                    continue

                self._display_tool_use(block)
                result = execute_tool(block.name, block.input)
                self._display_tool_result(block.name, result)
                result_str = json.dumps(result)
                if len(result_str) > 50000:
                    result_str = result_str[:50000] + "... [truncated]"
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result_str,
                })

        return tool_results, response.stop_reason, loop_detected

    def chat(self, user_message):
        self.messages.append({"role": "user", "content": user_message})
        self._tool_call_history = []

        for turn in range(MAX_TURNS):
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=MAX_TOKENS,
                    system=self._build_system_prompt(),
                    tools=self._build_tools(),
                    messages=self.messages,
                )
            except Exception as e:
                console.print(f"[bold red]API Error:[/bold red] {e}")
                return

            self.messages.append({"role": "assistant", "content": response.content})

            tool_results, stop_reason, loop_detected = self._process_response(response)

            if stop_reason == "end_turn" or not tool_results:
                break

            if loop_detected:
                self.messages.append({"role": "user", "content": tool_results})
                continue

            self.messages.append({"role": "user", "content": tool_results})

        self._display_token_usage()

    def _display_token_usage(self):
        console.print(
            f"\n[dim]Tokens: {self.total_input_tokens:,} in / "
            f"{self.total_output_tokens:,} out[/dim]",
            justify="right",
        )

    def reset(self):
        self.messages = []
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self._tool_call_history = []
