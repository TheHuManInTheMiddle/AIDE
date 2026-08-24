"""
core/security.py

Säkerhetsprinciper (avsnitt 13):
- AIDE får aldrig radera eller skriva över originalfiler automatiskt.
- Export sker alltid till en explicit vald målplats.
- Om målfilen redan finns måste en konfliktstrategi väljas explicit.

Denna modul innehåller inga GUI-beroenden, bara ren logik, så att den
kan testas isolerat och återanvändas av alla exporters.
"""

from __future__ import annotations

import os
import re
from enum import Enum


class ConflictStrategy(Enum):
    OVERWRITE = "overwrite"
    NEW_VERSION = "new_version"
    SKIP = "skip"


class ExportBlocked(Exception):
    """Höjs om en export skulle innebära en oavsiktlig destruktiv operation."""


def resolve_target_path(target_path: str, strategy: ConflictStrategy) -> str | None:
    """
    Givet en önskad målsökväg, returnera den faktiska sökväg som ska
    skrivas till, enligt vald konfliktstrategi.

    Returnerar None om filen ska hoppas över (SKIP).
    """
    if not os.path.exists(target_path):
        return target_path

    if strategy == ConflictStrategy.SKIP:
        return None

    if strategy == ConflictStrategy.OVERWRITE:
        return target_path

    if strategy == ConflictStrategy.NEW_VERSION:
        base, ext = os.path.splitext(target_path)
        counter = 1
        candidate = f"{base} ({counter}){ext}"
        while os.path.exists(candidate):
            counter += 1
            candidate = f"{base} ({counter}){ext}"
        return candidate

    raise ValueError(f"Okänd konfliktstrategi: {strategy}")


def ensure_within_export_dir(export_dir: str, filename: str) -> str:
    """
    Bygger en säker målsökväg inom exportmappen och skyddar mot att
    filnamn (t.ex. via manipulerad relativ sökväg) hamnar utanför den
    valda exportkatalogen.
    """
    export_dir_abs = os.path.abspath(export_dir)
    candidate = os.path.abspath(os.path.join(export_dir_abs, filename))
    if os.path.commonpath([export_dir_abs, candidate]) != export_dir_abs:
        raise ExportBlocked(f"Målsökväg hamnar utanför exportmappen: {filename}")
    return candidate


_INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def sanitize_filename(name: str, fallback: str = "AIDE_Project") -> str:
    """
    Gör om ett godtyckligt namn (t.ex. en källmapps basename) till ett
    filnamn som är säkert på Windows/macOS/Linux: inga sökvägsseparatorer
    eller andra tecken som är ogiltiga i filnamn, ingen ledande/avslutande
    whitespace eller punkt, och aldrig tomt.
    """
    cleaned = _INVALID_FILENAME_CHARS.sub("_", str(name)).strip().strip(".")
    cleaned = cleaned.strip()
    return cleaned or fallback
