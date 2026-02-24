# Octobot

Locally-runnable, super-efficient AI tool-calling agent using the Synthetic API (Anthropic-compatible).

## Architecture

```
main.py                  - Entry point
octobot/
  __init__.py            - Package init
  config.py              - Configuration (API key, model, base URL, constants)
  tools.py               - 19 tool definitions and execution handlers
  agent.py               - Core agent runtime with loop detection, approval, system prompt assembly
  cli.py                 - Interactive CLI with Rich formatting, /tools, /skills commands
  memory.py              - Persistent memory loading from ~/.octobot/memory/MEMORY.md
  skills.py              - Skills system (SKILL.md loader from ~/.octobot/skills/ and ./skills/)
  identity.py            - Identity/personality system (AGENT.md, IDENTITY.md)
  approval.py            - Approval workflows for dangerous operations (rm -rf, sudo, dotfiles)
  subagent.py            - Subagent spawning with isolated conversations (15 turn limit)
  browser.py             - Playwright browser automation with NixOS library auto-discovery
README.md                - Comprehensive project documentation
```

## Key Features

- **19 Tools**: read_file, write_file, edit_file, list_files, search_files, run_command, web_fetch, web_search, apply_patch, tree, file_info, memory_save, memory_read, spawn_subagent, browser_navigate, browser_screenshot, browser_click, browser_type, browser_get_text
- **Browser Automation**: Playwright headless Chromium, lazy-launch, auto library discovery on NixOS
- **Subagents**: Independent child agents for subtask delegation, 15 turn limit, no recursive spawning
- **Approval Workflows**: Confirms dangerous commands (rm -rf, sudo, chmod 777) and sensitive file writes (.bashrc, .env, .ssh/)
- **Persistent Memory**: ~/.octobot/memory/MEMORY.md loaded into system prompt
- **Skills System**: SKILL.md-based, compatible with OpenClaw/PicoClaw format
- **Custom Identity**: ~/.octobot/AGENT.md and IDENTITY.md for personality
- **Loop Detection**: Stops repetitive tool-call patterns automatically
- **Rich CLI**: Cyan-themed ASCII banner, markdown rendering, token tracking
- **Slash Commands**: /tools, /skills, /reset, /model, /tokens, /help, /quit

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

## System Dependencies (NixOS)

- nss, nspr, mesa, at-spi2-atk, cups, libdrm, alsa-lib, pango, cairo, gtk3, libxkbcommon, dbus, glib, expat
- xorg: libX11, libXcomposite, libXdamage, libXext, libXfixes, libXrandr, libxcb

## Running

```bash
python main.py                          # Interactive mode
python main.py -s "your prompt"         # Single prompt mode
python main.py -m "hf:model/name"       # Use a different model
```
