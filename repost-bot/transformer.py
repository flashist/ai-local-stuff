"""
Apply per-platform text substitutions defined in mentions.json.
"""
import json
from pathlib import Path

_MENTIONS_FILE = Path(__file__).parent / "mentions.json"

_PLATFORMS = ("vk", "instagram")


def _load_rules() -> list[dict]:
    with open(_MENTIONS_FILE, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("substitutions", [])


def transform(text: str, platform: str) -> str:
    """Return text with all substitution rules applied for the given platform."""
    if platform not in _PLATFORMS:
        raise ValueError(f"Unknown platform {platform!r}. Expected one of {_PLATFORMS}")

    rules = _load_rules()
    for rule in rules:
        match = rule.get("match", "")
        if match and platform in rule and match in text:
            text = text.replace(match, rule[platform])

    return text
