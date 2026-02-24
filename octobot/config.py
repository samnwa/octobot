import os
import json
from pathlib import Path


DEFAULT_MODEL = "hf:zai-org/GLM-4.7"
SYNTHETIC_BASE_URL = "https://api.synthetic.new/anthropic"
MAX_TOKENS = 16384
MAX_TURNS = 50
SUBAGENT_MAX_TURNS = 15

CONFIG_DIR = Path.home() / ".octobot"
CONFIG_FILE = CONFIG_DIR / "config.json"


def get_api_key():
    key = os.environ.get("SYNTHETIC_API_KEY")
    if not key:
        config = load_config()
        key = config.get("synthetic_api_key")
    if not key:
        raise ValueError(
            "SYNTHETIC_API_KEY not found. Set it as an environment variable "
            "or in ~/.octobot/config.json"
        )
    return key


def load_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {}


def save_config(config):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def get_model(override=None):
    if override:
        return override
    config = load_config()
    return config.get("model", DEFAULT_MODEL)
