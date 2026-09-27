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
