import json
import queue
import threading

from flask import Flask, Blueprint, render_template, jsonify, request, Response, redirect, send_from_directory
from synthchat.agents import AGENTS, AGENT_ORDER, CORE_AGENTS, OPTIONAL_AGENTS, get_agent_order
from synthchat.agent_loader import (
    get_all_agents, save_custom_agent, delete_custom_agent,
    load_custom_agents, load_community_agents, install_community_agent,
    publish_agent_to_community, is_agent_installed, is_agent_published,
    VALID_TOOLS, list_available_skills,
)
from synthchat.channels import ChannelStore
from synthchat.history import load_history, clear_history
from synthchat.scheduler import ScheduleStore
from synthchat.documents import DOCUMENTS_DIR

bp = Blueprint("synthchat", __name__,
               template_folder="templates",
               static_folder="static",
               static_url_path="static")

_stop_event = threading.Event()


def _agent_msg(agent_id, content, tool_use=None, mentions=None, ts_offset=0, documents=None):
    a = AGENTS[agent_id]
    msg = {
        "id": f"msg-{agent_id}-{ts_offset}",
        "agent_id": agent_id,
        "agent_name": a["name"],
        "avatar": a["avatar"],
        "color": a["color"],
        "role": a["role"],
        "content": content,
        "tool_use": tool_use or [],
        "mentions": mentions or [],
        "is_user": False,
        "ts_offset": ts_offset,
    }
    if documents:
        msg["documents"] = documents
    return msg


def _user_msg(content, ts_offset=0):
    return {
        "id": f"msg-user-{ts_offset}",
        "agent_id": "user",
        "agent_name": "You",
        "avatar": "👤",
        "color": "#94a3b8",
        "role": "User",
        "content": content,
        "tool_use": [],
        "mentions": [],
        "is_user": True,
        "ts_offset": ts_offset,
    }


MOCK_CONVERSATION = [
    _user_msg(
        "Create a Python script that fetches weather data from a free API and displays it nicely in the terminal.",
        ts_offset=0,
    ),
    _agent_msg(
        "otto",
        "Got it! I'll coordinate this. @Scout, can you find us a good free weather API we can use without authentication hassles? @Dev, stand by — once Scout reports back, you'll write the script.",
        mentions=["scout", "dev"],
        ts_offset=1,
    ),
    _agent_msg(
        "scout",
        "On it! Let me search for free weather APIs...",
        tool_use=[
            {
                "tool": "web_search",
                "input": "free weather API no authentication 2025",
                "result": "Found 8 results. Top hits: wttr.in (free, no API key), Open-Meteo (free, no key required), OpenWeatherMap (free tier, key required)...",
            }
        ],
        ts_offset=2,
    ),
    _agent_msg(
        "scout",
        "Found a great option! **wttr.in** is perfect:\n- Completely free, no API key needed\n- Simple HTTP GET: `curl wttr.in/London?format=j1`\n- Returns JSON with current conditions, temperature, humidity, wind, and 3-day forecast\n- Supports city names, zip codes, and coordinates\n\n@Dev, here's the endpoint: `https://wttr.in/{city}?format=j1`",
        tool_use=[
            {
                "tool": "web_fetch",
                "input": "https://wttr.in/London?format=j1",
                "result": '{"current_condition": [{"temp_C": "15", "weatherDesc": [{"value": "Partly cloudy"}], "humidity": "72", "windspeedKmph": "19"}], ...}',
            }
        ],
        mentions=["dev"],
        ts_offset=3,
    ),
    _agent_msg(
        "dev",
        "Nice find, @Scout! Let me write that up.",
        mentions=["scout"],
        tool_use=[
            {
                "tool": "write_file",
                "input": "weather.py",
                "result": "File written successfully (52 lines)",
            }
        ],
        ts_offset=4,
    ),
    _agent_msg(
        "dev",
        "Here's what I wrote:\n\n```python\nimport sys\nimport urllib.request\nimport json\n\ndef fetch_weather(city):\n    url = f\"https://wttr.in/{city}?format=j1\"\n    req = urllib.request.Request(url, headers={\"User-Agent\": \"Mozilla/5.0\"})\n    with urllib.request.urlopen(req, timeout=10) as resp:\n        return json.loads(resp.read())\n\ndef display_weather(data, city):\n    current = data[\"current_condition\"][0]\n    desc = current[\"weatherDesc\"][0][\"value\"]\n    temp = current[\"temp_C\"]\n    humidity = current[\"humidity\"]\n    wind = current[\"windspeedKmph\"]\n    \n    print(f\"\\n  🌍 Weather for {city.title()}\")\n    print(f\"  {'─' * 30}\")\n    print(f\"  ☁️  {desc}\")\n    print(f\"  🌡️  {temp}°C\")\n    print(f\"  💧 Humidity: {humidity}%\")\n    print(f\"  💨 Wind: {wind} km/h\")\n    \n    print(f\"\\n  📅 3-Day Forecast\")\n    print(f\"  {'─' * 30}\")\n    for day in data.get(\"weather\", [])[:3]:\n        date = day[\"date\"]\n        hi = day[\"maxtempC\"]\n        lo = day[\"mintempC\"]\n        desc = day[\"hourly\"][4][\"weatherDesc\"][0][\"value\"]\n        print(f\"  {date}  {lo}°–{hi}°C  {desc}\")\n    print()\n\nif __name__ == \"__main__\":\n    city = \" \".join(sys.argv[1:]) or \"London\"\n    try:\n        data = fetch_weather(city)\n        display_weather(data, city)\n    except Exception as e:\n        print(f\"Error: {e}\")\n```\n\n@Sage, mind taking a look?",
        mentions=["sage"],
        ts_offset=5,
    ),
    _agent_msg(
        "sage",
        "Nice work, @Dev! Clean and readable. A couple of suggestions:\n\n1. **Error handling** — `urlopen` can throw `URLError` or `HTTPError`. Catch those specifically so the user gets a helpful message (e.g. \"City not found\" vs a raw traceback).\n2. **Encoding** — City names with spaces/special chars should be URL-encoded.\n3. **Minor** — The emoji rendering depends on terminal support. Maybe add a `--plain` flag as a fallback.\n\nThe first two are worth fixing now. The third is nice-to-have.",
        mentions=["dev"],
        ts_offset=6,
    ),
    _agent_msg(
        "dev",
        "Good catches, @Sage! Let me fix those.",
        mentions=["sage"],
        tool_use=[
            {
                "tool": "edit_file",
                "input": "weather.py — add urllib.parse.quote, specific exception handling",
                "result": "File edited successfully (3 replacements)",
            }
        ],
        ts_offset=7,
    ),
    _agent_msg(
        "dev",
        "Updated! Added `urllib.parse.quote()` for the city name and specific exception handling:\n\n```python\nfrom urllib.error import URLError, HTTPError\nfrom urllib.parse import quote\n\ndef fetch_weather(city):\n    url = f\"https://wttr.in/{quote(city)}?format=j1\"\n    # ...\n\nif __name__ == \"__main__\":\n    city = \" \".join(sys.argv[1:]) or \"London\"\n    try:\n        data = fetch_weather(city)\n        display_weather(data, city)\n    except HTTPError as e:\n        if e.code == 404:\n            print(f\"City '{city}' not found.\")\n        else:\n            print(f\"API error: {e.code}\")\n    except URLError:\n        print(\"Network error. Check your connection.\")\n```\n\n@Otto, all done!",
        mentions=["otto"],
        ts_offset=8,
    ),
    _agent_msg(
        "otto",
        "Excellent work, team! One more thing — @Scheduler, let's set up a daily weather check reminder. @Recap, wrap it up when Scheduler is done.",
        mentions=["scheduler", "recap"],
        ts_offset=9,
    ),
    _agent_msg(
        "scheduler",
        "On it! Setting up a daily weather check.",
        tool_use=[
            {
                "tool": "schedule_task",
                "input": '{"name": "Daily Weather Check", "frequency": "daily", "action": "Run python weather.py London and report conditions"}',
                "result": '{"status": "created", "schedule": {"name": "Daily Weather Check", "frequency": "daily"}}',
            }
        ],
        ts_offset=10,
    ),
    _agent_msg(
        "scheduler",
        "Done! I've created a **daily** scheduled task:\n- **Name:** Daily Weather Check\n- **Frequency:** Every day\n- **Action:** Run the weather script and report current conditions\n\nYou can view or cancel this in the Schedules section of the sidebar. @Otto, all set!",
        mentions=["otto"],
        ts_offset=11,
    ),
    _agent_msg(
        "recap",
        "### \u2705 Task Complete: Weather Script + Daily Check\n\n**Created:** `weather.py` \u2014 a terminal weather tool using the free wttr.in API\n\n**Features:**\n- Current conditions (temperature, humidity, wind, description)\n- 3-day forecast\n- Emoji-enhanced terminal display\n- Proper URL encoding for city names with spaces/special characters\n- Specific error handling (city not found, network errors)\n\n**Scheduled:** Daily weather check reminder set up by Scheduler\n\n**Usage:** `python weather.py San Francisco`\n\n**Team:** Scout found the API, Dev wrote the code, Sage reviewed and caught two issues, Scheduler set up a daily check.\n\nI've also attached a downloadable PDF summary below.",
        tool_use=[
            {
                "tool": "create_document",
                "input": "weather-script-summary.pdf",
                "result": "Document created successfully",
            }
        ],
        documents=[
            {
                "id": "demo",
                "filename": "demo_weather-summary.pdf",
                "display_name": "weather-summary.pdf",
                "format": "pdf",
                "size": 1666,
                "url": "/api/documents/0ebaa7c6/0ebaa7c6_weather-script-summary.pdf",
            }
        ],
        ts_offset=12,
    ),
]


@bp.route("/")
def index():
    return render_template("synthchat.html")


@bp.route("/api/agents")
def get_agents():
    all_ag = get_all_agents()
    safe_agents = []
    def _agent_info(a):
        return {
            "id": a["id"],
            "name": a["name"],
            "role": a["role"],
            "avatar": a["avatar"],
            "color": a["color"],
            "description": a.get("description", ""),
            "tools": a.get("tools", []),
            "skills": a.get("skills", []),
            "is_builtin": a.get("is_builtin", False),
            "is_custom": a.get("is_custom", False),
        }
    for aid in AGENT_ORDER:
        if aid in all_ag:
            safe_agents.append(_agent_info(all_ag[aid]))
    for aid, a in all_ag.items():
        if aid not in AGENT_ORDER:
            safe_agents.append(_agent_info(a))
    return jsonify({"agents": safe_agents})


@bp.route("/api/available-agents")
def get_available_agents():
    all_ag = get_all_agents()
    agents = []
    for aid in AGENT_ORDER:
        if aid in all_ag:
            a = all_ag[aid]
            agents.append({
                "id": a["id"],
                "name": a["name"],
                "role": a["role"],
                "avatar": a["avatar"],
                "color": a["color"],
                "description": a.get("description", ""),
                "is_core": aid in CORE_AGENTS,
                "is_custom": a.get("is_custom", False),
            })
    for aid, a in all_ag.items():
        if aid not in AGENT_ORDER:
            agents.append({
                "id": a["id"],
                "name": a["name"],
                "role": a["role"],
                "avatar": a["avatar"],
                "color": a["color"],
                "description": a.get("description", ""),
                "is_core": False,
                "is_custom": a.get("is_custom", False),
            })
    return jsonify({"agents": agents})


@bp.route("/api/channels")
def list_channels():
    store = ChannelStore()
    channels = store.list()
    return jsonify({"channels": channels})


@bp.route("/api/channels", methods=["POST"])
def create_channel():
    data = request.get_json()
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "Channel name is required"}), 400
    description = data.get("description", "")
    agent_ids = data.get("agent_ids", get_agent_order())
    store = ChannelStore()
    channel = store.create(name, description, agent_ids)
    return jsonify({"channel": channel}), 201


@bp.route("/api/channels/<channel_id>", methods=["DELETE"])
def delete_channel(channel_id):
    store = ChannelStore()
    if store.delete(channel_id):
        clear_history(channel_id)
        return jsonify({"status": "deleted"})
    return jsonify({"error": "Cannot delete this channel"}), 400


@bp.route("/api/channels/<channel_id>/history")
def get_channel_history(channel_id):
    messages = load_history(channel_id)
    return jsonify({"messages": messages})


@bp.route("/api/channels/<channel_id>/history", methods=["DELETE"])
def clear_channel_history(channel_id):
    clear_history(channel_id)
    return jsonify({"status": "cleared"})


@bp.route("/api/schedules")
def list_schedules():
    store = ScheduleStore()
    channel_id = request.args.get("channel_id")
    schedules = store.list(channel_id=channel_id)
    return jsonify({"schedules": schedules})


@bp.route("/api/schedules/<schedule_id>", methods=["DELETE"])
def cancel_schedule(schedule_id):
    store = ScheduleStore()
    if store.cancel(schedule_id):
        return jsonify({"status": "cancelled"})
    return jsonify({"error": "Schedule not found"}), 404


@bp.route("/api/documents/<doc_id>/<filename>")
def download_document(doc_id, filename):
    import os
    if not filename.startswith(doc_id + "_"):
        return jsonify({"error": "Invalid document reference"}), 403

    safe_filename = os.path.basename(filename)
    filepath = os.path.join(DOCUMENTS_DIR, safe_filename)
    if not os.path.exists(filepath):
        return jsonify({"error": "Document not found"}), 404

    mime_map = {
        ".csv": "text/csv",
        ".html": "text/html",
        ".pdf": "application/pdf",
        ".png": "image/png",
    }
    ext = os.path.splitext(safe_filename)[1].lower()
    mimetype = mime_map.get(ext, "application/octet-stream")

    return send_from_directory(
        DOCUMENTS_DIR, safe_filename,
        mimetype=mimetype,
        as_attachment=True,
    )


@bp.route("/api/agents/<agent_id>")
def get_agent_profile(agent_id):
    all_ag = get_all_agents()
    if agent_id not in all_ag:
        return jsonify({"error": "Agent not found"}), 404
    a = all_ag[agent_id]
    profile = {
        "id": a["id"],
        "name": a["name"],
        "role": a["role"],
        "avatar": a["avatar"],
        "color": a["color"],
        "description": a.get("description", ""),
        "tools": a.get("tools", []),
        "skills": a.get("skills", []),
        "system": a.get("system", ""),
        "is_core": agent_id in CORE_AGENTS,
        "is_custom": a.get("is_custom", False),
    }
    return jsonify({"agent": profile})


@bp.route("/api/agents", methods=["POST"])
def create_agent():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400
    required = ["name", "role", "system"]
    for field in required:
        if not data.get(field, "").strip():
            return jsonify({"error": f"'{field}' is required"}), 400
    config = {
        "name": data["name"].strip(),
        "role": data["role"].strip(),
        "avatar": data.get("avatar", "🤖").strip() or "🤖",
        "color": data.get("color", "#6b7280").strip() or "#6b7280",
        "description": data.get("description", "").strip(),
        "tools": [t for t in data.get("tools", []) if t in VALID_TOOLS],
        "skills": data.get("skills", []),
        "system": data["system"].strip(),
    }
    try:
        agent_id = save_custom_agent(config)
        return jsonify({"agent_id": agent_id, "status": "created"}), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@bp.route("/api/agents/<agent_id>", methods=["PUT"])
def update_agent(agent_id):
    if agent_id in AGENTS:
        return jsonify({"error": "Cannot edit built-in agents"}), 400
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400
    required = ["name", "role", "system"]
    for field in required:
        if not data.get(field, "").strip():
            return jsonify({"error": f"'{field}' is required"}), 400
    config = {
        "id": agent_id,
        "name": data["name"].strip(),
        "role": data["role"].strip(),
        "avatar": data.get("avatar", "🤖").strip() or "🤖",
        "color": data.get("color", "#6b7280").strip() or "#6b7280",
        "description": data.get("description", "").strip(),
        "tools": [t for t in data.get("tools", []) if t in VALID_TOOLS],
        "skills": data.get("skills", []),
        "system": data["system"].strip(),
    }
    try:
        save_custom_agent(config)
        return jsonify({"agent_id": agent_id, "status": "updated"})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@bp.route("/api/agents/<agent_id>", methods=["DELETE"])
def delete_agent(agent_id):
    if agent_id in AGENTS:
        return jsonify({"error": "Cannot delete built-in agents"}), 400
    try:
        if delete_custom_agent(agent_id):
            return jsonify({"status": "deleted"})
        return jsonify({"error": "Agent not found"}), 404
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@bp.route("/api/tools")
def list_tools():
    tool_categories = {
        "File System": ["read_file", "write_file", "edit_file", "list_files", "search_files", "tree", "file_info", "apply_patch"],
        "Execution": ["run_command"],
        "Web": ["web_search", "web_fetch"],
        "Documents": ["create_document"],
        "Scheduling": ["schedule_task", "list_schedules", "cancel_schedule"],
    }
    tools = []
    for category, tool_names in tool_categories.items():
        for name in tool_names:
            if name in VALID_TOOLS:
                tools.append({"name": name, "category": category})
    return jsonify({"tools": tools})


@bp.route("/api/skills")
def list_skills():
    skills = list_available_skills()
    return jsonify({"skills": skills})


@bp.route("/api/community/agents")
def list_community_agents():
    community = load_community_agents()
    custom = load_custom_agents()
    agents = []
    for aid, a in sorted(community.items()):
        installed = aid in custom or aid in AGENTS
        agents.append({
            "id": a["id"],
            "name": a["name"],
            "role": a["role"],
            "avatar": a["avatar"],
            "color": a["color"],
            "description": a.get("description", ""),
            "tools": a.get("tools", []),
            "skills": a.get("skills", []),
            "installed": installed,
        })
    return jsonify({"agents": agents})


@bp.route("/api/agents/install", methods=["POST"])
def install_agent():
    data = request.get_json()
    agent_id = data.get("agent_id", "").strip()
    if not agent_id:
        return jsonify({"error": "agent_id is required"}), 400
    try:
        installed_id = install_community_agent(agent_id)
        return jsonify({"agent_id": installed_id, "status": "installed"}), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@bp.route("/api/agents/<agent_id>/publish", methods=["POST"])
def publish_agent(agent_id):
    try:
        publish_agent_to_community(agent_id)
        return jsonify({"agent_id": agent_id, "status": "published"})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@bp.route("/api/mock-conversation")
def get_mock_conversation():
    return jsonify({"messages": MOCK_CONVERSATION})


@bp.route("/chat", methods=["POST"])
def chat():
    from synthchat.engine import run_multi_agent_chat

    data = request.get_json()
    message = data.get("message", "").strip()
    channel_id = data.get("channel_id", "workspace")
    if not message:
        return jsonify({"error": "Empty message"}), 400

    _stop_event.clear()
    event_queue = queue.Queue()

    def run():
        try:
            run_multi_agent_chat(message, event_queue, _stop_event, channel_id=channel_id)
        except Exception as e:
            event_queue.put(("agent_error", {"agent_id": "system", "message": str(e)}))
            event_queue.put(("done", {}))

    thread = threading.Thread(target=run, daemon=True)
    thread.start()

    def generate():
        while True:
            try:
                event_type, data = event_queue.get(timeout=300)
            except queue.Empty:
                yield f"event: done\ndata: {{}}\n\n"
                break
            yield f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
            if event_type == "done":
                break

    return Response(generate(), mimetype="text/event-stream")


@bp.route("/stop", methods=["POST"])
def stop():
    _stop_event.set()
    return jsonify({"status": "ok"})


def create_standalone_app():
    app = Flask(__name__)
    app.register_blueprint(bp, url_prefix="/synthchat")

    @app.route("/")
    def root_redirect():
        return redirect("/synthchat/")

    return app
