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
