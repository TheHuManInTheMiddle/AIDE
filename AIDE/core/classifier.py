"""
core/classifier.py

Klassificerar filer i kategorier (Kod, Text, Konfiguration, Webb, Dokument,
Bild, Binär/Okänd) och flaggar potentiellt känsliga filer.

Modulen är medvetet datadriven (dict-baserad) så att listorna kan utökas
utan att ändra logiken, i linje med kravet i beställningen (avsnitt 6:
"Textformat ska inte begränsas till en liten hårdkodad lista.").
"""

from __future__ import annotations

import fnmatch
import os
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Kategoridefinitioner
# ---------------------------------------------------------------------------

CATEGORY_CODE = "Kod"
CATEGORY_TEXT = "Text"
CATEGORY_CONFIG = "Konfiguration/Data"
CATEGORY_WEB = "Webb"
CATEGORY_DOCUMENT = "Dokument"
CATEGORY_IMAGE = "Bild"
CATEGORY_BINARY = "Binär"
CATEGORY_UNKNOWN = "Okänd"

# Extension -> (category, markdown-språk för kodblock eller None)
EXTENSION_MAP: dict[str, tuple[str, str | None]] = {
    # Kod
    ".py": (CATEGORY_CODE, "python"),
    ".js": (CATEGORY_CODE, "javascript"),
    ".ts": (CATEGORY_CODE, "typescript"),
    ".java": (CATEGORY_CODE, "java"),
    ".cs": (CATEGORY_CODE, "csharp"),
    ".cpp": (CATEGORY_CODE, "cpp"),
    ".c": (CATEGORY_CODE, "c"),
    ".h": (CATEGORY_CODE, "c"),
    ".hpp": (CATEGORY_CODE, "cpp"),
    ".rs": (CATEGORY_CODE, "rust"),
    ".go": (CATEGORY_CODE, "go"),
    ".php": (CATEGORY_CODE, "php"),
    ".rb": (CATEGORY_CODE, "ruby"),
    ".ps1": (CATEGORY_CODE, "powershell"),
    ".bat": (CATEGORY_CODE, "batch"),
    ".sh": (CATEGORY_CODE, "bash"),

    # Text
    ".txt": (CATEGORY_TEXT, None),
    ".md": (CATEGORY_TEXT, "markdown"),
    ".rst": (CATEGORY_TEXT, None),
    ".log": (CATEGORY_TEXT, None),
    ".csv": (CATEGORY_TEXT, None),

    # Konfiguration / data
    ".json": (CATEGORY_CONFIG, "json"),
    ".jsonl": (CATEGORY_CONFIG, "json"),
    ".yaml": (CATEGORY_CONFIG, "yaml"),
    ".yml": (CATEGORY_CONFIG, "yaml"),
    ".toml": (CATEGORY_CONFIG, "toml"),
    ".ini": (CATEGORY_CONFIG, "ini"),
    ".xml": (CATEGORY_CONFIG, "xml"),
    ".env": (CATEGORY_CONFIG, None),

    # Webb
    ".html": (CATEGORY_WEB, "html"),
    ".css": (CATEGORY_WEB, "css"),

    # Dokument
    ".pdf": (CATEGORY_DOCUMENT, None),
    ".docx": (CATEGORY_DOCUMENT, None),
    ".odt": (CATEGORY_DOCUMENT, None),

    # Bild
    ".png": (CATEGORY_IMAGE, None),
    ".jpg": (CATEGORY_IMAGE, None),
    ".jpeg": (CATEGORY_IMAGE, None),
    ".webp": (CATEGORY_IMAGE, None),
    ".gif": (CATEGORY_IMAGE, None),
    ".svg": (CATEGORY_IMAGE, None),
}

# Filändelser som är text/kod och därmed kan paketeras rakt av (avsnitt 6).
PACKAGEABLE_TEXT_EXTENSIONS = {
    ext for ext, (cat, _) in EXTENSION_MAP.items()
    if cat in (CATEGORY_CODE, CATEGORY_TEXT, CATEGORY_CONFIG, CATEGORY_WEB)
}

# Binärformat som aldrig ska tolkas som text, även om de dyker upp okänt.
KNOWN_BINARY_EXTENSIONS = {
    ".exe", ".dll", ".so", ".dylib", ".bin", ".db", ".sqlite", ".sqlite3",
    ".zip", ".rar", ".7z", ".tar", ".gz", ".pyc", ".class", ".o", ".obj",
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".ico", ".pdf", ".docx",
    ".odt", ".mp3", ".mp4", ".mov", ".avi", ".wav", ".ttf", ".otf",
}

# Standardmönster för känsliga filer (avsnitt 19).
DEFAULT_SENSITIVE_PATTERNS = [
    ".env",
    "credentials.json",
    "secrets.json",
    "*.pem",
    "*.key",
    "*id_rsa*",
    "*.pfx",
    "*.p12",
    "*password*",
    "*secret*",
]

# Standardkataloger/filer att ignorera (avsnitt 12).
# OBS: .env ingår INTE här trots att den nämns i avsnitt 12, eftersom
# avsnitt 19 kräver att känsliga filer som .env ska upptäckas, visas
# och flaggas (⚠) i listan – inte tystas ner helt av skanningen.
DEFAULT_IGNORE_DIRS = {
    ".git", "__pycache__", "node_modules", "venv", ".venv", ".idea",
    ".vscode", "bin", "obj", "build", "dist",
}
DEFAULT_IGNORE_FILES = {
    ".gitignore",
}


@dataclass
class ClassificationResult:
    category: str
    language: str | None
    is_sensitive: bool
    is_binary: bool
    matched_sensitive_pattern: str | None = None


def classify_extension(extension: str) -> tuple[str, str | None]:
    """Returnerar (kategori, markdown-språk) för en filändelse (inkl. punkt)."""
    ext = extension.lower()
    if ext in EXTENSION_MAP:
        return EXTENSION_MAP[ext]
    if ext in KNOWN_BINARY_EXTENSIONS:
        return CATEGORY_BINARY, None
    return CATEGORY_UNKNOWN, None


def is_probably_binary(sample: bytes) -> bool:
    """Heuristik: null-byte eller hög andel icke-textbytes => binär."""
    if not sample:
        return False
    if b"\x00" in sample:
        return True
    text_chars = bytearray({7, 8, 9, 10, 12, 13, 27} | set(range(0x20, 0x100)) - {0x7f})
    non_text = sum(byte not in text_chars for byte in sample)
    return (non_text / len(sample)) > 0.30


def match_sensitive(filename: str, patterns: list[str] | None = None) -> str | None:
    """Returnerar matchande mönster om filnamnet ser känsligt ut, annars None."""
    patterns = patterns if patterns is not None else DEFAULT_SENSITIVE_PATTERNS
    name_lower = filename.lower()
    for pattern in patterns:
        if fnmatch.fnmatch(name_lower, pattern.lower()):
            return pattern
    return None


def classify_file(
    path: str,
    read_sample: bytes | None = None,
    sensitive_patterns: list[str] | None = None,
) -> ClassificationResult:
    """
    Klassificerar en fil utifrån ändelse (och ev. innehållsprov för
    binärdetektion av okända ändelser).
    """
    filename = os.path.basename(path)
    _, ext = os.path.splitext(filename)
    category, language = classify_extension(ext)

    # Bilder och dokument (pdf/docx/odt) är binära format på diskformatnivå
    # och ska aldrig dumpas som text i paketet, även om de fått en egen
    # visningskategori (avsnitt 20).
    is_binary = category in (CATEGORY_BINARY, CATEGORY_IMAGE, CATEGORY_DOCUMENT)
    if category == CATEGORY_UNKNOWN and read_sample is not None:
        if is_probably_binary(read_sample):
            category = CATEGORY_BINARY
            is_binary = True

    matched = match_sensitive(filename, sensitive_patterns)

    return ClassificationResult(
        category=category,
        language=language,
        is_sensitive=matched is not None,
        is_binary=is_binary,
        matched_sensitive_pattern=matched,
    )
