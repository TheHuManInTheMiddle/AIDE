"""
core/settings.py

Läser och sparar AIDE:s inställningar lokalt (avsnitt 23).
Ingen nätverkskommunikation. Inställningar sparas som JSON i en
plattformslämplig konfigurationskatalog.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field

from core.classifier import DEFAULT_IGNORE_DIRS, DEFAULT_IGNORE_FILES, DEFAULT_SENSITIVE_PATTERNS


def _default_config_dir() -> str:
    if os.name == "nt":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
        return os.path.join(base, "AIDE")
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = xdg if xdg else os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, "aide")


CONFIG_DIR = _default_config_dir()
CONFIG_FILE = os.path.join(CONFIG_DIR, "settings.json")


@dataclass
class Settings:
    ignore_dirs: list = field(default_factory=lambda: sorted(DEFAULT_IGNORE_DIRS))
    ignore_files: list = field(default_factory=lambda: sorted(DEFAULT_IGNORE_FILES))
    sensitive_patterns: list = field(default_factory=lambda: list(DEFAULT_SENSITIVE_PATTERNS))
    default_export_format: str = "markdown"  # markdown | text | json
    default_export_dir: str = ""
    show_binary_files: bool = True
    show_hidden_files: bool = False
    default_checkbox_state: bool = True  # True = markera icke-känsliga filer som standard

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> "Settings":
        defaults = Settings()
        merged = defaults.to_dict()
        merged.update({k: v for k, v in data.items() if k in merged})
        return Settings(**merged)


def load_settings(path: str = CONFIG_FILE) -> Settings:
    if not os.path.isfile(path):
        return Settings()
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return Settings.from_dict(data)
    except (OSError, json.JSONDecodeError):
        # Trasiga inställningar ska aldrig krascha appen; fall tillbaka på default.
        return Settings()


def save_settings(settings: Settings, path: str = CONFIG_FILE) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(settings.to_dict(), fh, ensure_ascii=False, indent=2)
