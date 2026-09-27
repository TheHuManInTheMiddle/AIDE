# -*- coding: utf-8 -*-
"""
core/easter_eggs.py

Små, ofarliga easter eggs i AIDE:s logg. Ren nöje — påverkar aldrig
filurval, klassificering, export eller något annat funktionellt.
Om log_callback saknas gör funktionen ingenting alls.
"""

from __future__ import annotations

import random

# Mycket låg sannolikhet per tillfälle (skanning eller export) — ska
# vara en sällsynt överraskning man kanske ser en gång på flera
# månader, inte en återkommande grej.
_DADDLE_PROBABILITY = 0.002  # ungefär 1 av 500 gånger

_DADDLE_MESSAGE = "[INFO] DADDLE has entered the chat."


def maybe_log_daddle(log_callback) -> None:
    """
    Mycket låg slumpchans att logga en liten hälsning från nästa
    projekt på tapeten. Anropas från scan- och exportflödet.
    """
    if log_callback is None:
        return
    if random.random() < _DADDLE_PROBABILITY:
        log_callback(_DADDLE_MESSAGE)