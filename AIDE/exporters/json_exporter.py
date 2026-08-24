"""
exporters/json_exporter.py

Skriver JSON-manifestet (project_manifest.json) till vald exportmapp.
Ingen filinnehåll skrivs — bara metadata (avsnitt 17-18).
"""

from __future__ import annotations

import json
import os

from core.manifest import build_manifest
from core.scanner import ScannedFile
from core.security import ConflictStrategy, ensure_within_export_dir, resolve_target_path


def export_json_manifest(
    project_name: str,
    source_roots: list[str],
    included_files: list[ScannedFile],
    export_dir: str,
    filename: str = "project_manifest.json",
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

    manifest = build_manifest(project_name, source_roots, included_files)
    with open(resolved, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)

    if log_callback:
        log_callback(f"JSON-manifest skapat: {resolved}")
    return resolved
