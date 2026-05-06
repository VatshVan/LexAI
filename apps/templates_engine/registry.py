import json
from pathlib import Path

TEMPLATES_DIR = Path(__file__).parent / "templates"

class TemplateRegistry:
    _cache: dict = {}

    def __new__(cls):
        if not cls._cache:
            for f in TEMPLATES_DIR.glob("*.json"):
                t = json.loads(f.read_text())
                cls._cache[t["template_name"]] = t
        return super().__new__(cls)

    def get_template(self, name: str) -> dict:
        if name not in self._cache:
            raise KeyError(f"Template '{name}' not found")
        return self._cache[name]

    def list_templates(self) -> list[dict]:
        return [
            {"template_name": t["template_name"],
             "display_name": t["display_name"],
             "version": t["version"],
             "field_count": len(t["fields"]),
             "required_field_count": sum(1 for f in t["fields"] if f["required"])}
            for t in self._cache.values()
        ]
