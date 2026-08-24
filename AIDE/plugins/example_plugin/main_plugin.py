# -*- coding: utf-8 -*-
"""
plugins/example_plugin/main_plugin.py

Referensimplementation som visar hela AIDEPlugin-kontraktet i
praktiken. Detta är INTE en riktig produktionsplugin — den finns för
att vara ett konkret, körbart exempel att kopiera och bygga vidare på
(se docs/PLUGIN_GUIDE.md).

Vad den gör:
  1. Klassificerar ".aide"-filer som "AIDE Meta" istället för "Okänd".
  2. Loggar hur många filer som hittades vid varje skanning.
  3. Filtrerar automatiskt bort filer större än 5 MB från exporten,
     som ett exempel på on_before_export.
  4. Registrerar ett eget litet exportformat: "shout" — samma innehåll
     som markdown-paketet, men med filrubriker i versaler. Ett
     medvetet enkelt, ofarligt exempel på get_exporters().
"""

from __future__ import annotations

from core.plugin_base import AIDEPlugin, PluginFileInfo


MAX_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


class ExamplePlugin(AIDEPlugin):

    @property
    def plugin_name(self) -> str:
        return "AIDE Example Plugin"

    @property
    def plugin_version(self) -> str:
        return "1.0.0"

    def initialize(self) -> None:
        print(f"[{self.plugin_name}] Initialiserad.")

    def on_classify(self, file_info: PluginFileInfo):
        if file_info.extension == ".aide":
            return {"category": "AIDE Meta", "language": None, "is_sensitive": False}
        return None

    def on_scan_complete(self, files: list[PluginFileInfo]) -> None:
        print(f"[{self.plugin_name}] Skanning klar: {len(files)} filer sågs av pluginet.")

    def on_before_export(self, files: list[PluginFileInfo]):
        filtered = [f for f in files if f.size_bytes <= MAX_SIZE_BYTES]
        if len(filtered) != len(files):
            print(
                f"[{self.plugin_name}] Filtrerade bort "
                f"{len(files) - len(filtered)} fil(er) över 5 MB."
            )
        return filtered

    def get_exporters(self):
        return {"shout": self._export_shout}

    # ------------------------------------------------------------------
    # Egen exportfunktion — följer exportörskontraktet i AIDEPlugin.get_exporters
    # ------------------------------------------------------------------

    @staticmethod
    def _export_shout(
        project_name: str,
        source_roots: list[str],
        included_files: list[PluginFileInfo],
        export_dir: str,
        conflict_strategy,
        log_callback,
    ) -> str | None:
        import os
        from core.security import ensure_within_export_dir, resolve_target_path

        os.makedirs(export_dir, exist_ok=True)
        target = ensure_within_export_dir(export_dir, "project_package_SHOUT.md")
        resolved = resolve_target_path(target, conflict_strategy)
        if resolved is None:
            log_callback(f"Hoppade över befintlig fil: {target}")
            return None

        lines = [f"AIDE SHOUT PACKAGE — {project_name.upper()}", "=" * 40, ""]
        for f in included_files:
            lines.append(f"### FILE: {f.relative_path.upper()} ###")
            if f.is_binary:
                lines.append("[BINARY]")
                continue
            try:
                with open(f.absolute_path, "r", encoding="utf-8", errors="replace") as fh:
                    lines.append(fh.read())
            except OSError as exc:
                lines.append(f"[Kunde inte läsa: {exc}]")
            lines.append("")

        with open(resolved, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines))

        log_callback(f"Shout-paket skapat: {resolved}")
        return resolved
