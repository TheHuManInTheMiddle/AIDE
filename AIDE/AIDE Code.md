AIDE PROJECT PACKAGE
====================

PROJECT:
AIDE

SOURCE FOLDER(S):
AIDE

FILES:
30

STRUCTURE:

AIDE/
├── core/
│   ├── __init__.py
│   ├── classifier.py
│   ├── manifest.py
│   ├── package_builder.py
│   ├── plugin_base.py
│   ├── plugin_loader.py
│   ├── scanner.py
│   ├── security.py
│   ├── settings.py
│   └── tree_renderer.py
├── docs/
│   └── PLUGIN_GUIDE.md
├── exporters/
│   ├── __init__.py
│   ├── json_exporter.py
│   ├── markdown_exporter.py
│   ├── text_exporter.py
│   └── tree_exporter.py
├── plugins/
│   └── example_plugin/
│       └── main_plugin.py
├── tests/
│   ├── __init__.py
│   ├── test_classifier.py
│   ├── test_export.py
│   ├── test_plugin_loader.py
│   ├── test_scanner.py
│   └── test_tree_renderer.py
├── ui/
│   ├── __init__.py
│   ├── file_tree.py
│   ├── main_window.py
│   ├── preview.py
│   ├── settings_window.py
│   └── theme.py
└── main.py

==================================================
FILE: main.py
TYPE: Kod
==================================================

```python
#!/usr/bin/env python3
"""
AIDE – AI Development Export tool
Startpunkt för applikationen.

Kör med:  python main.py
"""

from __future__ import annotations

import sys

from ui.main_window import MainWindow


def main() -> int:
    app = MainWindow()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())

```

==================================================
FILE: core/classifier.py
TYPE: Kod
==================================================

```python
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

```

==================================================
FILE: core/manifest.py
TYPE: Kod
==================================================

```python
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
) -> dict:
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
                "modified_at": f.modified_at.isoformat() if f.modified_at else None,
                "sensitive": f.is_sensitive,
                "binary": f.is_binary,
            }
            for f in included_files
        ],
    }

```

==================================================
FILE: core/package_builder.py
TYPE: Kod
==================================================

```python
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

```

==================================================
FILE: core/plugin_base.py
TYPE: Kod
==================================================

```python
"""
core/plugin_base.py

Publikt plugin-kontrakt för AIDE.

Detta är AVSIKTLIGT den enda gränsytan en plugin behöver känna till.
En pluginutvecklare (mänsklig eller AI) ska kunna bygga en fungerande
plugin genom att bara läsa docs/PLUGIN_GUIDE.md och implementera
AIDEPlugin nedan — utan att ha tillgång till, eller behöva förstå,
resten av AIDE:s interna källkod (core/scanner.py, ui/, etc).

Kontraktet är medvetet minimalt och stabilt: interna
implementationsdetaljer i AIDE:s kärna kan ändras fritt utan att
bryta befintliga plugins, så länge denna fil (och dess semantik)
inte ändras.

Säkerhetsprincip (samma som resten av AIDE, avsnitt 13):
En plugin får ALDRIG radera eller skriva över filer utanför den
exportmapp AIDE själv skickar in, och ska aldrig anta att den har
fri skrivrätt till filsystemet.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, Optional


@dataclass(frozen=True)
class PluginFileInfo:
    """
    Skrivskyddad, stabil vy av en skannad fil som AIDE skickar in till
    plugins. Detta är INTE samma klass som AIDE använder internt
    (core.scanner.ScannedFile) — den här är en medvetet minimal och
    stabil kopia så att interna fältändringar i AIDE aldrig kan
    plötsligt bryta en plugin.
    """
    relative_path: str      # t.ex. "src/core/router.py"
    absolute_path: str      # fullständig sökväg på disk
    filename: str           # t.ex. "router.py"
    extension: str          # t.ex. ".py" (inkl. punkt, gemener)
    category: str           # AIDE:s kategori, t.ex. "Kod", "Text", "Okänd"
    size_bytes: int
    is_sensitive: bool      # flaggad av AIDE:s känslighetsdetektion
    is_binary: bool


class AIDEPlugin(ABC):
    """
    Basklass som alla AIDE-plugins måste ärva från.

    En plugin behöver bara implementera `plugin_name`. Alla andra
    metoder har säkra standardimplementationer (no-op) och kan
    överlagras selektivt beroende på vad pluginet faktiskt gör.
    """

    @property
    @abstractmethod
    def plugin_name(self) -> str:
        """Kort, unikt visningsnamn för pluginet, t.ex. 'Min Export-plugin'."""
        raise NotImplementedError

    @property
    def plugin_version(self) -> str:
        return "0.1.0"

    # ------------------------------------------------------------------
    # Livscykel
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Anropas en gång direkt efter att AIDE har laddat pluginet."""
        pass

    def shutdown(self) -> None:
        """Anropas vid programavslut. Ska aldrig kasta ett undantag."""
        pass

    # ------------------------------------------------------------------
    # Identify-fasen: komplettera klassificering
    # ------------------------------------------------------------------

    def on_classify(self, file_info: PluginFileInfo) -> Optional[dict]:
        """
        Anropas av AIDE för varje fil som fick kategorin "Okänd" av
        kärnans inbyggda klassificerare (core/classifier.py).

        Returnera None för att inte påverka klassificeringen.
        Returnera annars en dict med valfria nycklar:

            {
                "category": "Mitt Format",   # visningskategori
                "language": "toml",          # ev. markdown-språk för kodblock
                "is_sensitive": False,       # override av känslighetsflagga
            }

        En plugin ska ALDRIG anta att den är den enda som körs — flera
        plugins kan vilja klassificera samma filtyp. AIDE använder det
        första icke-None-svaret i laddningsordning.
        """
        return None

    # ------------------------------------------------------------------
    # Determine-fasen: information/observation, ingen mutation av urval
    # ------------------------------------------------------------------

    def on_scan_complete(self, files: list[PluginFileInfo]) -> None:
        """
        Anropas efter att en skanning är klar (efter Identify-fasen,
        innan användaren gör sitt checkbox-urval). Rent informativt —
        returvärdet ignoreras. Bra plats för loggning eller egna
        sido-analyser. Ska aldrig skriva till disk.
        """
        pass

    def on_before_export(
        self, files: list[PluginFileInfo]
    ) -> Optional[list[PluginFileInfo]]:
        """
        Anropas precis innan export, med den lista av filer användaren
        markerat via checkboxarna.

        Returnera None för att inte påverka urvalet.
        Returnera annars en NY lista (filtrerad eller omordnad) som
        AIDE använder istället. Pluginet får INTE skriva eller radera
        filer i det här steget (avsnitt 13) — bara välja/vraka bland
        de filer som redan är markerade.
        """
        return None

    # ------------------------------------------------------------------
    # Export-fasen: registrera egna exportformat
    # ------------------------------------------------------------------

    def get_exporters(self) -> dict[str, Callable]:
        """
        Registrera ytterligare exportformat utöver AIDE:s inbyggda
        (markdown/text/json). Returnera en dict:

            {"mitt_format": exportfunktion}

        "mitt_format" dyker upp som ett valbart alternativ i AIDE:s
        exportformat-väljare.

        exportfunktionens kontrakt:

            def exportfunktion(
                project_name: str,
                source_roots: list[str],
                included_files: list[PluginFileInfo],
                export_dir: str,
                conflict_strategy,   # core.security.ConflictStrategy
                log_callback,        # Callable[[str], None]
            ) -> str | None:
                ...
                return skriven_sökväg_eller_None

        Exportfunktionen ansvarar själv för att respektera
        `conflict_strategy` (se core.security.resolve_target_path) och
        för att aldrig skriva utanför `export_dir`
        (se core.security.ensure_within_export_dir).
        """
        return {}

```

==================================================
FILE: core/plugin_loader.py
TYPE: Kod
==================================================

```python
"""
core/plugin_loader.py

Dynamisk upptäckt och laddning av AIDE-plugins från plugins/-katalogen.

Varje plugin bor i sin egen undermapp under plugins/ och innehåller en
main_plugin.py med en klass som ärver core.plugin_base.AIDEPlugin.
Mönstret är medvetet enkelt: ingen registreringsfil krävs, AIDE
upptäcker plugins genom att skanna katalogstrukturen (samma princip
som beställningens avsnitt 25 efterfrågar).

Ett fel i en enskild plugin får aldrig krascha AIDE eller hindra
övriga plugins från att laddas — i linje med avsnitt 27 (defensiv
felhantering).
"""

from __future__ import annotations

import importlib
import os
import sys

from core.plugin_base import AIDEPlugin


def discover_plugins(plugin_dir: str, log_callback=None) -> dict[str, AIDEPlugin]:
    """
    Skannar plugin_dir efter undermappar med en main_plugin.py som
    definierar en AIDEPlugin-subklass, instansierar och initialiserar
    dem.

    Returnerar en dict {plugin_name: instans}.
    """
    log = log_callback or (lambda msg: None)
    discovered: dict[str, AIDEPlugin] = {}

    if not os.path.isdir(plugin_dir):
        return discovered

    if plugin_dir not in sys.path:
        sys.path.insert(0, plugin_dir)

    for folder in sorted(os.listdir(plugin_dir)):
        folder_path = os.path.join(plugin_dir, folder)

        if not os.path.isdir(folder_path):
            continue
        if folder.startswith("__") or folder.startswith("."):
            continue

        main_file = os.path.join(folder_path, "main_plugin.py")
        if not os.path.isfile(main_file):
            continue

        module_name = f"{folder}.main_plugin"

        try:
            if module_name in sys.modules:
                importlib.reload(sys.modules[module_name])
            module = importlib.import_module(module_name)

            for attribute_name in dir(module):
                attribute = getattr(module, attribute_name)
                if (
                    isinstance(attribute, type)
                    and issubclass(attribute, AIDEPlugin)
                    and attribute is not AIDEPlugin
                ):
                    instance = attribute()
                    instance.initialize()
                    discovered[instance.plugin_name] = instance
                    log(f"Plugin loaded: '{instance.plugin_name}' (v{instance.plugin_version}) från {folder}/")

        except Exception as exc:  # en trasig plugin ska aldrig krascha AIDE
            log(f"⚠ Kunde inte ladda plugin i '{folder}': {exc}")

    return discovered

```

==================================================
FILE: core/scanner.py
TYPE: Kod
==================================================

```python
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

```

==================================================
FILE: core/security.py
TYPE: Kod
==================================================

```python
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

```

==================================================
FILE: core/settings.py
TYPE: Kod
==================================================

```python
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

```

==================================================
FILE: core/tree_renderer.py
TYPE: Kod
==================================================

```python
"""
core/tree_renderer.py

Renderar en klassisk ASCII-trädvy (├──/└──/│) av de filer som är
markerade för export. Bygger på samma hierarkiska tanke som
ui/file_tree.py (mappstruktur, inte kategori), men helt fristående
från GUI-koden så den kan användas av vilken exportör som helst.

Trädet visar bara det som faktiskt är MARKERAT — det är en spegling av
vad som kommer att exporteras, inte en fullständig katalogkarta.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from core.scanner import ScannedFile


@dataclass
class _Node:
    name: str
    is_file: bool
    children: dict = field(default_factory=dict)  # name -> _Node, bara för mappar


def _build_tree(included_files: list[ScannedFile]) -> _Node:
    root = _Node(name="", is_file=False)
    for f in included_files:
        parts = f.relative_path.split("/")
        current = root
        for part in parts[:-1]:
            if part not in current.children:
                current.children[part] = _Node(name=part, is_file=False)
            current = current.children[part]
        filename = parts[-1]
        current.children[filename] = _Node(name=filename, is_file=True)
    return root


def _render(node: _Node, prefix: str, lines: list[str]) -> None:
    # Mappar först (alfabetiskt), sedan filer (alfabetiskt) — samma
    # ordning som de flesta filhanterare och `tree`-kommandot använder.
    entries = sorted(
        node.children.values(),
        key=lambda n: (n.is_file, n.name.lower()),
    )
    for index, child in enumerate(entries):
        is_last = index == len(entries) - 1
        connector = "└── " if is_last else "├── "
        suffix = "" if child.is_file else "/"
        lines.append(f"{prefix}{connector}{child.name}{suffix}")
        if not child.is_file:
            extension = "    " if is_last else "│   "
            _render(child, prefix + extension, lines)


def build_ascii_tree(project_name: str, included_files: list[ScannedFile]) -> str:
    """
    Bygger en ASCII-trädrepresentation av de markerade filerna, t.ex.:

        mittprojekt/
        ├── config/
        │   └── settings.json
        ├── src/
        │   ├── core/
        │   │   └── router.py
        │   └── main.py
        └── docs/
            └── README.md

    Endast filens NAMN används i trädet — precis som resten av AIDE:s
    export innehåller trädet aldrig absoluta lokala sökvägar.
    """
    lines = [f"{project_name}/"]
    if not included_files:
        lines.append("(inga filer markerade)")
        return "\n".join(lines)

    root = _build_tree(included_files)
    _render(root, "", lines)
    return "\n".join(lines)

```

==================================================
FILE: core/__init__.py
TYPE: Kod
==================================================

```python


```

==================================================
FILE: docs/PLUGIN_GUIDE.md
TYPE: Text
==================================================

```markdown
# Bygga en plugin för A.I.D.E.

**Den här guiden är fristående.** Du behöver inte tillgång till AIDE:s
fullständiga källkod för att bygga en fungerande plugin — bara den här
filen, plus de två små kodstyckena som citeras nedan (`AIDEPlugin` och
`PluginFileInfo`). Om du implementerar mot kontraktet som beskrivs här
kommer din plugin att fungera när den släpps i en AIDE-installation.

---

## 1. Vad är AIDE?

AIDE (**A**rchive · **I**dentify · **D**etermine · **E**xport) är ett
lokalt, fristående desktopverktyg som:

1. **Archive** — samlar filer från en eller flera valda källmappar
   (rekursiv katalogskanning).
2. **Identify** — klassificerar varje fil (kod, text, konfiguration,
   bild, dokument, binär, okänd) och flaggar potentiellt känsliga
   filer.
3. **Determine** — låter användaren avgöra, via checkboxar, exakt
   vilka filer som ska ingå i slutresultatet.
4. **Export** — bygger ett färdigt paket (Markdown/text/JSON, eller ett
   format din plugin lägger till) till en mapp användaren själv valt.

En plugin hakar in i just dessa fyra faser — se avsnitt 3.

---

## 2. Var en plugin bor

```text
AIDE/
└── plugins/
    └── mitt_plugin_namn/       ← valfritt mappnamn, ingen konfigfil krävs
        └── main_plugin.py       ← MÅSTE heta exakt så
```

AIDE skannar `plugins/`-katalogen vid uppstart. Varje undermapp som
innehåller en fil `main_plugin.py` med minst en klass som ärver
`AIDEPlugin` laddas automatiskt. Inget registreringssteg, inget
manifest, ingen konfiguration krävs för att en plugin ska hittas.

En trasig plugin (t.ex. ett Python-undantag vid import) loggas och
hoppas över — den kraschar aldrig AIDE eller hindrar andra plugins
från att laddas.

---

## 3. Kontraktet: `AIDEPlugin`

Det här är hela gränsytan. Din pluginklass ärver `AIDEPlugin` och
behöver bara implementera `plugin_name` — allt annat är valfritt att
skriva över.

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, Optional


@dataclass(frozen=True)
class PluginFileInfo:
    """Skrivskyddad, stabil vy av en fil som AIDE skickar till plugins."""
    relative_path: str      # t.ex. "src/core/router.py"
    absolute_path: str      # fullständig sökväg på disk
    filename: str           # t.ex. "router.py"
    extension: str          # t.ex. ".py" (inkl. punkt, gemener)
    category: str           # AIDE:s kategori, t.ex. "Kod", "Text", "Okänd"
    size_bytes: int
    is_sensitive: bool      # flaggad av AIDE:s inbyggda känslighetsdetektion
    is_binary: bool


class AIDEPlugin(ABC):

    @property
    @abstractmethod
    def plugin_name(self) -> str:
        """Kort, unikt visningsnamn, t.ex. 'Min Export-plugin'."""
        raise NotImplementedError

    @property
    def plugin_version(self) -> str:
        return "0.1.0"

    # --- Livscykel ---

    def initialize(self) -> None:
        """Anropas en gång direkt efter att AIDE laddat pluginet."""
        pass

    def shutdown(self) -> None:
        """Anropas vid programavslut. Får aldrig kasta ett undantag."""
        pass

    # --- Identify-fasen ---

    def on_classify(self, file_info: PluginFileInfo) -> Optional[dict]:
        """
        Anropas för varje fil som AIDE:s inbyggda klassificerare gav
        kategorin "Okänd". Returnera None för att inte påverka den,
        eller en dict:
            {"category": "...", "language": "...", "is_sensitive": bool}
        """
        return None

    # --- Determine-fasen ---

    def on_scan_complete(self, files: list[PluginFileInfo]) -> None:
        """Informativ hook efter en skanning. Returvärdet ignoreras."""
        pass

    def on_before_export(
        self, files: list[PluginFileInfo]
    ) -> Optional[list[PluginFileInfo]]:
        """
        Anropas med de filer användaren markerat, precis innan export.
        Returnera None för att inte påverka urvalet, eller en ny
        (filtrerad/omordnad) lista. Får INTE skriva/radera filer här.
        """
        return None

    # --- Export-fasen ---

    def get_exporters(self) -> dict[str, Callable]:
        """
        Registrera egna exportformat: {"formatnamn": exportfunktion}.
        "formatnamn" dyker upp i AIDE:s format-väljare.
        Se signatur för exportfunktionen i avsnitt 5.
        """
        return {}
```

**Namnen `markdown`, `text` och `json` är reserverade** (AIDE:s
inbyggda format). Om din plugin registrerar ett format med något av
de namnen ignoreras det och en varning loggas.

---

## 4. Minimalt exempel

```python
# plugins/hello_plugin/main_plugin.py

from core.plugin_base import AIDEPlugin, PluginFileInfo


class HelloPlugin(AIDEPlugin):

    @property
    def plugin_name(self) -> str:
        return "Hello Plugin"

    def on_scan_complete(self, files: list[PluginFileInfo]) -> None:
        print(f"[Hello Plugin] Skanningen hittade {len(files)} filer.")
```

Det räcker för att pluginet ska upptäckas, laddas och köras vid nästa
skanning. Lägg mappen `hello_plugin/` i AIDE:s `plugins/`-katalog och
starta om AIDE.

> **Import-sökväg:** `from core.plugin_base import ...` fungerar
> eftersom din plugin körs med AIDE:s projektrot på Pythons
> sökväg — precis som vilken annan modul i AIDE som helst. Du behöver
> inte kopiera in `plugin_base.py` själv.

---

## 5. Bygga ett eget exportformat

Detta är den vanligaste typen av plugin: ett nytt sätt att paketera
de markerade filerna.

```python
def mitt_exportformat(
    project_name: str,
    source_roots: list[str],
    included_files: list[PluginFileInfo],
    export_dir: str,
    conflict_strategy,   # se avsnitt 6
    log_callback,        # Callable[[str], None] — skriv till AIDE:s logg
) -> str | None:
    """
    Bygg och skriv ditt paket. Returnera den skrivna sökvägen,
    eller None om inget skrevs (t.ex. vid "hoppa över"-konflikt).
    """
    ...
```

Registrera den i din plugin:

```python
class MittPlugin(AIDEPlugin):
    @property
    def plugin_name(self) -> str:
        return "Mitt Plugin"

    def get_exporters(self):
        return {"mitt_format": mitt_exportformat}
```

`"mitt_format"` dyker nu upp som ett valbart alternativ i AIDE:s
exportformat-väljare i huvudfönstret.

### Fullständigt, körbart exempel

AIDE levereras med `plugins/example_plugin/main_plugin.py` som en
referensimplementation — den visar alla fyra hooks i praktiken
(omklassificering av en filändelse, loggning vid skanning,
storleksfiltrering före export, och ett eget litet exportformat kallat
`"shout"`). Läs den filen som ett komplett, testat exempel att kopiera
och bygga vidare på.

---

## 6. Säkerhetsregler för plugins

AIDE:s grundprincip är att aldrig radera eller skriva över filer
automatiskt (se AIDE:s README, avsnitt "Vad AIDE är"). Din plugin
måste följa samma princip:

1. **Skriv aldrig utanför `export_dir`.** Bygg alltid din målsökväg
   inom den mapp AIDE skickar in.
2. **Respektera `conflict_strategy`.** Det är ett `ConflictStrategy`-
   objekt med tre möjliga lägen: skriv över, skapa ny version, eller
   hoppa över. Din exportfunktion ansvarar själv för att hantera det
   fall att målfilen redan finns — annars riskerar du att tysta
   skriva över användarens data.
3. **Rör aldrig `file_info.absolute_path` destruktivt.** Du får läsa
   från källfilerna, men aldrig radera, flytta eller skriva till dem.
4. **Krascha aldrig tyst.** Om något går fel, skriv till
   `log_callback(...)` och returnera `None` istället för att låta ett
   undantag brisera ut — AIDE fångar oväntade undantag defensivt, men
   ett tydligt loggmeddelande är mycket mer användbart för
   slutanvändaren än en stacktrace.
5. **Anta aldrig att du är den enda pluginet.** Flera plugins kan vara
   installerade samtidigt. `on_classify` använder första
   icke-`None`-svaret; skriv din hook så att den bara reagerar på
   filtyper/mönster du faktiskt känner igen.

---

## 7. Testa din plugin fristående

Du behöver inte hela AIDE-applikationen för att testa kontraktet:

```python
from core.plugin_loader import discover_plugins

plugins = discover_plugins("./plugins")
assert "Mitt Plugin" in plugins

plugin = plugins["Mitt Plugin"]
plugin.initialize()
# ... anropa hooks direkt med egenhändigt konstruerade PluginFileInfo-objekt
```

Se `tests/test_plugin_loader.py` i AIDE-projektet för fler exempel på
hur pluginladdningen kan testas isolerat, inklusive hur en trasig
plugin hanteras utan att krascha resten.

---

## 8. Checklista innan leverans

- [ ] `plugin_name` är unikt och beskrivande.
- [ ] Inga skriv-/raderingsoperationer sker utanför `export_dir`.
- [ ] `conflict_strategy` hanteras korrekt i alla egna exportfunktioner.
- [ ] Inga oväntade undantag läcker ut okontrollerat — fel loggas via
      `log_callback` där det är relevant.
- [ ] Pluginet fungerar även om det är det enda pluginet installerat
      OCH om flera andra plugins är installerade samtidigt.
- [ ] Testat mot `core.plugin_loader.discover_plugins(...)` fristående,
      utan att starta hela GUI:t.

---

Lycka till! Kontraktet ovan (`AIDEPlugin` + `PluginFileInfo`) är allt
du behöver — resten av AIDE:s interna implementation kan ändras fritt
utan att din plugin går sönder, så länge du håller dig till det.

```

==================================================
FILE: exporters/json_exporter.py
TYPE: Kod
==================================================

```python
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

```

==================================================
FILE: exporters/markdown_exporter.py
TYPE: Kod
==================================================

```python
"""
exporters/markdown_exporter.py

Skriver projektpaketet som en .md-fil till vald exportmapp.
"""

from __future__ import annotations

import os

from core.package_builder import build_package_text
from core.scanner import ScannedFile
from core.security import ConflictStrategy, ensure_within_export_dir, resolve_target_path


def export_markdown(
    project_name: str,
    source_roots: list[str],
    included_files: list[ScannedFile],
    export_dir: str,
    filename: str = "project_package.md",
    conflict_strategy: ConflictStrategy = ConflictStrategy.NEW_VERSION,
    log_callback=None,
) -> str | None:
    """Returnerar skrivna sökvägen, eller None om filen hoppades över."""
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
        log_callback(f"Markdown-paket skapat: {resolved}")
    return resolved

```

==================================================
FILE: exporters/text_exporter.py
TYPE: Kod
==================================================

```python
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

```

==================================================
FILE: exporters/tree_exporter.py
TYPE: Kod
==================================================

```python
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

```

==================================================
FILE: exporters/__init__.py
TYPE: Kod
==================================================

```python


```

==================================================
FILE: plugins/example_plugin/main_plugin.py
TYPE: Kod
==================================================

```python
# -*- coding: utf-8 -*-
"""
plugins/example_plugin/main_plugin.py

Referensimplementation som visar hela AIDEPlugin-kontraktet i
praktiken. Detta är INTE en riktig produktionsplugin — den finns för
att vara ett konkret, körbart exempel att kopiera och bygga vidare på
(se docs/PLUGIN_GUIDE.md).

Vad den gör:
  1. Klassificerar ".aide"-filer som "AIDE Meta" istället för "Okänd".
  2. Loggar hur många filer som hittades vid varje skanning.
  3. Filtrerar automatiskt bort filer större än 5 MB från exporten,
     som ett exempel på on_before_export.
  4. Registrerar ett eget litet exportformat: "shout" — samma innehåll
     som markdown-paketet, men med filrubriker i versaler. Ett
     medvetet enkelt, ofarligt exempel på get_exporters().
"""

from __future__ import annotations

from core.plugin_base import AIDEPlugin, PluginFileInfo


MAX_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


class ExamplePlugin(AIDEPlugin):

    @property
    def plugin_name(self) -> str:
        return "AIDE Example Plugin"

    @property
    def plugin_version(self) -> str:
        return "1.0.0"

    def initialize(self) -> None:
        print(f"[{self.plugin_name}] Initialiserad.")

    def on_classify(self, file_info: PluginFileInfo):
        if file_info.extension == ".aide":
            return {"category": "AIDE Meta", "language": None, "is_sensitive": False}
        return None

    def on_scan_complete(self, files: list[PluginFileInfo]) -> None:
        print(f"[{self.plugin_name}] Skanning klar: {len(files)} filer sågs av pluginet.")

    def on_before_export(self, files: list[PluginFileInfo]):
        filtered = [f for f in files if f.size_bytes <= MAX_SIZE_BYTES]
        if len(filtered) != len(files):
            print(
                f"[{self.plugin_name}] Filtrerade bort "
                f"{len(files) - len(filtered)} fil(er) över 5 MB."
            )
        return filtered

    def get_exporters(self):
        return {"shout": self._export_shout}

    # ------------------------------------------------------------------
    # Egen exportfunktion — följer exportörskontraktet i AIDEPlugin.get_exporters
    # ------------------------------------------------------------------

    @staticmethod
    def _export_shout(
        project_name: str,
        source_roots: list[str],
        included_files: list[PluginFileInfo],
        export_dir: str,
        conflict_strategy,
        log_callback,
    ) -> str | None:
        import os
        from core.security import ensure_within_export_dir, resolve_target_path

        os.makedirs(export_dir, exist_ok=True)
        target = ensure_within_export_dir(export_dir, "project_package_SHOUT.md")
        resolved = resolve_target_path(target, conflict_strategy)
        if resolved is None:
            log_callback(f"Hoppade över befintlig fil: {target}")
            return None

        lines = [f"AIDE SHOUT PACKAGE — {project_name.upper()}", "=" * 40, ""]
        for f in included_files:
            lines.append(f"### FILE: {f.relative_path.upper()} ###")
            if f.is_binary:
                lines.append("[BINARY]")
                continue
            try:
                with open(f.absolute_path, "r", encoding="utf-8", errors="replace") as fh:
                    lines.append(fh.read())
            except OSError as exc:
                lines.append(f"[Kunde inte läsa: {exc}]")
            lines.append("")

        with open(resolved, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines))

        log_callback(f"Shout-paket skapat: {resolved}")
        return resolved

```

==================================================
FILE: tests/test_classifier.py
TYPE: Kod
==================================================

```python
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.classifier import (
    CATEGORY_BINARY,
    CATEGORY_CODE,
    CATEGORY_CONFIG,
    CATEGORY_IMAGE,
    CATEGORY_TEXT,
    CATEGORY_UNKNOWN,
    classify_file,
    is_probably_binary,
    match_sensitive,
)


def test_python_file_classified_as_code():
    result = classify_file("src/main.py")
    assert result.category == CATEGORY_CODE
    assert result.language == "python"
    assert result.is_binary is False


def test_json_classified_as_config():
    result = classify_file("config/settings.json")
    assert result.category == CATEGORY_CONFIG


def test_markdown_classified_as_text():
    result = classify_file("README.md")
    assert result.category == CATEGORY_TEXT


def test_image_classified_as_image_and_binary():
    result = classify_file("assets/logo.png")
    assert result.category == CATEGORY_IMAGE
    assert result.is_binary is True


def test_unknown_extension_without_sample_is_unknown():
    result = classify_file("mystery.qzx")
    assert result.category == CATEGORY_UNKNOWN


def test_unknown_extension_with_binary_sample_is_binary():
    sample = bytes([0, 1, 2, 3, 255, 254]) * 10
    result = classify_file("mystery.qzx", read_sample=sample)
    assert result.category == CATEGORY_BINARY


def test_env_file_flagged_sensitive():
    result = classify_file(".env")
    assert result.is_sensitive is True


def test_pem_key_flagged_sensitive():
    result = classify_file("server.pem")
    assert result.is_sensitive is True
    assert match_sensitive("private.key") == "*.key"


def test_normal_python_file_not_sensitive():
    result = classify_file("main.py")
    assert result.is_sensitive is False


def test_is_probably_binary_detects_null_byte():
    assert is_probably_binary(b"hello\x00world") is True


def test_is_probably_binary_false_for_plain_text():
    assert is_probably_binary("Hej, det här är vanlig text.".encode("utf-8")) is False

```

==================================================
FILE: tests/test_export.py
TYPE: Kod
==================================================

```python
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.scanner import ScannedFile
from core.security import (
    ConflictStrategy,
    ExportBlocked,
    ensure_within_export_dir,
    resolve_target_path,
    sanitize_filename,
)
from exporters.json_exporter import export_json_manifest
from exporters.markdown_exporter import export_markdown
from exporters.text_exporter import export_text


def _make_file(tmp_path, rel_path, content, category="Kod", language="python", sensitive=False, binary=False):
    abs_path = tmp_path / rel_path
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    if binary:
        abs_path.write_bytes(content)
    else:
        abs_path.write_text(content, encoding="utf-8")
    return ScannedFile(
        absolute_path=str(abs_path),
        relative_path=rel_path,
        source_root=str(tmp_path),
        filename=os.path.basename(rel_path),
        extension=os.path.splitext(rel_path)[1],
        category=category,
        language=language,
        size_bytes=abs_path.stat().st_size,
        modified_at=datetime.now(),
        is_sensitive=sensitive,
        is_binary=binary,
        is_hidden=False,
        readable=True,
        included=True,
    )


def test_markdown_export_contains_file_headers(tmp_path):
    src = tmp_path / "src"
    files = [_make_file(src, "main.py", "print('hej')\n")]
    export_dir = tmp_path / "export"

    path = export_markdown("Proj", [str(src)], files, str(export_dir), conflict_strategy=ConflictStrategy.OVERWRITE)
    text = open(path, encoding="utf-8").read()
    assert "FILE: main.py" in text
    assert "```python" in text
    assert "print('hej')" in text


def test_text_export_writes_file(tmp_path):
    src = tmp_path / "src"
    files = [_make_file(src, "a.txt", "hello", category="Text", language=None)]
    export_dir = tmp_path / "export"

    path = export_text("Proj", [str(src)], files, str(export_dir), conflict_strategy=ConflictStrategy.OVERWRITE)
    assert path is not None
    assert os.path.isfile(path)
    assert path.endswith(".txt")


def test_json_manifest_contains_metadata_not_content(tmp_path):
    src = tmp_path / "src"
    files = [_make_file(src, "a.py", "SECRET = 1")]
    export_dir = tmp_path / "export"

    path = export_json_manifest("Proj", [str(src)], files, str(export_dir), conflict_strategy=ConflictStrategy.OVERWRITE)
    data = json.loads(open(path, encoding="utf-8").read())
    assert data["files"] == 1
    assert data["included_files"][0]["path"] == "a.py"
    assert "SECRET" not in json.dumps(data)  # manifestet ska aldrig innehålla filinnehåll


def test_conflict_overwrite_replaces_file(tmp_path):
    target = tmp_path / "out.md"
    target.write_text("gammalt innehåll")
    resolved = resolve_target_path(str(target), ConflictStrategy.OVERWRITE)
    assert resolved == str(target)


def test_conflict_new_version_creates_numbered_file(tmp_path):
    target = tmp_path / "out.md"
    target.write_text("gammalt innehåll")
    resolved = resolve_target_path(str(target), ConflictStrategy.NEW_VERSION)
    assert resolved == str(tmp_path / "out (1).md")


def test_conflict_skip_returns_none(tmp_path):
    target = tmp_path / "out.md"
    target.write_text("gammalt innehåll")
    resolved = resolve_target_path(str(target), ConflictStrategy.SKIP)
    assert resolved is None


def test_conflict_no_existing_file_returns_target(tmp_path):
    target = tmp_path / "does_not_exist.md"
    resolved = resolve_target_path(str(target), ConflictStrategy.SKIP)
    assert resolved == str(target)


def test_export_never_escapes_export_dir(tmp_path):
    export_dir = tmp_path / "export"
    export_dir.mkdir()
    try:
        ensure_within_export_dir(str(export_dir), "../../etc/passwd")
        assert False, "should have raised ExportBlocked"
    except ExportBlocked:
        pass


def test_markdown_export_never_leaks_absolute_source_path(tmp_path):
    src = tmp_path / "hemlig_användarmapp" / "Desktop" / "MittProjekt"
    files = [_make_file(src, "main.py", "print(1)")]
    export_dir = tmp_path / "export"

    path = export_markdown("MittProjekt", [str(src)], files, str(export_dir), conflict_strategy=ConflictStrategy.OVERWRITE)
    text = open(path, encoding="utf-8").read()

    assert str(src) not in text
    assert "hemlig_användarmapp" not in text
    assert "MittProjekt" in text  # bara mappnamnet, inte hela sökvägen


def test_json_manifest_never_leaks_absolute_source_path(tmp_path):
    src = tmp_path / "hemlig_användarmapp" / "Desktop" / "MittProjekt"
    files = [_make_file(src, "main.py", "print(1)")]
    export_dir = tmp_path / "export"

    path = export_json_manifest("MittProjekt", [str(src)], files, str(export_dir), conflict_strategy=ConflictStrategy.OVERWRITE)
    data = json.loads(open(path, encoding="utf-8").read())

    assert str(src) not in json.dumps(data)
    assert "hemlig_användarmapp" not in json.dumps(data)
    assert data["source_folders"] == ["MittProjekt"]


def test_full_export_pipeline_creates_markdown_and_manifest(tmp_path):
    src = tmp_path / "src"
    files = [
        _make_file(src, "main.py", "print(1)"),
        _make_file(src, "readme.md", "# hej", category="Text", language="markdown"),
    ]
    export_dir = tmp_path / "export"

    md_path = export_markdown("Proj", [str(src)], files, str(export_dir), conflict_strategy=ConflictStrategy.OVERWRITE)
    manifest_path = export_json_manifest("Proj", [str(src)], files, str(export_dir), conflict_strategy=ConflictStrategy.OVERWRITE)

    assert os.path.isfile(md_path)
    assert os.path.isfile(manifest_path)


def test_sanitize_filename_removes_invalid_characters():
    assert sanitize_filename('mitt:proj/med<konstiga>tecken?') == "mitt_proj_med_konstiga_tecken_"


def test_sanitize_filename_handles_empty_input():
    assert sanitize_filename("") == "AIDE_Project"
    assert sanitize_filename("   ") == "AIDE_Project"


def test_sanitize_filename_keeps_normal_names_unchanged():
    assert sanitize_filename("gamebridge_v1") == "gamebridge_v1"
    assert sanitize_filename("Mitt Projekt") == "Mitt Projekt"

```

==================================================
FILE: tests/test_plugin_loader.py
TYPE: Kod
==================================================

```python
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.plugin_base import AIDEPlugin, PluginFileInfo
from core.plugin_loader import discover_plugins


def _write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


def test_discover_plugins_finds_valid_plugin(tmp_path):
    plugin_dir = tmp_path / "plugins" / "hello_plugin"
    _write(
        str(plugin_dir / "main_plugin.py"),
        "from core.plugin_base import AIDEPlugin\n"
        "class HelloPlugin(AIDEPlugin):\n"
        "    @property\n"
        "    def plugin_name(self):\n"
        "        return 'Hello Plugin'\n",
    )

    plugins = discover_plugins(str(tmp_path / "plugins"))
    assert "Hello Plugin" in plugins
    assert isinstance(plugins["Hello Plugin"], AIDEPlugin)


def test_discover_plugins_ignores_folder_without_main_plugin(tmp_path):
    empty_dir = tmp_path / "plugins" / "not_a_plugin"
    empty_dir.mkdir(parents=True)
    (empty_dir / "readme.txt").write_text("hej")

    plugins = discover_plugins(str(tmp_path / "plugins"))
    assert plugins == {}


def test_discover_plugins_survives_broken_plugin(tmp_path):
    broken_dir = tmp_path / "plugins" / "broken_plugin"
    _write(str(broken_dir / "main_plugin.py"), "raise RuntimeError('kaputt')\n")

    good_dir = tmp_path / "plugins" / "good_plugin"
    _write(
        str(good_dir / "main_plugin.py"),
        "from core.plugin_base import AIDEPlugin\n"
        "class GoodPlugin(AIDEPlugin):\n"
        "    @property\n"
        "    def plugin_name(self):\n"
        "        return 'Good Plugin'\n",
    )

    log_messages = []
    plugins = discover_plugins(str(tmp_path / "plugins"), log_callback=log_messages.append)

    assert "Good Plugin" in plugins
    assert any("kaputt" in msg or "broken_plugin" in msg for msg in log_messages)


def test_discover_plugins_missing_directory_returns_empty():
    plugins = discover_plugins("/path/does/not/exist")
    assert plugins == {}


def test_plugin_base_default_hooks_are_safe_noops():
    class MinimalPlugin(AIDEPlugin):
        @property
        def plugin_name(self):
            return "Minimal"

    p = MinimalPlugin()
    info = PluginFileInfo(
        relative_path="a.xyz", absolute_path="/tmp/a.xyz", filename="a.xyz",
        extension=".xyz", category="Okänd", size_bytes=10,
        is_sensitive=False, is_binary=False,
    )

    assert p.on_classify(info) is None
    assert p.on_scan_complete([info]) is None
    assert p.on_before_export([info]) is None
    assert p.get_exporters() == {}
    p.initialize()
    p.shutdown()


def test_example_plugin_reclassifies_aide_files(tmp_path):
    import sys as _sys
    plugins_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "plugins"))
    plugins = discover_plugins(plugins_root)
    assert "AIDE Example Plugin" in plugins

    plugin = plugins["AIDE Example Plugin"]
    info = PluginFileInfo(
        relative_path="project.aide", absolute_path="/tmp/project.aide",
        filename="project.aide", extension=".aide", category="Okänd",
        size_bytes=20, is_sensitive=False, is_binary=False,
    )
    result = plugin.on_classify(info)
    assert result is not None
    assert result["category"] == "AIDE Meta"


def test_example_plugin_filters_large_files():
    plugins_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "plugins"))
    plugins = discover_plugins(plugins_root)
    plugin = plugins["AIDE Example Plugin"]

    small = PluginFileInfo("a.txt", "/tmp/a.txt", "a.txt", ".txt", "Text", 100, False, False)
    huge = PluginFileInfo("b.bin", "/tmp/b.bin", "b.bin", ".bin", "Binär", 6 * 1024 * 1024, False, True)

    filtered = plugin.on_before_export([small, huge])
    assert filtered == [small]

```

==================================================
FILE: tests/test_scanner.py
TYPE: Kod
==================================================

```python
import os
import stat
import sys
import threading

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.scanner import scan_sources


def _write(path, content=""):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


def test_recursive_scan_finds_nested_files(tmp_path):
    root = tmp_path / "proj"
    _write(str(root / "src" / "main.py"), "print(1)")
    _write(str(root / "src" / "core" / "router.py"), "print(2)")
    _write(str(root / "docs" / "readme.md"), "# hi")

    result = scan_sources([str(root)])
    rels = sorted(f.relative_path for f in result.files)
    assert rels == ["docs/readme.md", "src/core/router.py", "src/main.py"]


def test_ignored_directories_are_skipped(tmp_path):
    root = tmp_path / "proj"
    _write(str(root / "src" / "main.py"), "print(1)")
    _write(str(root / "node_modules" / "pkg" / "index.js"), "x")
    _write(str(root / ".git" / "HEAD"), "ref: refs/heads/main")

    result = scan_sources([str(root)])
    rels = [f.relative_path for f in result.files]
    assert "src/main.py" in rels
    assert not any("node_modules" in r for r in rels)
    assert not any(r.startswith(".git") for r in rels)


def test_empty_directory_produces_no_files(tmp_path):
    root = tmp_path / "empty_proj"
    (root / "empty_sub").mkdir(parents=True)

    result = scan_sources([str(root)])
    assert result.files == []
    assert result.errors == []


def test_utf8_filenames_are_handled(tmp_path):
    root = tmp_path / "proj"
    _write(str(root / "åäö_mapp" / "fil_ö.txt"), "internationellt innehåll: 中文 日本語")

    result = scan_sources([str(root)])
    assert len(result.files) == 1
    assert result.files[0].relative_path == "åäö_mapp/fil_ö.txt"


def test_unreadable_file_does_not_crash_scan(tmp_path):
    root = tmp_path / "proj"
    good = root / "good.py"
    bad = root / "bad.py"
    _write(str(good), "print(1)")
    _write(str(bad), "print(2)")

    os.chmod(str(bad), 0o000)
    try:
        result = scan_sources([str(root)])
    finally:
        os.chmod(str(bad), 0o644)  # städa upp så tmp_path kan rensas

    rels = {f.relative_path: f for f in result.files}
    assert "good.py" in rels
    assert "bad.py" in rels
    # Root-processer kan fortfarande läsa trots chmod 000; testa bara att
    # skanningen inte kraschar och att filen ändå upptäcks.
    assert rels["good.py"].readable is True


def test_sensitive_hidden_file_is_still_discovered(tmp_path):
    root = tmp_path / "proj"
    _write(str(root / ".env"), "SECRET=1")

    result = scan_sources([str(root)], show_hidden=False)
    rels = {f.relative_path: f for f in result.files}
    assert ".env" in rels
    assert rels[".env"].is_sensitive is True


def test_cancel_stops_scan_early(tmp_path):
    root = tmp_path / "proj"
    for i in range(50):
        _write(str(root / f"file_{i}.py"), "print(1)")

    cancel_event = threading.Event()
    cancel_event.set()  # avbryt direkt

    result = scan_sources([str(root)], cancel_event=cancel_event)
    assert result.cancelled is True


def test_nonexistent_source_reports_error_not_crash():
    result = scan_sources(["/path/does/not/exist/at/all"])
    assert result.files == []
    assert len(result.errors) == 1

```

==================================================
FILE: tests/test_tree_renderer.py
TYPE: Kod
==================================================

```python
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.scanner import ScannedFile
from core.security import ConflictStrategy
from core.tree_renderer import build_ascii_tree
from exporters.tree_exporter import export_tree


def _make_file(tmp_path, rel_path, category="Kod"):
    abs_path = tmp_path / rel_path
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    abs_path.write_text("innehåll", encoding="utf-8")
    return ScannedFile(
        absolute_path=str(abs_path),
        relative_path=rel_path,
        source_root=str(tmp_path),
        filename=os.path.basename(rel_path),
        extension=os.path.splitext(rel_path)[1],
        category=category,
        language=None,
        size_bytes=abs_path.stat().st_size,
        modified_at=datetime.now(),
        is_sensitive=False,
        is_binary=False,
        is_hidden=False,
        readable=True,
        included=True,
    )


def test_ascii_tree_nests_folders_correctly(tmp_path):
    files = [
        _make_file(tmp_path, "src/main.py"),
        _make_file(tmp_path, "src/core/router.py"),
        _make_file(tmp_path, "docs/readme.md"),
    ]
    tree = build_ascii_tree("MittProjekt", files)

    assert tree.startswith("MittProjekt/")
    assert "├── docs/" in tree or "└── docs/" in tree
    assert "main.py" in tree
    assert "router.py" in tree
    assert "readme.md" in tree
    # core/ ska vara nästlad under src/, dvs indenterad djupare
    src_line_index = next(i for i, line in enumerate(tree.splitlines()) if "src/" in line)
    core_line_index = next(i for i, line in enumerate(tree.splitlines()) if "core/" in line)
    assert core_line_index > src_line_index


def test_ascii_tree_folders_before_files_alphabetically(tmp_path):
    files = [
        _make_file(tmp_path, "zeta.py"),
        _make_file(tmp_path, "alpha/inside.py"),
    ]
    tree = build_ascii_tree("Proj", files)
    lines = tree.splitlines()
    # "alpha/" (mapp) ska komma före "zeta.py" (fil) trots att z < a alfabetiskt är falskt,
    # men mappar ska ändå sorteras före filer oavsett bokstavsordning
    alpha_index = next(i for i, l in enumerate(lines) if "alpha/" in l)
    zeta_index = next(i for i, l in enumerate(lines) if "zeta.py" in l)
    assert alpha_index < zeta_index


def test_ascii_tree_empty_selection():
    tree = build_ascii_tree("TomtProjekt", [])
    assert "TomtProjekt/" in tree
    assert "inga filer markerade" in tree


def test_ascii_tree_never_contains_absolute_paths(tmp_path):
    files = [_make_file(tmp_path, "src/main.py")]
    tree = build_ascii_tree("Proj", files)
    assert str(tmp_path) not in tree


def test_export_tree_writes_file_without_content(tmp_path):
    src = tmp_path / "src"
    files = [_make_file(src, "main.py")]
    export_dir = tmp_path / "export"

    path = export_tree("Proj", [str(src)], files, str(export_dir), conflict_strategy=ConflictStrategy.OVERWRITE)
    text = open(path, encoding="utf-8").read()

    assert "main.py" in text
    assert "innehåll" not in text  # filinnehåll ska ALDRIG vara med i tree-exporten
    assert "Filer: 1" in text


def test_export_tree_respects_conflict_skip(tmp_path):
    src = tmp_path / "src"
    files = [_make_file(src, "main.py")]
    export_dir = tmp_path / "export"
    export_dir.mkdir()
    (export_dir / "project_tree.md").write_text("gammalt")

    path = export_tree("Proj", [str(src)], files, str(export_dir), conflict_strategy=ConflictStrategy.SKIP)
    assert path is None
    assert (export_dir / "project_tree.md").read_text() == "gammalt"

```

==================================================
FILE: tests/__init__.py
TYPE: Kod
==================================================

```python


```

==================================================
FILE: ui/file_tree.py
TYPE: Kod
==================================================

```python
"""
ui/file_tree.py

Hierarkisk mappträdsvy med klickbara checkboxar på både filer och
mappar (avsnitt 9-10), plus möjlighet att exkludera hela delträd direkt
i trädet — inte bara via kategori eller ignore-listan i inställningarna.

Klick på en MAPP växlar hela dess delträd (alla filer och undermappar)
mellan markerat/omarkerat — exakt samma klick-är-toggle-princip som
filer redan använder. En mapp visar tre lägen:

    ☑  alla filer i delträdet är markerade
    ☐  inga filer i delträdet är markerade
    ◪  delträdet är blandat (vissa markerade, andra inte)

ttk har inga inbyggda checkboxar i Treeview, så vi renderar
checkbox-tecken i första kolumnen och togglar dem vid klick.
"""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import ttk

CHECKED = "☑"
UNCHECKED = "☐"
PARTIAL = "◪"
SENSITIVE_MARK = "⚠"


def _human_size(size_bytes: int) -> str:
    size = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


class _DirNode:
    __slots__ = ("iid", "name", "parent_iid", "files", "child_dirs")

    def __init__(self, iid, name, parent_iid):
        self.iid = iid
        self.name = name
        self.parent_iid = parent_iid
        self.files = []       # list[tuple[iid, ScannedFile]] direkt i denna mapp
        self.child_dirs = []  # list[iid] till direkta undermappar


class FileTreeView(ttk.Frame):
    def __init__(self, parent, on_selection_changed=None):
        super().__init__(parent)
        self.on_selection_changed = on_selection_changed
        self._scanned_files = []  # list[ScannedFile]
        self._file_items = {}     # iid -> ScannedFile
        self._dir_nodes = {}      # iid -> _DirNode
        self._dir_lookup = {}     # (parent_iid, name) -> iid
        self._filter_text = ""

        columns = ("size", "category", "status")
        self.tree = ttk.Treeview(self, columns=columns, show="tree headings", selectmode="extended")
        self.tree.heading("#0", text="Fil / Mapp")
        self.tree.heading("size", text="Storlek")
        self.tree.heading("category", text="Kategori")
        self.tree.heading("status", text="Status")
        self.tree.column("#0", width=420, stretch=True)
        self.tree.column("size", width=90, anchor="e")
        self.tree.column("category", width=140)
        self.tree.column("status", width=140)

        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self.tree.bind("<Button-1>", self._on_click)

    # ------------------------------------------------------------------
    # Publikt API
    # ------------------------------------------------------------------

    def load_files(self, scanned_files, default_checked_fn=None):
        """Fyller trädet hierarkiskt (mappstruktur) utifrån relativa sökvägar."""
        self._scanned_files = scanned_files
        self._file_items.clear()
        self._dir_nodes.clear()
        self._dir_lookup.clear()
        self.tree.delete(*self.tree.get_children())

        if default_checked_fn is not None:
            for f in scanned_files:
                f.included = default_checked_fn(f)

        multiple_roots = len({f.source_root for f in scanned_files}) > 1

        for f in sorted(scanned_files, key=lambda x: (x.source_root, x.relative_path.lower())):
            parts = f.relative_path.split("/")
            folder_parts = parts[:-1]
            filename = parts[-1]

            parent_iid = ""
            if multiple_roots:
                root_name = os.path.basename(f.source_root.rstrip("/\\")) or f.source_root
                parent_iid = self._ensure_dir_node(parent_iid, root_name)
            for part in folder_parts:
                parent_iid = self._ensure_dir_node(parent_iid, part)

            warn = f" {SENSITIVE_MARK}" if f.is_sensitive else ""
            status = "Känslig" if f.is_sensitive else ("Binär" if f.is_binary else "")
            if f.error:
                status = "Fel"
            item_iid = self.tree.insert(
                parent_iid, "end", text=f"{UNCHECKED} {filename}{warn}",
                values=(f.size_human, f.category, status), tags=("file",),
            )
            self._file_items[item_iid] = f
            if parent_iid in self._dir_nodes:
                self._dir_nodes[parent_iid].files.append((item_iid, f))

        self._refresh_all_labels()
        self._notify_changed()

    def _ensure_dir_node(self, parent_iid: str, name: str) -> str:
        key = (parent_iid, name)
        if key in self._dir_lookup:
            return self._dir_lookup[key]
        iid = self.tree.insert(parent_iid, "end", text=f"{UNCHECKED} {name}/", open=True, tags=("dir",))
        node = _DirNode(iid, name, parent_iid)
        self._dir_nodes[iid] = node
        self._dir_lookup[key] = iid
        if parent_iid and parent_iid in self._dir_nodes:
            self._dir_nodes[parent_iid].child_dirs.append(iid)
        return iid

    def apply_filter(self, text: str):
        """Filtrerar synliga rader efter filnamn/sökväg/kategori (avsnitt 11)."""
        self._filter_text = text.lower().strip()

        def process_dir(iid) -> bool:
            node = self._dir_nodes[iid]
            visible_any = False
            for item_iid, f in node.files:
                if self._file_matches(f):
                    self.tree.reattach(item_iid, iid, "end")
                    visible_any = True
                else:
                    self.tree.detach(item_iid)
            for child_iid in node.child_dirs:
                if process_dir(child_iid):
                    self.tree.reattach(child_iid, iid, "end")
                    visible_any = True
                else:
                    self.tree.detach(child_iid)
            return visible_any

        roots = [iid for iid, node in self._dir_nodes.items() if node.parent_iid == ""]
        for r in roots:
            if process_dir(r):
                self.tree.reattach(r, "", "end")
            else:
                self.tree.detach(r)

    def _file_matches(self, f) -> bool:
        if not self._filter_text:
            return True
        haystack = f"{f.filename} {f.relative_path} {f.category} {f.extension}".lower()
        return self._filter_text in haystack

    def set_all(self, included: bool):
        for f in self._scanned_files:
            f.included = included
        self._refresh_all_labels()
        self._notify_changed()

    def set_category(self, category: str, included: bool):
        for f in self._scanned_files:
            if f.category == category:
                f.included = included
        self._refresh_all_labels()
        self._notify_changed()

    def get_included_files(self):
        return [f for f in self._scanned_files if f.included]

    def get_all_files(self):
        return list(self._scanned_files)

    def get_categories(self):
        return sorted({f.category for f in self._scanned_files})

    # ------------------------------------------------------------------
    # Internt
    # ------------------------------------------------------------------

    def _gather_files(self, iid):
        """Returnerar [(iid, ScannedFile), ...] för alla filer i ett delträd."""
        node = self._dir_nodes[iid]
        items = list(node.files)
        for child_iid in node.child_dirs:
            items.extend(self._gather_files(child_iid))
        return items

    def _refresh_all_labels(self):
        for iid, f in self._file_items.items():
            mark = CHECKED if f.included else UNCHECKED
            warn = f" {SENSITIVE_MARK}" if f.is_sensitive else ""
            self.tree.item(iid, text=f"{mark} {f.filename}{warn}")

        def compute(iid):
            node = self._dir_nodes[iid]
            included_count = 0
            total_count = 0
            total_size = 0
            for _, f in node.files:
                total_count += 1
                total_size += f.size_bytes
                if f.included:
                    included_count += 1
            for child_iid in node.child_dirs:
                c_inc, c_tot, c_size = compute(child_iid)
                included_count += c_inc
                total_count += c_tot
                total_size += c_size

            if total_count == 0 or included_count == 0:
                mark = UNCHECKED
            elif included_count == total_count:
                mark = CHECKED
            else:
                mark = PARTIAL

            self.tree.item(
                iid,
                text=f"{mark} {node.name}/",
                values=(_human_size(total_size), "", f"{total_count} filer"),
            )
            return included_count, total_count, total_size

        roots = [iid for iid, node in self._dir_nodes.items() if node.parent_iid == ""]
        for r in roots:
            compute(r)

    def _on_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region != "tree":
            return
        item_iid = self.tree.identify_row(event.y)
        if not item_iid:
            return

        if item_iid in self._file_items:
            f = self._file_items[item_iid]
            f.included = not f.included
            self._refresh_all_labels()
            self._notify_changed()
        elif item_iid in self._dir_nodes:
            files = [f for _, f in self._gather_files(item_iid)]
            all_included = all(f.included for f in files) if files else False
            new_state = not all_included
            for f in files:
                f.included = new_state
            self._refresh_all_labels()
            self._notify_changed()

    def _notify_changed(self):
        if self.on_selection_changed:
            self.on_selection_changed()

```

==================================================
FILE: ui/main_window.py
TYPE: Kod
==================================================

```python
"""
ui/main_window.py

Huvudfönstret för AIDE. Kopplar samman scanner, classifier, file_tree,
preview, settings_window och exporters till en fungerande desktopapp.

Visuellt stilmatchad mot syskonverktyget G.A.M.E. B.R.I.D.G.E. (se
ui/theme.py för den delade färgpaletten/typografin) — samma mörka
CustomTkinter-identitet, statuslampa, panelstruktur och knappstil.

GUI-koden är medvetet hållen skild från filanalys/export-logiken:
den anropar bara funktioner i core/ och exporters/ (avsnitt 30).
"""

from __future__ import annotations

import os
import queue
import threading
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk

from core.classifier import CATEGORY_UNKNOWN
from core.plugin_base import PluginFileInfo
from core.plugin_loader import discover_plugins
from core.scanner import ScanResult, ScannedFile, scan_sources
from core.security import ConflictStrategy, sanitize_filename
from core.settings import Settings, load_settings
from exporters.json_exporter import export_json_manifest
from exporters.markdown_exporter import export_markdown
from exporters.text_exporter import export_text
from exporters.tree_exporter import export_tree
from ui.file_tree import FileTreeView
from ui.preview import PreviewWindow
from ui.settings_window import SettingsWindow
from ui import theme

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGINS_DIR = os.path.join(PROJECT_ROOT, "plugins")


def _to_plugin_file_info(f: ScannedFile) -> PluginFileInfo:
    return PluginFileInfo(
        relative_path=f.relative_path,
        absolute_path=f.absolute_path,
        filename=f.filename,
        extension=f.extension,
        category=f.category,
        size_bytes=f.size_bytes,
        is_sensitive=f.is_sensitive,
        is_binary=f.is_binary,
    )


class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(theme.APP_TITLE)
        self.geometry("1220x780")
        self.minsize(960, 620)
        self.configure(fg_color=theme.COLOR_BG_MAIN)

        self.settings: Settings = load_settings()
        self.source_roots: list[str] = []
        self.export_dir: str = self.settings.default_export_dir or ""
        self._cancel_event: threading.Event | None = None
        self._worker_thread: threading.Thread | None = None
        self._ui_queue: "queue.Queue" = queue.Queue()
        self._plugin_exporters: dict[str, callable] = {}

        self._configure_treeview_style()
        self._build_top_bar()
        self._build_matrix_bar()
        self._build_body()
        self._build_bottom_bar()
        self._build_status_bar()

        self.plugins = discover_plugins(PLUGINS_DIR, log_callback=self._log)
        self._register_plugin_exporters()

        self._poll_queue()

    # ------------------------------------------------------------------
    # ttk-tema för filträdet (ttk saknar mörkt tema som standard)
    # ------------------------------------------------------------------

    def _configure_treeview_style(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(
            "Treeview",
            background=theme.COLOR_BG_PANEL_ALT,
            fieldbackground=theme.COLOR_BG_PANEL_ALT,
            foreground=theme.COLOR_TEXT_PRIMARY,
            borderwidth=0,
            rowheight=24,
            font=theme.FONT_UI,
        )
        style.configure(
            "Treeview.Heading",
            background=theme.COLOR_BG_PANEL,
            foreground=theme.COLOR_TEXT_MUTED,
            borderwidth=0,
            font=theme.FONT_SECTION,
        )
        style.map(
            "Treeview",
            background=[("selected", theme.COLOR_BLUE_DARK)],
            foreground=[("selected", "#FFFFFF")],
        )
        style.map("Treeview.Heading", background=[("active", theme.COLOR_BG_PANEL)])
        style.configure("Vertical.TScrollbar", background=theme.COLOR_BG_PANEL, troughcolor=theme.COLOR_BG_MAIN)
        style.configure("Horizontal.TScrollbar", background=theme.COLOR_BG_PANEL, troughcolor=theme.COLOR_BG_MAIN)
        style.configure("TFrame", background=theme.COLOR_BG_MAIN)
        style.configure("TLabel", background=theme.COLOR_BG_MAIN, foreground=theme.COLOR_TEXT_PRIMARY)
        style.configure("TEntry", fieldbackground=theme.COLOR_BG_PANEL_ALT, foreground=theme.COLOR_TEXT_PRIMARY)

    # ------------------------------------------------------------------
    # Övre panel: statuslampa, källor/export, primära åtgärder
    # (motsvarar GameBridges top_frame)
    # ------------------------------------------------------------------

    def _build_top_bar(self):
        top = ctk.CTkFrame(self, corner_radius=10, fg_color=theme.COLOR_BG_PANEL)
        top.pack(pady=(10, 5), padx=10, fill="x")

        self.status_lamp = ctk.CTkLabel(
            top, text="●", text_color=theme.status_lamp_color("idle"),
            font=("Arial", 22),
        )
        self.status_lamp.pack(side="left", padx=(15, 5), pady=10)

        self.status_label = ctk.CTkLabel(top, text="Status: Redo", font=theme.FONT_TITLE)
        self.status_label.pack(side="left", padx=5, pady=10)

        ctk.CTkButton(
            top, text="Bygg paket", command=self._start_build, width=140,
            fg_color=theme.COLOR_GREEN_DARK, hover_color=theme.COLOR_GREEN,
        ).pack(side="right", padx=(5, 15), pady=10)

        ctk.CTkButton(
            top, text="Avbryt", command=self._cancel_operation, width=110,
            fg_color=theme.COLOR_RED_DARK, hover_color=theme.COLOR_RED,
        ).pack(side="right", padx=5, pady=10)

        ctk.CTkButton(
            top, text="Skanna", command=self._start_scan, width=120,
            fg_color=theme.COLOR_BLUE_DARK, hover_color=theme.COLOR_BLUE,
        ).pack(side="right", padx=5, pady=10)

        self.export_format_var = tk.StringVar(value=self.settings.default_export_format)
        self.export_format_menu = ctk.CTkOptionMenu(
            top, values=["markdown", "text", "tree", "json"], variable=self.export_format_var,
            width=110, fg_color=theme.COLOR_GRAY_DARK, button_color=theme.COLOR_GRAY,
            command=self._on_export_format_change,
        )
        self.export_format_menu.pack(side="right", padx=10, pady=10)

    # ------------------------------------------------------------------
    # "Matrix"-panel: samlade kontroller/togglar i grid
    # (motsvarar GameBridges matrix_frame / CHANNEL AND SIGNAL MATRIX)
    # ------------------------------------------------------------------

    def _build_matrix_bar(self):
        matrix = ctk.CTkFrame(self, corner_radius=10, fg_color=theme.COLOR_BG_PANEL)
        matrix.pack(pady=5, padx=10, fill="x")

        ctk.CTkLabel(
            matrix, text="SKANNINGS- OCH URVALSKONTROLL", font=theme.FONT_SECTION,
            text_color=theme.COLOR_TEXT_MUTED,
        ).pack(anchor="w", padx=15, pady=(8, 2))

        grid = ctk.CTkFrame(matrix, fg_color="transparent")
        grid.pack(fill="x", padx=15, pady=(0, 10))

        ctk.CTkButton(
            grid, text="Välj källmapp", command=self._choose_source, width=130,
            fg_color=theme.COLOR_GRAY_DARK, hover_color=theme.COLOR_GRAY,
        ).grid(row=0, column=0, padx=(0, 8), pady=8, sticky="w")

        ctk.CTkButton(
            grid, text="Ta bort vald källa", command=self._remove_source, width=140,
            fg_color=theme.COLOR_GRAY_DARK, hover_color=theme.COLOR_GRAY,
        ).grid(row=0, column=1, padx=8, pady=8, sticky="w")

        ctk.CTkButton(
            grid, text="Välj exportmapp", command=self._choose_export_dir, width=140,
            fg_color=theme.COLOR_GRAY_DARK, hover_color=theme.COLOR_GRAY,
        ).grid(row=0, column=2, padx=8, pady=8, sticky="w")

        ctk.CTkButton(
            grid, text="Förhandsgranska", command=self._preview, width=140,
            fg_color=theme.COLOR_GRAY_DARK, hover_color=theme.COLOR_GRAY,
        ).grid(row=0, column=3, padx=8, pady=8, sticky="w")

        ctk.CTkButton(
            grid, text="Rensa", command=self._clear_all, width=90,
            fg_color=theme.COLOR_RED_DARK, hover_color=theme.COLOR_RED,
        ).grid(row=0, column=4, padx=8, pady=8, sticky="w")

        ctk.CTkButton(
            grid, text="Inställningar", command=self._open_settings, width=120,
            fg_color=theme.COLOR_GRAY_DARK, hover_color=theme.COLOR_GRAY,
        ).grid(row=0, column=5, padx=8, pady=8, sticky="w")

        ctk.CTkButton(
            grid, text="Markera alla", command=lambda: self._set_all(True), width=110,
            fg_color=theme.COLOR_GRAY_DARK, hover_color=theme.COLOR_GRAY,
        ).grid(row=1, column=0, padx=(0, 8), pady=(0, 8), sticky="w")

        ctk.CTkButton(
            grid, text="Avmarkera alla", command=lambda: self._set_all(False), width=120,
            fg_color=theme.COLOR_GRAY_DARK, hover_color=theme.COLOR_GRAY,
        ).grid(row=1, column=1, padx=8, pady=(0, 8), sticky="w")

        self.category_var = tk.StringVar()
        self.category_combo = ctk.CTkOptionMenu(
            grid, values=["–"], variable=self.category_var, width=130,
            fg_color=theme.COLOR_GRAY_DARK, button_color=theme.COLOR_GRAY,
        )
        self.category_combo.grid(row=1, column=2, padx=8, pady=(0, 8), sticky="w")

        ctk.CTkButton(
            grid, text="Markera kategori", command=lambda: self._set_category(True), width=140,
            fg_color=theme.COLOR_GRAY_DARK, hover_color=theme.COLOR_GRAY,
        ).grid(row=1, column=3, padx=8, pady=(0, 8), sticky="w")

        ctk.CTkButton(
            grid, text="Avmarkera kategori", command=lambda: self._set_category(False), width=150,
            fg_color=theme.COLOR_GRAY_DARK, hover_color=theme.COLOR_GRAY,
        ).grid(row=1, column=4, padx=8, pady=(0, 8), sticky="w")

        self.show_binary_switch = ctk.CTkSwitch(
            grid, text="Visa binärfiler", command=self._on_quick_toggle,
            font=theme.FONT_UI, text_color=theme.COLOR_TEXT_PRIMARY, progress_color=theme.COLOR_BLUE,
        )
        self.show_binary_switch.grid(row=1, column=5, padx=8, pady=(0, 8), sticky="w")
        if self.settings.show_binary_files:
            self.show_binary_switch.select()

    # ------------------------------------------------------------------
    # Kropp: källor, filter, filträd (vänster) + status/logg (höger)
    # ------------------------------------------------------------------

    def _build_body(self):
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=10)

        left = ctk.CTkFrame(body, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True)

        src_frame = ctk.CTkFrame(left, corner_radius=10, fg_color=theme.COLOR_BG_PANEL)
        src_frame.pack(fill="x", pady=(0, 6))
        ctk.CTkLabel(
            src_frame, text="KÄLLMAPPAR", font=theme.FONT_SECTION, text_color=theme.COLOR_TEXT_MUTED,
        ).pack(anchor="w", padx=12, pady=(8, 2))
        self.sources_listbox = tk.Listbox(
            src_frame, height=3, bg=theme.COLOR_BG_PANEL_ALT, fg=theme.COLOR_TEXT_PRIMARY,
            selectbackground=theme.COLOR_BLUE_DARK, borderwidth=0, highlightthickness=0,
        )
        self.sources_listbox.pack(fill="x", padx=12, pady=(0, 10))

        filter_frame = ctk.CTkFrame(left, fg_color="transparent")
        filter_frame.pack(fill="x", pady=(0, 6))
        ctk.CTkLabel(filter_frame, text="Filter:", font=theme.FONT_UI).pack(side="left")
        self.filter_var = tk.StringVar()
        self.filter_var.trace_add("write", lambda *_: self.file_tree.apply_filter(self.filter_var.get()))
        ctk.CTkEntry(
            filter_frame, textvariable=self.filter_var, placeholder_text="Sök filnamn, sökväg, kategori...",
            fg_color=theme.COLOR_BG_PANEL_ALT,
        ).pack(side="left", fill="x", expand=True, padx=6)

        tree_container = ctk.CTkFrame(left, corner_radius=10, fg_color=theme.COLOR_BG_PANEL)
        tree_container.pack(fill="both", expand=True)
        self.file_tree = FileTreeView(tree_container, on_selection_changed=self._update_counts)
        self.file_tree.pack(fill="both", expand=True, padx=8, pady=8)

        right = ctk.CTkFrame(body, width=320, fg_color="transparent")
        right.pack(side="left", fill="y", padx=(10, 0))
        right.pack_propagate(False)

        info_frame = ctk.CTkFrame(right, corner_radius=10, fg_color=theme.COLOR_BG_PANEL)
        info_frame.pack(fill="x")
        ctk.CTkLabel(
            info_frame, text="STATUS", font=theme.FONT_SECTION, text_color=theme.COLOR_TEXT_MUTED,
        ).pack(anchor="w", padx=12, pady=(10, 4))

        self.export_dir_label = self._status_row(info_frame, "Exportmapp: (ej vald)")
        self.found_label = self._status_row(info_frame, "Hittade filer: 0")
        self.included_label = self._status_row(info_frame, "Inkluderade: 0")
        self.excluded_label = self._status_row(info_frame, "Exkluderade: 0")
        self.sensitive_label = self._status_row(info_frame, "Känsliga filer: 0", color=theme.COLOR_RED)
        self.op_label = self._status_row(info_frame, "Aktuell operation: Inaktiv")

        self.progress = ctk.CTkProgressBar(info_frame, progress_color=theme.COLOR_BLUE)
        self.progress.pack(fill="x", padx=12, pady=(6, 12))
        self.progress.set(0)

        log_frame = ctk.CTkFrame(right, corner_radius=10, fg_color=theme.COLOR_BG_PANEL)
        log_frame.pack(fill="both", expand=True, pady=(10, 0))
        ctk.CTkLabel(
            log_frame, text="LOGG", font=theme.FONT_SECTION, text_color=theme.COLOR_TEXT_MUTED,
        ).pack(anchor="w", padx=12, pady=(10, 4))
        self.log_text = ctk.CTkTextbox(
            log_frame, font=theme.FONT_MONO, corner_radius=8, fg_color=theme.COLOR_BG_PANEL_ALT,
            text_color=theme.COLOR_TEXT_PRIMARY,
        )
        self.log_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.log_text.configure(state="disabled")

    def _status_row(self, parent, text, color=None):
        label = ctk.CTkLabel(
            parent, text=text, font=theme.FONT_UI,
            text_color=color or theme.COLOR_TEXT_PRIMARY, anchor="w",
        )
        label.pack(anchor="w", padx=12, pady=1)
        return label

    # ------------------------------------------------------------------
    # Nedre panel: avbrott/lås av urval + inställningsgenväg
    # (motsvarar GameBridges bottom_frame/control_frame)
    # ------------------------------------------------------------------

    def _build_bottom_bar(self):
        control = ctk.CTkFrame(self, fg_color="transparent")
        control.pack(pady=(0, 5), padx=10, fill="x", side="bottom")

        self.lock_switch = ctk.CTkSwitch(
            control, text="Lås urval (skydda mot ändringar)", font=theme.FONT_UI,
            text_color=theme.COLOR_TEXT_PRIMARY, progress_color=theme.COLOR_RED,
            command=self._on_lock_toggle,
        )
        self.lock_switch.pack(side="left", padx=5)

        version_label = ctk.CTkLabel(
            control, text=f"AIDE v{theme.APP_VERSION}", font=theme.FONT_UI, text_color=theme.COLOR_TEXT_MUTED,
        )
        version_label.pack(side="right", padx=5)

    def _build_status_bar(self):
        self.status_var = tk.StringVar(value="Redo.")
        bar = ctk.CTkLabel(
            self, textvariable=self.status_var, anchor="w", font=theme.FONT_UI,
            text_color=theme.COLOR_TEXT_MUTED, fg_color=theme.COLOR_BG_PANEL, corner_radius=0,
        )
        bar.pack(fill="x", side="bottom")

    # ------------------------------------------------------------------
    # Plugins
    # ------------------------------------------------------------------

    def _register_plugin_exporters(self):
        """Samlar in exportformat som plugins registrerar och gör dem valbara."""
        self._plugin_exporters.clear()
        for plugin in self.plugins.values():
            try:
                exporters = plugin.get_exporters()
            except Exception as exc:
                self._log(f"⚠ Plugin '{plugin.plugin_name}' kraschade i get_exporters(): {exc}")
                continue
            for fmt_name, fn in (exporters or {}).items():
                if fmt_name in ("markdown", "text", "tree", "json"):
                    self._log(f"⚠ Plugin '{plugin.plugin_name}' försökte registrera reserverat formatnamn '{fmt_name}', hoppar över.")
                    continue
                self._plugin_exporters[fmt_name] = fn

        base_formats = ["markdown", "text", "tree", "json"]
        all_formats = base_formats + sorted(self._plugin_exporters.keys())
        self.export_format_menu.configure(values=all_formats)

    def _apply_plugin_classification(self, files: list[ScannedFile]):
        """Låter plugins komplettera klassificeringen av 'Okänd'-filer (Identify-fasen)."""
        unknown_files = [f for f in files if f.category == CATEGORY_UNKNOWN]
        if not unknown_files or not self.plugins:
            return
        for f in unknown_files:
            info = _to_plugin_file_info(f)
            for plugin in self.plugins.values():
                try:
                    result = plugin.on_classify(info)
                except Exception as exc:
                    self._log(f"⚠ Plugin '{plugin.plugin_name}' kraschade i on_classify(): {exc}")
                    continue
                if result:
                    f.category = result.get("category", f.category)
                    f.language = result.get("language", f.language)
                    f.is_sensitive = result.get("is_sensitive", f.is_sensitive)
                    break  # första plugin som svarar vinner

    def _notify_plugins_scan_complete(self, files: list[ScannedFile]):
        if not self.plugins:
            return
        infos = [_to_plugin_file_info(f) for f in files]
        for plugin in self.plugins.values():
            try:
                plugin.on_scan_complete(infos)
            except Exception as exc:
                self._log(f"⚠ Plugin '{plugin.plugin_name}' kraschade i on_scan_complete(): {exc}")

    def _apply_plugin_before_export(self, files: list[ScannedFile]) -> list[ScannedFile]:
        """Ger plugins chansen att filtrera urvalet strax innan export (Determine-fasen)."""
        if not self.plugins:
            return files
        by_path = {f.absolute_path: f for f in files}
        current = files
        for plugin in self.plugins.values():
            try:
                infos = [_to_plugin_file_info(f) for f in current]
                result = plugin.on_before_export(infos)
            except Exception as exc:
                self._log(f"⚠ Plugin '{plugin.plugin_name}' kraschade i on_before_export(): {exc}")
                continue
            if result is not None:
                new_current = [by_path[info.absolute_path] for info in result if info.absolute_path in by_path]
                self._log(f"Plugin '{plugin.plugin_name}' justerade exporturvalet: {len(current)} → {len(new_current)} filer.")
                current = new_current
        return current

    # ------------------------------------------------------------------
    # Källmappar
    # ------------------------------------------------------------------

    def _choose_source(self):
        directory = filedialog.askdirectory(title="Välj källmapp")
        if directory and directory not in self.source_roots:
            self.source_roots.append(directory)
            self.sources_listbox.insert("end", directory)

    def _remove_source(self):
        selection = self.sources_listbox.curselection()
        if not selection:
            return
        index = selection[0]
        self.sources_listbox.delete(index)
        del self.source_roots[index]

    def _choose_export_dir(self):
        directory = filedialog.askdirectory(title="Välj exportmapp")
        if directory:
            self.export_dir = directory
            self.export_dir_label.configure(text=f"Exportmapp: {directory}")

    def _on_export_format_change(self, value):
        self.settings.default_export_format = value

    def _on_quick_toggle(self):
        self.settings.show_binary_files = self.show_binary_switch.get() == 1

    def _on_lock_toggle(self):
        locked = self.lock_switch.get() == 1
        self._log("Urval låst." if locked else "Urval upplåst.")

    # ------------------------------------------------------------------
    # Skanning
    # ------------------------------------------------------------------

    def _start_scan(self):
        if self.lock_switch.get() == 1:
            messagebox.showinfo("Urval låst", "Lås upp urvalet innan du kör en ny skanning.")
            return
        if not self.source_roots:
            messagebox.showwarning("Inga källor", "Välj minst en källmapp innan skanning.")
            return
        if self._worker_thread and self._worker_thread.is_alive():
            messagebox.showinfo("Pågår redan", "En operation pågår redan.")
            return

        self._log(f"Scan started: {', '.join(self.source_roots)}")
        self.op_label.configure(text="Aktuell operation: Skannar...")
        self.status_label.configure(text="Status: Processar...")
        self.status_lamp.configure(text_color=theme.status_lamp_color("busy"))
        self.progress.configure(mode="indeterminate")
        self.progress.start()
        self._cancel_event = threading.Event()

        def worker():
            result = scan_sources(
                source_roots=self.source_roots,
                ignore_dirs=set(self.settings.ignore_dirs),
                ignore_files=set(self.settings.ignore_files),
                sensitive_patterns=self.settings.sensitive_patterns,
                show_hidden=self.settings.show_hidden_files,
                show_binary=self.settings.show_binary_files,
                progress_callback=lambda done, total, path: self._ui_queue.put(("scan_progress", done, path)),
                cancel_event=self._cancel_event,
            )
            self._ui_queue.put(("scan_done", result))

        self._worker_thread = threading.Thread(target=worker, daemon=True)
        self._worker_thread.start()

    def _on_scan_done(self, result: ScanResult):
        self.progress.stop()
        self.progress.configure(mode="determinate")
        self.progress.set(0)
        self.op_label.configure(text="Aktuell operation: Inaktiv")
        self.status_label.configure(text="Status: Redo")

        if result.cancelled:
            self._log("Scan cancelled by user")
            self.status_var.set("Skanning avbruten.")
            self.status_lamp.configure(text_color=theme.status_lamp_color("idle"))
            return

        for path, reason in result.errors:
            self._log(f"⚠ Kunde inte läsa: {path} — {reason}")

        sensitive_count = sum(1 for f in result.files if f.is_sensitive)
        self._log(f"{len(result.files)} files discovered")
        if sensitive_count:
            self._log(f"{sensitive_count} sensitive files detected")

        self._apply_plugin_classification(result.files)
        self._notify_plugins_scan_complete(result.files)

        def default_checked(f):
            if f.is_sensitive:
                return False
            if f.is_binary and not self.settings.show_binary_files:
                return False
            return self.settings.default_checkbox_state

        self.file_tree.load_files(result.files, default_checked_fn=default_checked)
        categories = self.file_tree.get_categories() or ["–"]
        self.category_combo.configure(values=categories)
        self.category_var.set(categories[0])

        selected_count = sum(1 for f in result.files if f.included)
        self._log(f"{selected_count} files selected")
        self.status_var.set(f"Skanning klar: {len(result.files)} filer hittade.")
        self.status_lamp.configure(text_color=theme.status_lamp_color("ok"))
        self._update_counts()

    # ------------------------------------------------------------------
    # Checkbox-styrning
    # ------------------------------------------------------------------

    def _set_all(self, included: bool):
        if self.lock_switch.get() == 1:
            return
        self.file_tree.set_all(included)

    def _set_category(self, included: bool):
        if self.lock_switch.get() == 1:
            return
        category = self.category_var.get()
        if category and category != "–":
            self.file_tree.set_category(category, included)

    def _clear_all(self):
        self.source_roots.clear()
        self.sources_listbox.delete(0, "end")
        self.file_tree.load_files([])
        self.category_combo.configure(values=["–"])
        self.category_var.set("–")
        self._update_counts()
        self._log("Cleared sources and file list")
        self.status_var.set("Rensat.")
        self.status_lamp.configure(text_color=theme.status_lamp_color("idle"))

    def _update_counts(self):
        all_files = self.file_tree.get_all_files()
        included = self.file_tree.get_included_files()
        self.found_label.configure(text=f"Hittade filer: {len(all_files)}")
        self.included_label.configure(text=f"Inkluderade: {len(included)}")
        self.excluded_label.configure(text=f"Exkluderade: {len(all_files) - len(included)}")
        self.sensitive_label.configure(
            text=f"Känsliga filer: {sum(1 for f in all_files if f.is_sensitive)}"
        )

    # ------------------------------------------------------------------
    # Förhandsgranskning & export
    # ------------------------------------------------------------------

    def _preview(self):
        all_files = self.file_tree.get_all_files()
        if not all_files:
            messagebox.showinfo("Inget att förhandsgranska", "Skanna en källmapp först.")
            return
        PreviewWindow(self, all_files, self.source_roots)

    def _start_build(self):
        included = self.file_tree.get_included_files()
        if not included:
            messagebox.showwarning("Inget markerat", "Markera minst en fil innan paketering.")
            return
        if not self.export_dir:
            messagebox.showwarning("Ingen exportmapp", "Välj en exportmapp innan paketering.")
            return
        if self._worker_thread and self._worker_thread.is_alive():
            messagebox.showinfo("Pågår redan", "En operation pågår redan.")
            return

        included = self._apply_plugin_before_export(included)
        if not included:
            messagebox.showwarning("Inget markerat", "Inga filer kvar att exportera efter plugin-filtrering.")
            return

        strategy = self._ask_conflict_strategy()
        if strategy is None:
            return

        self.op_label.configure(text="Aktuell operation: Paketerar...")
        self.status_label.configure(text="Status: Processar...")
        self.status_lamp.configure(text_color=theme.status_lamp_color("busy"))
        self.progress.configure(mode="indeterminate")
        self.progress.start()

        project_name = os.path.basename(self.source_roots[0]) if self.source_roots else "AIDE_Project"
        safe_name = sanitize_filename(project_name)

        def worker():
            written = []
            fmt = self.settings.default_export_format
            log = lambda msg: self._ui_queue.put(("log", msg))
            try:
                if fmt == "markdown":
                    path = export_markdown(project_name, self.source_roots, included, self.export_dir,
                                            filename=f"{safe_name}.md",
                                            conflict_strategy=strategy, log_callback=log)
                elif fmt == "text":
                    path = export_text(project_name, self.source_roots, included, self.export_dir,
                                        filename=f"{safe_name}.txt",
                                        conflict_strategy=strategy, log_callback=log)
                elif fmt == "tree":
                    path = export_tree(project_name, self.source_roots, included, self.export_dir,
                                        filename=f"{safe_name}_tree.md",
                                        conflict_strategy=strategy, log_callback=log)
                elif fmt == "json":
                    path = export_json_manifest(project_name, self.source_roots, included, self.export_dir,
                                                 filename=f"{safe_name}_manifest.json",
                                                 conflict_strategy=strategy, log_callback=log)
                elif fmt in self._plugin_exporters:
                    plugin_infos = [_to_plugin_file_info(f) for f in included]
                    path = self._plugin_exporters[fmt](
                        project_name, self.source_roots, plugin_infos, self.export_dir,
                        strategy, log,
                    )
                else:
                    log(f"⚠ Okänt exportformat '{fmt}', faller tillbaka på markdown.")
                    path = export_markdown(project_name, self.source_roots, included, self.export_dir,
                                            filename=f"{safe_name}.md",
                                            conflict_strategy=strategy, log_callback=log)
                if path:
                    written.append(path)

                manifest_path = export_json_manifest(
                    project_name, self.source_roots, included, self.export_dir,
                    filename=f"{safe_name}_manifest.json",
                    conflict_strategy=strategy, log_callback=log,
                )
                if manifest_path and manifest_path not in written:
                    written.append(manifest_path)

                self._ui_queue.put(("build_done", written))
            except Exception as exc:
                self._ui_queue.put(("build_error", str(exc)))

        self._worker_thread = threading.Thread(target=worker, daemon=True)
        self._worker_thread.start()

    def _ask_conflict_strategy(self) -> ConflictStrategy | None:
        answer = messagebox.askyesnocancel(
            "Konflikthantering",
            "Om filer redan finns i exportmappen:\n\n"
            "Ja = Skriv över\nNej = Skapa ny version\nAvbryt = Hoppa över befintliga filer",
        )
        if answer is None:
            return ConflictStrategy.SKIP
        return ConflictStrategy.OVERWRITE if answer else ConflictStrategy.NEW_VERSION

    def _on_build_done(self, written_paths: list[str]):
        self.progress.stop()
        self.progress.configure(mode="determinate")
        self.progress.set(0)
        self.op_label.configure(text="Aktuell operation: Inaktiv")
        self.status_label.configure(text="Status: Redo")
        self._log("Package created")
        if written_paths:
            self.status_var.set(f"Paket skapat: {len(written_paths)} fil(er) skrivna.")
            self.status_lamp.configure(text_color=theme.status_lamp_color("ok"))
            messagebox.showinfo("Klart", "Paket skapat:\n" + "\n".join(written_paths))
        else:
            self.status_var.set("Ingen fil skrevs (allt hoppades över).")
            self.status_lamp.configure(text_color=theme.status_lamp_color("idle"))

    def _on_build_error(self, message: str):
        self.progress.stop()
        self.progress.configure(mode="determinate")
        self.progress.set(0)
        self.op_label.configure(text="Aktuell operation: Inaktiv")
        self.status_label.configure(text="Status: Redo")
        self.status_lamp.configure(text_color=theme.status_lamp_color("error"))
        self._log(f"⚠ Fel vid paketering: {message}")
        messagebox.showerror("Fel", f"Kunde inte skapa paketet:\n{message}")

    def _cancel_operation(self):
        if self._cancel_event is not None:
            self._cancel_event.set()
            self._log("Cancel requested by user")

    # ------------------------------------------------------------------
    # Inställningar
    # ------------------------------------------------------------------

    def _open_settings(self):
        SettingsWindow(self, self.settings, on_saved=self._on_settings_saved)

    def _on_settings_saved(self, settings: Settings):
        self.settings = settings
        self.export_format_var.set(settings.default_export_format)
        self.show_binary_switch.select() if settings.show_binary_files else self.show_binary_switch.deselect()
        self._log("Settings updated")

    # ------------------------------------------------------------------
    # Logg och köhantering (bakgrundstråd -> huvudtråd)
    # ------------------------------------------------------------------

    def _log(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"{timestamp}  {message}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _poll_queue(self):
        try:
            while True:
                item = self._ui_queue.get_nowait()
                kind = item[0]
                if kind == "scan_progress":
                    _, done, path = item
                    self.status_var.set(f"Skannar... {done} filer ({path})")
                elif kind == "scan_done":
                    self._on_scan_done(item[1])
                elif kind == "build_done":
                    self._on_build_done(item[1])
                elif kind == "build_error":
                    self._on_build_error(item[1])
                elif kind == "log":
                    self._log(item[1])
        except queue.Empty:
            pass
        self.after(100, self._poll_queue)

    def on_close(self):
        if self._cancel_event is not None:
            self._cancel_event.set()
        for plugin in self.plugins.values():
            try:
                plugin.shutdown()
            except Exception:
                pass
        self.destroy()

```

==================================================
FILE: ui/preview.py
TYPE: Kod
==================================================

```python
"""
ui/preview.py

Förhandsgranskningsfönster (avsnitt 15). Visar sammanställning av vad
som kommer inkluderas/exkluderas innan export, samt eventuella
varningar. Visuellt stilmatchad mot huvudfönstret (ui/theme.py).
"""

from __future__ import annotations

from tkinter import ttk

import customtkinter as ctk

from ui import theme


class PreviewWindow(ctk.CTkToplevel):
    def __init__(self, parent, all_files, source_roots):
        super().__init__(parent)
        self.title("Förhandsgranskning — A.I.D.E.")
        self.geometry("760x600")
        self.configure(fg_color=theme.COLOR_BG_MAIN)
        self.transient(parent)

        included = [f for f in all_files if f.included]
        excluded = [f for f in all_files if not f.included]
        total_size = sum(f.size_bytes for f in included)
        sensitive_included = [f for f in included if f.is_sensitive]

        by_category = {}
        for f in included:
            by_category[f.category] = by_category.get(f.category, 0) + 1

        header = ctk.CTkFrame(self, corner_radius=10, fg_color=theme.COLOR_BG_PANEL)
        header.pack(fill="x", padx=12, pady=(12, 6))

        ctk.CTkLabel(
            header, text="SAMMANFATTNING", font=theme.FONT_SECTION, text_color=theme.COLOR_TEXT_MUTED,
        ).pack(anchor="w", padx=14, pady=(12, 4))

        def row(text, color=None):
            ctk.CTkLabel(
                header, text=text, font=theme.FONT_UI,
                text_color=color or theme.COLOR_TEXT_PRIMARY, anchor="w",
            ).pack(anchor="w", padx=14, pady=1)

        row(f"Källor: {', '.join(str(s) for s in source_roots)}")
        row(f"Inkluderade filer: {len(included)}")
        row(f"Exkluderade filer: {len(excluded)}")
        row(f"Total storlek (inkluderat): {_human_size(total_size)}")

        cat_text = ", ".join(f"{cat}: {count}" for cat, count in sorted(by_category.items()))
        row(f"Kategorifördelning: {cat_text or '–'}")

        if sensitive_included:
            row(
                f"⚠ Varning: {len(sensitive_included)} känslig(a) fil(er) är markerade för export!",
                color=theme.COLOR_RED,
            )

        ctk.CTkFrame(header, fg_color="transparent", height=8).pack()

        # Lista
        list_frame = ctk.CTkFrame(self, corner_radius=10, fg_color=theme.COLOR_BG_PANEL)
        list_frame.pack(fill="both", expand=True, padx=12, pady=(0, 6))

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(
            "Preview.Treeview",
            background=theme.COLOR_BG_PANEL_ALT,
            fieldbackground=theme.COLOR_BG_PANEL_ALT,
            foreground=theme.COLOR_TEXT_PRIMARY,
            borderwidth=0,
            rowheight=22,
            font=theme.FONT_UI,
        )
        style.configure(
            "Preview.Treeview.Heading",
            background=theme.COLOR_BG_PANEL,
            foreground=theme.COLOR_TEXT_MUTED,
            font=theme.FONT_SECTION,
        )

        columns = ("status", "category", "size")
        tree = ttk.Treeview(list_frame, columns=columns, show="tree headings", style="Preview.Treeview")
        tree.heading("#0", text="Fil")
        tree.heading("status", text="Status")
        tree.heading("category", text="Kategori")
        tree.heading("size", text="Storlek")
        tree.column("#0", width=380)
        tree.column("status", width=110)
        tree.column("category", width=140)
        tree.column("size", width=80, anchor="e")

        tree.pack(side="left", fill="both", expand=True, padx=8, pady=8)

        for f in sorted(all_files, key=lambda x: x.relative_path.lower()):
            status = "Inkluderas" if f.included else "Exkluderas"
            if f.is_sensitive:
                status += " ⚠"
            tree.insert("", "end", text=f.relative_path, values=(status, f.category, f.size_human))

        ctk.CTkButton(
            self, text="Stäng", command=self.destroy, width=120,
            fg_color=theme.COLOR_GRAY_DARK, hover_color=theme.COLOR_GRAY,
        ).pack(pady=(0, 12))


def _human_size(size_bytes: int) -> str:
    size = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} {unit}"
        size /= 1024
    return f"{size:.1f} GB"

```

==================================================
FILE: ui/settings_window.py
TYPE: Kod
==================================================

```python
"""
ui/settings_window.py

Separat inställningsfönster (avsnitt 23). Sparas lokalt via core/settings.py.
Visuellt stilmatchad mot huvudfönstret / G.A.M.E. B.R.I.D.G.E. (ui/theme.py).
"""

from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from core.settings import Settings, save_settings
from ui import theme


class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, parent, settings: Settings, on_saved=None):
        super().__init__(parent)
        self.title("Inställningar — A.I.D.E.")
        self.geometry("600x600")
        self.configure(fg_color=theme.COLOR_BG_MAIN)
        self.settings = settings
        self.on_saved = on_saved
        self.resizable(False, False)
        self.transient(parent)

        frame = ctk.CTkFrame(self, corner_radius=10, fg_color=theme.COLOR_BG_PANEL)
        frame.pack(fill="both", expand=True, padx=12, pady=12)

        ctk.CTkLabel(
            frame, text="INSTÄLLNINGAR", font=theme.FONT_SECTION, text_color=theme.COLOR_TEXT_MUTED,
        ).pack(anchor="w", padx=16, pady=(14, 6))

        def label(text):
            ctk.CTkLabel(frame, text=text, font=theme.FONT_UI, text_color=theme.COLOR_TEXT_PRIMARY).pack(
                anchor="w", padx=16, pady=(10, 2)
            )

        def entry(var):
            e = ctk.CTkEntry(frame, textvariable=var, fg_color=theme.COLOR_BG_PANEL_ALT, width=550)
            e.pack(padx=16, pady=(0, 2), fill="x")
            return e

        label("Ignorerade kataloger (komma-separerat)")
        self.ignore_dirs_var = tk.StringVar(value=", ".join(settings.ignore_dirs))
        entry(self.ignore_dirs_var)

        label("Ignorerade filnamn (komma-separerat)")
        self.ignore_files_var = tk.StringVar(value=", ".join(settings.ignore_files))
        entry(self.ignore_files_var)

        label("Känsliga filmönster (komma-separerat, t.ex. *.pem)")
        self.sensitive_var = tk.StringVar(value=", ".join(settings.sensitive_patterns))
        entry(self.sensitive_var)

        label("Standard-exportformat")
        self.export_format_var = tk.StringVar(value=settings.default_export_format)
        ctk.CTkOptionMenu(
            frame, values=["markdown", "text", "json"], variable=self.export_format_var,
            fg_color=theme.COLOR_GRAY_DARK, button_color=theme.COLOR_GRAY, width=550,
        ).pack(padx=16, pady=(0, 2), fill="x")

        label("Standard-målmapp")
        self.export_dir_var = tk.StringVar(value=settings.default_export_dir)
        entry(self.export_dir_var)

        switch_frame = ctk.CTkFrame(frame, fg_color="transparent")
        switch_frame.pack(fill="x", padx=16, pady=(16, 4))

        self.show_binary_var = tk.BooleanVar(value=settings.show_binary_files)
        self.show_binary_switch = ctk.CTkSwitch(
            switch_frame, text="Visa binärfiler i listan", variable=self.show_binary_var,
            font=theme.FONT_UI, text_color=theme.COLOR_TEXT_PRIMARY, progress_color=theme.COLOR_BLUE,
        )
        self.show_binary_switch.pack(anchor="w", pady=4)

        self.show_hidden_var = tk.BooleanVar(value=settings.show_hidden_files)
        self.show_hidden_switch = ctk.CTkSwitch(
            switch_frame, text="Visa dolda filer/kataloger", variable=self.show_hidden_var,
            font=theme.FONT_UI, text_color=theme.COLOR_TEXT_PRIMARY, progress_color=theme.COLOR_BLUE,
        )
        self.show_hidden_switch.pack(anchor="w", pady=4)

        self.default_checkbox_var = tk.BooleanVar(value=settings.default_checkbox_state)
        self.default_checkbox_switch = ctk.CTkSwitch(
            switch_frame,
            text="Markera icke-känsliga filer automatiskt vid skanning",
            variable=self.default_checkbox_var,
            font=theme.FONT_UI, text_color=theme.COLOR_TEXT_PRIMARY, progress_color=theme.COLOR_GREEN,
        )
        self.default_checkbox_switch.pack(anchor="w", pady=4)

        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=16, pady=(20, 16), side="bottom")
        ctk.CTkButton(
            btn_frame, text="Avbryt", command=self.destroy, width=110,
            fg_color=theme.COLOR_GRAY_DARK, hover_color=theme.COLOR_GRAY,
        ).pack(side="right", padx=(8, 0))
        ctk.CTkButton(
            btn_frame, text="Spara", command=self._save, width=110,
            fg_color=theme.COLOR_GREEN_DARK, hover_color=theme.COLOR_GREEN,
        ).pack(side="right")

    def _save(self):
        def split_csv(s: str) -> list[str]:
            return [x.strip() for x in s.split(",") if x.strip()]

        self.settings.ignore_dirs = split_csv(self.ignore_dirs_var.get())
        self.settings.ignore_files = split_csv(self.ignore_files_var.get())
        self.settings.sensitive_patterns = split_csv(self.sensitive_var.get())
        self.settings.default_export_format = self.export_format_var.get()
        self.settings.default_export_dir = self.export_dir_var.get().strip()
        self.settings.show_binary_files = self.show_binary_var.get()
        self.settings.show_hidden_files = self.show_hidden_var.get()
        self.settings.default_checkbox_state = self.default_checkbox_var.get()

        save_settings(self.settings)
        if self.on_saved:
            self.on_saved(self.settings)
        self.destroy()

```

==================================================
FILE: ui/theme.py
TYPE: Kod
==================================================

```python
"""
ui/theme.py

Delad visuell identitet för AIDE, medvetet stilmatchad mot syskonverktyget
G.A.M.E. B.R.I.D.G.E. (samma familj av lokala, fristående desktopverktyg).

Färgpaletten är hämtad direkt ur GameBridges interface/client_gui.py så att
de två applikationerna känns som samma produktfamilj:

    #1E293B  – panel-/matrisbakgrund (mörk skiffer)
    #0F172A  – huvudfönstrets bakgrund (ännu mörkare)
    #10B981  – grön accent (aktiv/positiv, t.ex. "Boot"-knappar)
    #059669  – grön, mörkare (knapp-fg_color)
    #3B82F6  – blå accent (sekundära toggles/val)
    #DC2626  – röd (destruktiv/avbryt, fg_color)
    #EF4444  – röd, ljusare (hover)
    #374151  – grå (neutrala knappar, fg_color)
    #4B5563  – grå, ljusare (hover)
    #9CA3AF  – grå text/status (inaktiv lampa)
    #94A3B8  – dämpad rubriktext
    #E2E8F0  – primär ljus text på mörk bakgrund
"""

from __future__ import annotations

COLOR_BG_MAIN = "#0F172A"
COLOR_BG_PANEL = "#1E293B"
COLOR_BG_PANEL_ALT = "#111827"

COLOR_GREEN = "#10B981"
COLOR_GREEN_DARK = "#059669"
COLOR_BLUE = "#3B82F6"
COLOR_BLUE_DARK = "#2563EB"
COLOR_RED = "#EF4444"
COLOR_RED_DARK = "#DC2626"
COLOR_GRAY = "#4B5563"
COLOR_GRAY_DARK = "#374151"
COLOR_GRAY_MUTED = "#9CA3AF"
COLOR_TEXT_MUTED = "#94A3B8"
COLOR_TEXT_PRIMARY = "#E2E8F0"
COLOR_WARNING = "#F59E0B"

FONT_UI = ("Arial", 12)
FONT_UI_BOLD = ("Arial", 12, "bold")
FONT_TITLE = ("Arial", 13, "bold")
FONT_SECTION = ("Arial", 11, "bold")
FONT_MONO = ("Consolas", 12)

APP_TITLE = "A.I.D.E. — Archive · Identify · Determine · Export"
APP_VERSION = "1.0.0"


def status_lamp_color(state: str) -> str:
    """
    Samma statuslampe-princip som GameBridges model_monitor_core:
    grå = inaktiv, gul = pågår, grön = klart, röd = fel.
    """
    return {
        "idle": COLOR_GRAY_MUTED,
        "busy": COLOR_WARNING,
        "ok": COLOR_GREEN,
        "error": COLOR_RED,
    }.get(state, COLOR_GRAY_MUTED)

```

==================================================
FILE: ui/__init__.py
TYPE: Kod
==================================================

```python


```
