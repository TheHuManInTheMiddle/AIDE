"""
core/plugin_loader.py

Dynamisk upptäckt och laddning av AIDE-plugins från plugins/-katalogen.

Varje plugin bor i sin egen undermapp under plugins/ och kan finnas i
ANTINGEN uppackad form (en main_plugin.py-fil direkt i mappen) ELLER
paketerad form (en .gbp-fil — se core/gbp_runtime.py och
tools/build_plugin_package.py) — eller båda, i vilket fall det räknas
som en dubblett och flaggas (men skanningen fortsätter ändå).

En paketerad (.gbp) plugin extraheras till en lokal temp/-runtime-
katalog av GbpRuntime innan dess main_plugin.py laddas — det enda som
skiljer den från en vanlig plugin är VARIFRÅN filen faktiskt laddas.
Allt annat (AIDEPlugin-kontraktet, hooks, exportörer) är identiskt.

Mönstret är medvetet enkelt: ingen registreringsfil krävs, AIDE
upptäcker plugins genom att skanna katalogstrukturen (samma princip
som beställningens avsnitt 25 efterfrågar).

Ett fel i en enskild plugin får aldrig krascha AIDE eller hindra
övriga plugins från att laddas — i linje med avsnitt 27 (defensiv
felhantering).
"""

from __future__ import annotations

import importlib
import importlib.util
import os
import sys

from core.gbp_runtime import GbpRuntime
from core.plugin_base import AIDEPlugin


def discover_plugins(plugin_dir: str, log_callback=None) -> dict[str, AIDEPlugin]:
    """
    Skannar plugin_dir efter undermappar med antingen en main_plugin.py
    direkt i mappen (uppackad plugin) eller en .gbp-fil (paketerad
    plugin, extraheras automatiskt), instansierar och initialiserar
    varje hittad AIDEPlugin-subklass.

    Rensar först alla gamla temp/-runtime-kataloger från en tidigare
    session (GbpRuntime.cleanup_all) innan skanningen börjar, så inga
    rester från en föregående körning kan blandas ihop med den nya.

    Returnerar en dict {plugin_name: instans}.
    """
    log = log_callback or (lambda msg: None)
    discovered: dict[str, AIDEPlugin] = {}

    if not os.path.isdir(plugin_dir):
        return discovered

    GbpRuntime.cleanup_all(plugin_dir)

    if plugin_dir not in sys.path:
        sys.path.insert(0, plugin_dir)

    # Engångsflagga: bara den FÖRSTA dubbletten loggas som varning för
    # att inte dränka loggen om flera plugins råkar vara dubbletter
    # samtidigt — skanningen fortsätter oavsett, precis som GameBridge
    # gör i sin motsvarande adapter_loader.py.
    duplicate_already_flagged = False

    for folder in sorted(os.listdir(plugin_dir)):
        folder_path = os.path.join(plugin_dir, folder)

        if not os.path.isdir(folder_path):
            continue
        if folder.startswith("__") or folder.startswith("."):
            continue

        # En pluginmapp kan innehålla den uppackade .py-representationen,
        # en paketerad .gbp-representation, eller båda.
        gbp_path = GbpRuntime.find_gbp_file(folder_path)
        main_file = os.path.join(folder_path, "main_plugin.py")
        has_unpacked = os.path.isfile(main_file)
        packed_plugin = False

        if has_unpacked and gbp_path and not duplicate_already_flagged:
            duplicate_already_flagged = True
            log(
                f"⚠ Dubblett upptäckt i '{folder}': både main_plugin.py "
                f"och en .gbp-fil ({os.path.basename(gbp_path)}) finns. "
                "Använder den uppackade main_plugin.py."
            )

        if not has_unpacked:
            if not gbp_path:
                continue  # varken uppackad eller paketerad plugin här

            try:
                runtime_dir = GbpRuntime.prepare_plugin(folder_path, gbp_path)
                main_file = GbpRuntime.get_main_plugin_path(runtime_dir)
                packed_plugin = True
                log(f"Paketerad plugin '{folder}' förberedd från {os.path.basename(gbp_path)}")
            except Exception as exc:
                log(f"⚠ Kunde inte förbereda paketerad plugin i '{folder}': {exc}")
                continue

        module_name = (
            f"aide_packed_{folder}_main_plugin" if packed_plugin else f"{folder}.main_plugin"
        )

        try:
            if packed_plugin:
                # Paketerade plugins ligger i en temp/-katalog, inte på
                # plugin_dir-nivå — spec_from_file_location laddar
                # direkt från filsökvägen istället för att förlita sig
                # på paketrelativ import (som annars skulle kräva att
                # temp/ också låg i sys.path som ett eget paket).
                spec = importlib.util.spec_from_file_location(module_name, main_file)
                if spec is None or spec.loader is None:
                    raise ImportError(f"Kunde inte skapa modulspecifikation för '{folder}'")
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
            else:
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
                    log(
                        f"Plugin loaded: '{instance.plugin_name}' "
                        f"(v{instance.plugin_version}) från {folder}/"
                        + (" (paketerad, .gbp)" if packed_plugin else "")
                    )

        except Exception as exc:  # en trasig plugin ska aldrig krascha AIDE
            log(f"⚠ Kunde inte ladda plugin i '{folder}': {exc}")

    return discovered
