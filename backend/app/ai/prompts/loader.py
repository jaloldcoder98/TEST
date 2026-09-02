from functools import lru_cache
from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent


@lru_cache
def load_prompt(name: str) -> str:
    """Prompts live as plain .txt files, not inline strings in service code (spec.md §61), so
    they can be reviewed/edited without touching Python."""
    return (_PROMPTS_DIR / f"{name}.txt").read_text(encoding="utf-8").strip()
