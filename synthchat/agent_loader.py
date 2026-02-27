import os
import re
import yaml
from pathlib import Path

from synthchat.agents import AGENTS

CUSTOM_AGENTS_DIR = os.path.expanduser("~/.octobot/agents")
COMMUNITY_AGENTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "community", "agents")
SKILLS_DIRS = [
    Path.home() / ".octobot" / "skills",
    Path.cwd() / "skills",
]

REQUIRED_FIELDS = {"name", "role", "avatar", "color", "description", "system"}
VALID_TOOLS = {
    "read_file", "write_file", "edit_file", "run_command", "list_files",
    "search_files", "tree", "file_info", "apply_patch", "create_document",
    "web_search", "web_fetch", "schedule_task", "list_schedules", "cancel_schedule",
}


def _ensure_dir():
    os.makedirs(CUSTOM_AGENTS_DIR, exist_ok=True)


def _slugify(name):
    slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
    return slug or "agent"


def _validate_agent_id(agent_id):
    if not agent_id or not re.match(r'^[a-z0-9][a-z0-9\-]*$', agent_id):
        raise ValueError(f"Invalid agent ID: '{agent_id}'")
    if '..' in agent_id or '/' in agent_id or '\\' in agent_id:
        raise ValueError(f"Invalid agent ID: '{agent_id}'")


def load_custom_agents():
    _ensure_dir()
    agents = {}
    for fname in os.listdir(CUSTOM_AGENTS_DIR):
        if not fname.endswith((".yaml", ".yml")):
            continue
        path = os.path.join(CUSTOM_AGENTS_DIR, fname)
        try:
            with open(path, "r") as f:
                config = yaml.safe_load(f)
            if not isinstance(config, dict):
                continue
            if not REQUIRED_FIELDS.issubset(config.keys()):
                continue
            agent_id = os.path.splitext(fname)[0]
            agents[agent_id] = {
                "id": agent_id,
                "name": config["name"],
                "role": config["role"],
                "avatar": config.get("avatar", "🤖"),
                "color": config.get("color", "#6b7280"),
                "description": config.get("description", ""),
                "tools": [t for t in config.get("tools", []) if t in VALID_TOOLS],
                "skills": config.get("skills", []),
                "system": config["system"],
                "is_custom": True,
                "is_builtin": False,
            }
        except (yaml.YAMLError, IOError, OSError):
            continue
    return agents


def save_custom_agent(config):
    _ensure_dir()
    agent_id = config.get("id") or _slugify(config["name"])
    _validate_agent_id(agent_id)

    if agent_id in AGENTS:
        raise ValueError(f"Cannot overwrite built-in agent '{agent_id}'")

    existing = [f[:-5] for f in os.listdir(CUSTOM_AGENTS_DIR) if f.endswith(".yaml")]
    if agent_id not in existing:
        base = agent_id
        counter = 1
        while agent_id in existing or agent_id in AGENTS:
            agent_id = f"{base}-{counter}"
            counter += 1

    yaml_data = {
        "name": config["name"],
        "role": config["role"],
        "avatar": config.get("avatar", "🤖"),
        "color": config.get("color", "#6b7280"),
        "description": config.get("description", ""),
        "tools": config.get("tools", []),
        "skills": config.get("skills", []),
        "system": config["system"],
    }

    path = os.path.join(CUSTOM_AGENTS_DIR, f"{agent_id}.yaml")
    with open(path, "w") as f:
        yaml.dump(yaml_data, f, default_flow_style=False, allow_unicode=True)

    return agent_id


def delete_custom_agent(agent_id):
    _validate_agent_id(agent_id)
    if agent_id in AGENTS:
        raise ValueError(f"Cannot delete built-in agent '{agent_id}'")

    path = os.path.join(CUSTOM_AGENTS_DIR, f"{agent_id}.yaml")
    if os.path.exists(path):
        os.remove(path)
        return True
    return False


def get_all_agents():
    all_agents = {}

    for aid, agent in AGENTS.items():
        all_agents[aid] = {**agent, "is_builtin": True, "is_custom": False}

    custom = load_custom_agents()
    for aid, agent in custom.items():
        if aid not in all_agents:
            all_agents[aid] = agent

    return all_agents


def load_community_agents():
    if not os.path.isdir(COMMUNITY_AGENTS_DIR):
        return {}
    agents = {}
    for fname in os.listdir(COMMUNITY_AGENTS_DIR):
        if not fname.endswith((".yaml", ".yml")):
            continue
        path = os.path.join(COMMUNITY_AGENTS_DIR, fname)
        try:
            with open(path, "r") as f:
                config = yaml.safe_load(f)
            if not isinstance(config, dict):
                continue
            if not REQUIRED_FIELDS.issubset(config.keys()):
                continue
            agent_id = os.path.splitext(fname)[0]
            agents[agent_id] = {
                "id": agent_id,
                "name": config["name"],
                "role": config["role"],
                "avatar": config.get("avatar", "🤖"),
                "color": config.get("color", "#6b7280"),
                "description": config.get("description", ""),
                "tools": [t for t in config.get("tools", []) if t in VALID_TOOLS],
                "skills": config.get("skills", []),
                "system": config["system"],
            }
        except (yaml.YAMLError, IOError, OSError):
            continue
    return agents


def install_community_agent(agent_id):
    _validate_agent_id(agent_id)
    community = load_community_agents()
    if agent_id not in community:
        raise ValueError(f"Community agent '{agent_id}' not found")
    if agent_id in AGENTS:
        raise ValueError(f"Cannot overwrite built-in agent '{agent_id}'")
    agent = community[agent_id]
    config = {
        "id": agent_id,
        "name": agent["name"],
        "role": agent["role"],
        "avatar": agent["avatar"],
        "color": agent["color"],
        "description": agent["description"],
        "tools": agent["tools"],
        "skills": agent["skills"],
        "system": agent["system"],
    }
    return save_custom_agent(config)


def publish_agent_to_community(agent_id):
    _validate_agent_id(agent_id)
    custom = load_custom_agents()
    if agent_id not in custom:
        raise ValueError(f"Custom agent '{agent_id}' not found")
    agent = custom[agent_id]
    os.makedirs(COMMUNITY_AGENTS_DIR, exist_ok=True)
    yaml_data = {
        "name": agent["name"],
        "role": agent["role"],
        "avatar": agent["avatar"],
        "color": agent["color"],
        "description": agent["description"],
        "tools": agent["tools"],
        "skills": agent["skills"],
        "system": agent["system"],
    }
    path = os.path.join(COMMUNITY_AGENTS_DIR, f"{agent_id}.yaml")
    with open(path, "w") as f:
        yaml.dump(yaml_data, f, default_flow_style=False, allow_unicode=True)
    return agent_id


def is_agent_installed(agent_id):
    _ensure_dir()
    path = os.path.join(CUSTOM_AGENTS_DIR, f"{agent_id}.yaml")
    return os.path.exists(path)


def is_agent_published(agent_id):
    if not os.path.isdir(COMMUNITY_AGENTS_DIR):
        return False
    path = os.path.join(COMMUNITY_AGENTS_DIR, f"{agent_id}.yaml")
    return os.path.exists(path)


def _parse_skill_frontmatter(text):
    name = ""
    description = ""
    parts = text.split("---", 2)
    if len(parts) < 3:
        return name, description
    frontmatter = parts[1].strip()
    for line in frontmatter.splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip().lower()
            value = value.strip()
            if key == "name":
                name = value
            elif key == "description":
                description = value
    return name, description


def load_skill(name):
    for base_dir in SKILLS_DIRS:
        skill_file = base_dir / name / "SKILL.md"
        if skill_file.is_file():
            return skill_file.read_text(encoding="utf-8")
    return None


def list_available_skills():
    skills = []
    seen = set()
    for base_dir in SKILLS_DIRS:
        if not base_dir.is_dir():
            continue
        for entry in sorted(base_dir.iterdir()):
            if not entry.is_dir():
                continue
            skill_file = entry / "SKILL.md"
            if not skill_file.is_file():
                continue
            skill_name = entry.name
            if skill_name in seen:
                continue
            seen.add(skill_name)
            content = skill_file.read_text(encoding="utf-8")
            parsed_name, description = _parse_skill_frontmatter(content)
            skills.append({
                "name": skill_name,
                "display_name": parsed_name or skill_name,
                "description": description or "",
            })
    return skills
