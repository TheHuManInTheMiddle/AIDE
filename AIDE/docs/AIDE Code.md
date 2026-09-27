AIDE PROJECT PACKAGE
====================

PROJECT:
AIDE

SOURCE FOLDER(S):
AIDE

FILES:
43

STRUCTURE:

AIDE/
├── core/
│   ├── __init__.py
│   ├── classifier.py
│   ├── easter_eggs.py
│   ├── gbp_runtime.py
│   ├── hotkey_utils.py
│   ├── localization_core.py
│   ├── manifest.py
│   ├── package_builder.py
│   ├── path_core.py
│   ├── plugin_base.py
│   ├── plugin_loader.py
│   ├── plugin_registration.py
│   ├── report_writer.py
│   ├── scanner.py
│   ├── security.py
│   ├── settings.py
│   └── tree_renderer.py
├── exporters/
│   ├── __init__.py
│   ├── json_exporter.py
│   ├── markdown_exporter.py
│   ├── text_exporter.py
│   └── tree_exporter.py
├── locales/
│   └── locales.json
├── plugins/
│   ├── example_plugin/
│   │   └── main_plugin.py
│   ├── gbp_packager/
│   │   └── main_plugin.py
│   ├── pdf_export/
│   │   └── main_plugin.py
│   └── zip_export/
│       └── main_plugin.py
├── tests/
│   ├── __init__.py
│   ├── test_classifier.py
│   ├── test_export.py
│   ├── test_plugin_loader.py
│   ├── test_report_writer.py
│   ├── test_scanner.py
│   └── test_tree_renderer.py
├── ui/
│   ├── __init__.py
│   ├── file_tree.py
│   ├── main_window.py
│   ├── preview.py
│   ├── scan_panel.py
│   ├── settings_window.py
│   └── theme.py
├── main.py
└── requirements.txt

==================================================
FILE: main.py
TYPE: Kod
==================================================

```python
#!/usr/bin/env python3
"""
AIDE – AI Development Export tool
Startpunkt för applikationen.

Två körlägen:

1. GUI (normalfallet):

       python main.py

   eller, som kompilerad .exe:

       AIDE.exe

2. Headless (för anrop utifrån, t.ex. GameBridge-pluginet):

       python main.py --create-report --input rapport.md --export-dir "AIDE Box/report"

   eller, som kompilerad .exe:

       AIDE.exe --create-report --input rapport.md --export-dir "AIDE Box/report"

   Ingen GUI startas i headless-läge — funktionen körs, den skrivna
   sökvägen skrivs ut på stdout, och processen avslutas med
   exitkod 0 (lyckades) eller 1 (misslyckades).

   Det här ÄR AIDE:s minimala kommandoradskontrakt: inga
   nätverksportar, ingen server som körs i bakgrunden — bara
   argv in, resultat ut, avsluta. Samma princip som
   NotepadAdapter redan använder i GameBridge för att starta
   externa .exe-filer (subprocess, inte en levande API-koppling).
   `--input` kan utelämnas för att läsa rapportinnehållet från
   stdin istället för en fil.
"""

from __future__ import annotations

import argparse
import sys


def _run_headless_create_report(args: argparse.Namespace) -> int:
    """
    Kör create_report() utan GUI.

    Returnerar en processavslutningskod (0 = lyckades, 1 =
    misslyckades) så en anropande process — t.ex. en GameBridge-
    adapter via subprocess.run(...) — kan avgöra om det gick bra
    utan att behöva tolka loggtext.
    """
    from core.report_writer import create_report
    from core.security import ConflictStrategy

    if args.input:
        try:
            with open(args.input, "r", encoding="utf-8") as fh:
                report_markdown = fh.read()
        except OSError as exc:
            print(f"[AIDE] Kunde inte läsa --input: {exc}", file=sys.stderr)
            return 1
    else:
        report_markdown = sys.stdin.read()

    strategy_map = {
        "overwrite": ConflictStrategy.OVERWRITE,
        "new_version": ConflictStrategy.NEW_VERSION,
        "skip": ConflictStrategy.SKIP,
    }
    strategy = strategy_map[args.conflict]

    written_path = create_report(
        export_dir=args.export_dir,
        report_markdown=report_markdown,
        project_name=args.project_name,
        conflict_strategy=strategy,
        log_callback=lambda msg: print(f"[AIDE] {msg}", file=sys.stderr),
    )

    if written_path is None:
        return 1

    # Skrivs till stdout (inte stderr) med avsikt: den anropande
    # processen kan läsa av EXAKT skriven sökväg utan att behöva
    # parsa loggrader, bara läsa stdout rakt av.
    print(written_path)
    return 0


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="AIDE",
        description="AIDE – AI Development Export tool",
    )
    parser.add_argument(
        "--create-report", action="store_true",
        help="Headless-läge: skriv en AI-genererad rapport och avsluta (ingen GUI).",
    )
    parser.add_argument(
        "--input", default=None,
        help="Sökväg till en fil med rapportinnehåll (Markdown). "
             "Utelämnas för att läsa innehållet från stdin istället.",
    )
    parser.add_argument(
        "--export-dir", default=None,
        help='Exportmapp rapporten ska skrivas till (t.ex. "AIDE Box/report").',
    )
    parser.add_argument(
        "--project-name", default=None,
        help="Valfritt projektnamn för rapportens rubrikrad.",
    )
    parser.add_argument(
        "--conflict", choices=["overwrite", "new_version", "skip"], default="new_version",
        help="Konfliktstrategi om rapporten redan finns (standard: new_version).",
    )
    return parser


def main() -> int:
    parser = _build_arg_parser()
    args = parser.parse_args()

    if args.create_report:
        if not args.export_dir:
            print("[AIDE] --create-report kräver --export-dir.", file=sys.stderr)
            return 1
        return _run_headless_create_report(args)

    # Normalfallet: starta GUI. Importeras här inne, inte på
    # modulnivå — headless-läget ska aldrig behöva initiera
    # tkinter/customtkinter bara för att skriva en rapportfil.
    from ui.main_window import MainWindow

    app = MainWindow()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())

```

==================================================
FILE: requirements.txt
TYPE: Text
==================================================

```
# AIDE:s körtidslogik (core/, exporters/) använder endast Pythons
# standardbibliotek. Gränssnittet är byggt med CustomTkinter för att
# visuellt matcha syskonverktyget G.A.M.E. B.R.I.D.G.E.
customtkinter>=5.2.0

# Nedanstående behövs endast för att köra testsviten under utveckling.
pytest>=8.0.0

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
FILE: core/easter_eggs.py
TYPE: Kod
==================================================

```python
# -*- coding: utf-8 -*-
"""
core/easter_eggs.py

Små, ofarliga easter eggs i AIDE:s logg. Ren nöje — påverkar aldrig
filurval, klassificering, export eller något annat funktionellt.
Om log_callback saknas gör funktionen ingenting alls.
"""

from __future__ import annotations

import random

# Mycket låg sannolikhet per tillfälle (skanning eller export) — ska
# vara en sällsynt överraskning man kanske ser en gång på flera
# månader, inte en återkommande grej.
_DADDLE_PROBABILITY = 0.002  # ungefär 1 av 500 gånger

_DADDLE_MESSAGE = "[INFO] DADDLE has entered the chat."


def maybe_log_daddle(log_callback) -> None:
    """
    Mycket låg slumpchans att logga en liten hälsning från nästa
    projekt på tapeten. Anropas från scan- och exportflödet.
    """
    if log_callback is None:
        return
    if random.random() < _DADDLE_PROBABILITY:
        log_callback(_DADDLE_MESSAGE)

```

==================================================
FILE: core/gbp_runtime.py
TYPE: Kod
==================================================

```python
# -*- coding: utf-8 -*-
"""
core/gbp_runtime.py

AIDE GBP Runtime — läser in .gbp-paketerade plugins. Samma ZIP-
baserade .gbp-format som GameBridge använder för sina adaptrar (se
tools/build_plugin_package.py och GameBridges "Plugin Packaging
Guide"), men AIDE:s variant letar efter main_plugin.py istället för
main_adapter.py. I övrigt är det här i praktiken en direkt AIDE-
portering av GameBridges egen core/gbp_runtime.py.

SYFTE:
Låter någon som bygger en AIDE-plugin MED externa Python-beroenden
(t.ex. pdf_export-pluginet, som behöver reportlab) paketera hela
pluginet inklusive dess beroenden i en enda .gbp-fil. Mottagaren
behöver då inte själv köra `pip install` för att pluginet ska
fungera — den droppar bara .gbp-filen i sin plugins/-mapp.

RUNTIME-STRUKTUR:

    plugins/
      pdf_export/
        pdf_export.gbp
        temp/                  <- skapas/rensas av GbpRuntime
          main_plugin.py
          dependencies/
            reportlab/
            ...

Den permanenta plugin-mappen hålls ren — .gbp-filen är källan,
temp/ är bara en extraherad arbetskopia som kan raderas och
återskapas fritt utan att något går förlorat.

SÄKERHET: skyddar mot ZIP path traversal (samma försiktighetsprincip
som AIDE:s egen ensure_within_export_dir i core/security.py, fast
här för INKOMMANDE data istället för utgående export). Ett trasigt
eller ogiltigt .gbp-paket kraschar aldrig AIDE:s uppstart (avsnitt 27
i originalspecen) — felet bubblar upp som ett vanligt undantag som
plugin_loader.py fångar och loggar, exakt som en trasig main_plugin.py
redan hanteras idag.
"""

from __future__ import annotations

import os
import shutil
import sys
import zipfile


class GbpRuntime:

    @staticmethod
    def get_temp_dir(plugin_dir: str) -> str:
        """Returnerar pluginets lokala runtime-katalog."""
        return os.path.join(plugin_dir, "temp")

    @staticmethod
    def cleanup_plugin(plugin_dir: str) -> bool:
        """
        Tar bort pluginets temp-runtime-katalog.

        Returnerar True om städningen gick bra (eller inte behövdes
        eftersom ingen temp-katalog fanns), False om den misslyckades.
        """
        temp_dir = GbpRuntime.get_temp_dir(plugin_dir)

        if not os.path.exists(temp_dir):
            return True

        try:
            shutil.rmtree(temp_dir)
            print(f"[GBP-RUNTIME] Rensade runtime: {temp_dir}")
            return True
        except OSError as exc:
            print(f"[GBP-RUNTIME-VARNING] Kunde inte rensa '{temp_dir}': {exc}")
            return False

    @staticmethod
    def cleanup_all(plugins_root: str) -> None:
        """
        Städar ALLA plugins temp-runtime-kataloger. Tänkt att köras
        vid varje AIDE-uppstart (t.ex. från core/plugin_loader.py
        innan discover_plugins() letar efter plugins) så inga gamla
        runtime-rester från en tidigare session kan bli kvar aktiva.
        """
        if not os.path.isdir(plugins_root):
            return

        for folder in os.listdir(plugins_root):
            plugin_dir = os.path.join(plugins_root, folder)

            if not os.path.isdir(plugin_dir):
                continue
            if folder.startswith("__") or folder.startswith("."):
                continue

            temp_dir = GbpRuntime.get_temp_dir(plugin_dir)
            if os.path.exists(temp_dir):
                GbpRuntime.cleanup_plugin(plugin_dir)

    @staticmethod
    def find_gbp_file(plugin_dir: str) -> str | None:
        """
        Letar efter en .gbp-fil direkt i en pluginmapp. Returnerar
        sökvägen till den första hittade, eller None om ingen finns
        — det vanliga fallet för en oförpackad main_plugin.py-plugin.
        """
        if not os.path.isdir(plugin_dir):
            return None
        for filename in sorted(os.listdir(plugin_dir)):
            if filename.lower().endswith(".gbp"):
                return os.path.join(plugin_dir, filename)
        return None

    @staticmethod
    def prepare_plugin(plugin_dir: str, gbp_path: str) -> str:
        """
        Extraherar ett .gbp-paket till pluginets lokala temp-
        runtime-katalog och gör dess buntade beroenden tillgängliga
        för Python.

        Returnerar absolut sökväg till den extraherade runtime-
        katalogen.

        Höjer FileNotFoundError/ValueError vid saknat, ogiltigt
        eller osäkert paket — plugin_loader.py ansvarar för att
        fånga det och logga utan att krascha resten av AIDE.
        """
        plugin_dir = os.path.abspath(plugin_dir)
        gbp_path = os.path.abspath(gbp_path)

        if not os.path.exists(gbp_path):
            raise FileNotFoundError(f"GBP-paket hittades inte: {gbp_path}")

        if not zipfile.is_zipfile(gbp_path):
            raise ValueError(f"Ogiltigt GBP-paket: {gbp_path}")

        # Börja alltid från en ren runtime.
        GbpRuntime.cleanup_plugin(plugin_dir)

        temp_dir = GbpRuntime.get_temp_dir(plugin_dir)
        os.makedirs(temp_dir, exist_ok=True)

        try:
            with zipfile.ZipFile(gbp_path, "r") as archive:
                # Skydd mot ZIP path traversal.
                temp_root = os.path.realpath(temp_dir)

                for member in archive.infolist():
                    member_path = os.path.realpath(
                        os.path.join(temp_dir, member.filename)
                    )
                    if not (
                        member_path == temp_root
                        or member_path.startswith(temp_root + os.sep)
                    ):
                        raise ValueError(
                            f"Osäker sökväg upptäckt i GBP-paketet: {member.filename}"
                        )

                archive.extractall(temp_dir)

        except Exception:
            GbpRuntime.cleanup_plugin(plugin_dir)
            raise

        main_plugin = os.path.join(temp_dir, "main_plugin.py")
        if not os.path.isfile(main_plugin):
            GbpRuntime.cleanup_plugin(plugin_dir)
            raise ValueError("GBP-paketet innehåller ingen main_plugin.py")

        GbpRuntime._register_runtime_paths(temp_dir)

        print(f"[GBP-RUNTIME] Paket laddat: {os.path.basename(gbp_path)}")
        print(f"[GBP-RUNTIME] Runtime-sökväg: {temp_dir}")

        return temp_dir

    @staticmethod
    def _register_runtime_paths(runtime_dir: str) -> None:
        """
        Gör pluginets runtime och dess buntade beroende-kataloger
        tillgängliga för Python. Ingen pip-installation sker här —
        det är redan gjort vid paketeringstillfället, se
        tools/build_plugin_package.py.
        """
        paths = [
            runtime_dir,
            os.path.join(runtime_dir, "lib"),
            os.path.join(runtime_dir, "dependencies"),
        ]
        for path in paths:
            if os.path.isdir(path) and path not in sys.path:
                sys.path.insert(0, path)
                print(f"[GBP-RUNTIME] Python-sökväg tillagd: {path}")

    @staticmethod
    def get_main_plugin_path(runtime_dir: str) -> str:
        """Returnerar sökvägen till den extraherade main_plugin.py."""
        return os.path.join(runtime_dir, "main_plugin.py")

```

==================================================
FILE: core/hotkey_utils.py
TYPE: Kod
==================================================

```python
# -*- coding: utf-8 -*-
"""
core/hotkey_utils.py

Tangentbordsidentifiering för AIDE:s egna GUI-genvägar (Skanna,
Bygg paket, osv), byggd med samma NORMALISERINGSPRINCIP som
GameBridges interface/hardware_io.py (HardwareIO.normalize_key) —
men medvetet UTAN GameBridges externa `keyboard`-bibliotek.

VARFÖR SKILLNADEN ÄR AVSIKTLIG:
GameBridges hotkey-fångst måste fungera GLOBALT över hela systemet
— användaren kan stå inne i ett helt annat program (t.ex. ett spel)
och ändå trigga en PTT-röstinspelning. Det kräver ett systemomfattande
tangentbordshak, därav `keyboard`-biblioteket (och de förhöjda
rättigheter det ibland kräver på Windows).

AIDE är ett vanligt fönsterbaserat skrivbordsprogram. Dess genvägar
(Ctrl+S för Skanna, osv) ska bara reagera NÄR AIDE:s fönster faktiskt
har fokus — exakt det beteende Tkinters egna `bind()`/`bind_all()`
redan ger, helt utan extra beroenden. Att dra in `keyboard`-biblioteket
här hade varit en onödigt tung lösning på ett enklare problem
("undvik överengineering", avsnitt 30 i AIDE:s originalspec).

Om AIDE någon gång FAKTISKT behöver globala genvägar (t.ex. för att
trigga en skanning även när AIDE ligger i bakgrunden) är `keyboard`-
biblioteket rätt verktyg då — men det är inte samma behov som
"ombindningsbara GUI-genvägar", som är vad den här modulen löser.
"""

from __future__ import annotations

from typing import Callable

# Alias -> normaliserat namn. Samma lista som GameBridges
# HardwareIO.normalize_key, plus några Tkinter-specifika varianter.
_MODIFIER_ALIASES = {
    "left ctrl": "ctrl", "right ctrl": "ctrl", "lctrl": "ctrl", "rctrl": "ctrl",
    "control_l": "ctrl", "control_r": "ctrl", "control": "ctrl",
    "left shift": "shift", "right shift": "shift", "lshift": "shift", "rshift": "shift",
    "shift_l": "shift", "shift_r": "shift",
    "left alt": "alt", "right alt": "alt", "alt gr": "alt",
    "alt_l": "alt", "alt_r": "alt",
}


def normalize_key_name(raw_key: str) -> str:
    """
    Normaliserar vanliga tangentaliasnamn till en konsekvent form,
    t.ex. "Left Ctrl" / "control_l" / "LCTRL" -> "ctrl". Används både
    när en genväg sparas (efter fångst) och när den visas i GUI:t, så
    samma fysiska tangent alltid representeras likadant oavsett
    plattform eller hur tangentbordshändelsen råkade namnges.
    """
    cleaned = str(raw_key).lower().strip()
    return _MODIFIER_ALIASES.get(cleaned, cleaned)


def format_shortcut_for_display(modifiers: list[str], key: str) -> str:
    """
    Bygger en läsbar genvägssträng för GUI:t, t.ex.
    (["ctrl"], "s") -> "Ctrl+S".
    """
    parts = [m.capitalize() for m in modifiers] + [key.upper() if len(key) == 1 else key.capitalize()]
    return "+".join(parts)


def format_shortcut_for_tk(modifiers: list[str], key: str) -> str:
    """
    Bygger en Tkinter-bindningssträng, t.ex.
    (["ctrl"], "s") -> "<Control-s>".
    """
    tk_modifier_names = {"ctrl": "Control", "shift": "Shift", "alt": "Alt"}
    tk_parts = [tk_modifier_names.get(m, m.capitalize()) for m in modifiers]
    tk_parts.append(key)
    return "<" + "-".join(tk_parts) + ">"


class HotkeyCapture:
    """
    Fångar nästa tangenttryckning inom ett Tkinter-widget-träd, för
    att låta användaren ombinda en AIDE-genväg i Inställningar.

    Motsvarar i praktiken GameBridges HotkeyCaptureCore.capture_next_keypress,
    men byggd på Tkinters egna <KeyPress>-event istället för det
    globala `keyboard`-biblioteket — se modulens docstring för varför.

    Användning:

        capture = HotkeyCapture(root_widget)
        capture.capture_next(
            on_captured=lambda mods, key: print(mods, key),
        )
    """

    def __init__(self, widget) -> None:
        self._widget = widget
        self._bind_id: str | None = None

    def capture_next(
        self,
        on_captured: Callable[[list[str], str], None],
        before_capture: Callable[[], None] | None = None,
    ) -> None:
        """
        Binder en engångslyssnare för nästa <KeyPress>. Modifierare
        (Ctrl/Shift/Alt) läses av händelsens `state`-bitmask; själva
        den tryckta tangenten normaliseras via normalize_key_name.
        Rena modifierartryckningar (bara Ctrl, bara Shift) ignoreras
        — vi väntar på en faktisk tangent att kombinera dem med.
        """
        if before_capture:
            before_capture()

        def _on_keypress(event) -> None:
            key = normalize_key_name(event.keysym)
            if key in ("ctrl", "shift", "alt"):
                return  # vänta på en riktig tangent, inte bara modifieraren

            modifiers = []
            if event.state & 0x0004:
                modifiers.append("ctrl")
            if event.state & 0x0001:
                modifiers.append("shift")
            if event.state & 0x20000 or event.state & 0x0008:
                modifiers.append("alt")

            self._widget.unbind("<KeyPress>", self._bind_id)
            self._bind_id = None
            on_captured(modifiers, key)

        self._bind_id = self._widget.bind("<KeyPress>", _on_keypress, add="+")

    def cancel(self) -> None:
        """Avbryter en pågående fångst utan att trigga on_captured."""
        if self._bind_id is not None:
            self._widget.unbind("<KeyPress>", self._bind_id)
            self._bind_id = None

```

==================================================
FILE: core/localization_core.py
TYPE: Kod
==================================================

```python
# -*- coding: utf-8 -*-
"""
core/localization_core.py

Systemspråksdetektering och textuppslagning för AIDE:s GUI, byggd
efter samma princip som GameBridges core/localization_core.py.

Skillnader mot GameBridge-versionen, medvetna:
- Läser locales.json via AIDE:s egen core.path_core.PathCore, från
  en fristående "locales/"-mapp bredvid AIDE.exe (inte config/) —
  hålls uttryckligen UTANFÖR .exe-bygget så slutanvändare kan
  redigera/översätta filen själva efteråt.
- Tvingat språkval (forced_lang) skickas in som konstruktorargument
  istället för att läsas direkt från en settings.json-fil här i
  klassen. AIDE:s Settings-dataclass (core/settings.py) äger det
  beslutet; LocalizationCore bryr sig bara om VILKET språk den ska
  visa, inte VARIFRÅN det valet kom. Håller de två modulerna
  oberoende av varandra.
- get_text() stödjer enkel .format(**kwargs)-substitution
  ("Hittade filer: {n}") eftersom AIDE:s statusrader ofta innehåller
  dynamiska värden, till skillnad från GameBridges mest statiska
  UI-etiketter.

Detekteringsordning vid autodetektering (identisk med GameBridge):
    1. Windows-registrets systemspråk (endast Windows)
    2. Miljövariabler (LANG, LC_ALL, LC_CTYPE)
    3. Pythons locale.getdefaultlocale()
    4. Fallback: engelska
"""

from __future__ import annotations

import json
import locale
import os
import sys
import threading
from typing import Any

from core.path_core import PathCore

# Hårdkodad nöd-fallback om locales.json är helt korrupt eller saknas.
# Håller AIDE körbar (om än fult) även om filen råkar illa ute.
_HARDCODED_FALLBACK = {
    "en": {
        "app_title": "A.I.D.E.",
        "status_ready": "Status: Ready",
    },
    "sv": {
        "app_title": "A.I.D.E.",
        "status_ready": "Status: Redo",
    },
}


class LocalizationCore:
    def __init__(self, forced_lang: str | None = None):
        self._lock = threading.Lock()
        self.locales_path = PathCore.get_locale_path()

        self.system_lang = "en"  # global fallback
        self._matrices: dict[str, dict[str, Any]] = {}

        self.load_locales_from_disk()
        self.initialize_localization(forced_lang)

    # ------------------------------------------------------------------
    # LADDNING
    # ------------------------------------------------------------------

    def load_locales_from_disk(self) -> None:
        """Läser locales/locales.json. Faller tillbaka på den
        hårdkodade nödmängden om filen saknas eller är trasig."""
        with self._lock:
            if os.path.exists(self.locales_path):
                try:
                    with open(self.locales_path, "r", encoding="utf-8") as fh:
                        self._matrices = json.load(fh)
                    return
                except (OSError, json.JSONDecodeError) as exc:
                    print(
                        f"[LOCALIZATION-ERROR] Kunde inte läsa locales.json: {exc}. "
                        "Använder hårdkodad nödfallback."
                    )
            else:
                print(
                    f"[LOCALIZATION-WARNING] locales.json saknas på "
                    f"{self.locales_path}. Använder hårdkodad nödfallback."
                )
            self._matrices = dict(_HARDCODED_FALLBACK)

    # ------------------------------------------------------------------
    # SPRÅKVAL
    # ------------------------------------------------------------------

    def initialize_localization(self, forced_lang: str | None) -> None:
        """
        Avgör aktivt språk. Ett explicit forced_lang (t.ex. från
        AIDE:s sparade inställningar) vinner alltid över
        autodetektering, om det finns bland laddade språk.
        """
        with self._lock:
            if forced_lang and forced_lang in self._matrices:
                self.system_lang = forced_lang
                return

            detected = self._detect_system_language()
            self.system_lang = detected if detected in self._matrices else "en"

    def set_language(self, lang_code: str) -> bool:
        """
        Byter aktivt språk manuellt (t.ex. när användaren väljer
        språk i Inställningar). Returnerar False om språket inte
        finns bland laddade matriser.
        """
        with self._lock:
            if lang_code not in self._matrices:
                return False
            self.system_lang = lang_code
            return True

    def available_languages(self) -> list[str]:
        with self._lock:
            return sorted(self._matrices.keys())

    @staticmethod
    def _detect_system_language() -> str:
        detected_iso = ""

        if sys.platform == "win32":
            try:
                import ctypes

                LOCALE_SISO639LANGNAME = 0x00000059
                buf = ctypes.create_unicode_buffer(9)
                result = ctypes.windll.kernel32.GetLocaleInfoW(
                    0x0400, LOCALE_SISO639LANGNAME, buf, 9
                )
                if result > 0:
                    detected_iso = buf.value.lower().strip()
            except Exception:
                pass

        if not detected_iso:
            for env_var in ("LANG", "LC_ALL", "LC_CTYPE"):
                val = os.environ.get(env_var, "").lower()
                if "_" in val:
                    detected_iso = val.split("_")[0]
                    break
                if val:
                    detected_iso = val
                    break

        if not detected_iso:
            try:
                loc = locale.getdefaultlocale() or locale.getlocale()
                if loc and loc[0]:
                    detected_iso = loc[0].lower().split("_")[0]
            except Exception:
                pass

        return detected_iso or "en"

    # ------------------------------------------------------------------
    # TEXTUPPSLAGNING
    # ------------------------------------------------------------------

    def get_text(self, key: str, **kwargs: Any) -> str:
        """
        Hämtar text för aktivt språk. Faller tillbaka på engelska,
        sedan på den hårdkodade nödfallbacken, om nyckeln saknas.
        Stödjer .format(**kwargs) för dynamiska värden, t.ex.:

            localizer.get_text("label_found_files", n=42)
            -> "Hittade filer: 42"
        """
        with self._lock:
            matrix = self._matrices.get(
                self.system_lang,
                self._matrices.get("en", _HARDCODED_FALLBACK["en"]),
            )
            template = matrix.get(key)

        if template is None:
            return f"[{key.upper()}_MISSING]"

        if not kwargs:
            return template

        try:
            return template.format(**kwargs)
        except (KeyError, IndexError):
            # Fel/saknat platshållarargument ska aldrig krascha GUI:t —
            # visa den oformaterade mallen hellre än att falla.
            return template

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

from core.easter_eggs import maybe_log_daddle
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
    maybe_log_daddle(log_callback)

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
FILE: core/path_core.py
TYPE: Kod
==================================================

```python
# -*- coding: utf-8 -*-
"""
core/path_core.py

AIDE Path Core — centraliserad, absolut sökvägshantering.

Fungerar både vid vanlig Python-körning och som PyInstaller .exe.
Byggd efter exakt samma princip som GameBridges core/path_core.py,
eftersom AIDE ska kunna packas till en fristående .exe precis som
GameBridge redan är.

VARFÖR DET HÄR BEHÖVS:
Kod som räknar ut sin egen mapp via
`os.path.dirname(os.path.abspath(__file__))` fungerar utmärkt vid
vanlig `python main.py`-körning, men går sönder när AIDE kompileras
med PyInstaller: `__file__` pekar då på en tillfällig
uppackningsmapp (`sys._MEIPASS`), inte på mappen där den faktiska
.exe-filen faktiskt ligger — så t.ex. `plugins/`-mappen (som ska
ligga BREDVID .exe:n, inte inne i den) hittas helt fel efter
kompilering. Det var precis den bugg GameBridges PathCore löste
(se providers/adapters-root-hanteringen i GameBridge Code v1.1).

PathCore löser det genom att peka mot
`os.path.dirname(sys.executable)` när AIDE körs som frozen .exe
(`getattr(sys, "frozen", False)`), annars mot projektroten som
vanligt vid python-körning.

EXTERN RUNTIME-STRUKTUR (identisk oavsett python- eller .exe-körning):

    AIDE/                    (eller: dist/AIDE/ efter PyInstaller)
    ├── AIDE.exe  (eller main.py vid python-körning)
    ├── plugins/
    ├── docs/
    └── ...
"""

from __future__ import annotations

import os
import sys


class PathCore:

    # ------------------------------------------------------------------
    # PROJECT / RUNTIME ROOT
    # ------------------------------------------------------------------

    if getattr(sys, "frozen", False):
        # PyInstaller: mappen där den körbara filen faktiskt ligger,
        # så externa mappar som plugins/ ligger bredvid AIDE.exe.
        PROJECT_ROOT = os.path.dirname(os.path.abspath(sys.executable))
    else:
        # Vanlig Python-körning: core/path_core.py ligger en nivå
        # under projektroten.
        _CORE_DIR = os.path.dirname(os.path.abspath(__file__))
        PROJECT_ROOT = os.path.dirname(_CORE_DIR)

    # ------------------------------------------------------------------
    # GENERELL SÖKVÄG
    # ------------------------------------------------------------------

    @classmethod
    def get_absolute_path(cls, *paths: str) -> str:
        """
        Kombinerar sökvägar till en garanterad absolut sökväg,
        förankrad i AIDE:s faktiska rotmapp (källkod eller .exe).
        All extern resurshantering i AIDE ska byggas genom den här
        metoden, inte genom egna __file__-uträkningar.
        """
        return os.path.abspath(os.path.join(cls.PROJECT_ROOT, *paths))

    # ------------------------------------------------------------------
    # PLUGINS
    # ------------------------------------------------------------------

    @classmethod
    def get_plugins_root(cls) -> str:
        """Absolut sökväg till plugins/-mappen."""
        return cls.get_absolute_path("plugins")

    # ------------------------------------------------------------------
    # DOCS
    # ------------------------------------------------------------------

    @classmethod
    def get_docs_path(cls, filename: str) -> str:
        """Absolut sökväg till en fil i docs/ (t.ex. PLUGIN_GUIDE.md)."""
        return cls.get_absolute_path("docs", filename)

    # ------------------------------------------------------------------
    # LOKALISERING (för kommande localization-arbete)
    # ------------------------------------------------------------------

    @classmethod
    def get_locale_path(cls, filename: str = "locales.json") -> str:
        """Absolut sökväg till lokaliseringsdata."""
        return cls.get_absolute_path("locales", filename)

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

Varje plugin bor i sin egen undermapp under plugins/ och kan finnas i
ANTINGEN uppackad form (en main_plugin.py-fil direkt i mappen) ELLER
paketerad form (en .gbp-fil — se core/gbp_runtime.py och
tools/build_plugin_package.py) — eller båda, i vilket fall det räknas
som en dubblett och flaggas (men skanningen fortsätter ändå).

En paketerad (.gbp) plugin extraheras till en lokal temp/-runtime-
katalog av GbpRuntime innan dess main_plugin.py laddas — det enda som
skiljer den från en vanlig plugin är VARIFRÅN filen faktiskt laddas.
Allt annat (AIDEPlugin-kontraktet, hooks, exportörer) är identiskt.

Mönstret är medvetet enkelt: ingen registreringsfil krävs, AIDE
upptäcker plugins genom att skanna katalogstrukturen (samma princip
som beställningens avsnitt 25 efterfrågar).

Ett fel i en enskild plugin får aldrig krascha AIDE eller hindra
övriga plugins från att laddas — i linje med avsnitt 27 (defensiv
felhantering).
"""

from __future__ import annotations

import importlib
import importlib.util
import os
import sys

from core.gbp_runtime import GbpRuntime
from core.plugin_base import AIDEPlugin


def discover_plugins(plugin_dir: str, log_callback=None) -> dict[str, AIDEPlugin]:
    """
    Skannar plugin_dir efter undermappar med antingen en main_plugin.py
    direkt i mappen (uppackad plugin) eller en .gbp-fil (paketerad
    plugin, extraheras automatiskt), instansierar och initialiserar
    varje hittad AIDEPlugin-subklass.

    Rensar först alla gamla temp/-runtime-kataloger från en tidigare
    session (GbpRuntime.cleanup_all) innan skanningen börjar, så inga
    rester från en föregående körning kan blandas ihop med den nya.

    Returnerar en dict {plugin_name: instans}.
    """
    log = log_callback or (lambda msg: None)
    discovered: dict[str, AIDEPlugin] = {}

    if not os.path.isdir(plugin_dir):
        return discovered

    GbpRuntime.cleanup_all(plugin_dir)

    if plugin_dir not in sys.path:
        sys.path.insert(0, plugin_dir)

    # Engångsflagga: bara den FÖRSTA dubbletten loggas som varning för
    # att inte dränka loggen om flera plugins råkar vara dubbletter
    # samtidigt — skanningen fortsätter oavsett, precis som GameBridge
    # gör i sin motsvarande adapter_loader.py.
    duplicate_already_flagged = False

    for folder in sorted(os.listdir(plugin_dir)):
        folder_path = os.path.join(plugin_dir, folder)

        if not os.path.isdir(folder_path):
            continue
        if folder.startswith("__") or folder.startswith("."):
            continue

        # En pluginmapp kan innehålla den uppackade .py-representationen,
        # en paketerad .gbp-representation, eller båda.
        gbp_path = GbpRuntime.find_gbp_file(folder_path)
        main_file = os.path.join(folder_path, "main_plugin.py")
        has_unpacked = os.path.isfile(main_file)
        packed_plugin = False

        if has_unpacked and gbp_path and not duplicate_already_flagged:
            duplicate_already_flagged = True
            log(
                f"⚠ Dubblett upptäckt i '{folder}': både main_plugin.py "
                f"och en .gbp-fil ({os.path.basename(gbp_path)}) finns. "
                "Använder den uppackade main_plugin.py."
            )

        if not has_unpacked:
            if not gbp_path:
                continue  # varken uppackad eller paketerad plugin här

            try:
                runtime_dir = GbpRuntime.prepare_plugin(folder_path, gbp_path)
                main_file = GbpRuntime.get_main_plugin_path(runtime_dir)
                packed_plugin = True
                log(f"Paketerad plugin '{folder}' förberedd från {os.path.basename(gbp_path)}")
            except Exception as exc:
                log(f"⚠ Kunde inte förbereda paketerad plugin i '{folder}': {exc}")
                continue

        module_name = (
            f"aide_packed_{folder}_main_plugin" if packed_plugin else f"{folder}.main_plugin"
        )

        try:
            if packed_plugin:
                # Paketerade plugins ligger i en temp/-katalog, inte på
                # plugin_dir-nivå — spec_from_file_location laddar
                # direkt från filsökvägen istället för att förlita sig
                # på paketrelativ import (som annars skulle kräva att
                # temp/ också låg i sys.path som ett eget paket).
                spec = importlib.util.spec_from_file_location(module_name, main_file)
                if spec is None or spec.loader is None:
                    raise ImportError(f"Kunde inte skapa modulspecifikation för '{folder}'")
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
            else:
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
                    log(
                        f"Plugin loaded: '{instance.plugin_name}' "
                        f"(v{instance.plugin_version}) från {folder}/"
                        + (" (paketerad, .gbp)" if packed_plugin else "")
                    )

        except Exception as exc:  # en trasig plugin ska aldrig krascha AIDE
            log(f"⚠ Kunde inte ladda plugin i '{folder}': {exc}")

    return discovered

```

==================================================
FILE: core/plugin_registration.py
TYPE: Kod
==================================================

```python
"""
core/plugin_registration.py

Skriver en liten lokal registreringsfil (AIDE Box/reports/plugin_registration.json)
som GameBridge-pluginet (AideAdapter) läser för att automatiskt hitta:

  - aide_root      : var AIDE själv är installerad (för boot_or_attach)
  - aide_scan_dir  : AIDE Box/scan/ — den enda mapp GameBridge/AI får leta i

VIKTIGT — designval: registreringen pekar INTE på ett specifikt projekts
källrot. Den pekar bara på scan/-katalogen, som är AIDE:s permanenta,
statiska samlingsplats för ALLA skannade projekts manifest. Det betyder
att registreringen bara behöver göras EN gång — inte om igen varje gång
ett nytt projekt scannas.

Varje enskilt manifest i scan/ kan (opt-in) bära sin egen absoluta
källrot via fältet "source_folders_absolute" (se core/manifest.py).
GameBridge-adaptern kombinerar alltså:

    aide_scan_dir (från denna fil, statisk)
        + valt manifest i scan/ (source_folders_absolute + relativ path)
        = absolut sökväg till en specifik fil

Detta håller AI:ns åtkomst avgränsad till scan/-katalogen istället för
hela hårddisken — samma säkerhetsprincip som resten av AIDE (avsnitt 13).

Filen skrivs BARA när användaren uttryckligen trycker på knappen
"Registrera för GameBridge" — aldrig automatiskt vid en vanlig scan.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone


def register_for_gamebridge(
    aide_root: str,
    log_callback=None,
) -> str:
    """
    Skriver <aide_root>/AIDE Box/reports/plugin_registration.json.

    aide_root: AIDE:s egen installationsrot (mappen med main.py).

    Notera: tar INTE emot source_roots längre — scan/-katalogen är
    statisk och samlar alla projekt, så ingen per-projekt-registrering
    behövs.
    """
    aide_root_abs = os.path.abspath(aide_root)
    scan_dir = os.path.join(aide_root_abs, "AIDE Box", "scan")

    reports_dir = os.path.join(aide_root_abs, "AIDE Box", "reports")
    os.makedirs(reports_dir, exist_ok=True)

    target = os.path.join(reports_dir, "plugin_registration.json")

    data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "aide_root": aide_root_abs,
        "aide_scan_dir": scan_dir,
    }

    with open(target, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)

    if log_callback:
        log_callback(f"GameBridge-registrering skapad: {target}")

    return target

```

==================================================
FILE: core/report_writer.py
TYPE: Kod
==================================================

```python
# -*- coding: utf-8 -*-
"""
core/report_writer.py

Skriver en AI-genererad rapport till disk.

Det här är avsiktligt EN ren, fristående kärnfunktion — inte ett
exportformat kopplat till AIDE:s vanliga filurvals-GUI (checkboxar,
scan, "Bygg paket"). Den tar emot färdig rapporttext utifrån och
skriver den till AIDE Box/report/ (eller vald exportmapp).

Tänkt användning (enligt GameBridge-integrationsplanen):

    AI (via GameBridge)
      ↓
    läser markerade filer via befintlig telemetri/manifest
      ↓
    AI resonerar/jämför
      ↓
    Channel 2 → AIDE-pluginets whitelisted "create_report"-action
      ↓
    create_report(...) HÄR i AIDE-kärnan
      ↓
    AIDE Box/report/report.md

AIDE-pluginet i GameBridge (byggs senare) blir alltså bara en tunn
översättare som ropar på den här funktionen — själva skrivlogiken
ligger i AIDE:s kärna, inte i adaptern (samma princip som resten av
AIDE:s exportörer).

SÄKERHETSPRINCIP: samma som core/security.py i övrigt — skriver
aldrig utanför export_dir, respekterar conflict_strategy, och
kraschar aldrig tyst (avsnitt 13, 27 i AIDE:s originalspec).
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

from core.security import ConflictStrategy, ensure_within_export_dir, resolve_target_path

DEFAULT_FILENAME = "report.md"
DEFAULT_SUBFOLDER = "report"


def _resolve_relative_target(export_dir: str, filename: str, subfolder: str) -> str:
    """
    Samma "redan i rätt undermapp?"-logik som ZIP- och PDF-pluginen
    använder: om export_dir redan HETER t.ex. "report" läggs ingen
    extra "report"-nivå på ovanpå (undviker en "report/report"-
    dubblering); annars läggs subfolder till som standardplats.
    """
    already_in_subfolder = (
        os.path.basename(os.path.normpath(str(export_dir))).lower() == subfolder.lower()
    )
    if already_in_subfolder:
        return filename
    return os.path.join(subfolder, filename)


def create_report(
    export_dir: str,
    report_markdown: str,
    project_name: str | None = None,
    filename: str = DEFAULT_FILENAME,
    conflict_strategy: ConflictStrategy = ConflictStrategy.NEW_VERSION,
    log_callback=None,
) -> str | None:
    """
    Skriver en redan färdigformulerad Markdown-rapport till disk.

    Parametrar:
        export_dir: vald exportmapp (t.ex. "AIDE Box" eller redan
            "AIDE Box/report" — båda funkar, se _resolve_relative_target).
        report_markdown: rapportens innehåll, redan i Markdown-format.
            Den här funktionen formulerar INGET innehåll själv — det är
            AI:ns jobb; funktionen bara skriver det säkert till disk.
        project_name: valfritt, används bara för en liten rubrikrad
            överst i filen om den anges.
        filename: standard "report.md". Vid NEW_VERSION-konflikt blir
            efterföljande rapporter "report (1).md" osv, precis som
            AIDE:s övriga exportörer.
        conflict_strategy: samma tre lägen som resten av AIDE
            (OVERWRITE / NEW_VERSION / SKIP).
        log_callback: valfri Callable[[str], None] för AIDE:s logg.

    Returnerar skriven sökväg, eller None om exporten hoppades över
    (SKIP-konflikt) eller misslyckades.
    """
    log = log_callback or (lambda msg: None)

    if not isinstance(report_markdown, str) or not report_markdown.strip():
        log("⚠ Kunde inte skapa rapport: inget rapportinnehåll angavs.")
        return None

    os.makedirs(export_dir, exist_ok=True)

    rel_target = _resolve_relative_target(export_dir, filename, DEFAULT_SUBFOLDER)

    try:
        target = ensure_within_export_dir(export_dir, rel_target)
    except Exception as exc:  # ExportBlocked eller annat oväntat sökvägsfel
        log(f"⚠ Kunde inte skapa rapport (osäker sökväg): {exc}")
        return None

    resolved = resolve_target_path(target, conflict_strategy)
    if resolved is None:
        log(f"Hoppade över befintlig rapport: {target}")
        return None

    os.makedirs(os.path.dirname(resolved), exist_ok=True)

    generated = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M")
    header = ""
    if project_name:
        header = f"# AI-rapport — {project_name}\n\n_Genererad: {generated}_\n\n---\n\n"

    content = header + report_markdown
    if not content.endswith("\n"):
        content += "\n"

    try:
        with open(resolved, "w", encoding="utf-8") as fh:
            fh.write(content)
    except OSError as exc:
        log(f"⚠ Kunde inte skriva rapportfilen: {exc}")
        return None

    log(f"Rapport skapad: {resolved}")
    return resolved

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

# Standardgenvägar för AIDE:s GUI-kommandon (core/hotkey_utils.py).
# Formatet matchar hotkey_utils.format_shortcut_for_tk/_for_display:
# {"modifiers": ["ctrl", ...], "key": "s"}.
DEFAULT_HOTKEYS: dict = {
    "scan": {"modifiers": ["ctrl"], "key": "s"},
    "build_package": {"modifiers": ["ctrl"], "key": "b"},
    "preview": {"modifiers": ["ctrl"], "key": "p"},
}


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

    # Tom sträng = autodetektera systemspråk (se core/localization_core.py).
    # Annars en språkkod som finns i locales/locales.json, t.ex. "sv" eller "en".
    language: str = ""

    # Ombindningsbara genvägar för AIDE:s GUI-kommandon. Nyckeln är
    # kommandots interna namn (matchar DEFAULT_HOTKEYS ovan), värdet
    # är {"modifiers": [...], "key": "..."} — samma format som
    # core.hotkey_utils.HotkeyCapture producerar vid ombindning.
    hotkeys: dict = field(default_factory=lambda: {k: dict(v) for k, v in DEFAULT_HOTKEYS.items()})

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> "Settings":
        defaults = Settings()
        merged = defaults.to_dict()
        merged.update({k: v for k, v in data.items() if k in merged})

        # Djupmerge hotkeys specifikt: en sparad settings.json från en
        # äldre AIDE-version känner bara till de genvägar som fanns då.
        # Om en ny standardgenväg läggs till i en senare version ska
        # den ändå dyka upp för befintliga användare, inte tystas ner
        # bara för att den saknas i deras gamla sparade fil. Alla
        # övriga fält (inklusive resten av hotkeys-posterna) förblir
        # oförändrade — bara nya nycklar fylls i från defaults.
        if "hotkeys" in data and isinstance(data["hotkeys"], dict):
            merged_hotkeys = {k: dict(v) for k, v in defaults.hotkeys.items()}
            merged_hotkeys.update(data["hotkeys"])
            merged["hotkeys"] = merged_hotkeys

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
    include_absolute_paths: bool = False,
) -> str | None:
    os.makedirs(export_dir, exist_ok=True)
    target = ensure_within_export_dir(export_dir, filename)
    resolved = resolve_target_path(target, conflict_strategy)
    if resolved is None:
        if log_callback:
            log_callback(f"Hoppade över befintlig fil: {target}")
        return None

    manifest = build_manifest(
        project_name, source_roots, included_files,
        include_absolute_paths=include_absolute_paths,
    )
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
FILE: locales/locales.json
TYPE: Konfiguration/Data
==================================================

```json
{
    "sv": {
        "app_title": "A.I.D.E. — Archive · Identify · Determine · Export",

        "status_ready": "Status: Redo",
        "status_processing": "Status: Processar...",

        "btn_scan": "Skanna",
        "btn_cancel": "Avbryt",
        "btn_build_package": "Bygg paket",
        "btn_choose_source": "Välj källmapp",
        "btn_remove_source": "Ta bort vald källa",
        "btn_choose_export_dir": "Välj exportmapp",
        "btn_preview": "Förhandsgranska",
        "btn_clear": "Rensa",
        "btn_settings": "Inställningar",
        "btn_select_all": "Markera alla",
        "btn_deselect_all": "Avmarkera alla",
        "btn_select_category": "Markera kategori",
        "btn_deselect_category": "Avmarkera kategori",
        "btn_register_gamebridge": "Registrera för GameBridge",

        "switch_show_binary": "Visa binärfiler",
        "switch_lock_selection": "Lås urval (skydda mot ändringar)",

        "section_scan_control": "SKANNINGS- OCH URVALSKONTROLL",
        "section_sources": "KÄLLMAPPAR",
        "section_status": "STATUS",
        "section_log": "LOGG",

        "filter_label": "Filter:",
        "filter_placeholder": "Sök filnamn, sökväg, kategori...",

        "label_export_dir_unset": "Exportmapp: (ej vald)",
        "label_export_dir": "Exportmapp: {path}",
        "label_found_files": "Hittade filer: {n}",
        "label_included": "Inkluderade: {n}",
        "label_excluded": "Exkluderade: {n}",
        "label_sensitive_files": "Känsliga filer: {n}",
        "label_current_op_idle": "Aktuell operation: Inaktiv",
        "label_current_op_scanning": "Aktuell operation: Skannar...",
        "label_current_op_packaging": "Aktuell operation: Paketerar...",

        "dialog_selection_locked_title": "Urval låst",
        "dialog_selection_locked_msg": "Lås upp urvalet innan du kör en ny skanning.",
        "dialog_no_sources_title": "Inga källor",
        "dialog_no_sources_msg": "Välj minst en källmapp innan skanning.",
        "dialog_busy_title": "Pågår redan",
        "dialog_busy_msg": "En operation pågår redan.",
        "dialog_nothing_to_preview_title": "Inget att förhandsgranska",
        "dialog_nothing_to_preview_msg": "Skanna en källmapp först.",
        "dialog_nothing_selected_title": "Inget markerat",
        "dialog_nothing_selected_msg": "Markera minst en fil innan paketering.",
        "dialog_nothing_selected_preview_msg": "Markera minst en fil för att förhandsgranska.",
        "dialog_nothing_left_after_plugin_msg": "Inga filer kvar att exportera efter plugin-filtrering.",
        "dialog_no_export_dir_title": "Ingen exportmapp",
        "dialog_no_export_dir_msg": "Välj en exportmapp innan paketering.",
        "dialog_conflict_title": "Konflikthantering",
        "dialog_conflict_msg": "Om filer redan finns i exportmappen:\n\nJa = Skriv över\nNej = Skapa ny version\nAvbryt = Hoppa över befintliga filer",
        "dialog_done_title": "Klart",
        "dialog_done_msg": "Paket skapat:\n",
        "dialog_error_title": "Fel",
        "dialog_error_msg": "Kunde inte skapa paketet:\n",

        "settings_window_title": "Inställningar — A.I.D.E.",
        "settings_header": "INSTÄLLNINGAR",
        "settings_language": "Språk",
        "settings_ignore_dirs": "Ignorerade kataloger (komma-separerat)",
        "settings_ignore_files": "Ignorerade filnamn (komma-separerat)",
        "settings_sensitive_patterns": "Känsliga filmönster (komma-separerat, t.ex. *.pem)",
        "settings_default_format": "Standard-exportformat",
        "settings_default_export_dir": "Standard-målmapp",
        "settings_show_binary": "Visa binärfiler i listan",
        "settings_show_hidden": "Visa dolda filer/kataloger",
        "settings_default_checkbox": "Markera icke-känsliga filer automatiskt vid skanning",
        "settings_hotkeys_header": "Tangentbordsgenvägar",
        "settings_cancel": "Avbryt",
        "settings_save": "Spara",

        "preview_window_title": "Förhandsgranskning — A.I.D.E.",
        "preview_summary": "SAMMANFATTNING",
        "preview_sources": "Källor: {sources}",
        "preview_included": "Inkluderade filer: {n}",
        "preview_excluded": "Exkluderade filer: {n}",
        "preview_total_size": "Total storlek (inkluderat): {size}",
        "preview_category_breakdown": "Kategorifördelning: {breakdown}",
        "preview_sensitive_warning": "⚠ Varning: {n} känslig(a) fil(er) är markerade för export!",
        "preview_col_file": "Fil",
        "preview_col_status": "Status",
        "preview_col_category": "Kategori",
        "preview_col_size": "Storlek",
        "preview_status_included": "Inkluderas",
        "preview_status_excluded": "Exkluderas",
        "preview_close": "Stäng",

        "tree_col_name": "Fil / Mapp",
        "tree_col_size": "Storlek",
        "tree_col_category": "Kategori",
        "tree_col_status": "Status",
        "tree_status_sensitive": "Känslig",
        "tree_status_binary": "Binär",
        "tree_status_error": "Fel",
        "tree_dir_file_count": "{n} filer"
    },
    "en": {
        "app_title": "A.I.D.E. — Archive · Identify · Determine · Export",

        "status_ready": "Status: Ready",
        "status_processing": "Status: Processing...",

        "btn_scan": "Scan",
        "btn_cancel": "Cancel",
        "btn_build_package": "Build Package",
        "btn_choose_source": "Choose Source Folder",
        "btn_remove_source": "Remove Selected Source",
        "btn_choose_export_dir": "Choose Export Folder",
        "btn_preview": "Preview",
        "btn_clear": "Clear",
        "btn_settings": "Settings",
        "btn_select_all": "Select All",
        "btn_deselect_all": "Deselect All",
        "btn_select_category": "Select Category",
        "btn_deselect_category": "Deselect Category",
        "btn_register_gamebridge": "Register for GameBridge",

        "switch_show_binary": "Show Binary Files",
        "switch_lock_selection": "Lock Selection (protect from changes)",

        "section_scan_control": "SCAN AND SELECTION CONTROL",
        "section_sources": "SOURCE FOLDERS",
        "section_status": "STATUS",
        "section_log": "LOG",

        "filter_label": "Filter:",
        "filter_placeholder": "Search filename, path, category...",

        "label_export_dir_unset": "Export folder: (not set)",
        "label_export_dir": "Export folder: {path}",
        "label_found_files": "Files found: {n}",
        "label_included": "Included: {n}",
        "label_excluded": "Excluded: {n}",
        "label_sensitive_files": "Sensitive files: {n}",
        "label_current_op_idle": "Current operation: Idle",
        "label_current_op_scanning": "Current operation: Scanning...",
        "label_current_op_packaging": "Current operation: Packaging...",

        "dialog_selection_locked_title": "Selection Locked",
        "dialog_selection_locked_msg": "Unlock the selection before running a new scan.",
        "dialog_no_sources_title": "No Sources",
        "dialog_no_sources_msg": "Choose at least one source folder before scanning.",
        "dialog_busy_title": "Already Running",
        "dialog_busy_msg": "An operation is already in progress.",
        "dialog_nothing_to_preview_title": "Nothing to Preview",
        "dialog_nothing_to_preview_msg": "Scan a source folder first.",
        "dialog_nothing_selected_title": "Nothing Selected",
        "dialog_nothing_selected_msg": "Select at least one file before packaging.",
        "dialog_nothing_selected_preview_msg": "Select at least one file to preview.",
        "dialog_nothing_left_after_plugin_msg": "No files left to export after plugin filtering.",
        "dialog_no_export_dir_title": "No Export Folder",
        "dialog_no_export_dir_msg": "Choose an export folder before packaging.",
        "dialog_conflict_title": "Conflict Handling",
        "dialog_conflict_msg": "If files already exist in the export folder:\n\nYes = Overwrite\nNo = Create new version\nCancel = Skip existing files",
        "dialog_done_title": "Done",
        "dialog_done_msg": "Package created:\n",
        "dialog_error_title": "Error",
        "dialog_error_msg": "Could not create the package:\n",

        "settings_window_title": "Settings — A.I.D.E.",
        "settings_header": "SETTINGS",
        "settings_language": "Language",
        "settings_ignore_dirs": "Ignored directories (comma-separated)",
        "settings_ignore_files": "Ignored filenames (comma-separated)",
        "settings_sensitive_patterns": "Sensitive file patterns (comma-separated, e.g. *.pem)",
        "settings_default_format": "Default export format",
        "settings_default_export_dir": "Default target folder",
        "settings_show_binary": "Show binary files in the list",
        "settings_show_hidden": "Show hidden files/directories",
        "settings_default_checkbox": "Select non-sensitive files automatically on scan",
        "settings_hotkeys_header": "Keyboard Shortcuts",
        "settings_cancel": "Cancel",
        "settings_save": "Save",

        "preview_window_title": "Preview — A.I.D.E.",
        "preview_summary": "SUMMARY",
        "preview_sources": "Sources: {sources}",
        "preview_included": "Included files: {n}",
        "preview_excluded": "Excluded files: {n}",
        "preview_total_size": "Total size (included): {size}",
        "preview_category_breakdown": "Category breakdown: {breakdown}",
        "preview_sensitive_warning": "⚠ Warning: {n} sensitive file(s) are marked for export!",
        "preview_col_file": "File",
        "preview_col_status": "Status",
        "preview_col_category": "Category",
        "preview_col_size": "Size",
        "preview_status_included": "Included",
        "preview_status_excluded": "Excluded",
        "preview_close": "Close",

        "tree_col_name": "File / Folder",
        "tree_col_size": "Size",
        "tree_col_category": "Category",
        "tree_col_status": "Status",
        "tree_status_sensitive": "Sensitive",
        "tree_status_binary": "Binary",
        "tree_status_error": "Error",
        "tree_dir_file_count": "{n} files"
    }
}

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
FILE: plugins/gbp_packager/main_plugin.py
TYPE: Kod
==================================================

```python
# -*- coding: utf-8 -*-
"""
plugins/gbp_packager/main_plugin.py

.gbp-paketering som ett vanligt AIDE-exportformat ("gbp" i export-
format-väljaren) — samma arbetsflöde som tools/build_plugin_package.py
automatiserar fristående, fast nu inbakat i AIDE:s vanliga
skanna-markera-exportera-flöde istället för en separat kommandorad.

ANVÄNDNING:
  1. Skanna pluginets källmapp i AIDE (t.ex. plugins/pdf_export/ eller
     en GameBridge-adapters mapp).
  2. Markera entry point-filen (main_plugin.py för en AIDE-plugin,
     main_adapter.py för en GameBridge-adapter) plus eventuella extra
     filer som ska buntas med (plugin_config.json, plugin_prompt.txt).
  3. Välj exportformat "gbp" och kör "Bygg paket".

Vad som händer internt:
  1. pipreqs analyserar KÄLLMAPPEN (inte bara de markerade filerna —
     pipreqs behöver se all kod för att hitta alla imports) och listar
     externa beroenden.
  2. Interna modulnamn (core, ui, adapters, osv — AIDE:s/GameBridges
     egna paket, som pipreqs annars kan misstolka som PyPI-paket)
     filtreras bort.
  3. De återstående beroendena installeras isolerat med
     `pip install --target` i en tillfällig stagingkatalog.
  4. Entry point + eventuella extra markerade filer (de som ligger
     direkt i källmappens rot, inte i undermappar) + dependencies/
     zippas ihop till en .gbp-fil.

Paketet hamnar som standard i en "gbp"-undermapp under vald exportmapp
(samma princip som zip/pdf-pluginen), med samma "redan i rätt
undermapp?"-skydd mot dubblering.

Följer AIDEPlugin-kontraktet i docs/PLUGIN_GUIDE.md:
- Skriver aldrig utanför export_dir (ensure_within_export_dir).
- Respekterar conflict_strategy (resolve_target_path).
- Kraschar aldrig tyst — varje steg loggas via log_callback, och
  funktionen returnerar None vid fel istället för att låta ett
  undantag brisera ut och stoppa resten av AIDE.

Kräver `pipreqs` (pip install pipreqs) installerat i samma Python-
miljö som kör AIDE.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from core.plugin_base import AIDEPlugin, PluginFileInfo
from core.security import ExportBlocked, ensure_within_export_dir, resolve_target_path, sanitize_filename

# Vilka filnamn som räknas som en giltig entry point — söks i den
# ordningen bland de MARKERADE filerna.
ENTRY_POINT_CANDIDATES = ["main_plugin.py", "main_adapter.py"]

# Samma standardlista interna moduler som tools/build_plugin_package.py.
DEFAULT_INTERNAL_MODULES = {
    "adapters", "ai", "core", "functions", "interface", "providers",
    "ui", "exporters", "plugins",
    "main",
}


def _find_entry_point(included_files: list[PluginFileInfo]) -> PluginFileInfo | None:
    by_filename = {f.filename: f for f in included_files}
    for candidate in ENTRY_POINT_CANDIDATES:
        if candidate in by_filename:
            return by_filename[candidate]
    return None


def _run_pipreqs(source_dir: str, log_callback) -> list[str] | None:
    """Kör pipreqs mot källmappen. Returnerar None om pipreqs saknas."""
    result = None
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pipreqs.pipreqs", source_dir, "--print"],
            capture_output=True, text=True, check=False,
        )
    except FileNotFoundError:
        pass

    if result is None or result.returncode != 0:
        try:
            result = subprocess.run(
                ["pipreqs", source_dir, "--print"],
                capture_output=True, text=True, check=False,
            )
        except FileNotFoundError:
            log_callback("⚠ pipreqs hittades inte. Installera med: pip install pipreqs")
            return None

    lines = []
    for raw_line in result.stdout.splitlines():
        line = raw_line.strip()
        if not line or line.upper().startswith("WARNING"):
            continue
        lines.append(line)
    return lines


def _filter_internal_modules(requirements: list[str], log_callback) -> list[str]:
    kept = []
    for req in requirements:
        pkg_name = req.split("==")[0].split(">=")[0].split("<=")[0].strip().lower()
        if pkg_name in DEFAULT_INTERNAL_MODULES:
            log_callback(f"Hoppar över intern modul (inte ett riktigt PyPI-paket): {req}")
            continue
        kept.append(req)
    return kept


def _install_dependencies(requirements: list[str], target_dir: Path, log_callback) -> None:
    """Höjer RuntimeError vid pip-fel — fångas av anroparen."""
    target_dir.mkdir(parents=True, exist_ok=True)

    if not requirements:
        log_callback("Inga externa beroenden att installera.")
        return

    req_file = target_dir.parent / "requirements.txt"
    req_file.write_text("\n".join(requirements) + "\n", encoding="utf-8")

    log_callback(f"Installerar {len(requirements)} beroende(n) isolerat ...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", str(req_file), "--target", str(target_dir)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"pip install misslyckades: {result.stderr.strip()[-500:]}")


def export_gbp(
    project_name: str,
    source_roots: list[str],
    included_files: list[PluginFileInfo],
    export_dir: str,
    conflict_strategy,
    log_callback,
) -> str | None:
    entry_file = _find_entry_point(included_files)
    if entry_file is None:
        log_callback(
            "⚠ Hittar ingen main_plugin.py eller main_adapter.py bland "
            "markerade filer — markera entry point-filen och försök igen."
        )
        return None

    if not source_roots:
        log_callback("⚠ Ingen källmapp känd — kan inte köra pipreqs.")
        return None
    source_dir = source_roots[0]

    os.makedirs(export_dir, exist_ok=True)

    # Samma "redan i rätt undermapp?"-princip som zip/pdf-pluginen.
    already_in_subfolder = (
        os.path.basename(os.path.normpath(str(export_dir))).lower() == "gbp"
    )
    safe_name = sanitize_filename(project_name)
    rel_target = f"{safe_name}.gbp"
    if not already_in_subfolder:
        rel_target = os.path.join("gbp", rel_target)

    try:
        target = ensure_within_export_dir(export_dir, rel_target)
    except ExportBlocked as exc:
        log_callback(f"⚠ Hoppade över (osäker sökväg): {exc}")
        return None

    resolved = resolve_target_path(target, conflict_strategy)
    if resolved is None:
        log_callback(f"Hoppade över befintlig fil: {target}")
        return None

    os.makedirs(os.path.dirname(resolved), exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="aide_gbp_build_") as tmp:
        staging_dir = Path(tmp)
        dependencies_dir = staging_dir / "dependencies"

        log_callback(f"[1/4] Upptäcker beroenden med pipreqs i {source_dir} ...")
        raw_requirements = _run_pipreqs(source_dir, log_callback)
        if raw_requirements is None:
            return None  # pipreqs saknas, redan loggat

        log_callback("[2/4] Filtrerar bort interna moduler ...")
        requirements = _filter_internal_modules(raw_requirements, log_callback)
        log_callback(f"       Externa beroenden: {requirements or '(inga)'}")

        log_callback("[3/4] Installerar beroenden isolerat (pip install --target) ...")
        try:
            _install_dependencies(requirements, dependencies_dir, log_callback)
        except RuntimeError as exc:
            log_callback(f"⚠ {exc}")
            return None

        log_callback("[4/4] Bygger .gbp-arkiv ...")

        # Extra filer: andra markerade filer som ligger direkt i
        # källmappens rot (inte i undermappar — de täcks redan av
        # dependencies/ eller hör inte hemma i paketet).
        extra_files = [
            f for f in included_files
            if f is not entry_file and "/" not in f.relative_path
        ]

        try:
            with zipfile.ZipFile(resolved, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.write(entry_file.absolute_path, arcname=entry_file.filename)
                for f in extra_files:
                    zf.write(f.absolute_path, arcname=f.filename)

                if dependencies_dir.exists():
                    for file_path in dependencies_dir.rglob("*"):
                        if file_path.is_file():
                            arcname = file_path.relative_to(staging_dir)
                            zf.write(file_path, arcname=str(arcname))
        except OSError as exc:
            log_callback(f"⚠ Kunde inte skapa .gbp-arkivet: {exc}")
            return None

    size_kb = os.path.getsize(resolved) / 1024
    log_callback(
        f".gbp-paket skapat: {resolved} "
        f"(entry point: {entry_file.filename}, {len(extra_files)} extra fil(er), "
        f"{size_kb:.1f} KB)"
    )
    return resolved


class GbpPackagerPlugin(AIDEPlugin):

    @property
    def plugin_name(self) -> str:
        return "AIDE GBP Packager"

    @property
    def plugin_version(self) -> str:
        return "1.0.0"

    def initialize(self) -> None:
        print(f"[{self.plugin_name}] Initialiserad.")

    def get_exporters(self):
        return {"gbp": export_gbp}

```

==================================================
FILE: plugins/pdf_export/main_plugin.py
TYPE: Kod
==================================================

```python
# -*- coding: utf-8 -*-
"""
plugins/pdf_export/main_plugin.py

Snyggt formaterad PDF-export för AIDE — en PDF PER markerad fil (inte
en sammanslagen PDF för hela urvalet). Vill du ha en sammanslagen
sammanställning, kör Markdown-exporten först och sedan PDF-exporten
på den resulterande .md-filen — då blir den ena sammanslagna filen
en enda snygg PDF, och principen "en fil in, en PDF ut" hålls konsekvent.

Varje PDF får:
  - en färgkodad rubrikrad efter kategori (Kod/Text/Konfiguration/
    Webb/Dokument/Bild/Binär/Okänd — samma kategorier som
    core/classifier.py använder)
  - en kompakt metarad (källa, storlek, genereringstid)
  - filens innehåll radbrutet i en läsbar monospace-box, uppdelat i
    sidsäkra "bitar" så godtyckligt långa filer aldrig kraschar layouten
  - sidnumrering och en tunn accentlinje i sidhuvudet

PDF-filerna hamnar som standard i en egen "pdf"-undermapp under vald
exportmapp (samma princip som ZIP-backuperna hamnar i en "zip"-under-
mapp) — bevarad relativ mappstruktur, så en fil som t.ex. låg i
"core/scanner.py" hamnar i "pdf/core/scanner.py.pdf".

Kräver reportlab (`pip install reportlab` — lägg till i requirements.txt).
Om reportlab saknas misslyckas bara den här modulens import; AIDE:s
plugin_loader loggar det och fortsätter ladda övriga plugins som vanligt
(avsnitt 27 i specen, defensiv felhantering — ingen trasig plugin får
krascha resten av AIDE).

Följer AIDEPlugin-kontraktet i docs/PLUGIN_GUIDE.md:
- Skriver aldrig utanför export_dir (ensure_within_export_dir).
- Respekterar conflict_strategy (resolve_target_path) per fil.
- Ett fel på EN fil stoppar aldrig resten av batchen — loggas och
  loopen fortsätter, precis som AIDE:s egen scanner/export gör.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from xml.sax.saxutils import escape as _xml_escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    HRFlowable,
    PageTemplate,
    Paragraph,
    Preformatted,
    Spacer,
    Table,
    TableStyle,
)

from core.package_builder import MAX_INLINE_BYTES
from core.plugin_base import AIDEPlugin, PluginFileInfo
from core.security import ExportBlocked, ensure_within_export_dir, resolve_target_path

# ---------------------------------------------------------------------------
# Visuell identitet — samma familjekänsla som ui/theme.py, fast anpassad
# för utskrift: ljus bakgrund med mörka/färgade accenter istället för
# AIDE:s mörka GUI-tema (svart text på vit botten läser man helt enkelt
# bäst på papper).
# ---------------------------------------------------------------------------

COLOR_INK = colors.HexColor("#0F172A")
COLOR_MUTED = colors.HexColor("#64748B")
COLOR_ACCENT = colors.HexColor("#2563EB")
COLOR_BORDER = colors.HexColor("#CBD5E1")
COLOR_CODE_BG = colors.HexColor("#F1F5F9")
COLOR_WARNING = colors.HexColor("#DC2626")

# Samma kategorier som core/classifier.py använder — varje kategori får
# en egen accentfärg i filrubriken.
CATEGORY_COLORS = {
    "Kod": colors.HexColor("#2563EB"),
    "Text": colors.HexColor("#475569"),
    "Konfiguration/Data": colors.HexColor("#7C3AED"),
    "Webb": colors.HexColor("#EA580C"),
    "Dokument": colors.HexColor("#0D9488"),
    "Bild": colors.HexColor("#DB2777"),
    "Binär": colors.HexColor("#DC2626"),
    "Okänd": colors.HexColor("#6B7280"),
}
DEFAULT_CATEGORY_COLOR = colors.HexColor("#334155")

PAGE_SIZE = A4
MARGIN_LEFT = 20 * mm
MARGIN_RIGHT = 20 * mm
MARGIN_TOP = 24 * mm
MARGIN_BOTTOM = 20 * mm

# En Table-cell (används för den ljusgrå kodboxen) kan ALDRIG delas
# över en sidbrytning — hela cellen måste rymmas på en enda sida,
# annars kastar reportlab LayoutError. Vi radbryter därför texten
# själva och delar upp den i sidsäkra "bitar" (chunks), så en
# godtyckligt lång fil ändå flyter fritt över flera sidor.
CODE_MAX_LINE_LEN = 108
CODE_CHUNK_LINES = 55  # 55 * 9.6pt leading + 14pt padding ≈ 542pt, gott om marginal


def _wrap_text_lines(text: str, max_len: int) -> list[str]:
    """Bryter text till en lista visningsrader, max max_len tecken per
    rad. Hård radbrytning utan ordbrytningslogik — det här är kod/
    förformaterad text där exakt brytpunkt inte spelar någon roll,
    bara att raden inte blir bredare än boxen."""
    lines: list[str] = []
    for raw_line in text.split("\n"):
        if not raw_line:
            lines.append("")
            continue
        for i in range(0, len(raw_line), max_len):
            lines.append(raw_line[i:i + max_len])
    return lines


def _append_boxed_chunks(story, text, style, bg_color, width, max_len, chunk_size) -> None:
    """Radbryter text, delar upp i sidsäkra bitar och lägger till en
    boxad Preformatted-flowable per bit i story."""
    lines = _wrap_text_lines(text, max_len)
    if not lines:
        return
    for i in range(0, len(lines), chunk_size):
        chunk_text = "\n".join(lines[i:i + chunk_size])
        story.append(_boxed(Preformatted(chunk_text, style), bg_color, width))
        story.append(Spacer(1, 3))


def _styles() -> dict:
    """Egna stilar; medvetet fristående från reportlabs standardmallar
    så utseendet är förutsägbart oavsett reportlab-version."""
    return {
        "meta_value": ParagraphStyle(
            "MetaValue", fontName="Helvetica", fontSize=9,
            leading=13, textColor=COLOR_MUTED,
        ),
        "file_name": ParagraphStyle(
            "FileName", fontName="Helvetica-Bold", fontSize=13,
            leading=17, textColor=colors.white,
        ),
        "file_tag": ParagraphStyle(
            "FileTag", fontName="Helvetica-Bold", fontSize=8,
            leading=17, textColor=colors.white, alignment=2,  # höger
        ),
        "muted_italic": ParagraphStyle(
            "MutedItalic", fontName="Helvetica-Oblique", fontSize=9.5,
            leading=14, textColor=COLOR_MUTED,
        ),
        "warning_italic": ParagraphStyle(
            "WarningItalic", fontName="Helvetica-Oblique", fontSize=9.5,
            leading=14, textColor=COLOR_WARNING,
        ),
        "code": ParagraphStyle(
            "Code", fontName="Courier", fontSize=7.6, leading=9.6,
            textColor=COLOR_INK,
        ),
    }


def _boxed(flowable, bg_color, width) -> Table:
    """Ramar in en Flowable (t.ex. Preformatted kodblock) i en tunn,
    ljus box med subtil kant."""
    t = Table([[flowable]], colWidths=[width])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg_color),
        ("BOX", (0, 0), (-1, -1), 0.6, COLOR_BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    return t


def _file_header(filename: str, category: str, width) -> Table:
    """Färgkodad rubrikrad — färgen styrs av kategori."""
    color = CATEGORY_COLORS.get(category, DEFAULT_CATEGORY_COLOR)
    styles = _styles()
    name_para = Paragraph(_xml_escape(filename), styles["file_name"])
    tag_para = Paragraph(_xml_escape(category.upper()), styles["file_tag"])
    t = Table([[name_para, tag_para]], colWidths=[width * 0.72, width * 0.28])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), color),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (0, 0), 12),
        ("RIGHTPADDING", (1, 0), (1, 0), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]))
    return t


def _read_text(path: str) -> tuple[str | None, str | None]:
    """Läser en textfil defensivt. Returnerar (innehåll, felmeddelande)."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read(), None
    except OSError as exc:
        return None, str(exc)


def _make_page_furniture(running_header_text: str):
    """Sidhuvud/sidfot: tunn accentlinje överst, en liten löptext
    (projektnamn) + sidnummer underst."""

    def _on_page(canvas, doc):
        canvas.saveState()
        page_w, page_h = PAGE_SIZE
        canvas.setFillColor(COLOR_ACCENT)
        canvas.rect(0, page_h - 5 * mm, page_w, 5 * mm, fill=1, stroke=0)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(COLOR_MUTED)
        canvas.drawString(MARGIN_LEFT, 12 * mm, running_header_text)
        canvas.drawRightString(page_w - MARGIN_RIGHT, 12 * mm, f"Sida {doc.page}")
        canvas.restoreState()

    return _on_page


def _write_single_pdf(
    f: PluginFileInfo,
    project_name: str,
    source_roots: list[str],
    output_path: str,
    styles: dict,
    content_width,
) -> None:
    """Bygger en enda PDF för en enda fil."""
    doc = BaseDocTemplate(
        output_path,
        pagesize=PAGE_SIZE,
        leftMargin=MARGIN_LEFT, rightMargin=MARGIN_RIGHT,
        topMargin=MARGIN_TOP, bottomMargin=MARGIN_BOTTOM,
        title=f"{f.relative_path} — AIDE",
        author="AIDE",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
    doc.addPageTemplates([
        PageTemplate(id="main", frames=[frame], onPage=_make_page_furniture(project_name))
    ])

    story = [_file_header(f.relative_path, f.category, content_width), Spacer(1, 8)]

    generated = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M")
    source_names = ", ".join(
        os.path.basename(str(s).rstrip("/\\")) or str(s) for s in source_roots
    ) or "–"
    meta_line = (
        f"Källa: {source_names}   •   Storlek: {f.size_bytes} bytes   •   "
        f"Genererat: {generated}"
    )
    story.append(Paragraph(_xml_escape(meta_line), styles["meta_value"]))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=0.6, color=COLOR_BORDER))
    story.append(Spacer(1, 14))

    if f.is_binary:
        story.append(Paragraph("[BINÄR FIL — innehåll ej inkluderat]", styles["muted_italic"]))
    elif f.size_bytes > MAX_INLINE_BYTES:
        story.append(Paragraph(
            f"[Filen är för stor för inline-inkludering "
            f"({f.size_bytes} bytes) — hoppades över]",
            styles["warning_italic"],
        ))
    else:
        content, error = _read_text(f.absolute_path)
        if error is not None:
            story.append(Paragraph(
                f"⚠ Kunde inte läsa filen: {_xml_escape(error)}", styles["warning_italic"],
            ))
        elif not (content or "").strip():
            story.append(Paragraph("[tom fil]", styles["muted_italic"]))
        else:
            _append_boxed_chunks(
                story, content, styles["code"], COLOR_CODE_BG, content_width,
                CODE_MAX_LINE_LEN, CODE_CHUNK_LINES,
            )

    doc.build(story)


def export_pdf(
    project_name: str,
    source_roots: list[str],
    included_files: list[PluginFileInfo],
    export_dir: str,
    conflict_strategy,
    log_callback,
) -> str | None:
    """
    Bygger EN PDF PER markerad fil, skrivna till en "pdf"-undermapp
    under export_dir med bevarad relativ mappstruktur (t.ex.
    "core/scanner.py" -> "pdf/core/scanner.py.pdf").

    Returnerar sökvägen till "pdf"-undermappen (så AIDE:s bekräftelse-
    dialog har något meningsfullt att peka på), eller None om inga
    filer alls kunde skrivas. Varje enskild fil loggas dessutom för
    sig via log_callback.
    """
    os.makedirs(export_dir, exist_ok=True)

    styles = _styles()
    content_width = PAGE_SIZE[0] - MARGIN_LEFT - MARGIN_RIGHT

    # Om användaren redan står i en mapp som heter "pdf" (t.ex. valde
    # "AIDE Box/pdf" som exportmapp för att den redan använder den
    # konventionen manuellt), ska vi INTE lägga till ännu en "pdf"-
    # undermapp ovanpå — det gav tidigare en "pdf/pdf"-dubblering.
    already_in_subfolder = (
        os.path.basename(os.path.normpath(str(export_dir))).lower() == "pdf"
    )
    subfolder_prefix = "" if already_in_subfolder else "pdf"

    written_count = 0
    for f in included_files:
        rel_target = f"{f.relative_path}.pdf"
        if subfolder_prefix:
            rel_target = os.path.join(subfolder_prefix, rel_target)

        try:
            target = ensure_within_export_dir(export_dir, rel_target)
        except ExportBlocked as exc:
            log_callback(f"⚠ Hoppade över (osäker sökväg): {f.relative_path} ({exc})")
            continue

        resolved = resolve_target_path(target, conflict_strategy)
        if resolved is None:
            log_callback(f"Hoppade över befintlig fil: {target}")
            continue

        os.makedirs(os.path.dirname(resolved), exist_ok=True)

        try:
            _write_single_pdf(f, project_name, source_roots, resolved, styles, content_width)
            written_count += 1
            log_callback(f"PDF skapad: {resolved}")
        except Exception as exc:
            log_callback(
                f"⚠ Kunde inte skapa PDF för {f.relative_path} "
                f"({type(exc).__name__}): {exc}"
            )

    if written_count == 0:
        return None

    pdf_dir = os.path.abspath(export_dir) if already_in_subfolder else ensure_within_export_dir(export_dir, "pdf")
    log_callback(f"PDF-export klar: {written_count}/{len(included_files)} filer i {pdf_dir}")
    return pdf_dir


class PdfExportPlugin(AIDEPlugin):

    @property
    def plugin_name(self) -> str:
        return "AIDE PDF Export"

    @property
    def plugin_version(self) -> str:
        return "1.1.0"

    def initialize(self) -> None:
        print(f"[{self.plugin_name}] Initialiserad.")

    def get_exporters(self):
        return {"pdf": export_pdf}

```

==================================================
FILE: plugins/zip_export/main_plugin.py
TYPE: Kod
==================================================

```python
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
FILE: tests/test_report_writer.py
TYPE: Kod
==================================================

```python
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.report_writer import create_report
from core.security import ConflictStrategy


def test_create_report_writes_file(tmp_path):
    export_dir = tmp_path / "AIDE Box"
    path = create_report(str(export_dir), "## Jämförelse\n\nFil A och B skiljer sig åt.")
    assert path is not None
    assert os.path.isfile(path)
    assert path.endswith("report.md")


def test_create_report_lands_in_report_subfolder(tmp_path):
    export_dir = tmp_path / "AIDE Box"
    path = create_report(str(export_dir), "innehåll")
    assert os.path.basename(os.path.dirname(path)) == "report"


def test_create_report_no_double_subfolder_if_already_there(tmp_path):
    export_dir = tmp_path / "AIDE Box" / "report"
    path = create_report(str(export_dir), "innehåll")
    # ska INTE bli .../report/report/report.md
    assert os.path.dirname(path) == str(export_dir)


def test_create_report_includes_project_header_when_given(tmp_path):
    export_dir = tmp_path / "AIDE Box"
    path = create_report(str(export_dir), "kroppstext", project_name="MittProjekt")
    text = open(path, encoding="utf-8").read()
    assert "MittProjekt" in text
    assert "kroppstext" in text


def test_create_report_omits_header_without_project_name(tmp_path):
    export_dir = tmp_path / "AIDE Box"
    path = create_report(str(export_dir), "kroppstext")
    text = open(path, encoding="utf-8").read()
    assert text.strip() == "kroppstext"


def test_create_report_rejects_empty_content(tmp_path):
    export_dir = tmp_path / "AIDE Box"
    path = create_report(str(export_dir), "   ")
    assert path is None
    assert not (export_dir / "report").exists()


def test_create_report_conflict_new_version(tmp_path):
    export_dir = tmp_path / "AIDE Box"
    first = create_report(str(export_dir), "första rapporten")
    second = create_report(str(export_dir), "andra rapporten", conflict_strategy=ConflictStrategy.NEW_VERSION)
    assert first != second
    assert os.path.isfile(first)
    assert os.path.isfile(second)


def test_create_report_conflict_skip_keeps_existing(tmp_path):
    export_dir = tmp_path / "AIDE Box"
    first = create_report(str(export_dir), "original")
    second = create_report(str(export_dir), "ny text", conflict_strategy=ConflictStrategy.SKIP)
    assert second is None
    assert open(first, encoding="utf-8").read().strip() == "original"


def test_create_report_conflict_overwrite_replaces(tmp_path):
    export_dir = tmp_path / "AIDE Box"
    first = create_report(str(export_dir), "original")
    second = create_report(str(export_dir), "uppdaterad", conflict_strategy=ConflictStrategy.OVERWRITE)
    assert first == second
    assert open(first, encoding="utf-8").read().strip() == "uppdaterad"


def test_create_report_never_escapes_export_dir(tmp_path):
    export_dir = tmp_path / "AIDE Box"
    export_dir.mkdir()
    path = create_report(str(export_dir), "innehåll", filename="../../etc/passwd")
    assert path is None

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
    def __init__(self, parent, on_selection_changed=None, localizer=None):
        super().__init__(parent)
        self.on_selection_changed = on_selection_changed

        self.localizer = localizer or getattr(parent, "localizer", None)
        if self.localizer is None:
            from core.localization_core import LocalizationCore
            self.localizer = LocalizationCore()

        self._scanned_files = []  # list[ScannedFile]
        self._file_items = {}     # iid -> ScannedFile
        self._dir_nodes = {}      # iid -> _DirNode
        self._dir_lookup = {}     # (parent_iid, name) -> iid
        self._filter_text = ""

        columns = ("size", "category", "status")
        self.tree = ttk.Treeview(self, columns=columns, show="tree headings", selectmode="extended")
        self.tree.heading("#0", text=self.localizer.get_text("tree_col_name"))
        self.tree.heading("size", text=self.localizer.get_text("tree_col_size"))
        self.tree.heading("category", text=self.localizer.get_text("tree_col_category"))
        self.tree.heading("status", text=self.localizer.get_text("tree_col_status"))
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
            if f.is_sensitive:
                status = self.localizer.get_text("tree_status_sensitive")
            elif f.is_binary:
                status = self.localizer.get_text("tree_status_binary")
            else:
                status = ""
            if f.error:
                status = self.localizer.get_text("tree_status_error")
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
                values=(
                    _human_size(total_size),
                    "",
                    self.localizer.get_text("tree_dir_file_count", n=total_count),
                ),
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
from core.easter_eggs import maybe_log_daddle
from core.hotkey_utils import format_shortcut_for_tk
from core.localization_core import LocalizationCore
from core.path_core import PathCore
from core.plugin_base import PluginFileInfo
from core.plugin_loader import discover_plugins
from core.scanner import ScanResult, ScannedFile, scan_sources
from core.security import ConflictStrategy, sanitize_filename
from core.settings import Settings, load_settings
from exporters.json_exporter import export_json_manifest
from exporters.markdown_exporter import export_markdown
from exporters.text_exporter import export_text
from exporters.tree_exporter import export_tree
from ui import theme
from ui.file_tree import FileTreeView
from ui.preview import PreviewWindow
from ui.settings_window import SettingsWindow


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

PROJECT_ROOT = PathCore.PROJECT_ROOT
PLUGINS_DIR = PathCore.get_plugins_root()
AIDE_BOX_DIR = PathCore.get_absolute_path("AIDE Box")


def _aide_box_subdir(name: str) -> str:
    """
    Returnerar (och skapar vid behov) en undermapp under AIDE Box.

    All automatisk export hamnar i en känd, förutsägbar struktur under
    AIDE:s egen installationsmapp — ingen manuell exportmapp krävs.
    """
    path = os.path.join(AIDE_BOX_DIR, name)
    os.makedirs(path, exist_ok=True)
    return path


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

        self.settings: Settings = load_settings()
        self.localizer = LocalizationCore(forced_lang=self.settings.language or None)

        self.title(self.localizer.get_text("app_title"))
        self.geometry("1220x780")
        self.minsize(960, 620)
        self.configure(fg_color=theme.COLOR_BG_MAIN)

        self.source_roots: list[str] = []

        # Export sker automatiskt till AIDE Box.
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
        self._bind_hotkeys()

        self.plugins = discover_plugins(
            PLUGINS_DIR,
            log_callback=self._log,
        )
        self._register_plugin_exporters()

        self._poll_queue()

        # Förbereds för framtida AI-rapporter.
        _aide_box_subdir("reports")

    # ------------------------------------------------------------------
    # ttk-tema för filträdet
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

        style.map(
            "Treeview.Heading",
            background=[("active", theme.COLOR_BG_PANEL)],
        )

        style.configure(
            "Vertical.TScrollbar",
            background=theme.COLOR_BG_PANEL,
            troughcolor=theme.COLOR_BG_MAIN,
        )

        style.configure(
            "Horizontal.TScrollbar",
            background=theme.COLOR_BG_PANEL,
            troughcolor=theme.COLOR_BG_MAIN,
        )

        style.configure(
            "TFrame",
            background=theme.COLOR_BG_MAIN,
        )

        style.configure(
            "TLabel",
            background=theme.COLOR_BG_MAIN,
            foreground=theme.COLOR_TEXT_PRIMARY,
        )

        style.configure(
            "TEntry",
            fieldbackground=theme.COLOR_BG_PANEL_ALT,
            foreground=theme.COLOR_TEXT_PRIMARY,
        )

    # ------------------------------------------------------------------
    # Tangentbordsgenvägar
    # ------------------------------------------------------------------

    def _bind_hotkeys(self):
        """
        Binder AIDE:s ombindningsbara genvägar (core/hotkey_utils.py)
        utifrån sparade inställningar (Settings.hotkeys). Anropas igen
        efter att Inställningar sparats, ifall en genväg ombundits.
        """
        handlers = {
            "scan": self._start_scan,
            "build_package": self._start_build,
            "preview": self._preview,
        }
        for name, handler in handlers.items():
            binding = self.settings.hotkeys.get(name)
            if not binding:
                continue
            tk_sequence = format_shortcut_for_tk(
                binding.get("modifiers", []), binding.get("key", "")
            )
            self.bind_all(tk_sequence, lambda event, h=handler: h())

    # ------------------------------------------------------------------
    # Övre panel
    # ------------------------------------------------------------------

    def _build_top_bar(self):
        top = ctk.CTkFrame(
            self,
            corner_radius=10,
            fg_color=theme.COLOR_BG_PANEL,
        )
        top.pack(pady=(10, 5), padx=10, fill="x")

        self.status_lamp = ctk.CTkLabel(
            top,
            text="●",
            text_color=theme.status_lamp_color("idle"),
            font=("Arial", 22),
        )
        self.status_lamp.pack(
            side="left",
            padx=(15, 5),
            pady=10,
        )

        self.status_label = ctk.CTkLabel(
            top,
            text=self.localizer.get_text("status_ready"),
            font=theme.FONT_TITLE,
        )
        self.status_label.pack(
            side="left",
            padx=5,
            pady=10,
        )

        ctk.CTkButton(
            top,
            text=self.localizer.get_text("btn_build_package"),
            command=self._start_build,
            width=140,
            fg_color=theme.COLOR_GREEN_DARK,
            hover_color=theme.COLOR_GREEN,
        ).pack(
            side="right",
            padx=(5, 15),
            pady=10,
        )

        ctk.CTkButton(
            top,
            text=self.localizer.get_text("btn_cancel"),
            command=self._cancel_operation,
            width=110,
            fg_color=theme.COLOR_RED_DARK,
            hover_color=theme.COLOR_RED,
        ).pack(
            side="right",
            padx=5,
            pady=10,
        )

        ctk.CTkButton(
            top,
            text=self.localizer.get_text("btn_scan"),
            command=self._start_scan,
            width=120,
            fg_color=theme.COLOR_BLUE_DARK,
            hover_color=theme.COLOR_BLUE,
        ).pack(
            side="right",
            padx=5,
            pady=10,
        )

        self.export_format_var = tk.StringVar(
            value=self.settings.default_export_format
        )

        self.export_format_menu = ctk.CTkOptionMenu(
            top,
            values=["markdown", "text", "tree", "json"],
            variable=self.export_format_var,
            width=110,
            fg_color=theme.COLOR_GRAY_DARK,
            button_color=theme.COLOR_GRAY,
            command=self._on_export_format_change,
        )

        self.export_format_menu.pack(
            side="right",
            padx=10,
            pady=10,
        )

    # ------------------------------------------------------------------
    # Matrix-panel
    # ------------------------------------------------------------------

    def _build_matrix_bar(self):
        matrix = ctk.CTkFrame(
            self,
            corner_radius=10,
            fg_color=theme.COLOR_BG_PANEL,
        )
        matrix.pack(
            pady=5,
            padx=10,
            fill="x",
        )

        ctk.CTkLabel(
            matrix,
            text=self.localizer.get_text("section_scan_control"),
            font=theme.FONT_SECTION,
            text_color=theme.COLOR_TEXT_MUTED,
        ).pack(
            anchor="w",
            padx=15,
            pady=(8, 2),
        )

        grid = ctk.CTkFrame(
            matrix,
            fg_color="transparent",
        )
        grid.pack(
            fill="x",
            padx=15,
            pady=(0, 10),
        )

        ctk.CTkButton(
            grid,
            text=self.localizer.get_text("btn_choose_source"),
            command=self._choose_source,
            width=130,
            fg_color=theme.COLOR_GRAY_DARK,
            hover_color=theme.COLOR_GRAY,
        ).grid(
            row=0,
            column=0,
            padx=(0, 8),
            pady=8,
            sticky="w",
        )

        ctk.CTkButton(
            grid,
            text=self.localizer.get_text("btn_remove_source"),
            command=self._remove_source,
            width=140,
            fg_color=theme.COLOR_GRAY_DARK,
            hover_color=theme.COLOR_GRAY,
        ).grid(
            row=0,
            column=1,
            padx=8,
            pady=8,
            sticky="w",
        )

        ctk.CTkButton(
            grid,
            text=self.localizer.get_text("btn_choose_export_dir"),
            command=self._choose_export_dir,
            width=140,
            fg_color=theme.COLOR_GRAY_DARK,
            hover_color=theme.COLOR_GRAY,
        ).grid(
            row=0,
            column=2,
            padx=8,
            pady=8,
            sticky="w",
        )

        ctk.CTkButton(
            grid,
            text=self.localizer.get_text("btn_preview"),
            command=self._preview,
            width=140,
            fg_color=theme.COLOR_GRAY_DARK,
            hover_color=theme.COLOR_GRAY,
        ).grid(
            row=0,
            column=3,
            padx=8,
            pady=8,
            sticky="w",
        )

        ctk.CTkButton(
            grid,
            text=self.localizer.get_text("btn_clear"),
            command=self._clear_all,
            width=90,
            fg_color=theme.COLOR_RED_DARK,
            hover_color=theme.COLOR_RED,
        ).grid(
            row=0,
            column=4,
            padx=8,
            pady=8,
            sticky="w",
        )

        ctk.CTkButton(
            grid,
            text=self.localizer.get_text("btn_settings"),
            command=self._open_settings,
            width=120,
            fg_color=theme.COLOR_GRAY_DARK,
            hover_color=theme.COLOR_GRAY,
        ).grid(
            row=0,
            column=5,
            padx=8,
            pady=8,
            sticky="w",
        )

        ctk.CTkButton(
            grid,
            text=self.localizer.get_text("btn_select_all"),
            command=lambda: self._set_all(True),
            width=110,
            fg_color=theme.COLOR_GRAY_DARK,
            hover_color=theme.COLOR_GRAY,
        ).grid(
            row=1,
            column=0,
            padx=(0, 8),
            pady=(0, 8),
            sticky="w",
        )

        ctk.CTkButton(
            grid,
            text=self.localizer.get_text("btn_deselect_all"),
            command=lambda: self._set_all(False),
            width=120,
            fg_color=theme.COLOR_GRAY_DARK,
            hover_color=theme.COLOR_GRAY,
        ).grid(
            row=1,
            column=1,
            padx=8,
            pady=(0, 8),
            sticky="w",
        )

        self.category_var = tk.StringVar()

        self.category_combo = ctk.CTkOptionMenu(
            grid,
            values=["–"],
            variable=self.category_var,
            width=130,
            fg_color=theme.COLOR_GRAY_DARK,
            button_color=theme.COLOR_GRAY,
        )
        self.category_combo.grid(
            row=1,
            column=2,
            padx=8,
            pady=(0, 8),
            sticky="w",
        )

        ctk.CTkButton(
            grid,
            text=self.localizer.get_text("btn_select_category"),
            command=lambda: self._set_category(True),
            width=140,
            fg_color=theme.COLOR_GRAY_DARK,
            hover_color=theme.COLOR_GRAY,
        ).grid(
            row=1,
            column=3,
            padx=8,
            pady=(0, 8),
            sticky="w",
        )

        ctk.CTkButton(
            grid,
            text=self.localizer.get_text("btn_deselect_category"),
            command=lambda: self._set_category(False),
            width=150,
            fg_color=theme.COLOR_GRAY_DARK,
            hover_color=theme.COLOR_GRAY,
        ).grid(
            row=1,
            column=4,
            padx=8,
            pady=(0, 8),
            sticky="w",
        )

        self.show_binary_switch = ctk.CTkSwitch(
            grid,
            text=self.localizer.get_text("switch_show_binary"),
            command=self._on_quick_toggle,
            font=theme.FONT_UI,
            text_color=theme.COLOR_TEXT_PRIMARY,
            progress_color=theme.COLOR_BLUE,
        )
        self.show_binary_switch.grid(
            row=1,
            column=5,
            padx=8,
            pady=(0, 8),
            sticky="w",
        )

        if self.settings.show_binary_files:
            self.show_binary_switch.select()

        ctk.CTkButton(
            grid, text=self.localizer.get_text("btn_register_gamebridge"), command=self._register_for_gamebridge, width=190,
            fg_color=theme.COLOR_BLUE_DARK, hover_color=theme.COLOR_BLUE,
        ).grid(row=1, column=6, padx=8, pady=(0, 8), sticky="w")

    # ------------------------------------------------------------------
    # Kropp
    # ------------------------------------------------------------------

    def _build_body(self):
        body = ctk.CTkFrame(
            self,
            fg_color="transparent",
        )
        body.pack(
            fill="both",
            expand=True,
            padx=10,
        )

        left = ctk.CTkFrame(
            body,
            fg_color="transparent",
        )
        left.pack(
            side="left",
            fill="both",
            expand=True,
        )

        src_frame = ctk.CTkFrame(
            left,
            corner_radius=10,
            fg_color=theme.COLOR_BG_PANEL,
        )
        src_frame.pack(
            fill="x",
            pady=(0, 6),
        )

        ctk.CTkLabel(
            src_frame,
            text=self.localizer.get_text("section_sources"),
            font=theme.FONT_SECTION,
            text_color=theme.COLOR_TEXT_MUTED,
        ).pack(
            anchor="w",
            padx=12,
            pady=(8, 2),
        )

        self.sources_listbox = tk.Listbox(
            src_frame,
            height=3,
            bg=theme.COLOR_BG_PANEL_ALT,
            fg=theme.COLOR_TEXT_PRIMARY,
            selectbackground=theme.COLOR_BLUE_DARK,
            borderwidth=0,
            highlightthickness=0,
        )
        self.sources_listbox.pack(
            fill="x",
            padx=12,
            pady=(0, 10),
        )

        filter_frame = ctk.CTkFrame(
            left,
            fg_color="transparent",
        )
        filter_frame.pack(
            fill="x",
            pady=(0, 6),
        )

        ctk.CTkLabel(
            filter_frame,
            text=self.localizer.get_text("filter_label"),
            font=theme.FONT_UI,
        ).pack(side="left")

        self.filter_var = tk.StringVar()
        self.filter_var.trace_add(
            "write",
            lambda *_: self.file_tree.apply_filter(
                self.filter_var.get()
            ),
        )

        ctk.CTkEntry(
            filter_frame,
            textvariable=self.filter_var,
            placeholder_text=self.localizer.get_text("filter_placeholder"),
            fg_color=theme.COLOR_BG_PANEL_ALT,
        ).pack(
            side="left",
            fill="x",
            expand=True,
            padx=6,
        )

        tree_container = ctk.CTkFrame(
            left,
            corner_radius=10,
            fg_color=theme.COLOR_BG_PANEL,
        )
        tree_container.pack(
            fill="both",
            expand=True,
        )

        self.file_tree = FileTreeView(
            tree_container,
            on_selection_changed=self._update_counts,
            localizer=self.localizer,
        )
        self.file_tree.pack(
            fill="both",
            expand=True,
            padx=8,
            pady=8,
        )

        right = ctk.CTkFrame(
            body,
            width=320,
            fg_color="transparent",
        )
        right.pack(
            side="left",
            fill="y",
            padx=(10, 0),
        )
        right.pack_propagate(False)

        info_frame = ctk.CTkFrame(
            right,
            corner_radius=10,
            fg_color=theme.COLOR_BG_PANEL,
        )
        info_frame.pack(fill="x")

        ctk.CTkLabel(
            info_frame,
            text=self.localizer.get_text("section_status"),
            font=theme.FONT_SECTION,
            text_color=theme.COLOR_TEXT_MUTED,
        ).pack(
            anchor="w",
            padx=12,
            pady=(10, 4),
        )

        self.export_dir_label = self._status_row(
            info_frame,
            self.localizer.get_text("label_export_dir_unset"),
        )
        self.found_label = self._status_row(
            info_frame,
            self.localizer.get_text("label_found_files", n=0),
        )
        self.included_label = self._status_row(
            info_frame,
            self.localizer.get_text("label_included", n=0),
        )
        self.excluded_label = self._status_row(
            info_frame,
            self.localizer.get_text("label_excluded", n=0),
        )
        self.sensitive_label = self._status_row(
            info_frame,
            self.localizer.get_text("label_sensitive_files", n=0),
            color=theme.COLOR_RED,
        )
        self.op_label = self._status_row(
            info_frame,
            self.localizer.get_text("label_current_op_idle"),
        )

        self.progress = ctk.CTkProgressBar(
            info_frame,
            progress_color=theme.COLOR_BLUE,
        )
        self.progress.pack(
            fill="x",
            padx=12,
            pady=(6, 12),
        )
        self.progress.set(0)

        log_frame = ctk.CTkFrame(
            right,
            corner_radius=10,
            fg_color=theme.COLOR_BG_PANEL,
        )
        log_frame.pack(
            fill="both",
            expand=True,
            pady=(10, 0),
        )

        ctk.CTkLabel(
            log_frame,
            text=self.localizer.get_text("section_log"),
            font=theme.FONT_SECTION,
            text_color=theme.COLOR_TEXT_MUTED,
        ).pack(
            anchor="w",
            padx=12,
            pady=(10, 4),
        )

        self.log_text = ctk.CTkTextbox(
            log_frame,
            font=theme.FONT_MONO,
            corner_radius=8,
            fg_color=theme.COLOR_BG_PANEL_ALT,
            text_color=theme.COLOR_TEXT_PRIMARY,
        )
        self.log_text.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=(0, 10),
        )
        self.log_text.configure(state="disabled")

    def _status_row(self, parent, text, color=None):
        label = ctk.CTkLabel(
            parent,
            text=text,
            font=theme.FONT_UI,
            text_color=color or theme.COLOR_TEXT_PRIMARY,
            anchor="w",
        )
        label.pack(
            anchor="w",
            padx=12,
            pady=1,
        )
        return label

    # ------------------------------------------------------------------
    # Nedre panel
    # ------------------------------------------------------------------

    def _build_bottom_bar(self):
        control = ctk.CTkFrame(
            self,
            fg_color="transparent",
        )
        control.pack(
            pady=(0, 5),
            padx=10,
            fill="x",
            side="bottom",
        )

        self.lock_switch = ctk.CTkSwitch(
            control,
            text=self.localizer.get_text("switch_lock_selection"),
            font=theme.FONT_UI,
            text_color=theme.COLOR_TEXT_PRIMARY,
            progress_color=theme.COLOR_RED,
            command=self._on_lock_toggle,
        )
        self.lock_switch.pack(
            side="left",
            padx=5,
        )

        version_label = ctk.CTkLabel(
            control,
            text=f"AIDE v{theme.APP_VERSION}",
            font=theme.FONT_UI,
            text_color=theme.COLOR_TEXT_MUTED,
        )
        version_label.pack(
            side="right",
            padx=5,
        )

    def _build_status_bar(self):
        self.status_var = tk.StringVar(value="Redo.")

        bar = ctk.CTkLabel(
            self,
            textvariable=self.status_var,
            anchor="w",
            font=theme.FONT_UI,
            text_color=theme.COLOR_TEXT_MUTED,
            fg_color=theme.COLOR_BG_PANEL,
            corner_radius=0,
        )
        bar.pack(
            fill="x",
            side="bottom",
        )

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
                self._log(
                    f"⚠ Plugin '{plugin.plugin_name}' "
                    f"kraschade i get_exporters(): {exc}"
                )
                continue

            for fmt_name, fn in (exporters or {}).items():
                if fmt_name in ("markdown", "text", "tree", "json"):
                    self._log(
                        f"⚠ Plugin '{plugin.plugin_name}' försökte registrera "
                        f"reserverat formatnamn '{fmt_name}', hoppar över."
                    )
                    continue

                self._plugin_exporters[fmt_name] = fn

        self.export_format_menu.configure(
            values=self._available_export_formats()
        )

    def _available_export_formats(self) -> list[str]:
        """
        Samlade exportformat: AIDE:s inbyggda plus vad som helst
        plugins registrerat via get_exporters(). Enda källan till
        sanning för detta — används både av exportformat-menyn här
        och av standardformat-väljaren i Inställningar, så de två
        aldrig kan hamna i otakt med varandra.
        """
        base_formats = ["markdown", "text", "tree", "json"]
        return base_formats + sorted(self._plugin_exporters.keys())

    def _apply_plugin_classification(self, files: list[ScannedFile]):
        """Låter plugins komplettera klassificeringen av 'Okänd'-filer."""
        unknown_files = [
            f for f in files
            if f.category == CATEGORY_UNKNOWN
        ]

        if not unknown_files or not self.plugins:
            return

        for f in unknown_files:
            info = _to_plugin_file_info(f)

            for plugin in self.plugins.values():
                try:
                    result = plugin.on_classify(info)
                except Exception as exc:
                    self._log(
                        f"⚠ Plugin '{plugin.plugin_name}' "
                        f"kraschade i on_classify(): {exc}"
                    )
                    continue

                if result:
                    f.category = result.get(
                        "category",
                        f.category,
                    )
                    f.language = result.get(
                        "language",
                        f.language,
                    )
                    f.is_sensitive = result.get(
                        "is_sensitive",
                        f.is_sensitive,
                    )
                    break

    def _notify_plugins_scan_complete(
        self,
        files: list[ScannedFile],
    ):
        if not self.plugins:
            return

        infos = [
            _to_plugin_file_info(f)
            for f in files
        ]

        for plugin in self.plugins.values():
            try:
                plugin.on_scan_complete(infos)
            except Exception as exc:
                self._log(
                    f"⚠ Plugin '{plugin.plugin_name}' "
                    f"kraschade i on_scan_complete(): {exc}"
                )

    def _apply_plugin_before_export(
        self,
        files: list[ScannedFile],
    ) -> list[ScannedFile]:
        """Ger plugins chansen att filtrera urvalet strax innan export."""
        if not self.plugins:
            return files

        by_path = {
            f.absolute_path: f
            for f in files
        }

        current = files

        for plugin in self.plugins.values():
            try:
                infos = [
                    _to_plugin_file_info(f)
                    for f in current
                ]
                result = plugin.on_before_export(infos)
            except Exception as exc:
                self._log(
                    f"⚠ Plugin '{plugin.plugin_name}' "
                    f"kraschade i on_before_export(): {exc}"
                )
                continue

            if result is not None:
                new_current = [
                    by_path[info.absolute_path]
                    for info in result
                    if info.absolute_path in by_path
                ]

                self._log(
                    f"Plugin '{plugin.plugin_name}' justerade "
                    f"exporturvalet: {len(current)} → "
                    f"{len(new_current)} filer."
                )

                current = new_current

        return current

    # ------------------------------------------------------------------
    # Källmappar
    # ------------------------------------------------------------------

    def _choose_source(self):
        directory = filedialog.askdirectory(
            title=self.localizer.get_text("btn_choose_source")
        )

        if directory and directory not in self.source_roots:
            self.source_roots.append(directory)
            self.sources_listbox.insert(
                "end",
                directory,
            )

    def _remove_source(self):
        selection = self.sources_listbox.curselection()

        if not selection:
            return

        index = selection[0]

        self.sources_listbox.delete(index)
        del self.source_roots[index]

    def _choose_export_dir(self):
        directory = filedialog.askdirectory(
            title=self.localizer.get_text("btn_choose_export_dir")
        )

        if directory:
            self.export_dir = directory
            self.export_dir_label.configure(
                text=self.localizer.get_text("label_export_dir", path=directory)
            )

    def _on_export_format_change(self, value):
        self.settings.default_export_format = value

    def _on_quick_toggle(self):
        self.settings.show_binary_files = (
            self.show_binary_switch.get() == 1
        )

    def _on_lock_toggle(self):
        locked = self.lock_switch.get() == 1
        self._log(
            "Urval låst."
            if locked
            else "Urval upplåst."
        )

    # ------------------------------------------------------------------
    # Skanning
    # ------------------------------------------------------------------

    def _start_scan(self):
        if self.lock_switch.get() == 1:
            messagebox.showinfo(
                self.localizer.get_text("dialog_selection_locked_title"),
                self.localizer.get_text("dialog_selection_locked_msg"),
            )
            return

        if not self.source_roots:
            messagebox.showwarning(
                self.localizer.get_text("dialog_no_sources_title"),
                self.localizer.get_text("dialog_no_sources_msg"),
            )
            return

        if (
            self._worker_thread
            and self._worker_thread.is_alive()
        ):
            messagebox.showinfo(
                self.localizer.get_text("dialog_busy_title"),
                self.localizer.get_text("dialog_busy_msg"),
            )
            return

        self._log(
            f"Scan started: {', '.join(self.source_roots)}"
        )

        self.op_label.configure(
            text=self.localizer.get_text("label_current_op_scanning")
        )
        self.status_label.configure(
            text=self.localizer.get_text("status_processing")
        )
        self.status_lamp.configure(
            text_color=theme.status_lamp_color("busy")
        )

        self.progress.configure(
            mode="indeterminate"
        )
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
                progress_callback=lambda done, total, path: (
                    self._ui_queue.put(
                        ("scan_progress", done, path)
                    )
                ),
                cancel_event=self._cancel_event,
            )

            self._ui_queue.put(
                ("scan_done", result)
            )

        self._worker_thread = threading.Thread(
            target=worker,
            daemon=True,
        )
        self._worker_thread.start()

    def _on_scan_done(self, result: ScanResult):
        self.progress.stop()
        self.progress.configure(
            mode="determinate"
        )
        self.progress.set(0)

        self.op_label.configure(
            text=self.localizer.get_text("label_current_op_idle")
        )
        self.status_label.configure(
            text=self.localizer.get_text("status_ready")
        )

        if result.cancelled:
            self._log(
                "Scan cancelled by user"
            )
            self.status_var.set(
                "Skanning avbruten."
            )
            self.status_lamp.configure(
                text_color=theme.status_lamp_color("idle")
            )
            return

        for path, reason in result.errors:
            self._log(
                f"⚠ Kunde inte läsa: {path} — {reason}"
            )

        sensitive_count = sum(
            1
            for f in result.files
            if f.is_sensitive
        )

        self._log(
            f"{len(result.files)} files discovered"
        )
        maybe_log_daddle(self._log)

        if sensitive_count:
            self._log(
                f"{sensitive_count} sensitive files detected"
            )

        self._apply_plugin_classification(
            result.files
        )
        self._notify_plugins_scan_complete(
            result.files
        )

        def default_checked(f):
            if f.is_sensitive:
                return False

            if (
                f.is_binary
                and not self.settings.show_binary_files
            ):
                return False

            return self.settings.default_checkbox_state

        self.file_tree.load_files(
            result.files,
            default_checked_fn=default_checked,
        )

        categories = (
            self.file_tree.get_categories()
            or ["–"]
        )

        self.category_combo.configure(
            values=categories
        )
        self.category_var.set(
            categories[0]
        )

        selected_count = sum(
            1
            for f in result.files
            if f.included
        )

        self._log(
            f"{selected_count} files selected"
        )

        self.status_var.set(
            f"Skanning klar: {len(result.files)} filer hittade."
        )

        self.status_lamp.configure(
            text_color=theme.status_lamp_color("ok")
        )

        self._update_counts()

        # Manifest skrivs automatiskt efter varje scan.
        self._write_scan_manifest(
            result.files
        )

    def _write_scan_manifest(
        self,
        all_files: list[ScannedFile],
    ):
        """
        Skriver manifestet automatiskt till AIDE Box/scan/ vid varje scan,
        så GameBridge/adaptern alltid ser färskaste state — oavsett om
        användaren senare bygger ett fullt paket eller inte.

        Skrivs alltid tyst över (ingen konfliktdialog): manifestet är en
        spegling av nuläget, inte ett artefakt att versionera.
        """
        if not self.source_roots:
            return

        included = [
            f
            for f in all_files
            if f.included
        ]

        project_name = (
            os.path.basename(
                self.source_roots[0].rstrip("/\\")
            )
            or "AIDE_Project"
        )

        safe_name = sanitize_filename(
            project_name
        )

        try:
            path = export_json_manifest(
                project_name,
                self.source_roots,
                included,
                _aide_box_subdir("scan"),
                filename=f"{safe_name}_manifest.json",
                conflict_strategy=ConflictStrategy.OVERWRITE,
                log_callback=self._log,
                include_absolute_paths=True,
            )

            if path:
                self._log(
                    f"Manifest uppdaterat: {path}"
                )

        except Exception as exc:
            self._log(
                f"⚠ Kunde inte skriva scan-manifest: {exc}"
            )

    # ------------------------------------------------------------------
    # Checkbox-styrning
    # ------------------------------------------------------------------

    def _set_all(self, included: bool):
        if self.lock_switch.get() == 1:
            return

        self.file_tree.set_all(
            included
        )

    def _set_category(self, included: bool):
        if self.lock_switch.get() == 1:
            return

        category = self.category_var.get()

        if category and category != "–":
            self.file_tree.set_category(
                category,
                included,
            )

    def _clear_all(self):
        self.source_roots.clear()
        self.sources_listbox.delete(
            0,
            "end",
        )

        self.file_tree.load_files([])

        self.category_combo.configure(
            values=["–"]
        )
        self.category_var.set("–")

        self._update_counts()
        self._log(
            "Cleared sources and file list"
        )
        self.status_var.set(
            "Rensat."
        )
        self.status_lamp.configure(
            text_color=theme.status_lamp_color("idle")
        )

    def _update_counts(self):
        all_files = self.file_tree.get_all_files()
        included = self.file_tree.get_included_files()

        self.found_label.configure(
            text=self.localizer.get_text("label_found_files", n=len(all_files))
        )

        self.included_label.configure(
            text=self.localizer.get_text("label_included", n=len(included))
        )

        self.excluded_label.configure(
            text=self.localizer.get_text(
                "label_excluded", n=len(all_files) - len(included)
            )
        )

        self.sensitive_label.configure(
            text=self.localizer.get_text(
                "label_sensitive_files",
                n=sum(1 for f in all_files if f.is_sensitive),
            )
        )

    # ------------------------------------------------------------------
    # Förhandsgranskning & export
    # ------------------------------------------------------------------

    def _preview(self):
        included = self.file_tree.get_included_files()

        if not included:
            messagebox.showinfo(
                self.localizer.get_text("dialog_nothing_selected_title"),
                self.localizer.get_text("dialog_nothing_selected_preview_msg"),
            )
            return

        PreviewWindow(
            self,
            self.file_tree.get_all_files(),
            self.source_roots,
            localizer=self.localizer,
        )

    def _start_build(self):
        included = self.file_tree.get_included_files()

        if not included:
            messagebox.showwarning(
                self.localizer.get_text("dialog_nothing_selected_title"),
                self.localizer.get_text("dialog_nothing_selected_msg"),
            )
            return

        if (
            self._worker_thread
            and self._worker_thread.is_alive()
        ):
            messagebox.showinfo(
                self.localizer.get_text("dialog_busy_title"),
                self.localizer.get_text("dialog_busy_msg"),
            )
            return

        included = self._apply_plugin_before_export(
            included
        )

        if not included:
            messagebox.showwarning(
                self.localizer.get_text("dialog_nothing_selected_title"),
                self.localizer.get_text("dialog_nothing_left_after_plugin_msg"),
            )
            return

        strategy = self._ask_conflict_strategy()

        if strategy is None:
            return

        self.op_label.configure(
            text=self.localizer.get_text("label_current_op_packaging")
        )
        self.status_label.configure(
            text=self.localizer.get_text("status_processing")
        )
        self.status_lamp.configure(
            text_color=theme.status_lamp_color("busy")
        )

        self.progress.configure(
            mode="indeterminate"
        )
        self.progress.start()

        project_name = (
            os.path.basename(
                self.source_roots[0]
            )
            if self.source_roots
            else "AIDE_Project"
        )

        safe_name = sanitize_filename(
            project_name
        )

        def worker():
            written = []
            fmt = self.settings.default_export_format

            log = lambda msg: self._ui_queue.put(
                ("log", msg)
            )

            try:
                if fmt == "markdown":
                    path = export_markdown(
                        project_name,
                        self.source_roots,
                        included,
                        _aide_box_subdir("md"),
                        filename=f"{safe_name}.md",
                        conflict_strategy=strategy,
                        log_callback=log,
                    )

                elif fmt == "text":
                    path = export_text(
                        project_name,
                        self.source_roots,
                        included,
                        _aide_box_subdir("text"),
                        filename=f"{safe_name}.txt",
                        conflict_strategy=strategy,
                        log_callback=log,
                    )

                elif fmt == "tree":
                    path = export_tree(
                        project_name,
                        self.source_roots,
                        included,
                        _aide_box_subdir("tree"),
                        filename=f"{safe_name}_tree.md",
                        conflict_strategy=strategy,
                        log_callback=log,
                    )

                elif fmt == "json":
                    path = export_json_manifest(
                        project_name,
                        self.source_roots,
                        included,
                        _aide_box_subdir("scan"),
                        filename=f"{safe_name}_manifest.json",
                        conflict_strategy=ConflictStrategy.OVERWRITE,
                        log_callback=log,
                    )

                elif fmt in self._plugin_exporters:
                    plugin_infos = [
                        _to_plugin_file_info(f)
                        for f in included
                    ]

                    path = self._plugin_exporters[fmt](
                        project_name,
                        self.source_roots,
                        plugin_infos,
                        _aide_box_subdir(fmt),
                        strategy,
                        log,
                    )

                else:
                    log(
                        f"⚠ Okänt exportformat '{fmt}', "
                        "faller tillbaka på markdown."
                    )

                    path = export_markdown(
                        project_name,
                        self.source_roots,
                        included,
                        _aide_box_subdir("md"),
                        filename=f"{safe_name}.md",
                        conflict_strategy=strategy,
                        log_callback=log,
                    )

                if path:
                    written.append(path)

                # Manifestet vid build ska alltid speglas i scan/.
                # Tyst överskrivning, oavsett vald konfliktstrategi
                # för själva paketet.
                manifest_path = export_json_manifest(
                    project_name,
                    self.source_roots,
                    included,
                    _aide_box_subdir("scan"),
                    filename=f"{safe_name}_manifest.json",
                    conflict_strategy=ConflictStrategy.OVERWRITE,
                    log_callback=log,
                    include_absolute_paths=True,
                )

                if (
                    manifest_path
                    and manifest_path not in written
                ):
                    written.append(
                        manifest_path
                    )

                self._ui_queue.put(
                    ("build_done", written)
                )

            except Exception as exc:
                self._ui_queue.put(
                    ("build_error", str(exc))
                )

        self._worker_thread = threading.Thread(
            target=worker,
            daemon=True,
        )
        self._worker_thread.start()

    def _ask_conflict_strategy(
        self,
    ) -> ConflictStrategy | None:
        answer = messagebox.askyesnocancel(
            self.localizer.get_text("dialog_conflict_title"),
            self.localizer.get_text("dialog_conflict_msg"),
        )

        if answer is None:
            return ConflictStrategy.SKIP

        return (
            ConflictStrategy.OVERWRITE
            if answer
            else ConflictStrategy.NEW_VERSION
        )

    def _on_build_done(
        self,
        written_paths: list[str],
    ):
        self.progress.stop()
        self.progress.configure(
            mode="determinate"
        )
        self.progress.set(0)

        self.op_label.configure(
            text=self.localizer.get_text("label_current_op_idle")
        )
        self.status_label.configure(
            text=self.localizer.get_text("status_ready")
        )

        self._log(
            "Package created"
        )

        if written_paths:
            self.status_var.set(
                f"Paket skapat: {len(written_paths)} fil(er) skrivna."
            )

            self.status_lamp.configure(
                text_color=theme.status_lamp_color("ok")
            )

            messagebox.showinfo(
                self.localizer.get_text("dialog_done_title"),
                self.localizer.get_text("dialog_done_msg")
                + "\n".join(written_paths),
            )

        else:
            self.status_var.set(
                "Ingen fil skrevs (allt hoppades över)."
            )

            self.status_lamp.configure(
                text_color=theme.status_lamp_color("idle")
            )

    def _on_build_error(
        self,
        message: str,
    ):
        self.progress.stop()
        self.progress.configure(
            mode="determinate"
        )
        self.progress.set(0)

        self.op_label.configure(
            text=self.localizer.get_text("label_current_op_idle")
        )
        self.status_label.configure(
            text=self.localizer.get_text("status_ready")
        )
        self.status_lamp.configure(
            text_color=theme.status_lamp_color("error")
        )

        self._log(
            f"⚠ Fel vid paketering: {message}"
        )

        messagebox.showerror(
            self.localizer.get_text("dialog_error_title"),
            self.localizer.get_text("dialog_error_msg") + message,
        )

    def _cancel_operation(self):
        if self._cancel_event is not None:
            self._cancel_event.set()
            self._log(
                "Cancel requested by user"
            )

    # ------------------------------------------------------------------
    # Inställningar
    # ------------------------------------------------------------------

    def _open_settings(self):
        SettingsWindow(
            self,
            self.settings,
            on_saved=self._on_settings_saved,
            available_formats=self._available_export_formats(),
        )

    def _register_for_gamebridge(self):
        from core.plugin_registration import register_for_gamebridge

        path = register_for_gamebridge(PROJECT_ROOT, log_callback=self._log)
        self.status_var.set(f"Registrerad för GameBridge: {path}")

    def _on_settings_saved(
        self,
        settings: Settings,
    ):
        self.settings = settings

        # Ny sparad LocalizationCore-instans i fallet språket byttes;
        # get_text-anropen i redan byggda widgets uppdateras inte
        # retroaktivt (kräver en fönster-omritning för att synas fullt
        # ut), men nya dialoger/fönster som öppnas efter det här
        # använder rätt språk direkt.
        self.localizer.set_language(settings.language) if settings.language else None

        self.export_format_var.set(
            settings.default_export_format
        )

        if settings.show_binary_files:
            self.show_binary_switch.select()
        else:
            self.show_binary_switch.deselect()

        self._bind_hotkeys()

        self._log(
            "Settings updated"
        )

    # ------------------------------------------------------------------
    # Logg och köhantering
    # ------------------------------------------------------------------

    def _log(self, message: str):
        timestamp = datetime.now().strftime(
            "%H:%M:%S"
        )

        self.log_text.configure(
            state="normal"
        )

        self.log_text.insert(
            "end",
            f"{timestamp}  {message}\n",
        )

        self.log_text.see("end")

        self.log_text.configure(
            state="disabled"
        )

    def _poll_queue(self):
        try:
            while True:
                item = self._ui_queue.get_nowait()
                kind = item[0]

                if kind == "scan_progress":
                    _, done, path = item
                    self.status_var.set(
                        f"Skannar... {done} filer ({path})"
                    )

                elif kind == "scan_done":
                    self._on_scan_done(
                        item[1]
                    )

                elif kind == "build_done":
                    self._on_build_done(
                        item[1]
                    )

                elif kind == "build_error":
                    self._on_build_error(
                        item[1]
                    )

                elif kind == "log":
                    self._log(
                        item[1]
                    )

        except queue.Empty:
            pass

        self.after(
            100,
            self._poll_queue,
        )

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
    def __init__(self, parent, all_files, source_roots, localizer=None):
        super().__init__(parent)

        self.localizer = localizer or getattr(parent, "localizer", None)
        if self.localizer is None:
            from core.localization_core import LocalizationCore
            self.localizer = LocalizationCore()

        self.title(self.localizer.get_text("preview_window_title"))
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
            header, text=self.localizer.get_text("preview_summary"), font=theme.FONT_SECTION,
            text_color=theme.COLOR_TEXT_MUTED,
        ).pack(anchor="w", padx=14, pady=(12, 4))

        def row(text, color=None):
            ctk.CTkLabel(
                header, text=text, font=theme.FONT_UI,
                text_color=color or theme.COLOR_TEXT_PRIMARY, anchor="w",
            ).pack(anchor="w", padx=14, pady=1)

        row(self.localizer.get_text(
            "preview_sources", sources=", ".join(str(s) for s in source_roots)
        ))
        row(self.localizer.get_text("preview_included", n=len(included)))
        row(self.localizer.get_text("preview_excluded", n=len(excluded)))
        row(self.localizer.get_text("preview_total_size", size=_human_size(total_size)))

        cat_text = ", ".join(f"{cat}: {count}" for cat, count in sorted(by_category.items()))
        row(self.localizer.get_text("preview_category_breakdown", breakdown=cat_text or "–"))

        if sensitive_included:
            row(
                self.localizer.get_text("preview_sensitive_warning", n=len(sensitive_included)),
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
        tree.heading("#0", text=self.localizer.get_text("preview_col_file"))
        tree.heading("status", text=self.localizer.get_text("preview_col_status"))
        tree.heading("category", text=self.localizer.get_text("preview_col_category"))
        tree.heading("size", text=self.localizer.get_text("preview_col_size"))
        tree.column("#0", width=380)
        tree.column("status", width=110)
        tree.column("category", width=140)
        tree.column("size", width=80, anchor="e")

        tree.pack(side="left", fill="both", expand=True, padx=8, pady=8)

        for f in sorted(all_files, key=lambda x: x.relative_path.lower()):
            status = (
                self.localizer.get_text("preview_status_included")
                if f.included
                else self.localizer.get_text("preview_status_excluded")
            )
            if f.is_sensitive:
                status += " ⚠"
            tree.insert("", "end", text=f.relative_path, values=(status, f.category, f.size_human))

        ctk.CTkButton(
            self, text=self.localizer.get_text("preview_close"), command=self.destroy, width=120,
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
FILE: ui/scan_panel.py
TYPE: Kod
==================================================

```python
"""
ui/scan_panel.py

Självständig, återanvändbar scan-enhet: källmappar (flera, som i AIDE:s
normalläge), skanna-knapp, filträd, filter, statusrader, och automatisk
manifestskrivning till AIDE Box/scan/.

ANVÄNDNING:
  - Jämförelseläge i MainWindow: två ScanPanel-instanser sida vid sida
    ("A" och "B"), var och en med sina egna källmappar, eget träd, eget
    manifest. Endast en panel är "aktiv för export" åt gången — det styrs
    utifrån (MainWindow), inte av panelen själv.

ANSVARSGRÄNS:
  Panelen känner INTE till export-logik för md/text/tree/json. Den
  ansvarar bara för: välja källor, skanna, visa träd, räkna, och
  automatiskt skriva sitt eget manifest vid varje scan (samma mönster
  som AIDE:s normalläge). MainWindow läser panelens
  get_included_files() / source_roots när ett faktiskt paket ska byggas.

FILNAMN VID MANIFEST-SKRIVNING:
  Baseras på källmappens namn (samma som normalläget). Om två paneler
  råkar ha källmappar med IDENTISKT namn skriver de över samma fil i
  AIDE Box/scan/ — det är avsett beteende (manifestet ska alltid spegla
  senaste scan av den mappen, historik hanteras av separat planerad
  backup-funktion, inte av jämförelseläget).
"""

from __future__ import annotations

import os
import threading
import queue
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk

from core.scanner import ScanResult, ScannedFile, scan_sources
from core.security import ConflictStrategy, sanitize_filename
from exporters.json_exporter import export_json_manifest
from ui.file_tree import FileTreeView
from ui import theme


class ScanPanel(ctk.CTkFrame):
    """
    En självständig scan-panel. panel_id ("A"/"B") används för tydliga
    loggetiketter och visuell märkning — så det alltid är uppenbart
    vilken panel som skannas eller är aktiv för export.
    """

    def __init__(
        self,
        parent,
        panel_id: str,
        settings,
        aide_box_subdir_fn,
        log_callback,
        on_selection_changed=None,
        on_scan_started=None,
        on_scan_finished=None,
    ):
        super().__init__(parent, fg_color="transparent")
        self.panel_id = panel_id  # "A" eller "B"
        self.settings = settings
        self._aide_box_subdir = aide_box_subdir_fn
        self._log = log_callback
        self._on_selection_changed_cb = on_selection_changed
        self._on_scan_started_cb = on_scan_started
        self._on_scan_finished_cb = on_scan_finished

        self.source_roots: list[str] = []
        self._cancel_event: threading.Event | None = None
        self._worker_thread: threading.Thread | None = None
        self._ui_queue: "queue.Queue" = queue.Queue()

        self._build_ui()
        self._poll_queue()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        header = ctk.CTkFrame(self, corner_radius=10, fg_color=theme.COLOR_BG_PANEL)
        header.pack(fill="x", pady=(0, 6))

        title_row = ctk.CTkFrame(header, fg_color="transparent")
        title_row.pack(fill="x", padx=12, pady=(8, 2))

        ctk.CTkLabel(
            title_row, text=f"KÄLLMAPPAR — PANEL {self.panel_id}", font=theme.FONT_SECTION,
            text_color=theme.COLOR_TEXT_MUTED,
        ).pack(side="left")

        self.active_indicator = ctk.CTkLabel(
            title_row, text="", font=theme.FONT_SECTION,
            text_color=theme.COLOR_GREEN,
        )
        self.active_indicator.pack(side="right")

        self.sources_listbox = tk.Listbox(
            header, height=3, bg=theme.COLOR_BG_PANEL_ALT, fg=theme.COLOR_TEXT_PRIMARY,
            selectbackground=theme.COLOR_BLUE_DARK, borderwidth=0, highlightthickness=0,
        )
        self.sources_listbox.pack(fill="x", padx=12, pady=(0, 8))

        btn_row = ctk.CTkFrame(header, fg_color="transparent")
        btn_row.pack(fill="x", padx=12, pady=(0, 10))

        ctk.CTkButton(
            btn_row, text="Välj källmapp", command=self._choose_source, width=120,
            fg_color=theme.COLOR_GRAY_DARK, hover_color=theme.COLOR_GRAY,
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            btn_row, text="Ta bort", command=self._remove_source, width=90,
            fg_color=theme.COLOR_GRAY_DARK, hover_color=theme.COLOR_GRAY,
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            btn_row, text=f"Skanna {self.panel_id}", command=self._start_scan, width=110,
            fg_color=theme.COLOR_BLUE_DARK, hover_color=theme.COLOR_BLUE,
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            btn_row, text="Avbryt", command=self._cancel_operation, width=90,
            fg_color=theme.COLOR_RED_DARK, hover_color=theme.COLOR_RED,
        ).pack(side="left")

        filter_frame = ctk.CTkFrame(self, fg_color="transparent")
        filter_frame.pack(fill="x", pady=(0, 6))
        ctk.CTkLabel(filter_frame, text="Filter:", font=theme.FONT_UI).pack(side="left")
        self.filter_var = tk.StringVar()
        self.filter_var.trace_add("write", lambda *_: self.file_tree.apply_filter(self.filter_var.get()))
        ctk.CTkEntry(
            filter_frame, textvariable=self.filter_var, placeholder_text="Sök filnamn, sökväg, kategori...",
            fg_color=theme.COLOR_BG_PANEL_ALT,
        ).pack(side="left", fill="x", expand=True, padx=6)

        tree_container = ctk.CTkFrame(self, corner_radius=10, fg_color=theme.COLOR_BG_PANEL)
        tree_container.pack(fill="both", expand=True, pady=(0, 6))
        self.file_tree = FileTreeView(tree_container, on_selection_changed=self._on_tree_changed)
        self.file_tree.pack(fill="both", expand=True, padx=8, pady=8)

        status_frame = ctk.CTkFrame(self, corner_radius=10, fg_color=theme.COLOR_BG_PANEL)
        status_frame.pack(fill="x")
        self.found_label = self._status_row(status_frame, "Hittade filer: 0")
        self.included_label = self._status_row(status_frame, "Inkluderade: 0")
        self.sensitive_label = self._status_row(status_frame, "Känsliga filer: 0", color=theme.COLOR_RED)
        self.op_label = self._status_row(status_frame, "Aktuell operation: Inaktiv")

        self.progress = ctk.CTkProgressBar(status_frame, progress_color=theme.COLOR_BLUE)
        self.progress.pack(fill="x", padx=12, pady=(6, 10))
        self.progress.set(0)

    def _status_row(self, parent, text, color=None):
        label = ctk.CTkLabel(
            parent, text=text, font=theme.FONT_UI,
            text_color=color or theme.COLOR_TEXT_PRIMARY, anchor="w",
        )
        label.pack(anchor="w", padx=12, pady=1)
        return label

    # ------------------------------------------------------------------
    # Aktiv-markering (visuell — MainWindow bestämmer vilken panel som
    # är aktiv, panelen bara visar det tydligt)
    # ------------------------------------------------------------------

    def set_active_indicator(self, is_active: bool):
        self.active_indicator.configure(
            text="● AKTIV FÖR EXPORT" if is_active else ""
        )

    # ------------------------------------------------------------------
    # Källmappar
    # ------------------------------------------------------------------

    def _choose_source(self):
        directory = filedialog.askdirectory(title=f"Välj källmapp — Panel {self.panel_id}")
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

    # ------------------------------------------------------------------
    # Skanning
    # ------------------------------------------------------------------

    def _start_scan(self):
        if not self.source_roots:
            messagebox.showwarning(
                "Inga källor", f"Välj minst en källmapp i Panel {self.panel_id} innan skanning."
            )
            return
        if self._worker_thread and self._worker_thread.is_alive():
            messagebox.showinfo("Pågår redan", f"En skanning pågår redan i Panel {self.panel_id}.")
            return

        self._log(f"[Panel {self.panel_id}] Scan started: {', '.join(self.source_roots)}")
        self.op_label.configure(text="Aktuell operation: Skannar...")
        self.progress.configure(mode="indeterminate")
        self.progress.start()
        self._cancel_event = threading.Event()

        if self._on_scan_started_cb:
            self._on_scan_started_cb(self.panel_id)

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

        if result.cancelled:
            self._log(f"[Panel {self.panel_id}] Scan cancelled by user")
            if self._on_scan_finished_cb:
                self._on_scan_finished_cb(self.panel_id, cancelled=True)
            return

        for path, reason in result.errors:
            self._log(f"[Panel {self.panel_id}] ⚠ Kunde inte läsa: {path} — {reason}")

        sensitive_count = sum(1 for f in result.files if f.is_sensitive)
        self._log(f"[Panel {self.panel_id}] {len(result.files)} files discovered")
        if sensitive_count:
            self._log(f"[Panel {self.panel_id}] {sensitive_count} sensitive files detected")

        def default_checked(f):
            if f.is_sensitive:
                return False
            if f.is_binary and not self.settings.show_binary_files:
                return False
            return self.settings.default_checkbox_state

        self.file_tree.load_files(result.files, default_checked_fn=default_checked)

        selected_count = sum(1 for f in result.files if f.included)
        self._log(f"[Panel {self.panel_id}] {selected_count} files selected")

        self._update_counts()
        self._write_scan_manifest(result.files)

        if self._on_scan_finished_cb:
            self._on_scan_finished_cb(self.panel_id, cancelled=False)

    def _write_scan_manifest(self, all_files: list[ScannedFile]):
        """Skriver panelens manifest automatiskt till AIDE Box/scan/ (tyst överskrivning)."""
        if not self.source_roots:
            return

        included = [f for f in all_files if f.included]
        project_name = os.path.basename(self.source_roots[0].rstrip("/\\")) or "AIDE_Project"
        safe_name = sanitize_filename(project_name)

        try:
            path = export_json_manifest(
                project_name, self.source_roots, included,
                self._aide_box_subdir("scan"),
                filename=f"{safe_name}_manifest.json",
                conflict_strategy=ConflictStrategy.OVERWRITE,
                log_callback=self._log,
                include_absolute_paths=True,
            )
            if path:
                self._log(f"[Panel {self.panel_id}] Manifest uppdaterat: {path}")
        except Exception as exc:
            self._log(f"[Panel {self.panel_id}] ⚠ Kunde inte skriva scan-manifest: {exc}")

    def _cancel_operation(self):
        if self._cancel_event is not None:
            self._cancel_event.set()
            self._log(f"[Panel {self.panel_id}] Cancel requested by user")

    # ------------------------------------------------------------------
    # Status / räknare
    # ------------------------------------------------------------------

    def _on_tree_changed(self):
        self._update_counts()
        if self._on_selection_changed_cb:
            self._on_selection_changed_cb(self.panel_id)

    def _update_counts(self):
        all_files = self.file_tree.get_all_files()
        included = self.file_tree.get_included_files()
        self.found_label.configure(text=f"Hittade filer: {len(all_files)}")
        self.included_label.configure(text=f"Inkluderade: {len(included)}")
        self.sensitive_label.configure(
            text=f"Känsliga filer: {sum(1 for f in all_files if f.is_sensitive)}"
        )

    # ------------------------------------------------------------------
    # Publikt API mot MainWindow
    # ------------------------------------------------------------------

    def get_included_files(self) -> list[ScannedFile]:
        return self.file_tree.get_included_files()

    def get_all_files(self) -> list[ScannedFile]:
        return self.file_tree.get_all_files()

    def get_categories(self) -> list[str]:
        return self.file_tree.get_categories()

    def has_scanned_data(self) -> bool:
        return len(self.file_tree.get_all_files()) > 0

    def clear(self):
        self.source_roots.clear()
        self.sources_listbox.delete(0, "end")
        self.file_tree.load_files([])
        self._update_counts()

    # ------------------------------------------------------------------
    # Köhantering (bakgrundstråd -> huvudtråd)
    # ------------------------------------------------------------------

    def _poll_queue(self):
        try:
            while True:
                item = self._ui_queue.get_nowait()
                kind = item[0]
                if kind == "scan_done":
                    self._on_scan_done(item[1])
                # scan_progress ignoreras medvetet här — panelens op_label
                # räcker som statusindikation, ingen separat progressbar-text.
        except queue.Empty:
            pass
        self.after(100, self._poll_queue)

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

Lokalisering: återanvänder huvudfönstrets LocalizationCore-instans
(via parent.localizer) istället för att skapa en egen — så språkvalet
alltid är konsekvent mellan fönstren. Faller tillbaka på en egen
instans om fönstret av någon anledning öppnas utan en förälder som
har en localizer (t.ex. i tester), så modulen aldrig kraschar bara
för att den körs fristående.

Genvägar: visar AIDE:s ombindningsbara genvägar (core/hotkey_utils.py)
och låter användaren spela in en ny tangentkombination per kommando.
Ändringar sparas lokalt i fönstret och committas till settings.hotkeys
först vid "Spara", precis som alla andra fält i det här fönstret.
"""

from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from core.hotkey_utils import HotkeyCapture, format_shortcut_for_display
from core.settings import Settings, save_settings
from ui import theme

# Vilka locales.json-nycklar som ska användas som visningsnamn för
# respektive ombindningsbart kommando i settings.hotkeys. Återanvänder
# huvudfönstrets egna knapptextnycklar så namnen alltid är konsekventa.
HOTKEY_COMMAND_LABEL_KEYS = {
    "scan": "btn_scan",
    "build_package": "btn_build_package",
    "preview": "btn_preview",
}

# Visningsnamn för språkväljaren. Medvetet tvåspråkiga etiketter här
# (inte lokaliserade via get_text) eftersom det här ÄR språkvalet
# självt — ett hönan/ägget-problem att lokalisera den egna kontrollen
# för att byta språk.
LANGUAGE_DISPLAY_NAMES = {
    "": "Automatiskt (systemspråk) / Auto (system language)",
    "sv": "Svenska",
    "en": "English",
}


class SettingsWindow(ctk.CTkToplevel):
    def __init__(
        self,
        parent,
        settings: Settings,
        on_saved=None,
        localizer=None,
        available_formats: list[str] | None = None,
    ):
        super().__init__(parent)

        self.localizer = localizer or getattr(parent, "localizer", None)
        if self.localizer is None:
            from core.localization_core import LocalizationCore
            self.localizer = LocalizationCore(forced_lang=settings.language or None)

        self.title(self.localizer.get_text("settings_window_title"))
        self.geometry("600x640")
        self.minsize(520, 420)
        self.configure(fg_color=theme.COLOR_BG_MAIN)
        self.settings = settings
        self.on_saved = on_saved
        self.resizable(True, True)
        self.transient(parent)

        # Lokal arbetskopia av genvägarna — committas till self.settings
        # först vid "Spara", precis som resten av fönstrets fält.
        self._hotkeys_working = {k: dict(v) for k, v in settings.hotkeys.items()}
        self._hotkey_capture = HotkeyCapture(self)
        self._hotkey_value_labels: dict[str, ctk.CTkLabel] = {}
        self._hotkey_rebind_buttons: dict[str, ctk.CTkButton] = {}

        # Knappraden packas FÖRST och med side="bottom" direkt på
        # fönstret (inte i den scrollbara ytan) — den reserverar sin
        # plats innan resten av innehållet läggs till, så Spara/Avbryt
        # alltid syns oavsett hur mycket annat innehåll fönstret får
        # (t.ex. fler genvägar i en framtida version). Tidigare låg allt
        # i en enda ej-scrollbar CTkFrame med fast fönsterhöjd, vilket
        # gjorde att knapparna helt enkelt hamnade utanför synligt
        # område när genvägssektionen lades till — knapparna fanns i
        # koden men gick aldrig att nå.
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=16, pady=(8, 12), side="bottom")
        ctk.CTkButton(
            btn_frame, text=self.localizer.get_text("settings_cancel"), command=self.destroy, width=110,
            fg_color=theme.COLOR_GRAY_DARK, hover_color=theme.COLOR_GRAY,
        ).pack(side="right", padx=(8, 0))
        ctk.CTkButton(
            btn_frame, text=self.localizer.get_text("settings_save"), command=self._save, width=110,
            fg_color=theme.COLOR_GREEN_DARK, hover_color=theme.COLOR_GREEN,
        ).pack(side="right")

        frame = ctk.CTkScrollableFrame(self, corner_radius=10, fg_color=theme.COLOR_BG_PANEL)
        frame.pack(fill="both", expand=True, padx=12, pady=(12, 0))

        ctk.CTkLabel(
            frame, text=self.localizer.get_text("settings_header"),
            font=theme.FONT_SECTION, text_color=theme.COLOR_TEXT_MUTED,
        ).pack(anchor="w", padx=16, pady=(14, 6))

        def label(text):
            ctk.CTkLabel(frame, text=text, font=theme.FONT_UI, text_color=theme.COLOR_TEXT_PRIMARY).pack(
                anchor="w", padx=16, pady=(10, 2)
            )

        def entry(var):
            e = ctk.CTkEntry(frame, textvariable=var, fg_color=theme.COLOR_BG_PANEL_ALT, width=550)
            e.pack(padx=16, pady=(0, 2), fill="x")
            return e

        # --- Språk ------------------------------------------------------

        label(self.localizer.get_text("settings_language"))
        current_display = LANGUAGE_DISPLAY_NAMES.get(
            settings.language, LANGUAGE_DISPLAY_NAMES[""]
        )
        self.language_var = tk.StringVar(value=current_display)
        language_menu = ctk.CTkOptionMenu(
            frame, values=list(LANGUAGE_DISPLAY_NAMES.values()),
            command=self.language_var.set,
            fg_color=theme.COLOR_GRAY_DARK, button_color=theme.COLOR_GRAY, width=550,
        )
        language_menu.set(current_display)
        language_menu.pack(padx=16, pady=(0, 2), fill="x")

        # --- Filhantering -------------------------------------------------

        label(self.localizer.get_text("settings_ignore_dirs"))
        self.ignore_dirs_var = tk.StringVar(value=", ".join(settings.ignore_dirs))
        entry(self.ignore_dirs_var)

        label(self.localizer.get_text("settings_ignore_files"))
        self.ignore_files_var = tk.StringVar(value=", ".join(settings.ignore_files))
        entry(self.ignore_files_var)

        label(self.localizer.get_text("settings_sensitive_patterns"))
        self.sensitive_var = tk.StringVar(value=", ".join(settings.sensitive_patterns))
        entry(self.sensitive_var)

        label(self.localizer.get_text("settings_default_format"))
        self.export_format_var = tk.StringVar(value=settings.default_export_format)

        # Dynamiskt: kommer från MainWindow:s faktiska plugin-register
        # (_available_export_formats()), inte en hårdkodad lista här —
        # så nya exportformat från plugins (zip, pdf, report, och vad
        # Gemini än hittar på framöver) dyker upp automatiskt utan att
        # den här filen behöver ändras varje gång.
        format_values = list(available_formats) if available_formats else ["markdown", "text", "tree", "json"]
        if settings.default_export_format not in format_values:
            # Ett tidigare sparat format vars plugin inte är installerad
            # just nu (eller är avstängd) — visa det ändå istället för
            # att tyst byta bort användarens val i bakgrunden.
            format_values = [settings.default_export_format] + format_values

        format_menu = ctk.CTkOptionMenu(
            frame, values=format_values,
            command=self.export_format_var.set,
            fg_color=theme.COLOR_GRAY_DARK, button_color=theme.COLOR_GRAY, width=550,
        )
        format_menu.set(settings.default_export_format)
        format_menu.pack(padx=16, pady=(0, 2), fill="x")

        label(self.localizer.get_text("settings_default_export_dir"))
        self.export_dir_var = tk.StringVar(value=settings.default_export_dir)
        entry(self.export_dir_var)

        switch_frame = ctk.CTkFrame(frame, fg_color="transparent")
        switch_frame.pack(fill="x", padx=16, pady=(16, 4))

        self.show_binary_var = tk.BooleanVar(value=settings.show_binary_files)
        self.show_binary_switch = ctk.CTkSwitch(
            switch_frame, text=self.localizer.get_text("settings_show_binary"), variable=self.show_binary_var,
            font=theme.FONT_UI, text_color=theme.COLOR_TEXT_PRIMARY, progress_color=theme.COLOR_BLUE,
        )
        self.show_binary_switch.pack(anchor="w", pady=4)

        self.show_hidden_var = tk.BooleanVar(value=settings.show_hidden_files)
        self.show_hidden_switch = ctk.CTkSwitch(
            switch_frame, text=self.localizer.get_text("settings_show_hidden"), variable=self.show_hidden_var,
            font=theme.FONT_UI, text_color=theme.COLOR_TEXT_PRIMARY, progress_color=theme.COLOR_BLUE,
        )
        self.show_hidden_switch.pack(anchor="w", pady=4)

        self.default_checkbox_var = tk.BooleanVar(value=settings.default_checkbox_state)
        self.default_checkbox_switch = ctk.CTkSwitch(
            switch_frame,
            text=self.localizer.get_text("settings_default_checkbox"),
            variable=self.default_checkbox_var,
            font=theme.FONT_UI, text_color=theme.COLOR_TEXT_PRIMARY, progress_color=theme.COLOR_GREEN,
        )
        self.default_checkbox_switch.pack(anchor="w", pady=4)

        # --- Tangentbordsgenvägar ------------------------------------------

        label(self.localizer.get_text("settings_hotkeys_header"))
        hotkeys_frame = ctk.CTkFrame(frame, fg_color=theme.COLOR_BG_PANEL_ALT, corner_radius=8)
        hotkeys_frame.pack(padx=16, pady=(0, 4), fill="x")

        for command_name, label_key in HOTKEY_COMMAND_LABEL_KEYS.items():
            self._build_hotkey_row(hotkeys_frame, command_name, label_key)

    # ------------------------------------------------------------------
    # Tangentbordsgenvägar
    # ------------------------------------------------------------------

    def _build_hotkey_row(self, parent, command_name: str, label_key: str) -> None:
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=6)

        ctk.CTkLabel(
            row, text=self.localizer.get_text(label_key), font=theme.FONT_UI,
            text_color=theme.COLOR_TEXT_PRIMARY, width=180, anchor="w",
        ).pack(side="left")

        current = self._hotkeys_working.get(command_name, {})
        value_label = ctk.CTkLabel(
            row,
            text=format_shortcut_for_display(current.get("modifiers", []), current.get("key", "")),
            font=theme.FONT_MONO, text_color=theme.COLOR_TEXT_MUTED, width=140, anchor="w",
        )
        value_label.pack(side="left", padx=(0, 10))
        self._hotkey_value_labels[command_name] = value_label

        rebind_btn = ctk.CTkButton(
            row, text="⌨", width=44, fg_color=theme.COLOR_GRAY_DARK, hover_color=theme.COLOR_GRAY,
            command=lambda: self._start_hotkey_capture(command_name),
        )
        rebind_btn.pack(side="right")
        self._hotkey_rebind_buttons[command_name] = rebind_btn

    def _start_hotkey_capture(self, command_name: str) -> None:
        button = self._hotkey_rebind_buttons[command_name]
        value_label = self._hotkey_value_labels[command_name]

        def _on_captured(modifiers: list[str], key: str) -> None:
            self._hotkeys_working[command_name] = {"modifiers": modifiers, "key": key}
            value_label.configure(text=format_shortcut_for_display(modifiers, key))
            button.configure(text="⌨", state="normal")

        button.configure(text="...", state="disabled")
        self._hotkey_capture.capture_next(on_captured=_on_captured)

    # ------------------------------------------------------------------
    # Spara
    # ------------------------------------------------------------------

    def _save(self):
        def split_csv(s: str) -> list[str]:
            return [x.strip() for x in s.split(",") if x.strip()]

        reverse_language_map = {v: k for k, v in LANGUAGE_DISPLAY_NAMES.items()}

        self.settings.ignore_dirs = split_csv(self.ignore_dirs_var.get())
        self.settings.ignore_files = split_csv(self.ignore_files_var.get())
        self.settings.sensitive_patterns = split_csv(self.sensitive_var.get())
        self.settings.default_export_format = self.export_format_var.get()
        self.settings.default_export_dir = self.export_dir_var.get().strip()
        self.settings.show_binary_files = self.show_binary_var.get()
        self.settings.show_hidden_files = self.show_hidden_var.get()
        self.settings.default_checkbox_state = self.default_checkbox_var.get()
        self.settings.language = reverse_language_map.get(self.language_var.get(), "")
        self.settings.hotkeys = {k: dict(v) for k, v in self._hotkeys_working.items()}

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
