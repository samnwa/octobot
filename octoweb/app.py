import json
import os
import queue
import threading
from flask import Flask, render_template, request, Response, jsonify, send_from_directory

from octobot.agent import Agent
from octobot.tools import TOOL_DEFINITIONS

app = Flask(__name__)

_agent = None
_agent_lock = threading.Lock()
_touched_files = set()
_stop_event = threading.Event()

SKIP_DIRS = {
    "__pycache__", ".git", "node_modules", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "egg-info", ".eggs",
}

CORE_PREFIXES = ("octobot/", "octoweb/", ".git/", "__pycache__/", ".local/")

COMMANDS = [
    {"name": "/reset", "description": "Clear conversation history"},
    {"name": "/model [name]", "description": "Switch model (session)"},
    {"name": "/models", "description": "List available models"},
    {"name": "/tokens", "description": "Show token usage"},
    {"name": "/tools", "description": "List available tools"},
    {"name": "/skills", "description": "List loaded skills"},
    {"name": "/stats", "description": "Show router stats"},
    {"name": "/history", "description": "List past conversations"},
    {"name": "/octo", "description": "Toggle swimming octopus"},
    {"name": "/help", "description": "Show help"},
]


def get_agent():
    global _agent
    if _agent is None:
        _agent = Agent()
    return _agent


def track_file(tool_name, tool_input):
    global _touched_files
    if tool_name in ("write_file", "edit_file", "apply_patch") and "path" in tool_input:
        _touched_files.add(tool_input["path"])


@app.route("/")
def index():
    from octobot.config import has_api_key, get_model
    if not has_api_key():
        return render_template(
            "index.html",
            configured=False,
            model="",
            tool_count=len(TOOL_DEFINITIONS),
        )
    agent = get_agent()
    return render_template(
        "index.html",
        configured=True,
        model=agent.model,
        tool_count=len(TOOL_DEFINITIONS),
    )


@app.route("/chat", methods=["POST"])
def chat():
    global _stop_event
    data = request.get_json()
    message = data.get("message", "").strip()
    if not message:
        return jsonify({"error": "Empty message"}), 400

    _stop_event.clear()
    agent = get_agent()
    event_queue = queue.Queue()

    def run_agent():
        try:
            web_chat(agent, message, event_queue, _stop_event)
        except Exception as e:
            event_queue.put(("error", {"message": str(e)}))
        finally:
            event_queue.put(("done", {}))

    thread = threading.Thread(target=run_agent, daemon=True)
    thread.start()

    def generate():
        while True:
            try:
                event_type, data = event_queue.get(timeout=120)
            except queue.Empty:
                yield f"event: error\ndata: {json.dumps({'message': 'Timeout'})}\n\n"
                break
            yield f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
            if event_type == "done":
                break

    return Response(generate(), mimetype="text/event-stream")


@app.route("/stop", methods=["POST"])
def stop():
    _stop_event.set()
    return jsonify({"status": "ok"})


@app.route("/reset", methods=["POST"])
def reset():
    global _touched_files
    agent = get_agent()
    agent.reset()
    _touched_files = set()
    return jsonify({"status": "ok"})


@app.route("/status")
def status():
    agent = get_agent()
    return jsonify({
        "model": agent.model,
        "tools": len(TOOL_DEFINITIONS),
        "input_tokens": agent.total_input_tokens,
        "output_tokens": agent.total_output_tokens,
    })


@app.route("/api/files")
def api_files():
    base = os.getcwd()
    hide_core = request.args.get("hide_core", "true").lower() == "true"

    def scan_dir(dirpath, rel_prefix=""):
        entries = []
        try:
            items = sorted(os.listdir(dirpath))
        except PermissionError:
            return entries

        for name in items:
            if name.startswith(".") and name not in (".env",):
                if not rel_prefix:
                    continue
            full = os.path.join(dirpath, name)
            rel = os.path.join(rel_prefix, name) if rel_prefix else name

            if os.path.isdir(full):
                if name in SKIP_DIRS:
                    continue
                if name.endswith(".egg-info"):
                    continue
                if hide_core and any(rel.startswith(p.rstrip("/")) for p in CORE_PREFIXES):
                    continue
                children = scan_dir(full, rel)
                entries.append({
                    "name": name,
                    "path": rel,
                    "type": "dir",
                    "children": children,
                    "touched": any(t.startswith(rel + "/") for t in _touched_files),
                })
            else:
                if hide_core and any(rel.startswith(p) for p in CORE_PREFIXES):
                    continue
                try:
                    stat = os.stat(full)
                    size = stat.st_size
                    mtime = stat.st_mtime
                except OSError:
                    size = 0
                    mtime = 0
                entries.append({
                    "name": name,
                    "path": rel,
                    "type": "file",
                    "size": size,
                    "modified": mtime,
                    "touched": rel in _touched_files,
                })
        return entries

    tree = scan_dir(base)
    return jsonify({"files": tree, "touched": list(_touched_files)})


@app.route("/api/file")
def api_file():
    base = os.getcwd()
    path = request.args.get("path", "")
    if not path:
        return jsonify({"error": "No path"}), 400

    full = os.path.normpath(os.path.join(base, path))
    if not full.startswith(base):
        return jsonify({"error": "Access denied"}), 403

    if not os.path.isfile(full):
        return jsonify({"error": "File not found"}), 404

    size = os.path.getsize(full)
    if size > 100_000:
        return jsonify({"error": "File too large", "size": size}), 400

    try:
        with open(full, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    ext = os.path.splitext(path)[1].lstrip(".")
    return jsonify({
        "path": path,
        "content": content,
        "size": size,
        "extension": ext,
        "touched": path in _touched_files,
    })


@app.route("/api/models")
def api_models():
    import httpx
    from octobot.config import get_api_key
    try:
        r = httpx.get(
            "https://api.synthetic.new/openai/v1/models",
            headers={"Authorization": f"Bearer {get_api_key()}"},
            timeout=10,
        )
        data = r.json()
        models = []
        for m in data.get("data", []):
            models.append({
                "id": m.get("id", ""),
                "name": m.get("name", ""),
                "context_length": m.get("context_length", 0),
                "provider": m.get("provider", ""),
                "features": m.get("supported_features", []),
            })
        models.sort(key=lambda x: x["id"])
        return jsonify({"models": models})
    except Exception as e:
        return jsonify({"error": str(e), "models": []}), 500


@app.route("/api/model", methods=["GET", "POST"])
def api_model():
    from octobot.config import load_config, save_config
    agent = get_agent()
    if request.method == "GET":
        return jsonify({"model": agent.model})

    data = request.get_json()
    new_model = data.get("model", "").strip()
    persist = data.get("persist", False)
    if not new_model:
        return jsonify({"error": "No model specified"}), 400

    agent.model = new_model
    agent.reset()

    if persist:
        config = load_config()
        config["model"] = new_model
        save_config(config)

    return jsonify({"model": agent.model, "persisted": persist})


@app.route("/api/setup", methods=["GET", "POST"])
def api_setup():
    from octobot.config import has_api_key, load_config, save_config
    if request.method == "GET":
        return jsonify({"configured": has_api_key()})

    data = request.get_json()
    api_key = data.get("api_key", "").strip()
    if not api_key:
        return jsonify({"error": "API key is required"}), 400

    try:
        import httpx
        r = httpx.get(
            "https://api.synthetic.new/openai/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10,
        )
        if r.status_code == 401:
            return jsonify({"error": "Invalid API key"}), 401
    except Exception:
        pass

    config = load_config()
    config["synthetic_api_key"] = api_key
    save_config(config)

    global _agent
    _agent = None

    return jsonify({"status": "ok"})


@app.route("/api/commands")
def api_commands():
    return jsonify({"commands": COMMANDS})


@app.route("/api/router")
def api_router():
    from octobot.router import get_model_stats, FALLBACK_ORDER, is_model_healthy
    agent = get_agent()
    return jsonify({
        "primary": agent.model,
        "fallback_order": FALLBACK_ORDER,
        "stats": get_model_stats(),
        "healthy": {m: is_model_healthy(m) for m in FALLBACK_ORDER},
    })


@app.route("/api/history")
def api_history():
    from octobot.history import list_sessions
    sessions = list_sessions()
    agent = get_agent()
    return jsonify({
        "sessions": sessions,
        "current_session": agent.session_id,
    })


@app.route("/api/history/<session_id>", methods=["POST"])
def api_history_load(session_id):
    agent = get_agent()
    if agent.load_history(session_id):
        return jsonify({"status": "ok", "message_count": len(agent.messages)})
    return jsonify({"error": "Session not found"}), 404


@app.route("/api/history/<session_id>", methods=["DELETE"])
def api_history_delete(session_id):
    from octobot.history import delete_session
    if delete_session(session_id):
        return jsonify({"status": "ok"})
    return jsonify({"error": "Session not found"}), 404


@app.route("/favicon.ico")
def favicon():
    return "", 204


def web_chat(agent, user_message, eq, stop_event=None):
    import time as _time
    from octobot.config import MAX_TOKENS, MAX_TURNS
    from octobot.tools import get_tool_definitions, execute_tool
    from octobot.approval import check_approval
    from octobot.agent import _tag_untrusted_content, _UNTRUSTED_CONTENT_TOOLS, _parse_xml_tool_calls
    from octobot.router import record_success, record_failure, get_fallbacks

    agent.messages.append({"role": "user", "content": user_message})
    agent._tool_call_history = []
    agent.save_history()

    for turn in range(MAX_TURNS):
        if stop_event and stop_event.is_set():
            eq.put(("text", {"content": "\n\n*Stopped by user.*"}))
            agent.save_history()
            return

        eq.put(("thinking", {"text": "Thinking..."}))

        response = None
        models_to_try = [agent.model] + get_fallbacks(agent.model)
        for try_model in models_to_try:
            try:
                t0 = _time.time()
                response = agent.client.messages.create(
                    model=try_model,
                    max_tokens=MAX_TOKENS,
                    system=agent._build_system_prompt(),
                    tools=agent._build_tools(),
                    messages=agent.messages,
                )
                latency = _time.time() - t0
                record_success(
                    try_model, latency,
                    response.usage.input_tokens, response.usage.output_tokens,
                )
                if try_model != agent.model:
                    eq.put(("text", {
                        "content": f"*Failover: using {try_model} (primary unavailable)*\n\n",
                    }))
                break
            except Exception as e:
                record_failure(try_model)
                if try_model == models_to_try[-1]:
                    eq.put(("error", {"message": f"API Error: All models failed. {e}"}))
                    return

        agent.total_input_tokens += response.usage.input_tokens
        agent.total_output_tokens += response.usage.output_tokens
        eq.put(("tokens", {
            "input": agent.total_input_tokens,
            "output": agent.total_output_tokens,
        }))

        agent.messages.append({"role": "assistant", "content": response.content})
        agent.save_history()

        tool_results = []
        loop_detected = False

        for block in response.content:
            block_type = getattr(block, "type", None)

            if block_type == "thinking":
                eq.put(("thinking", {"text": block.thinking or ""}))
            elif block_type == "text":
                xml_calls, clean_text = _parse_xml_tool_calls(block.text)
                if clean_text:
                    agent._tool_call_history.append("__TEXT__")
                    eq.put(("text", {"content": clean_text}))

                for call in xml_calls:
                    call_id = f"xmltool_{id(call)}"
                    if agent._check_loop(call["name"], call["input"]):
                        loop_detected = True
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": call_id,
                            "content": json.dumps({"error": "Loop detected."}),
                        })
                        eq.put(("error", {"message": "Loop detected."}))
                        continue

                    inp_summary = json.dumps(call["input"], indent=2)
                    if len(inp_summary) > 500:
                        inp_summary = inp_summary[:500] + "..."
                    eq.put(("tool_use", {"name": call["name"], "input": inp_summary}))

                    needs_approval, reason = check_approval(call["name"], call["input"])
                    if needs_approval:
                        eq.put(("error", {"message": f"Operation requires approval: {reason} — auto-declined in web mode."}))
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": call_id,
                            "content": json.dumps({"error": "Declined in web mode for safety."}),
                        })
                        continue

                    track_file(call["name"], call["input"])
                    result = execute_tool(call["name"], call["input"])
                    result_display = json.dumps(result, indent=2)
                    if len(result_display) > 1000:
                        result_display = result_display[:1000] + "\n... [truncated]"
                    eq.put(("tool_result", {"name": call["name"], "result": result_display}))
                    if call["name"] in ("write_file", "edit_file", "apply_patch") and "path" in call["input"]:
                        eq.put(("file_written", {"path": call["input"]["path"]}))

                    if call["name"] in _UNTRUSTED_CONTENT_TOOLS:
                        result = _tag_untrusted_content(result)

                    r_str = json.dumps(result)
                    if len(r_str) > 50000:
                        r_str = r_str[:50000] + "... [truncated]"
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": call_id,
                        "content": r_str,
                    })

            elif block_type == "tool_use":
                if agent._check_loop(block.name, block.input):
                    loop_detected = True
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps({"error": "Loop detected — stopping repeated calls."}),
                    })
                    eq.put(("error", {"message": "Loop detected — stopping repeated tool calls."}))
                    continue

                inp_summary = json.dumps(block.input, indent=2)
                if len(inp_summary) > 500:
                    inp_summary = inp_summary[:500] + "..."
                eq.put(("tool_use", {"name": block.name, "input": inp_summary}))

                needs_approval, reason = check_approval(block.name, block.input)
                if needs_approval:
                    eq.put(("error", {"message": f"Operation requires approval: {reason} — auto-declined in web mode."}))
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps({"error": "Operation requires user approval. Declined in web mode for safety."}),
                    })
                    continue

                track_file(block.name, block.input)
                result = execute_tool(block.name, block.input)

                result_str = json.dumps(result, indent=2)
                if len(result_str) > 1000:
                    result_str = result_str[:1000] + "\n... [truncated]"
                eq.put(("tool_result", {"name": block.name, "result": result_str}))
                if block.name in ("write_file", "edit_file", "apply_patch") and hasattr(block, "input") and "path" in block.input:
                    eq.put(("file_written", {"path": block.input["path"]}))

                if block.name in _UNTRUSTED_CONTENT_TOOLS:
                    result = _tag_untrusted_content(result)

                if block.name == "browser_vision" and "base64" in result:
                    image_b64 = result.pop("base64")
                    text_part = json.dumps(result)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": [
                            {"type": "text", "text": text_part},
                            {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": image_b64}},
                        ],
                    })
                else:
                    r_str = json.dumps(result)
                    if len(r_str) > 50000:
                        r_str = r_str[:50000] + "... [truncated]"
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": r_str,
                    })

        if stop_event and stop_event.is_set():
            eq.put(("text", {"content": "\n\n*Stopped by user.*"}))
            agent.save_history()
            return

        if response.stop_reason == "end_turn" or not tool_results:
            break

        if loop_detected:
            agent.messages.append({"role": "user", "content": tool_results})
            continue

        agent.messages.append({"role": "user", "content": tool_results})

    agent.save_history()


def run_web(host="0.0.0.0", port=5000):
    from octobot.config import has_api_key
    if has_api_key():
        get_agent()
    else:
        print("\n  No API key configured — setup screen will be shown in the web UI.")
    print(f"\n  Octobot Web UI running at http://{host}:{port}\n")
    app.run(host=host, port=port, debug=False, threaded=True)
