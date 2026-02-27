import re
import json
import time
import traceback
from anthropic import Anthropic, APIError, APITimeoutError

from octobot.config import get_api_key, get_model, SYNTHETIC_BASE_URL, MAX_TOKENS, load_config
from octobot.tools import execute_tool, TOOL_DEFINITIONS, _build_description_with_examples
from octobot.agent import _parse_xml_tool_calls, _tag_untrusted_content, _UNTRUSTED_CONTENT_TOOLS, _is_transient_error
from octobot.router import record_success, record_failure, get_fallbacks

from synthchat.agents import AGENTS
from synthchat.channels import ChannelStore
from synthchat.scheduler import SCHEDULER_TOOL_DEFINITIONS, execute_scheduler_tool
from synthchat.documents import DOCUMENT_TOOL_DEFINITIONS, execute_document_tool
from synthchat.history import save_message, load_history

_MENTION_RE = re.compile(r'@(\w+)', re.IGNORECASE)

_AGENT_NAME_TO_ID = {a["name"].lower(): aid for aid, a in AGENTS.items()}

_SCHEDULER_TOOL_NAMES = {t["name"] for t in SCHEDULER_TOOL_DEFINITIONS}
_DOCUMENT_TOOL_NAMES = {t["name"] for t in DOCUMENT_TOOL_DEFINITIONS}

_channel_store = None


def _get_channel_store():
    global _channel_store
    if _channel_store is None:
        _channel_store = ChannelStore()
    return _channel_store


def _get_tools_for_agent(agent_id):
    agent_def = AGENTS[agent_id]
    allowed = set(agent_def.get("tools", []))
    if not allowed:
        return []
    tools = []
    for t in TOOL_DEFINITIONS:
        if t["name"] in allowed:
            tools.append({
                "name": t["name"],
                "description": _build_description_with_examples(t),
                "input_schema": {**t["input_schema"]},
            })
    for t in SCHEDULER_TOOL_DEFINITIONS:
        if t["name"] in allowed:
            tools.append(t)
    for t in DOCUMENT_TOOL_DEFINITIONS:
        if t["name"] in allowed:
            tools.append(t)
    return tools


def _call_model(client, model, system_prompt, messages, tools, eq, agent_id):
    config = load_config()
    timeout_val = config.get("api_timeout", 90)

    kwargs = {
        "model": model,
        "max_tokens": MAX_TOKENS,
        "system": system_prompt,
        "messages": messages,
    }
    if tools:
        kwargs["tools"] = tools

    models_to_try = [model] + get_fallbacks(model)

    for try_model in models_to_try:
        try:
            kwargs["model"] = try_model
            t0 = time.time()
            response = client.messages.create(**kwargs)
            latency = time.time() - t0
            record_success(try_model, latency,
                           response.usage.input_tokens, response.usage.output_tokens)
            if try_model != model:
                eq.put(("agent_status", {
                    "agent_id": agent_id,
                    "text": f"Using {try_model} (failover)",
                }))
            return response
        except (APIError, APITimeoutError) as e:
            record_failure(try_model)
            if not _is_transient_error(e):
                raise
        except Exception as e:
            traceback.print_exc()
            record_failure(try_model)
            if not _is_transient_error(e):
                raise
    raise Exception("All models failed")


def _extract_mentions(text):
    found = []
    for m in _MENTION_RE.finditer(text):
        name = m.group(1).lower()
        aid = _AGENT_NAME_TO_ID.get(name)
        if aid:
            found.append(aid)
    return found


def _build_channel_context(channel_messages, current_agent_id):
    parts = []
    for msg in channel_messages:
        label = f"[{msg['agent_name']} ({msg['role']})]"
        parts.append(f"{label}: {msg['content']}")

    transcript = "\n\n".join(parts)

    agent_def = AGENTS.get(current_agent_id, {})
    if current_agent_id == "recap":
        instruction = "It's your turn. Summarize everything that was accomplished in this conversation. Produce your summary now."
    else:
        instruction = "It's your turn to respond. Read the conversation and contribute based on your role. Respond naturally as if chatting in a team workspace."

    return [
        {"role": "user", "content": f"Here is the team conversation so far:\n\n{transcript}\n\n{instruction}"},
    ]


def _run_agent_turn(client, model, agent_id, channel_messages, eq, stop_event, channel_id="workspace", max_tool_turns=4):
    agent_def = AGENTS[agent_id]
    system_prompt = agent_def["system"]
    tools = _get_tools_for_agent(agent_id)

    conversation = _build_channel_context(channel_messages, agent_id)

    eq.put(("typing", {
        "agent_id": agent_id,
        "agent_name": agent_def["name"],
        "avatar": agent_def["avatar"],
        "color": agent_def["color"],
    }))

    all_text_parts = []
    created_documents = []

    for tool_turn in range(max_tool_turns):
        if stop_event and stop_event.is_set():
            return None

        try:
            response = _call_model(client, model, system_prompt, conversation, tools, eq, agent_id)
        except Exception as e:
            eq.put(("agent_error", {
                "agent_id": agent_id,
                "message": f"API error: {e}",
            }))
            return None

        text_parts = []
        tool_calls = []

        for block in response.content:
            if hasattr(block, "text"):
                xml_calls, clean_text = _parse_xml_tool_calls(block.text)
                if clean_text:
                    text_parts.append(clean_text)
                tool_calls.extend(xml_calls)
            elif block.type == "tool_use":
                tool_calls.append({"name": block.name, "input": block.input, "id": block.id})

        if text_parts:
            all_text_parts.extend(text_parts)

        if not tool_calls:
            break

        tool_results_for_api = []
        for tc in tool_calls:
            tool_name = tc["name"]
            tool_input = tc["input"]

            eq.put(("tool_use", {
                "agent_id": agent_id,
                "tool": tool_name,
                "input": json.dumps(tool_input)[:200],
            }))

            if tool_name in _SCHEDULER_TOOL_NAMES:
                result = execute_scheduler_tool(tool_name, tool_input, channel_id)
            elif tool_name in _DOCUMENT_TOOL_NAMES:
                result = execute_document_tool(tool_name, tool_input)
                try:
                    doc_data = json.loads(result)
                    if "error" not in doc_data:
                        created_documents.append(doc_data)
                        eq.put(("document", {
                            "agent_id": agent_id,
                            **doc_data,
                        }))
                except (json.JSONDecodeError, TypeError):
                    pass
            else:
                result = execute_tool(tool_name, tool_input)

            if tool_name in _UNTRUSTED_CONTENT_TOOLS:
                result = _tag_untrusted_content(result)

            result_str = json.dumps(result) if isinstance(result, dict) else str(result)
            if len(result_str) > 4000:
                result_str = result_str[:4000] + "... (truncated)"

            eq.put(("tool_result", {
                "agent_id": agent_id,
                "tool": tool_name,
                "result": result_str[:500],
            }))

            if "id" in tc:
                tool_results_for_api.append({
                    "type": "tool_result",
                    "tool_use_id": tc["id"],
                    "content": result_str,
                })
            else:
                tool_results_for_api.append({
                    "type": "tool_result",
                    "tool_use_id": f"xml_{tool_name}",
                    "content": result_str,
                })

        conversation.append({"role": "assistant", "content": response.content})
        if tool_results_for_api:
            conversation.append({"role": "user", "content": tool_results_for_api})
        else:
            conversation.append({"role": "user", "content": result_str})

        if response.stop_reason == "end_turn":
            break

    full_text = "\n\n".join(all_text_parts)
    if not full_text:
        full_text = "(No response)"

    mentions = _extract_mentions(full_text)

    msg = {
        "agent_id": agent_id,
        "agent_name": agent_def["name"],
        "avatar": agent_def["avatar"],
        "color": agent_def["color"],
        "role": agent_def["role"],
        "content": full_text,
        "mentions": mentions,
        "is_user": False,
        "timestamp": time.time(),
    }

    if created_documents:
        msg["documents"] = created_documents

    eq.put(("typing_clear", {"agent_id": agent_id}))
    eq.put(("message", msg))

    save_message(channel_id, msg)

    return msg


def run_multi_agent_chat(user_message, eq, stop_event=None, channel_id="workspace"):
    try:
        client = Anthropic(
            api_key=get_api_key(),
            base_url=SYNTHETIC_BASE_URL,
            timeout=float(load_config().get("api_timeout", 90)),
        )
        model = get_model()

        store = _get_channel_store()
        channel = store.get(channel_id)
        if not channel:
            channel = store.get("workspace")
            channel_id = "workspace"

        channel_agent_ids = set(channel.get("agent_ids", []))

        prior_history = load_history(channel_id)
        channel_messages = list(prior_history) if prior_history else []

        user_msg = {
            "agent_id": "user",
            "agent_name": "You",
            "avatar": "👤",
            "color": "#94a3b8",
            "role": "User",
            "content": user_message,
            "mentions": [],
            "is_user": True,
            "timestamp": time.time(),
        }
        channel_messages.append(user_msg)
        save_message(channel_id, user_msg)

        if "otto" not in channel_agent_ids:
            eq.put(("agent_error", {
                "agent_id": "system",
                "message": "Otto (Orchestrator) is required but not in this channel.",
            }))
            eq.put(("done", {}))
            return

        otto_msg = _run_agent_turn(client, model, "otto", channel_messages, eq, stop_event, channel_id)
        if not otto_msg:
            eq.put(("done", {}))
            return
        channel_messages.append(otto_msg)

        mentioned = _extract_mentions(otto_msg["content"])
        mentioned = [aid for aid in mentioned if aid not in ("otto", "recap") and aid in channel_agent_ids]

        if not mentioned:
            if "dev" in channel_agent_ids:
                mentioned = ["dev"]
            else:
                available = [aid for aid in channel_agent_ids if aid not in ("otto", "recap")]
                if available:
                    mentioned = [available[0]]

        for agent_id in mentioned:
            if stop_event and stop_event.is_set():
                break

            msg = _run_agent_turn(client, model, agent_id, channel_messages, eq, stop_event, channel_id)
            if msg:
                channel_messages.append(msg)

                next_mentions = _extract_mentions(msg["content"])
                for nm in next_mentions:
                    if nm not in mentioned and nm not in ("otto", "recap", "user") and nm != agent_id and nm in channel_agent_ids:
                        mentioned.append(nm)

        if stop_event and stop_event.is_set():
            eq.put(("done", {}))
            return

        has_sage = any(m.get("agent_id") == "sage" for m in channel_messages if not m.get("is_user"))
        dev_msgs = [m for m in channel_messages if m.get("agent_id") == "dev" and not m.get("is_user")]
        if not has_sage and dev_msgs and "sage" in channel_agent_ids:
            sage_msg = _run_agent_turn(client, model, "sage", channel_messages, eq, stop_event, channel_id)
            if sage_msg:
                channel_messages.append(sage_msg)

                sage_mentions = _extract_mentions(sage_msg["content"])
                if "dev" in sage_mentions and "dev" in channel_agent_ids:
                    fix_msg = _run_agent_turn(client, model, "dev", channel_messages, eq, stop_event, channel_id)
                    if fix_msg:
                        channel_messages.append(fix_msg)

        if "recap" in channel_agent_ids:
            recap_msg = _run_agent_turn(client, model, "recap", channel_messages, eq, stop_event, channel_id)
            if recap_msg:
                channel_messages.append(recap_msg)

        eq.put(("done", {}))

    except Exception as e:
        traceback.print_exc()
        eq.put(("agent_error", {
            "agent_id": "system",
            "message": f"System error: {e}",
        }))
        eq.put(("done", {}))
