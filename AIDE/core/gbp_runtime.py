# -*- coding: utf-8 -*-
"""
core/gbp_runtime.py

AIDE GBP Runtime — läser in .gbp-paketerade plugins. Samma ZIP-
baserade .gbp-format som GameBridge använder för sina adaptrar (se
tools/build_plugin_package.py och GameBridges "Plugin Packaging
Guide"), men AIDE:s variant letar efter main_plugin.py istället för
main_adapter.py. I övrigt är det här i praktiken en direkt AIDE-
portering av GameBridges egen core/gbp_runtime.py.

SYFTE:
Låter någon som bygger en AIDE-plugin MED externa Python-beroenden
(t.ex. pdf_export-pluginet, som behöver reportlab) paketera hela
pluginet inklusive dess beroenden i en enda .gbp-fil. Mottagaren
behöver då inte själv köra `pip install` för att pluginet ska
fungera — den droppar bara .gbp-filen i sin plugins/-mapp.

RUNTIME-STRUKTUR:

    plugins/
      pdf_export/
        pdf_export.gbp
        temp/                  <- skapas/rensas av GbpRuntime
          main_plugin.py
          dependencies/
            reportlab/
            ...

Den permanenta plugin-mappen hålls ren — .gbp-filen är källan,
temp/ är bara en extraherad arbetskopia som kan raderas och
återskapas fritt utan att något går förlorat.

SÄKERHET: skyddar mot ZIP path traversal (samma försiktighetsprincip
som AIDE:s egen ensure_within_export_dir i core/security.py, fast
här för INKOMMANDE data istället för utgående export). Ett trasigt
eller ogiltigt .gbp-paket kraschar aldrig AIDE:s uppstart (avsnitt 27
i originalspecen) — felet bubblar upp som ett vanligt undantag som
plugin_loader.py fångar och loggar, exakt som en trasig main_plugin.py
redan hanteras idag.
"""

from __future__ import annotations

import os
import shutil
import sys
import zipfile


class GbpRuntime:

    @staticmethod
    def get_temp_dir(plugin_dir: str) -> str:
        """Returnerar pluginets lokala runtime-katalog."""
        return os.path.join(plugin_dir, "temp")

    @staticmethod
    def cleanup_plugin(plugin_dir: str) -> bool:
        """
        Tar bort pluginets temp-runtime-katalog.

        Returnerar True om städningen gick bra (eller inte behövdes
        eftersom ingen temp-katalog fanns), False om den misslyckades.
        """
        temp_dir = GbpRuntime.get_temp_dir(plugin_dir)

        if not os.path.exists(temp_dir):
            return True

        try:
            shutil.rmtree(temp_dir)
            print(f"[GBP-RUNTIME] Rensade runtime: {temp_dir}")
            return True
        except OSError as exc:
            print(f"[GBP-RUNTIME-VARNING] Kunde inte rensa '{temp_dir}': {exc}")
            return False

    @staticmethod
    def cleanup_all(plugins_root: str) -> None:
        """
        Städar ALLA plugins temp-runtime-kataloger. Tänkt att köras
        vid varje AIDE-uppstart (t.ex. från core/plugin_loader.py
        innan discover_plugins() letar efter plugins) så inga gamla
        runtime-rester från en tidigare session kan bli kvar aktiva.
        """
        if not os.path.isdir(plugins_root):
            return

        for folder in os.listdir(plugins_root):
            plugin_dir = os.path.join(plugins_root, folder)

            if not os.path.isdir(plugin_dir):
                continue
            if folder.startswith("__") or folder.startswith("."):
                continue

            temp_dir = GbpRuntime.get_temp_dir(plugin_dir)
            if os.path.exists(temp_dir):
                GbpRuntime.cleanup_plugin(plugin_dir)

    @staticmethod
    def find_gbp_file(plugin_dir: str) -> str | None:
        """
        Letar efter en .gbp-fil direkt i en pluginmapp. Returnerar
        sökvägen till den första hittade, eller None om ingen finns
        — det vanliga fallet för en oförpackad main_plugin.py-plugin.
        """
        if not os.path.isdir(plugin_dir):
            return None
        for filename in sorted(os.listdir(plugin_dir)):
            if filename.lower().endswith(".gbp"):
                return os.path.join(plugin_dir, filename)
        return None

    @staticmethod
    def prepare_plugin(plugin_dir: str, gbp_path: str) -> str:
        """
        Extraherar ett .gbp-paket till pluginets lokala temp-
        runtime-katalog och gör dess buntade beroenden tillgängliga
        för Python.

        Returnerar absolut sökväg till den extraherade runtime-
        katalogen.

        Höjer FileNotFoundError/ValueError vid saknat, ogiltigt
        eller osäkert paket — plugin_loader.py ansvarar för att
        fånga det och logga utan att krascha resten av AIDE.
        """
        plugin_dir = os.path.abspath(plugin_dir)
        gbp_path = os.path.abspath(gbp_path)

        if not os.path.exists(gbp_path):
            raise FileNotFoundError(f"GBP-paket hittades inte: {gbp_path}")

        if not zipfile.is_zipfile(gbp_path):
            raise ValueError(f"Ogiltigt GBP-paket: {gbp_path}")

        # Börja alltid från en ren runtime.
        GbpRuntime.cleanup_plugin(plugin_dir)

        temp_dir = GbpRuntime.get_temp_dir(plugin_dir)
        os.makedirs(temp_dir, exist_ok=True)

        try:
            with zipfile.ZipFile(gbp_path, "r") as archive:
                # Skydd mot ZIP path traversal.
                temp_root = os.path.realpath(temp_dir)

                for member in archive.infolist():
                    member_path = os.path.realpath(
                        os.path.join(temp_dir, member.filename)
                    )
                    if not (
                        member_path == temp_root
                        or member_path.startswith(temp_root + os.sep)
                    ):
                        raise ValueError(
                            f"Osäker sökväg upptäckt i GBP-paketet: {member.filename}"
                        )

                archive.extractall(temp_dir)

        except Exception:
            GbpRuntime.cleanup_plugin(plugin_dir)
            raise

        main_plugin = os.path.join(temp_dir, "main_plugin.py")
        if not os.path.isfile(main_plugin):
            GbpRuntime.cleanup_plugin(plugin_dir)
            raise ValueError("GBP-paketet innehåller ingen main_plugin.py")

        GbpRuntime._register_runtime_paths(temp_dir)

        print(f"[GBP-RUNTIME] Paket laddat: {os.path.basename(gbp_path)}")
        print(f"[GBP-RUNTIME] Runtime-sökväg: {temp_dir}")

        return temp_dir

    @staticmethod
    def _register_runtime_paths(runtime_dir: str) -> None:
        """
        Gör pluginets runtime och dess buntade beroende-kataloger
        tillgängliga för Python. Ingen pip-installation sker här —
        det är redan gjort vid paketeringstillfället, se
        tools/build_plugin_package.py.
        """
        paths = [
            runtime_dir,
            os.path.join(runtime_dir, "lib"),
            os.path.join(runtime_dir, "dependencies"),
        ]
        for path in paths:
            if os.path.isdir(path) and path not in sys.path:
                sys.path.insert(0, path)
                print(f"[GBP-RUNTIME] Python-sökväg tillagd: {path}")

    @staticmethod
    def get_main_plugin_path(runtime_dir: str) -> str:
        """Returnerar sökvägen till den extraherade main_plugin.py."""
        return os.path.join(runtime_dir, "main_plugin.py")
