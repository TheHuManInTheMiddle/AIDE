"""
core/package_builder.py

Bygger det textbaserade projektpaketet (avsnitt 16-17) från en lista
av markerade ScannedFile. Innehåller ingen filsystemsskrivning —
det ansvaret ligger hos exporters/*, i linje med kravet att hålla
GUI, filanalys och export separerade (avsnitt 30).

SÄKERHETSPRINCIP: paketet får ALDRIG innehålla absoluta lokala
sökvägar (de kan avslöja användarnamn, mappstruktur eller annan lokal
information) eller information om filer utanför det valda källträdet.
Bara källmappens NAMN (basename) tas med — aldrig dess fullständiga
sökväg. Se avsnitt 29 i den ursprungliga specen.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from core.scanner import ScannedFile
from core.tree_renderer import build_ascii_tree

MAX_INLINE_BYTES = 2_000_000  # skydd mot att av misstag dumpa jättefiler som text


@dataclass
class FileReadOutcome:
    scanned_file: ScannedFile
    content: str | None
    skipped_reason: str | None = None


def _read_text_file(path: str) -> tuple[str | None, str | None]:
    """Läser en textfil defensivt. Returnerar (innehåll, felmeddelande)."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read(), None
    except OSError as exc:
        return None, str(exc)


def build_package_text(
    project_name: str,
    source_roots: list[str],
    included_files: list[ScannedFile],
    log_callback=None,
) -> str:
    """
    Bygger hela paketets textinnehåll enligt formatet i avsnitt 16.

    OBS: source_roots skickas in för bakåtkompatibilitet men endast
    respektive mappnamn (basename) skrivs ut — aldrig den fullständiga
    lokala sökvägen. Se säkerhetsprincipen i modulens docstring.
    """
    lines: list[str] = []
    lines.append("AIDE PROJECT PACKAGE")
    lines.append("=" * 20)
    lines.append("")
    lines.append("PROJECT:")
    lines.append(project_name)
    lines.append("")
    lines.append("SOURCE FOLDER(S):")
    for root in source_roots:
        lines.append(os.path.basename(str(root).rstrip("/\\")) or str(root))
    lines.append("")
    lines.append("FILES:")
    lines.append(str(len(included_files)))
    lines.append("")
    lines.append("STRUCTURE:")
    lines.append("")
    lines.append(build_ascii_tree(project_name, included_files))
    lines.append("")

    for f in included_files:
        lines.append("=" * 50)
        lines.append(f"FILE: {f.relative_path}")
        lines.append(f"TYPE: {f.category}")
        lines.append("=" * 50)
        lines.append("")

        if f.is_binary:
            lines.append("[BINARY - innehåll ej inkluderat]")
            lines.append("")
            continue

        if not f.readable:
            lines.append(f"⚠ Kunde inte läsa filen. Orsak: {f.error or 'okänd'}")
            lines.append("")
            if log_callback:
                log_callback(f"Kunde inte läsa: {f.relative_path} ({f.error})")
            continue

        if f.size_bytes > MAX_INLINE_BYTES:
            lines.append(
                f"[FIL FÖR STOR FÖR INLINE-INKLUDERING: {f.size_human}, hoppas över]"
            )
            lines.append("")
            if log_callback:
                log_callback(f"Hoppade över (för stor): {f.relative_path}")
            continue

        content, error = _read_text_file(f.absolute_path)
        if error is not None:
            lines.append(f"⚠ Kunde inte läsa filen. Orsak: {error}")
            lines.append("")
            if log_callback:
                log_callback(f"Kunde inte läsa: {f.relative_path} ({error})")
            continue

        fence_lang = f.language or ""
        lines.append(f"```{fence_lang}")
        lines.append(content if content is not None else "")
        if content is not None and not content.endswith("\n"):
            lines.append("")
        lines.append("```")
        lines.append("")

    return "\n".join(lines)
