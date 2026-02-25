# Changelog

All notable changes to Octobot will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.1.0] - 2025-02-25

### Added
- 25 built-in tools: file operations, shell, web search/fetch, browser automation, memory, subagents, code execution sandbox
- Smart model router with automatic failover across 4 models (Kimi-K2.5 → Qwen3.5 → MiniMax-M2.5 → GLM-4.7)
- Health monitoring with exponential backoff and persistent stats
- Web UI with dark terminal-style design, markdown rendering, and mobile responsiveness
- Terminal CLI with Rich formatting, syntax highlighting, and slash commands
- File browser sidebar with syntax-highlighted viewer and HTML preview mode
- Command menu with fuzzy autocomplete
- Model selector dropdown with 16 available models
- Real-time status indicator showing thinking, tool calls, and progress
- First-run setup screen for API key configuration
- Playwright-powered browser automation with accessibility snapshots and ref-based targeting
- Vision support for visual page analysis
- Subagent system for delegating subtasks to independent child agents
- Approval workflows for dangerous operations (rm -rf, sudo, sensitive file writes)
- Persistent memory across sessions (~/.octobot/memory/MEMORY.md)
- Extensible skills system (compatible with OpenClaw/PicoClaw format)
- Custom identity via AGENT.md and IDENTITY.md
- Loop detection for repetitive tool-call patterns
- Deferred tool loading to save tokens (12 always-loaded, 13 on-demand)
- Code execution sandbox with AST-based security validation
- Smart web extraction via trafilatura
- Prompt injection defense with content tagging and pattern scanning
- Token tracking per session
- Swimming octopus loading animation
- start.sh launcher with auto-dependency installation
