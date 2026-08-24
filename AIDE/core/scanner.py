"""
core/scanner.py

Rekursiv katalogskanning. Går igenom hela katalogträdet under en eller
flera källmappar, klassificerar varje fil och samlar metadata.

Designmål (enligt beställningen):
- Aldrig anta att en katalog bara har filer på första nivån (avsnitt 2).
- Behålla relativ sökväg från källroten (avsnitt 4, 29).
- Ett enskilt filfel får inte krascha hela skanningen (avsnitt 27).
- Stöd för avbrott (avsnitt 21).
- Stöd för UTF-8 / internationella filnamn (avsnitt 28).
"""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Optional

from core.classifier import (
    CATEGORY_UNKNOWN,
    DEFAULT_IGNORE_DIRS,
    DEFAULT_IGNORE_FILES,
    classify_file,
)

# Hur många bytes som läses för binärheuristik på okända filtyper.
SNIFF_BYTES = 4096


@dataclass
class ScannedFile:
    absolute_path: str
    relative_path: str  # relativt vald källrot, alltid med "/" som separator
    source_root: str
    filename: str
    extension: str
    category: str
    language: Optional[str]
    size_bytes: int
    modified_at: Optional[datetime]
    is_sensitive: bool
    is_binary: bool
    is_hidden: bool
    readable: bool
    error: Optional[str] = None
    included: bool = False  # styrs av checkbox-läge i UI/settings

    @property
    def size_human(self) -> str:
        size = float(self.size_bytes)
        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024 or unit == "GB":
                return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} {unit}"
            size /= 1024
        return f"{size:.1f} GB"


@dataclass
class ScanResult:
    files: list[ScannedFile] = field(default_factory=list)
    errors: list[tuple[str, str]] = field(default_factory=list)  # (path, orsak)
    cancelled: bool = False
    total_discovered: int = 0


def _is_hidden(name: str) -> bool:
    return name.startswith(".")


def scan_sources(
    source_roots: list[str],
    ignore_dirs: set[str] | None = None,
    ignore_files: set[str] | None = None,
    sensitive_patterns: list[str] | None = None,
    show_hidden: bool = False,
    show_binary: bool = True,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    cancel_event: Optional[threading.Event] = None,
) -> ScanResult:
    """
    Skannar rekursivt en eller flera källkataloger.

    progress_callback(discovered_count, current_total_estimate, current_path)
    cancel_event: om satt, avbryts skanningen så snart som möjligt (avsnitt 21).
    """
    ignore_dirs = ignore_dirs if ignore_dirs is not None else set(DEFAULT_IGNORE_DIRS)
    ignore_files = ignore_files if ignore_files is not None else set(DEFAULT_IGNORE_FILES)

    result = ScanResult()
    discovered = 0

    for root_raw in source_roots:
        source_root = os.path.abspath(root_raw)
        if not os.path.isdir(source_root):
            result.errors.append((source_root, "Källmappen finns inte eller är inte en katalog"))
            continue

        for current_dir, dirnames, filenames in os.walk(source_root, topdown=True, onerror=None):
            if cancel_event is not None and cancel_event.is_set():
                result.cancelled = True
                return result

            # Filtrera bort ignorerade/dolda kataloger innan os.walk går vidare in i dem.
            kept_dirs = []
            for d in dirnames:
                if d in ignore_dirs:
                    continue
                if not show_hidden and _is_hidden(d):
                    continue
                kept_dirs.append(d)
            dirnames[:] = kept_dirs

            for filename in filenames:
                if cancel_event is not None and cancel_event.is_set():
                    result.cancelled = True
                    return result

                if filename in ignore_files:
                    continue

                absolute_path = os.path.join(current_dir, filename)
                rel = os.path.relpath(absolute_path, source_root)
                rel = rel.replace(os.sep, "/")

                try:
                    stat = os.stat(absolute_path)
                    size_bytes = stat.st_size
                    modified_at = datetime.fromtimestamp(stat.st_mtime)
                    readable = os.access(absolute_path, os.R_OK)
                    error = None

                    sample = b""
                    if readable and size_bytes > 0:
                        try:
                            with open(absolute_path, "rb") as fh:
                                sample = fh.read(SNIFF_BYTES)
                        except OSError as exc:
                            readable = False
                            error = str(exc)

                    classification = classify_file(
                        absolute_path, read_sample=sample, sensitive_patterns=sensitive_patterns
                    )

                    # Dolda filer döljs enligt inställning, MEN känsliga filer
                    # (t.ex. .env) ska alltid upptäckas och flaggas – att gömma
                    # dem helt vore i strid med avsnitt 19.
                    if _is_hidden(filename) and not show_hidden and not classification.is_sensitive:
                        continue

                    if classification.is_binary and not show_binary:
                        # Fortfarande upptäckt/loggad, men flaggas för att kunna
                        # filtreras bort i UI. Vi tar med den i listan ändå så
                        # att antal hittade filer stämmer; UI:t filtrerar visning.
                        pass

                    scanned = ScannedFile(
                        absolute_path=absolute_path,
                        relative_path=rel,
                        source_root=source_root,
                        filename=filename,
                        extension=os.path.splitext(filename)[1].lower(),
                        category=classification.category,
                        language=classification.language,
                        size_bytes=size_bytes,
                        modified_at=modified_at,
                        is_sensitive=classification.is_sensitive,
                        is_binary=classification.is_binary,
                        is_hidden=_is_hidden(filename),
                        readable=readable,
                        error=error,
                        included=False,
                    )

                except OSError as exc:
                    scanned = ScannedFile(
                        absolute_path=absolute_path,
                        relative_path=rel,
                        source_root=source_root,
                        filename=filename,
                        extension=os.path.splitext(filename)[1].lower(),
                        category=CATEGORY_UNKNOWN,
                        language=None,
                        size_bytes=0,
                        modified_at=None,
                        is_sensitive=False,
                        is_binary=False,
                        is_hidden=_is_hidden(filename),
                        readable=False,
                        error=str(exc),
                        included=False,
                    )
                    result.errors.append((absolute_path, str(exc)))

                result.files.append(scanned)
                discovered += 1

                if progress_callback is not None:
                    progress_callback(discovered, discovered, rel)

    result.total_discovered = discovered
    return result
