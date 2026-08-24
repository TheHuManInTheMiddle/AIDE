"""
exporters/tree_exporter.py

Exporterar ENBART en ASCII-trädrepresentation av de markerade filerna
— inget filinnehåll. Bra för att snabbt dokumentera eller kommunicera
ett projekts struktur utan att dumpa kod, t.ex. för att klistra in i
en chatt eller en PR-beskrivning.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

from core.scanner import ScannedFile
from core.security import ConflictStrategy, ensure_within_export_dir, resolve_target_path
from core.tree_renderer import build_ascii_tree


def export_tree(
    project_name: str,
    source_roots: list[str],
    included_files: list[ScannedFile],
    export_dir: str,
    filename: str = "project_tree.md",
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

    tree_text = build_ascii_tree(project_name, included_files)

    total_size = sum(f.size_bytes for f in included_files)
    by_category: dict[str, int] = {}
    for f in included_files:
        by_category[f.category] = by_category.get(f.category, 0) + 1
    category_summary = ", ".join(f"{cat}: {count}" for cat, count in sorted(by_category.items()))

    lines = [
        "```text",
        tree_text,
        "```",
        "",
        f"Filer: {len(included_files)}",
        f"Kategorier: {category_summary or '–'}",
        f"Genererat av AIDE: {datetime.now(timezone.utc).isoformat()}",
    ]

    with open(resolved, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))

    if log_callback:
        log_callback(f"Filträd skapat: {resolved}")
    return resolved
