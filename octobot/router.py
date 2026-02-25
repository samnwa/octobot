import json
import os
import time
from pathlib import Path

CONFIG_DIR = Path.home() / ".octobot"
ROUTER_STATS_FILE = CONFIG_DIR / "router_stats.json"

MODEL_REGISTRY = {
    "hf:nvidia/Kimi-K2.5-NVFP4": {
        "context": 262144,
        "strengths": ["tool_calling", "speed", "efficiency"],
        "provider": "synthetic",
        "tier": "primary",
    },
    "hf:Qwen/Qwen3.5-397B-A17B": {
        "context": 262144,
        "strengths": ["reasoning", "tool_calling", "code"],
        "provider": "synthetic",
        "tier": "fallback",
    },
    "hf:MiniMaxAI/MiniMax-M2.5": {
        "context": 191488,
        "strengths": ["reasoning", "tool_calling"],
        "provider": "synthetic",
        "tier": "fallback",
    },
    "hf:zai-org/GLM-4.7": {
        "context": 202752,
        "strengths": ["reasoning"],
        "provider": "synthetic",
        "tier": "fallback",
        "quirks": ["xml_tool_calls"],
    },
}

FALLBACK_ORDER = [
    "hf:nvidia/Kimi-K2.5-NVFP4",
    "hf:Qwen/Qwen3.5-397B-A17B",
    "hf:MiniMaxAI/MiniMax-M2.5",
    "hf:zai-org/GLM-4.7",
]


def _load_stats():
    if ROUTER_STATS_FILE.exists():
        try:
            with open(ROUTER_STATS_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_stats(stats):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(ROUTER_STATS_FILE, "w") as f:
            json.dump(stats, f, indent=2)
    except OSError:
        pass


def record_success(model, latency, input_tokens, output_tokens):
    stats = _load_stats()
    if model not in stats:
        stats[model] = {
            "successes": 0,
            "failures": 0,
            "total_latency": 0.0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "last_failure": 0,
            "consecutive_failures": 0,
        }
    s = stats[model]
    s["successes"] += 1
    s["total_latency"] += latency
    s["total_input_tokens"] += input_tokens
    s["total_output_tokens"] += output_tokens
    s["consecutive_failures"] = 0
    _save_stats(stats)


def record_failure(model):
    stats = _load_stats()
    if model not in stats:
        stats[model] = {
            "successes": 0,
            "failures": 0,
            "total_latency": 0.0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "last_failure": 0,
            "consecutive_failures": 0,
        }
    s = stats[model]
    s["failures"] += 1
    s["last_failure"] = time.time()
    s["consecutive_failures"] = s.get("consecutive_failures", 0) + 1
    _save_stats(stats)


def is_model_healthy(model):
    stats = _load_stats()
    s = stats.get(model)
    if not s:
        return True
    if s.get("consecutive_failures", 0) >= 3:
        cooldown = min(300, 30 * (2 ** (s["consecutive_failures"] - 3)))
        if time.time() - s.get("last_failure", 0) < cooldown:
            return False
    return True


def get_fallbacks(primary_model):
    fallbacks = []
    for model in FALLBACK_ORDER:
        if model != primary_model and is_model_healthy(model):
            fallbacks.append(model)
    return fallbacks


def get_model_stats():
    stats = _load_stats()
    result = {}
    for model, s in stats.items():
        total = s.get("successes", 0) + s.get("failures", 0)
        avg_latency = (
            s["total_latency"] / s["successes"]
            if s.get("successes", 0) > 0
            else 0
        )
        result[model] = {
            "requests": total,
            "successes": s.get("successes", 0),
            "failures": s.get("failures", 0),
            "avg_latency": round(avg_latency, 2),
            "healthy": is_model_healthy(model),
            "avg_input_tokens": (
                round(s["total_input_tokens"] / s["successes"])
                if s.get("successes", 0) > 0
                else 0
            ),
            "avg_output_tokens": (
                round(s["total_output_tokens"] / s["successes"])
                if s.get("successes", 0) > 0
                else 0
            ),
        }
    return result


def get_best_model_for_context(token_count):
    for model in FALLBACK_ORDER:
        info = MODEL_REGISTRY.get(model, {})
        if info.get("context", 0) > token_count and is_model_healthy(model):
            return model
    return FALLBACK_ORDER[0]
