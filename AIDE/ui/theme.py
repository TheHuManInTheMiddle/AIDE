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
