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
