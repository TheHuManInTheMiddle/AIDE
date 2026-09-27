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
