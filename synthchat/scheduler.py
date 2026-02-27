import json
import os
import uuid
from datetime import datetime


SCHEDULES_PATH = os.path.expanduser("~/.octobot/schedules.json")


class ScheduleStore:
    def __init__(self):
        self._ensure_dir()
        self._schedules = self._load()

    def _ensure_dir(self):
        os.makedirs(os.path.dirname(SCHEDULES_PATH), exist_ok=True)

    def _load(self):
        if os.path.exists(SCHEDULES_PATH):
            with open(SCHEDULES_PATH, "r") as f:
                return json.load(f)
        return []

    def _save(self):
        self._ensure_dir()
        with open(SCHEDULES_PATH, "w") as f:
            json.dump(self._schedules, f, indent=2)

    def add(self, name, description, frequency, action, channel_id):
        schedule = {
            "id": str(uuid.uuid4()),
            "name": name,
            "description": description,
            "frequency": frequency,
            "action": action,
            "channel_id": channel_id,
            "created_at": datetime.now().isoformat(),
            "enabled": True,
        }
        self._schedules.append(schedule)
        self._save()
        return schedule

    def list(self, channel_id=None):
        active = [s for s in self._schedules if s.get("enabled", True)]
        if channel_id:
            active = [s for s in active if s.get("channel_id") == channel_id]
        return active

    def cancel(self, schedule_id):
        for s in self._schedules:
            if s["id"] == schedule_id:
                s["enabled"] = False
                self._save()
                return True
        return False

    def get_all(self):
        return list(self._schedules)


SCHEDULER_TOOL_DEFINITIONS = [
    {
        "name": "schedule_task",
        "description": "Create a new scheduled or recurring task. Use this to set up reminders, recurring actions, or one-time future tasks.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Short name for the scheduled task",
                },
                "description": {
                    "type": "string",
                    "description": "Detailed description of what this schedule does",
                },
                "frequency": {
                    "type": "string",
                    "enum": ["once", "daily", "weekly", "monthly"],
                    "description": "How often the task should run",
                },
                "action": {
                    "type": "string",
                    "description": "The action to perform when the schedule triggers",
                },
            },
            "required": ["name", "frequency", "action"],
        },
    },
    {
        "name": "list_schedules",
        "description": "List all active scheduled tasks for the current channel.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "cancel_schedule",
        "description": "Cancel an existing scheduled task by its ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "schedule_id": {
                    "type": "string",
                    "description": "The unique ID of the schedule to cancel",
                },
            },
            "required": ["schedule_id"],
        },
    },
]

_store = None


def _get_store():
    global _store
    if _store is None:
        _store = ScheduleStore()
    return _store


def execute_scheduler_tool(tool_name, tool_input, channel_id):
    store = _get_store()

    if tool_name == "schedule_task":
        schedule = store.add(
            name=tool_input["name"],
            description=tool_input.get("description", ""),
            frequency=tool_input["frequency"],
            action=tool_input["action"],
            channel_id=channel_id,
        )
        return json.dumps({
            "status": "created",
            "schedule": schedule,
        })

    elif tool_name == "list_schedules":
        schedules = store.list(channel_id=channel_id)
        return json.dumps({
            "status": "ok",
            "schedules": schedules,
            "count": len(schedules),
        })

    elif tool_name == "cancel_schedule":
        success = store.cancel(tool_input["schedule_id"])
        if success:
            return json.dumps({"status": "cancelled", "schedule_id": tool_input["schedule_id"]})
        else:
            return json.dumps({"status": "error", "message": f"Schedule '{tool_input['schedule_id']}' not found"})

    return json.dumps({"status": "error", "message": f"Unknown scheduler tool: {tool_name}"})
