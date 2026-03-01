# SynthChat

A Slack-like multi-agent workspace where specialized AI agents collaborate on your tasks. Send a message, and a team of agents coordinates to research, code, review, schedule, and summarize -- all in real time.

## Getting Started

SynthChat runs automatically as part of Octobot. No extra setup needed.

| Command | What it does |
|---------|-------------|
| `python main.py` | Octobot + SynthChat at `http://localhost:5000/synthchat/` |
| `python main-chat.py` | SynthChat standalone at `http://localhost:3000` |
| `python desktop.py` | Native desktop window via pywebview |

All modes use the same API key and configuration as Octobot.

### Desktop App

`python desktop.py` opens SynthChat in a native OS window using [pywebview](https://pywebview.flowrl.com/). It starts the server in the background, opens the app, and shuts everything down when you close the window. pywebview is auto-installed on first run.

### PWA Install

Visit SynthChat in Chrome or Edge and click "Install" in the address bar. This gives you a standalone window, taskbar icon, and offline-capable app experience -- no `desktop.py` or pywebview needed.

## How It Works

You send a message in a channel. **Otto** (the orchestrator) reads it, decides which agents to involve, and delegates via @mentions. Each agent works with its own tools, then passes results along. **Recap** wraps up with a summary when the task is done.

```
You: "Research the best Python web frameworks and create a comparison chart"

Otto: "@Scout, find the top Python web frameworks. @Dev, stand by to create the chart."
Scout: [searches web, fetches articles] "Here are the top 5 frameworks with pros/cons..."
Dev: [creates HTML document] "Built a comparison chart. @Sage, review?"
Sage: "Clean layout. Consider adding performance benchmarks."
Dev: [updates chart] "Added benchmarks. @Recap, wrap it up."
Recap: "Task complete. Created comparison chart with 5 frameworks..." [attaches PDF summary]
```

## Built-in Agents

| Agent | Role | Tools | What They Do |
|-------|------|-------|-------------|
| **Otto** 🐙 | Orchestrator | None | Routes tasks, delegates to specialists, coordinates the team |
| **Dev** ⚡ | Coder | `read_file`, `write_file`, `edit_file`, `run_command`, `list_files`, `search_files`, `tree`, `file_info`, `apply_patch`, `create_document` | Writes and edits code, runs commands, creates files |
| **Scout** 🔍 | Researcher | `web_search`, `web_fetch`, `create_document` | Searches the web, gathers information, fetches URLs |
| **Sage** 🦉 | Reviewer | `read_file`, `search_files`, `list_files` | Reviews code for bugs, security issues, and improvements |
| **Scheduler** 📅 | Scheduler | `schedule_task`, `list_schedules`, `cancel_schedule` | Creates recurring tasks, manages reminders and schedules |
| **Recap** 📋 | Summary | `create_document` | Summarizes completed work, generates downloadable reports |

Otto and Recap are **core agents** -- they're always present in every channel. The others are optional and can be toggled per channel.

## Channels

Channels let you organize work into separate contexts, each with its own conversation history and agent roster.

- **#workspace** -- the default channel with all agents. Cannot be deleted.
- **Custom channels** -- click the **+** next to "Channels" to create one. Choose a name, description, and which agents to include.

Each channel maintains its own conversation history, saved to `~/.octobot/synthchat/history/<channel_id>.json`.

## Custom Agents

You can create your own agents with custom tools, personalities, and capabilities.

### Creating via the UI

1. Click the **+** next to "Agents" in the sidebar, or open the **Library** and click **+ Create Agent**
2. Fill in the form:
   - **Name** and **Role** -- how the agent identifies itself
   - **Avatar** -- any emoji
   - **Color** -- pick from swatches or enter a hex code
   - **Tools** -- check which tools the agent can use (grouped by category)
   - **Skills** -- select skills to load into the agent's context
   - **System Prompt** -- the instructions that define the agent's behavior
3. Click **Create Agent** -- it appears in the sidebar immediately

Custom agents can be edited, deleted, added to channels, and mentioned by Otto just like built-in agents.

### YAML Format

Under the hood, custom agents are stored as YAML files in `~/.octobot/agents/`:

```yaml
name: DataAnalyst
role: Data Analyst
avatar: "📊"
color: "#818cf8"
description: Analyzes datasets and creates visualizations
tools:
  - run_command
  - read_file
  - write_file
  - create_document
  - list_files
skills:
  - data-analysis
system: |
  You are DataAnalyst, a Data Analysis agent in SynthChat.
  You specialize in analyzing data and creating clear reports.

  RULES:
  1. Use run_command with python to execute data scripts.
  2. Use create_document to export results as CSV or PNG.
  3. Be precise with numbers.
```

### Available Tools

Tools you can assign to custom agents:

| Category | Tools |
|----------|-------|
| **File System** | `read_file`, `write_file`, `edit_file`, `list_files`, `search_files`, `tree`, `file_info`, `apply_patch` |
| **Execution** | `run_command` |
| **Web** | `web_search`, `web_fetch` |
| **Documents** | `create_document` |
| **Scheduling** | `schedule_task`, `list_schedules`, `cancel_schedule` |

## Agent Library

The Library is your central hub for managing agents. Open it by clicking the **Library** button at the bottom of the sidebar.

### My Agents

View all your agents -- built-in and custom. Custom agents can be edited, deleted, or published to the community catalog.

### Community Catalog

A collection of pre-made agents ready to install with one click. SynthChat ships with 5 community agents:

| Agent | Role | Description |
|-------|------|-------------|
| **DataAnalyst** 📊 | Data Analyst | Analyzes datasets, creates visualizations, runs statistical queries |
| **DevOps** 🔧 | DevOps Engineer | Manages infrastructure, CI/CD pipelines, Docker configs |
| **Writer** ✍️ | Content Writer | Creates blog posts, docs, marketing copy, technical writing |
| **QATester** 🧪 | QA Tester | Tests code for bugs, edge cases, writes test plans |
| **Designer** 🎨 | UI/UX Designer | Designs interfaces, creates mockups, reviews UX patterns |

Click **+ Add to Library** on any community agent to install it. It becomes a custom agent in your workspace -- you can add it to channels, edit it, or delete it.

### Publishing

Created a useful agent? Click **Publish** in the Library to add it to the community catalog. Other users of SynthChat can then install it with one click.

## Skills

Skills are reusable knowledge modules that get loaded into an agent's system prompt at runtime. They teach agents **how** to do specific things without creating separate agents.

- An **Agent** is a *who* -- a persona with tools and personality
- A **Skill** is a *how* -- domain knowledge and instructions

### Using Skills

Add a `skills` list to any agent (built-in or custom):

```yaml
skills:
  - react
  - testing
```

At runtime, the engine loads each skill's `SKILL.md` content and appends it to the agent's system prompt.

### Creating Skills

Create a directory in `~/.octobot/skills/` or `./skills/` with a `SKILL.md` file:

```
~/.octobot/skills/
  react/
    SKILL.md
  data-analysis/
    SKILL.md
```

Skill format (with optional frontmatter):

```markdown
---
name: React Development
description: Best practices for building React applications
---

## React Development Guidelines

When building React components:
1. Use functional components with hooks
2. Keep components small and focused
...
```

Skills appear in the **Skills** tab of the Library and in the agent creation form.

## Document Generation

Agents with the `create_document` tool can generate downloadable files in 4 formats:

| Format | Use Case | Technology |
|--------|----------|------------|
| **CSV** | Data tables, spreadsheets | Python csv module |
| **HTML** | Styled web pages, reports | Auto-generated layout |
| **PDF** | Formatted documents, summaries | fpdf2 |
| **PNG** | Info cards, visualizations | Pillow |

Documents appear as download cards attached to agent messages. Click to download. Document cards persist in conversation history -- they're still there when you reload.

Files are stored in `~/.octobot/synthchat/documents/` with unique IDs.

## Scheduler

The Scheduler agent manages time-based tasks with three tools:

- **schedule_task** -- create a new scheduled task (name, frequency, action, optional description)
- **list_schedules** -- view all active schedules in the current channel
- **cancel_schedule** -- remove a schedule by ID

Schedules appear in the sidebar under the "Schedules" section. Each channel has its own schedules.

Frequencies: `once`, `daily`, `weekly`, `monthly`, `hourly`.

Schedules are stored in `~/.octobot/schedules.json`.

## Architecture

```
synthchat/
  app.py              Flask Blueprint (mounted at /synthchat), API routes
  agents.py           6 built-in agent definitions
  agent_loader.py     Custom agent YAML loader, community catalog, install/publish
  engine.py           Multi-agent orchestration engine, tool execution, history
  channels.py         Channel management, per-channel agent rosters
  scheduler.py        Schedule store + scheduler tools
  documents.py        Document generation tool (CSV, HTML, PDF, PNG)
  history.py          Per-channel conversation persistence
  templates/          HTML template (synthchat.html)
  static/
    app.js            Frontend JS (SSE, agents, channels, library, scheduler)
    style.css         Dark theme, sidebar, modals, responsive layout
    manifest.json     PWA manifest (name, icons, theme)
    sw.js             Service worker (offline caching)
    icon-192.png      PWA icon (192x192)
    icon-512.png      PWA icon (512x512)

desktop.py            Native desktop launcher (pywebview)
community/
  agents/             Community agent YAML catalog (ships with 5 agents)
```

### Orchestration Flow

1. User sends a message in a channel
2. Engine saves the message to history and queues it
3. **Otto** receives the message + channel context, decides which agents to involve
4. Otto's response is parsed for @mentions
5. Each mentioned agent gets their turn with the conversation context
6. Agents can use tools (up to 4 tool turns each for efficiency)
7. Agents can @mention other agents, triggering their turns
8. **Recap** is called at the end to summarize (or when explicitly mentioned)
9. All messages stream to the frontend via Server-Sent Events (SSE)

### Data Storage

All data lives in `~/.octobot/`:

```
~/.octobot/
  agents/                    Custom agent YAML files
  skills/                    User skill directories (SKILL.md files)
  synthchat/
    history/<channel>.json   Conversation history per channel
    channels.json            Channel definitions and rosters
    documents/               Generated document files
  schedules.json             Scheduled tasks
```

## Demo

The **#workspace** channel has a **Watch Demo** button that plays through a mock conversation showing the full agent collaboration flow -- Otto delegating, Scout researching, Dev coding, Sage reviewing, Scheduler setting up a task, and Recap summarizing with a downloadable PDF.

## API Reference

All routes are prefixed with `/synthchat` (or root `/` in standalone mode).

| Method | Route | Description |
|--------|-------|-------------|
| `GET` | `/api/agents` | List all agents (built-in + custom) |
| `GET` | `/api/agents/<id>` | Get agent profile details |
| `POST` | `/api/agents` | Create a custom agent |
| `PUT` | `/api/agents/<id>` | Update a custom agent |
| `DELETE` | `/api/agents/<id>` | Delete a custom agent |
| `GET` | `/api/community/agents` | List community catalog |
| `POST` | `/api/agents/install` | Install a community agent |
| `POST` | `/api/agents/<id>/publish` | Publish agent to community |
| `GET` | `/api/channels` | List channels |
| `POST` | `/api/channels` | Create a channel |
| `DELETE` | `/api/channels/<id>` | Delete a channel |
| `GET` | `/api/channels/<id>/history` | Get channel conversation history |
| `DELETE` | `/api/channels/<id>/history` | Clear channel history |
| `GET` | `/api/schedules` | List schedules |
| `DELETE` | `/api/schedules/<id>` | Cancel a schedule |
| `GET` | `/api/tools` | List available tools |
| `GET` | `/api/skills` | List available skills |
| `POST` | `/chat` | Send a message (returns SSE stream) |
| `POST` | `/stop` | Stop current agent execution |
