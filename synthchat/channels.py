import os
import json
import re
import time

from synthchat.agents import AGENTS, AGENT_ORDER

CHANNELS_DIR = os.path.expanduser("~/.octobot/synthchat")
CHANNELS_FILE = os.path.join(CHANNELS_DIR, "channels.json")

CORE_AGENT_IDS = {"otto", "recap"}


def _slugify(name):
    slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
    return slug or "channel"


def _ensure_dir():
    os.makedirs(CHANNELS_DIR, exist_ok=True)


def _default_workspace():
    return {
        "id": "workspace",
        "name": "Workspace",
        "description": "Default workspace with all agents",
        "agent_ids": list(AGENT_ORDER),
        "created_at": time.time(),
    }


class ChannelStore:
    def __init__(self):
        _ensure_dir()
        self._channels = self._load()

    def _load(self):
        if os.path.exists(CHANNELS_FILE):
            try:
                with open(CHANNELS_FILE, "r") as f:
                    data = json.load(f)
                if not any(ch["id"] == "workspace" for ch in data):
                    data.insert(0, _default_workspace())
                    self._save_data(data)
                return data
            except (json.JSONDecodeError, IOError):
                pass
        data = [_default_workspace()]
        self._save_data(data)
        return data

    def _save(self):
        self._save_data(self._channels)

    def _save_data(self, data):
        _ensure_dir()
        with open(CHANNELS_FILE, "w") as f:
            json.dump(data, f, indent=2)

    def _enforce_core_agents(self, agent_ids):
        ids = list(agent_ids)
        for core in CORE_AGENT_IDS:
            if core not in ids:
                ids.append(core)
        valid = [aid for aid in ids if aid in AGENTS]
        ordered = [aid for aid in AGENT_ORDER if aid in valid]
        for aid in valid:
            if aid not in ordered:
                ordered.append(aid)
        return ordered

    def create(self, name, description="", agent_ids=None):
        if agent_ids is None:
            agent_ids = list(AGENT_ORDER)
        agent_ids = self._enforce_core_agents(agent_ids)

        slug = _slugify(name)
        existing_ids = {ch["id"] for ch in self._channels}
        base_slug = slug
        counter = 1
        while slug in existing_ids:
            slug = f"{base_slug}-{counter}"
            counter += 1

        channel = {
            "id": slug,
            "name": name,
            "description": description,
            "agent_ids": agent_ids,
            "created_at": time.time(),
        }
        self._channels.append(channel)
        self._save()
        return channel

    def list(self):
        return list(self._channels)

    def get(self, channel_id):
        for ch in self._channels:
            if ch["id"] == channel_id:
                return ch
        return None

    def delete(self, channel_id):
        if channel_id == "workspace":
            return False
        before = len(self._channels)
        self._channels = [ch for ch in self._channels if ch["id"] != channel_id]
        if len(self._channels) < before:
            self._save()
            return True
        return False

    def update_agents(self, channel_id, agent_ids):
        agent_ids = self._enforce_core_agents(agent_ids)
        for ch in self._channels:
            if ch["id"] == channel_id:
                ch["agent_ids"] = agent_ids
                self._save()
                return ch
        return None
