# -*- coding: utf-8 -*-
"""
plugins/zip_export/main_plugin.py

ZIP-backup-export för AIDE.

Zippar de markerade filerna rakt av (binärt kopierade, inte textdumpade)
med bevarad relativ mappstruktur, plus ett medföljande JSON-manifest
(samma fält som AIDE:s vanliga manifest) inbakat i arkivet under namnet
"_manifest.json" — så att GameBridge/AI senare snabbt kan jämföra
arkivens innehåll utan att packa upp dem.

Följer AIDEPlugin-kontraktet i docs/PLUGIN_GUIDE.md:
- Skriver aldrig utanför export_dir (ensure_within_export_dir).
- Respekterar conflict_strategy (resolve_target_path).
- Kraschar aldrig tyst — fel loggas via log_callback och funktionen
  returnerar None istället för att låta ett undantag brisera ut.
"""

from __future__ import annotations

import json
import os
import zipfile
from datetime import datetime, timezone

from core.plugin_base import AIDEPlugin, PluginFileInfo
from core.security import ensure_within_export_dir, resolve_target_path, sanitize_filename


def _build_manifest(project_name, source_roots, included_files):
    """
    Samma manifestform som core/manifest.py, men byggd från
    PluginFileInfo (pluginets skrivskyddade, stabila vy) istället för
    core.scanner.ScannedFile.

    PluginFileInfo saknar modified_at (den finns bara på ScannedFile
    internt i AIDE), så fältet utelämnas här snarare än att gissa.
    """
    return {
        "project": project_name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "files": len(included_files),
        "source_folders": [
            os.path.basename(str(s).rstrip("/\\")) or str(s) for s in source_roots
        ],
        "included_files": [
            {
                "path": f.relative_path,
                "filename": f.filename,
                "extension": f.extension,
                "category": f.category,
                "size_bytes": f.size_bytes,
                "sensitive": f.is_sensitive,
                "binary": f.is_binary,
            }
            for f in included_files
        ],
    }


def export_zip(
    project_name: str,
    source_roots: list[str],
    included_files: list[PluginFileInfo],
    export_dir: str,
    conflict_strategy,
    log_callback,
) -> str | None:
    """
    Zippar de markerade filerna (riktiga filkopior, bevarad mappstruktur)
    plus ett manifest ("_manifest.json") in i samma arkiv.

    Returnerar skriven sökväg, eller None om exporten hoppades över
    (t.ex. SKIP-konflikt) eller misslyckades.
    """
    os.makedirs(export_dir, exist_ok=True)

    # Standardmapp: zip-backuper hamnar i en egen "zip"-undermapp under
    # vald exportmapp, så man slipar leta/bläddra dit manuellt varje
    # gång — och om man glömmer välja alls hamnar de ändå på ett
    # förutsägbart ställe. Om man redan STÅR i en mapp som heter "zip"
    # (t.ex. valde "AIDE Box/zip" direkt), lägger vi INTE till ännu en
    # "zip"-nivå ovanpå — det gav tidigare en "zip/zip"-dubblering.
    already_in_subfolder = (
        os.path.basename(os.path.normpath(str(export_dir))).lower() == "zip"
    )
    safe_name = sanitize_filename(project_name)
    rel_target = f"{safe_name}.zip"
    if not already_in_subfolder:
        rel_target = os.path.join("zip", rel_target)
    target = ensure_within_export_dir(export_dir, rel_target)
    resolved = resolve_target_path(target, conflict_strategy)
    if resolved is None:
        log_callback(f"Hoppade över befintlig fil: {target}")
        return None

    os.makedirs(os.path.dirname(resolved), exist_ok=True)

    try:
        with zipfile.ZipFile(resolved, "w", zipfile.ZIP_DEFLATED) as zf:
            written = 0
            for f in included_files:
                try:
                    zf.write(f.absolute_path, arcname=f.relative_path)
                    written += 1
                except OSError as exc:
                    log_callback(
                        f"⚠ Kunde inte lägga till i zip: {f.relative_path} ({exc})"
                    )

            manifest = _build_manifest(project_name, source_roots, included_files)
            zf.writestr(
                "_manifest.json",
                json.dumps(manifest, ensure_ascii=False, indent=2),
            )

    except OSError as exc:
        log_callback(f"⚠ Kunde inte skapa zip-arkivet: {exc}")
        return None

    log_callback(f"ZIP-backup skapad: {resolved} ({written}/{len(included_files)} filer)")
    return resolved


class ZipExportPlugin(AIDEPlugin):

    @property
    def plugin_name(self) -> str:
        return "AIDE ZIP Backup"

    @property
    def plugin_version(self) -> str:
        return "1.0.0"

    def initialize(self) -> None:
        print(f"[{self.plugin_name}] Initialiserad.")

    def get_exporters(self):
        return {"zip": export_zip}
