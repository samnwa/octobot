from pathlib import Path


class SkillsManager:
    def __init__(self):
        self.skills = []
        self.load_skills()

    def load_skills(self):
        skill_dirs = [
            Path.home() / ".octobot" / "skills",
            Path.cwd() / "skills",
        ]

        for base_dir in skill_dirs:
            if not base_dir.is_dir():
                continue
            for entry in sorted(base_dir.iterdir()):
                if not entry.is_dir():
                    continue
                skill_file = entry / "SKILL.md"
                if not skill_file.is_file():
                    continue
                content = skill_file.read_text(encoding="utf-8")
                name, description = self._parse_frontmatter(content)
                if not name:
                    name = entry.name
                self.skills.append({
                    "name": name,
                    "description": description or "",
                    "path": str(skill_file),
                    "content": content,
                })

    def _parse_frontmatter(self, text):
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

    def get_skills_metadata(self):
        return [{"name": s["name"], "description": s["description"]} for s in self.skills]

    def get_skills_context(self):
        if not self.skills:
            return ""
        sections = ["## Available Skills\n"]
        for skill in self.skills:
            sections.append(skill["content"])
        return "\n".join(sections)
