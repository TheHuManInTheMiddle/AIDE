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
