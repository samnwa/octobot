import json
import queue
import threading
from flask import Flask, render_template, request, Response, jsonify, send_from_directory

from octobot.agent import Agent
from octobot.tools import TOOL_DEFINITIONS

app = Flask(__name__)

_agent = None
_agent_lock = threading.Lock()


def get_agent():
    global _agent
    if _agent is None:
        _agent = Agent()
    return _agent


@app.route("/")
def index():
    agent = get_agent()
    return render_template(
        "index.html",
        model=agent.model,
        tool_count=len(TOOL_DEFINITIONS),
    )


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    message = data.get("message", "").strip()
    if not message:
        return jsonify({"error": "Empty message"}), 400

    agent = get_agent()
    event_queue = queue.Queue()

    def run_agent():
        try:
            web_chat(agent, message, event_queue)
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


@app.route("/reset", methods=["POST"])
def reset():
    agent = get_agent()
    agent.reset()
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


@app.route("/favicon.ico")
def favicon():
    return "", 204


def web_chat(agent, user_message, eq):
    from octobot.config import MAX_TOKENS, MAX_TURNS
    from octobot.tools import get_tool_definitions, execute_tool
    from octobot.approval import check_approval
    from octobot.agent import _tag_untrusted_content, _UNTRUSTED_CONTENT_TOOLS

    agent.messages.append({"role": "user", "content": user_message})
    agent._tool_call_history = []

    for turn in range(MAX_TURNS):
        eq.put(("thinking", {"text": "Thinking..."}))

        try:
            response = agent.client.messages.create(
                model=agent.model,
                max_tokens=MAX_TOKENS,
                system=agent._build_system_prompt(),
                tools=agent._build_tools(),
                messages=agent.messages,
            )
        except Exception as e:
            eq.put(("error", {"message": f"API Error: {e}"}))
            return

        agent.total_input_tokens += response.usage.input_tokens
        agent.total_output_tokens += response.usage.output_tokens
        eq.put(("tokens", {
            "input": agent.total_input_tokens,
            "output": agent.total_output_tokens,
        }))

        agent.messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        loop_detected = False

        for block in response.content:
            block_type = getattr(block, "type", None)

            if block_type == "thinking":
                eq.put(("thinking", {"text": block.thinking or ""}))
            elif block_type == "text":
                agent._tool_call_history.append("__TEXT__")
                eq.put(("text", {"content": block.text}))
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

                result = execute_tool(block.name, block.input)

                result_str = json.dumps(result, indent=2)
                if len(result_str) > 1000:
                    result_str = result_str[:1000] + "\n... [truncated]"
                eq.put(("tool_result", {"name": block.name, "result": result_str}))

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

        if response.stop_reason == "end_turn" or not tool_results:
            break

        if loop_detected:
            agent.messages.append({"role": "user", "content": tool_results})
            continue

        agent.messages.append({"role": "user", "content": tool_results})


def run_web(host="0.0.0.0", port=5000):
    get_agent()
    print(f"\n  Octobot Web UI running at http://{host}:{port}\n")
    app.run(host=host, port=port, debug=False, threaded=True)
