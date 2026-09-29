# -*- coding: utf-8 -*-
"""
plugins/gbp_packager/main_plugin.py

.gbp-paketering som ett vanligt AIDE-exportformat ("gbp" i export-
format-väljaren) — samma arbetsflöde som tools/build_plugin_package.py
automatiserar fristående, fast nu inbakat i AIDE:s vanliga
skanna-markera-exportera-flöde istället för en separat kommandorad.

ANVÄNDNING:
  1. Skanna pluginets källmapp i AIDE (t.ex. plugins/pdf_export/ eller
     en GameBridge-adapters mapp).
  2. Markera entry point-filen (main_plugin.py för en AIDE-plugin,
     main_adapter.py för en GameBridge-adapter) plus eventuella extra
     filer som ska buntas med (plugin_config.json, plugin_prompt.txt).
  3. Välj exportformat "gbp" och kör "Bygg paket".

Vad som händer internt:
  1. pipreqs analyserar KÄLLMAPPEN (inte bara de markerade filerna —
     pipreqs behöver se all kod för att hitta alla imports) och listar
     externa beroenden.
  2. Interna modulnamn (core, ui, adapters, osv — AIDE:s/GameBridges
     egna paket, som pipreqs annars kan misstolka som PyPI-paket)
     filtreras bort.
  3. De återstående beroendena installeras isolerat med
     `pip install --target` i en tillfällig stagingkatalog.
  4. Entry point + eventuella extra markerade filer (de som ligger
     direkt i källmappens rot, inte i undermappar) + dependencies/
     zippas ihop till en .gbp-fil.

Paketet hamnar som standard i en "gbp"-undermapp under vald exportmapp
(samma princip som zip/pdf-pluginen), med samma "redan i rätt
undermapp?"-skydd mot dubblering.

Följer AIDEPlugin-kontraktet i docs/PLUGIN_GUIDE.md:
- Skriver aldrig utanför export_dir (ensure_within_export_dir).
- Respekterar conflict_strategy (resolve_target_path).
- Kraschar aldrig tyst — varje steg loggas via log_callback, och
  funktionen returnerar None vid fel istället för att låta ett
  undantag brisera ut och stoppa resten av AIDE.

Kräver `pipreqs` (pip install pipreqs) installerat i samma Python-
miljö som kör AIDE.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from core.plugin_base import AIDEPlugin, PluginFileInfo
from core.security import ExportBlocked, ensure_within_export_dir, resolve_target_path, sanitize_filename

# Vilka filnamn som räknas som en giltig entry point — söks i den
# ordningen bland de MARKERADE filerna.
ENTRY_POINT_CANDIDATES = ["main_plugin.py", "main_adapter.py"]

# Samma standardlista interna moduler som tools/build_plugin_package.py.
DEFAULT_INTERNAL_MODULES = {
    "adapters", "ai", "core", "functions", "interface", "providers",
    "ui", "exporters", "plugins",
    "main",
}


def _find_entry_point(included_files: list[PluginFileInfo]) -> PluginFileInfo | None:
    by_filename = {f.filename: f for f in included_files}
    for candidate in ENTRY_POINT_CANDIDATES:
        if candidate in by_filename:
            return by_filename[candidate]
    return None


def _run_pipreqs(source_dir: str, log_callback) -> list[str] | None:
    """Kör pipreqs mot källmappen. Returnerar None om pipreqs saknas."""
    result = None
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pipreqs.pipreqs", source_dir, "--print"],
            capture_output=True, text=True, check=False,
        )
    except FileNotFoundError:
        pass

    if result is None or result.returncode != 0:
        try:
            result = subprocess.run(
                ["pipreqs", source_dir, "--print"],
                capture_output=True, text=True, check=False,
            )
        except FileNotFoundError:
            log_callback("⚠ pipreqs hittades inte. Installera med: pip install pipreqs")
            return None

    lines = []
    for raw_line in result.stdout.splitlines():
        line = raw_line.strip()
        if not line or line.upper().startswith("WARNING"):
            continue
        lines.append(line)
    return lines


def _filter_internal_modules(requirements: list[str], log_callback) -> list[str]:
    kept = []
    for req in requirements:
        pkg_name = req.split("==")[0].split(">=")[0].split("<=")[0].strip().lower()
        if pkg_name in DEFAULT_INTERNAL_MODULES:
            log_callback(f"Hoppar över intern modul (inte ett riktigt PyPI-paket): {req}")
            continue
        kept.append(req)
    return kept


def _get_pip_python() -> list[str]:
    """
    Returnerar kommandot som ska användas för att köra pip.

    Vid vanlig Python-körning används samma Python som kör AIDE.
    När AIDE är paketerad med PyInstaller pekar sys.executable på
    AIDE.exe, så då används en vanlig Python-installation istället.
    """
    if not getattr(sys, "frozen", False):
        return [sys.executable]

    python_path = shutil.which("python")
    if python_path:
        return [python_path]

    py_launcher = shutil.which("py")
    if py_launcher:
        return [py_launcher, "-3"]

    raise RuntimeError(
        "Ingen vanlig Python-installation hittades för pip-installation. "
        "Installera Python och kontrollera att python/py finns i PATH."
    )


def _install_dependencies(requirements: list[str], target_dir: Path, log_callback) -> None:
    """Höjer RuntimeError vid pip-fel — fångas av anroparen."""
    target_dir.mkdir(parents=True, exist_ok=True)

    if not requirements:
        log_callback("Inga externa beroenden att installera.")
        return

    req_file = target_dir.parent / "requirements.txt"
    req_file.write_text("\n".join(requirements) + "\n", encoding="utf-8")

    log_callback(f"Installerar {len(requirements)} beroende(n) isolerat ...")

    pip_python = _get_pip_python()

    result = subprocess.run(
        pip_python + [
            "-m", "pip", "install",
            "-r", str(req_file),
            "--target", str(target_dir),
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(f"pip install misslyckades: {result.stderr.strip()[-500:]}")


def export_gbp(
    project_name: str,
    source_roots: list[str],
    included_files: list[PluginFileInfo],
    export_dir: str,
    conflict_strategy,
    log_callback,
) -> str | None:
    entry_file = _find_entry_point(included_files)
    if entry_file is None:
        log_callback(
            "⚠ Hittar ingen main_plugin.py eller main_adapter.py bland "
            "markerade filer — markera entry point-filen och försök igen."
        )
        return None

    if not source_roots:
        log_callback("⚠ Ingen källmapp känd — kan inte köra pipreqs.")
        return None
    source_dir = source_roots[0]

    os.makedirs(export_dir, exist_ok=True)

    # Samma "redan i rätt undermapp?"-princip som zip/pdf-pluginen.
    already_in_subfolder = (
        os.path.basename(os.path.normpath(str(export_dir))).lower() == "gbp"
    )
    safe_name = sanitize_filename(project_name)
    rel_target = f"{safe_name}.gbp"
    if not already_in_subfolder:
        rel_target = os.path.join("gbp", rel_target)

    try:
        target = ensure_within_export_dir(export_dir, rel_target)
    except ExportBlocked as exc:
        log_callback(f"⚠ Hoppade över (osäker sökväg): {exc}")
        return None

    resolved = resolve_target_path(target, conflict_strategy)
    if resolved is None:
        log_callback(f"Hoppade över befintlig fil: {target}")
        return None

    os.makedirs(os.path.dirname(resolved), exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="aide_gbp_build_") as tmp:
        staging_dir = Path(tmp)
        dependencies_dir = staging_dir / "dependencies"

        log_callback(f"[1/4] Upptäcker beroenden med pipreqs i {source_dir} ...")
        raw_requirements = _run_pipreqs(source_dir, log_callback)
        if raw_requirements is None:
            return None

        log_callback("[2/4] Filtrerar bort interna moduler ...")
        requirements = _filter_internal_modules(raw_requirements, log_callback)
        log_callback(f"       Externa beroenden: {requirements or '(inga)'}")

        log_callback("[3/4] Installerar beroenden isolerat (pip install --target) ...")
        try:
            _install_dependencies(requirements, dependencies_dir, log_callback)
        except RuntimeError as exc:
            log_callback(f"⚠ {exc}")
            return None

        log_callback("[4/4] Bygger .gbp-arkiv ...")

        extra_files = [
            f for f in included_files
            if f is not entry_file and "/" not in f.relative_path
        ]

        try:
            with zipfile.ZipFile(resolved, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.write(entry_file.absolute_path, arcname=entry_file.filename)
                for f in extra_files:
                    zf.write(f.absolute_path, arcname=f.filename)

                if dependencies_dir.exists():
                    for file_path in dependencies_dir.rglob("*"):
                        if file_path.is_file():
                            arcname = file_path.relative_to(staging_dir)
                            zf.write(file_path, arcname=str(arcname))
        except OSError as exc:
            log_callback(f"⚠ Kunde inte skapa .gbp-arkivet: {exc}")
            return None

    size_kb = os.path.getsize(resolved) / 1024
    log_callback(
        f".gbp-paket skapat: {resolved} "
        f"(entry point: {entry_file.filename}, {len(extra_files)} extra fil(er), "
        f"{size_kb:.1f} KB)"
    )
    return resolved


class GbpPackagerPlugin(AIDEPlugin):

    @property
    def plugin_name(self) -> str:
        return "AIDE GBP Packager"

    @property
    def plugin_version(self) -> str:
        return "1.0.0"

    def initialize(self) -> None:
        print(f"[{self.plugin_name}] Initialiserad.")

    def get_exporters(self):
        return {"gbp": export_gbp}