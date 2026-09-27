"""
core/manifest.py

Bygger JSON-metadata (project_manifest.json) för ett exportpaket,
enligt avsnitt 17-18. Inga hemligheter eller filinnehåll inkluderas
i manifestet — bara metadata.

SÄKERHETSPRINCIP: precis som package_builder.py skriver manifestet
aldrig ut fullständiga lokala sökvägar för källmapparna, bara deras
mappnamn (basename). Se avsnitt 29.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

from core.scanner import ScannedFile


def build_manifest(
    project_name: str,
    source_roots: list[str],
    included_files: list[ScannedFile],
    include_absolute_paths: bool = False,
) -> dict:
    manifest = {
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
                "modified_at": f.modified_at.isoformat() if f.modified_at else None,
                "sensitive": f.is_sensitive,
                "binary": f.is_binary,
            }
            for f in included_files
        ],
    }

    if include_absolute_paths:
        # ENDAST för AIDE Box/scan/ — internt maskin-till-maskin-kontrakt
        # mellan AIDE och GameBridge på samma dator. Får ALDRIG sättas till
        # True för paket som kan lämna datorn (md/text/tree, eller json
        # explicit delat externt). Standardvärdet False håller den
        # befintliga säkerhetsgarantin oförändrad för alla andra anrop.
        manifest["source_folders_absolute"] = [
            os.path.abspath(str(s)) for s in source_roots
        ]

    return manifest
