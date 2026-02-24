# Octobot

Locally-runnable, super-efficient AI tool-calling agent using the Synthetic API (Anthropic-compatible).

## Architecture

```
main.py                  - Entry point
octobot/
  __init__.py            - Package init
  config.py              - Configuration (API key, model, base URL, constants)
  tools.py               - 25 tool definitions, deferred loading, path restrictions, execution handlers
  agent.py               - Core agent runtime with loop detection, approval, content tagging, deferred tool summary
  cli.py                 - Interactive CLI with Rich formatting, /tools, /skills commands
  memory.py              - Persistent memory loading from ~/.octobot/memory/MEMORY.md
  skills.py              - Skills system (SKILL.md loader from ~/.octobot/skills/ and ./skills/)
  identity.py            - Identity/personality system (AGENT.md, IDENTITY.md)
  approval.py            - Approval workflows for dangerous operations (rm -rf, sudo, dotfiles)
  subagent.py            - Subagent spawning with isolated conversations (15 turn limit)
  browser.py             - Playwright browser automation with NixOS library auto-discovery
  sandbox.py             - AST-validated Python sandbox for multi-tool chaining
  octopus.py             - Swimming octopus animation (loading indicator during API calls)
README.md                - Comprehensive project documentation
```

## Key Features

- **25 Tools**: file ops (read/write/edit/list/search/tree/file_info/apply_patch), shell (run_command), web (web_fetch with trafilatura, web_search), memory (save/read), subagent (spawn_subagent), browser (navigate/screenshot/click/type/get_text/snapshot/click_ref/type_ref/vision), meta-tools (tool_search, code_execution)
- **Efficiency Optimizations** (inspired by Anthropic's advanced tool calling):
  - Deferred tool loading: 13 tools deferred, 12 always loaded; saves tokens per request
  - Code execution sandbox: chain multiple tool calls in one round trip via Python code
  - Smart web extraction: trafilatura extracts main content, stripping boilerplate
  - Input examples: embedded in tool descriptions for better model understanding
- **Security Layers**:
  - AST-based code sandbox (blocks imports, dunder access, dangerous builtins at syntax tree level)
  - Path restrictions (writes confined to project dir + /tmp, system paths blocked)
  - Approval workflows (dangerous commands and sensitive file writes require user confirmation)
  - Prompt injection defense (untrusted content tagged with delimiters, injection patterns detected)
  - System prompt instructs model to never follow instructions in <untrusted_content> tags
- **Browser Automation**: Playwright headless Chromium, accessibility snapshots with numbered refs, ref-based clicking/typing, vision (base64 screenshots sent as image blocks)
- **Subagents**: Independent child agents for subtask delegation, 15 turn limit, no recursive spawning
- **Persistent Memory**: ~/.octobot/memory/MEMORY.md loaded into system prompt
- **Skills System**: SKILL.md-based, compatible with OpenClaw/PicoClaw format
- **Custom Identity**: ~/.octobot/AGENT.md and IDENTITY.md for personality
- **Loop Detection**: Stops repetitive tool-call patterns automatically
- **Rich CLI**: Cyan-themed ASCII banner, markdown rendering, token tracking

## Configuration

- **API**: Synthetic API at `https://api.synthetic.new/anthropic`
- **Model**: `hf:zai-org/GLM-4.7` (default, supports tool use + thinking)
- **Secret**: `SYNTHETIC_API_KEY` (stored as Replit secret)

## Dependencies

- anthropic (SDK for API calls)
- rich (terminal formatting)
- click (CLI framework)
- httpx (HTTP client for web_fetch/web_search)
- playwright (browser automation)
- trafilatura (smart web content extraction)

## System Dependencies (NixOS)

- nss, nspr, mesa, at-spi2-atk, cups, libdrm, alsa-lib, pango, cairo, gtk3, libxkbcommon, dbus, glib, expat
- xorg: libX11, libXcomposite, libXdamage, libXext, libXfixes, libXrandr, libxcb

## Running

```bash
python main.py                          # Interactive mode
python main.py -s "your prompt"         # Single prompt mode
python main.py -m "hf:model/name"       # Use a different model
```
