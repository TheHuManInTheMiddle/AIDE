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
