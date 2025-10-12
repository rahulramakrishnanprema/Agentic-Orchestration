"""
Prompt Loader - Loads and formats prompt templates from Markdown files.
"""
import re
from pathlib import Path
from typing import Any, Dict

class PromptLoader:
    """Loads and formats prompt templates from Markdown files."""

    def __init__(self, prompts_dir: str = "prompts"):
        self.prompts_dir = Path(prompts_dir)
        self._cache: Dict[str, str] = {}

    def load(self, name: str) -> str:
        if name not in self._cache:
            path = self.prompts_dir / f"{name}.md"
            if not path.exists():
                raise FileNotFoundError(f"Prompt file not found: {path}")
            self._cache[name] = path.read_text(encoding="utf-8")
        return self._cache[name]

    def format(self, name: str, **vars: Any) -> str:
        template = self.load(name)
        for k, v in vars.items():
            template = template.replace(f"{{{{{k}}}}}", str(v))
        return template