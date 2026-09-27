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