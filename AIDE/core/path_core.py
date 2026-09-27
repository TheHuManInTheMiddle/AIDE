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
