"""
core/plugin_loader.py

Dynamisk upptäckt och laddning av AIDE-plugins från plugins/-katalogen.

Varje plugin bor i sin egen undermapp under plugins/ och innehåller en
main_plugin.py med en klass som ärver core.plugin_base.AIDEPlugin.
Mönstret är medvetet enkelt: ingen registreringsfil krävs, AIDE
upptäcker plugins genom att skanna katalogstrukturen (samma princip
som beställningens avsnitt 25 efterfrågar).

Ett fel i en enskild plugin får aldrig krascha AIDE eller hindra
övriga plugins från att laddas — i linje med avsnitt 27 (defensiv
felhantering).
"""

from __future__ import annotations

import importlib
import os
import sys

from core.plugin_base import AIDEPlugin


def discover_plugins(plugin_dir: str, log_callback=None) -> dict[str, AIDEPlugin]:
    """
    Skannar plugin_dir efter undermappar med en main_plugin.py som
    definierar en AIDEPlugin-subklass, instansierar och initialiserar
    dem.

    Returnerar en dict {plugin_name: instans}.
    """
    log = log_callback or (lambda msg: None)
    discovered: dict[str, AIDEPlugin] = {}

    if not os.path.isdir(plugin_dir):
        return discovered

    if plugin_dir not in sys.path:
        sys.path.insert(0, plugin_dir)

    for folder in sorted(os.listdir(plugin_dir)):
        folder_path = os.path.join(plugin_dir, folder)

        if not os.path.isdir(folder_path):
            continue
        if folder.startswith("__") or folder.startswith("."):
            continue

        main_file = os.path.join(folder_path, "main_plugin.py")
        if not os.path.isfile(main_file):
            continue

        module_name = f"{folder}.main_plugin"

        try:
            if module_name in sys.modules:
                importlib.reload(sys.modules[module_name])
            module = importlib.import_module(module_name)

            for attribute_name in dir(module):
                attribute = getattr(module, attribute_name)
                if (
                    isinstance(attribute, type)
                    and issubclass(attribute, AIDEPlugin)
                    and attribute is not AIDEPlugin
                ):
                    instance = attribute()
                    instance.initialize()
                    discovered[instance.plugin_name] = instance
                    log(f"Plugin loaded: '{instance.plugin_name}' (v{instance.plugin_version}) från {folder}/")

        except Exception as exc:  # en trasig plugin ska aldrig krascha AIDE
            log(f"⚠ Kunde inte ladda plugin i '{folder}': {exc}")

    return discovered
