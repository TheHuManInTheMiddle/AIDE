"""
exporters/text_exporter.py

Skriver projektpaketet som en ren .txt-fil till vald exportmapp.
Innehållet är samma struktur som Markdown-exporten (den är redan
läsbar som ren text), men sparas med .txt-ändelse.
"""

from __future__ import annotations

import os

from core.package_builder import build_package_text
from core.scanner import ScannedFile
from core.security import ConflictStrategy, ensure_within_export_dir, resolve_target_path


def export_text(
    project_name: str,
    source_roots: list[str],
    included_files: list[ScannedFile],
    export_dir: str,
    filename: str = "project_package.txt",
    conflict_strategy: ConflictStrategy = ConflictStrategy.NEW_VERSION,
    log_callback=None,
) -> str | None:
    os.makedirs(export_dir, exist_ok=True)
    target = ensure_within_export_dir(export_dir, filename)
    resolved = resolve_target_path(target, conflict_strategy)
    if resolved is None:
        if log_callback:
            log_callback(f"Hoppade över befintlig fil: {target}")
        return None

    text = build_package_text(project_name, source_roots, included_files, log_callback=log_callback)
    with open(resolved, "w", encoding="utf-8") as fh:
        fh.write(text)

    if log_callback:
        log_callback(f"Textpaket skapat: {resolved}")
    return resolved
