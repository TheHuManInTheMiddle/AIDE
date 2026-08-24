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
