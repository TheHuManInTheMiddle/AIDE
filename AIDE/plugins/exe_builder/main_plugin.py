# -*- coding: utf-8 -*-
"""
plugins/exe_builder/main_plugin.py

Bygger en .exe (PyInstaller, onedir som standard) av de filer som är
ikryssade i AIDE. Exportformat: "exe" -> AIDE Box/exe/<namn>/

ANVÄNDNING:
  1. Skanna projektets källmapp i AIDE.
  2. Kryssa ur det som INTE ska in i bygget (config/, assets/, plugins/,
     providers/ ... samt .env och annat känsligt).
  3. Välj exportformat "exe" och kör "Bygg paket".
  4. Flytta .exe-filen till rätt plats och lägg dina utkryssade
     mappar bredvid den. (Med "onefile": false får du istället en mapp
     med _internal som måste flyttas i sin helhet.)

VAD SOM HÄNDER:
  1. Förkontroll (autocancel): Python, entry point, ikon. Hittas
     problem avbryts allt med en förklaring i loggen, INNAN något
     dyrt startar.
  2. De ikryssade filerna kopieras till en tillfällig stagingmapp med
     mappstrukturen intakt (känsliga filer hoppas alltid över).
  3. Icke-Python-filer bland de ikryssade filerna läggs automatiskt till
     som PyInstaller-data med samma relativa sökväg i den byggda appen.
     Exempel: manual/manual.html -> manual/manual.html i EXE:n.
  4. Beroenden: finns en requirements.txt bland de ikryssade filerna
     används den. Annars används en sparad <projekt>.requirements.txt i
     AIDE Box/exe/, och saknas även den upptäcks beroendena med pipreqs
     i en separat, isolerad venv (projektets egna moduler filtreras
     bort) och listan sparas dit för att kunna redigeras för hand.
     Därefter skapas en tillfällig venv där beroenden + PyInstaller
     installeras.
  5. PyInstaller körs. Varje steg har timeout.
  6. Resultatet kopieras till AIDE Box/exe/<namn>/. Standard är
     ONEFILE: en enda .exe med biblioteken inbakade. Nackdelar: något
     långsammare start och oftare antivirus-falsklarm än onedir.

KONFIGURATION:
  <projekt>.build_config.json i AIDE Box/exe/. Skapas som utkast vid
  första bygget (skrivs aldrig över). Fält som saknas upptäcks
  automatiskt.

AVBROTT:
  Autocancel vid förkontrollfel, timeout per steg och när AIDE
  stängs (shutdown() dödar en pågående byggprocess). Avbrott sker
  "så snart som möjligt", inte omedelbart.

Följer AIDEPlugin-kontraktet: skriver aldrig utanför export_dir,
respekterar conflict_strategy, och returnerar None + loggar vid fel.

Kräver en vanlig Python 3.8+ på datorn (med venv) och internet vid
bygget (pip). pipreqs installeras automatiskt i en tillfällig venv.

Konsolfönster: GUI-program (tkinter, customtkinter, PyQt, ...) byggs
utan konsolfönster automatiskt. "windowed": true/false i configen vinner.
Utan konsol syns inga print()-utskrifter — sätt "windowed": false när du
felsöker ett bygge.

Kända begränsningar: pipreqs missar dynamiska importer och paket vars
importnamn skiljer sig från paketnamnet — lägg i så fall till dem i
<projekt>.requirements.txt eller "hidden_imports" i configen.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import traceback
from pathlib import Path

from core.plugin_base import AIDEPlugin, PluginFileInfo
from core.security import (
    ConflictStrategy,
    ExportBlocked,
    ensure_within_export_dir,
    resolve_target_path,
    sanitize_filename,
)

ENTRY_CANDIDATES = ["main.py", "app.py", "run.py", "__main__.py"]

DEFAULT_TIMEOUTS = {
    "venv": 180,
    "pip": 900,
    "pipreqs": 300,
    "pyinstaller": 1800,
}

AUTO_COLLECT_ALL = {
    "customtkinter": "customtkinter",
    "tkinterweb": "tkinterweb",
}

IGNORED_TOP_DIRS = {
    ".git", "__pycache__", "venv", ".venv", "build", "dist",
    "node_modules", ".idea", ".vscode",
}

PYPI_JSON_SERVER = "https://pypi.org/pypi/"

UNRESOLVED_RE = re.compile(
    r'Package "([^"]+)" does not exist or network problems'
)

LOG_EVERY_N_LINES = 25

INTERESTING = re.compile(
    r"(ERROR|WARNING|Building |completed successfully|"
    r"Successfully installed|Collecting )"
)


class BuildAborted(Exception):
    """Avbryter bygget med en läsbar orsak som loggas för användaren."""


# ----------------------------------------------------------------------
# Hjälpfunktioner
# ----------------------------------------------------------------------

def _creationflags() -> int:
    return (
        getattr(subprocess, "CREATE_NO_WINDOW", 0)
        if os.name == "nt"
        else 0
    )


def _clean_env() -> dict:
    """Miljö utan AIDE:s egna Python-variabler."""
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in ("PYTHONHOME", "PYTHONPATH")
        and not k.startswith("_PYI")
    }

    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"

    return env


def _candidate_pythons() -> list[list[str]]:
    if not getattr(sys, "frozen", False):
        return [[sys.executable]]

    found = []

    for name in ("python", "python3"):
        path = shutil.which(name)

        if path:
            found.append([path])

    launcher = shutil.which("py")

    if launcher:
        found.append([launcher, "-3"])

    return found


def _find_python() -> tuple[list[str] | None, str]:
    """Returnerar (kommando, förklaring)."""
    reasons = []

    for cmd in _candidate_pythons():
        try:
            result = subprocess.run(
                cmd + [
                    "-c",
                    "import sys, venv, ensurepip; "
                    "print(sys.version_info[0], sys.version_info[1])"
                ],
                capture_output=True,
                text=True,
                timeout=20,
                env=_clean_env(),
                creationflags=_creationflags(),
            )

        except (OSError, subprocess.TimeoutExpired) as exc:
            reasons.append(f"{cmd[0]}: {exc}")
            continue

        if result.returncode != 0:
            reasons.append(
                f"{cmd[0]}: saknar venv/ensurepip eller är ingen riktig Python"
            )
            continue

        try:
            major, minor = (
                int(x)
                for x in result.stdout.split()[:2]
            )

        except ValueError:
            reasons.append(
                f"{cmd[0]}: oväntat svar vid versionskontroll"
            )
            continue

        if (major, minor) < (3, 8):
            reasons.append(
                f"{cmd[0]}: Python {major}.{minor} är för gammal (kräver 3.8+)"
            )
            continue

        return cmd, f"Python {major}.{minor} ({cmd[0]})"

    if not reasons:
        reasons.append("ingen python/py hittades i PATH")

    return None, "; ".join(reasons)


def _detect_entry(
    files: list[PluginFileInfo],
    configured: str | None,
):
    by_rel = {
        f.relative_path: f
        for f in files
    }

    if configured:
        return by_rel.get(
            configured.replace("\\", "/")
        )

    candidates = [
        f
        for f in files
        if f.filename in ENTRY_CANDIDATES
    ]

    if not candidates:
        return None

    candidates.sort(
        key=lambda f: (
            f.relative_path.count("/"),
            ENTRY_CANDIDATES.index(f.filename),
            f.relative_path,
        )
    )

    return candidates[0]


def _detect_requirements(
    files: list[PluginFileInfo],
    configured,
):
    """configured: sökväg, False eller None."""

    if configured is False:
        return None

    by_rel = {
        f.relative_path: f
        for f in files
    }

    if isinstance(configured, str) and configured:
        return by_rel.get(
            configured.replace("\\", "/")
        )

    candidates = [
        f
        for f in files
        if f.filename.lower() == "requirements.txt"
    ]

    if not candidates:
        return None

    candidates.sort(
        key=lambda f: (
            f.relative_path.count("/"),
            f.relative_path,
        )
    )

    return candidates[0]


def _package_names(
    requirements_text: str,
) -> set[str]:
    names = set()

    for raw in requirements_text.splitlines():
        line = raw.split("#", 1)[0].strip()

        if not line or line.startswith("-"):
            continue

        match = re.match(
            r"[A-Za-z0-9_.\-]+",
            line,
        )

        if match:
            names.add(
                match.group(0)
                .lower()
                .replace("-", "_")
            )

    return names


GUI_IMPORT_RE = re.compile(
    r"^\s*(?:import|from)\s+"
    r"(tkinter|customtkinter|PyQt5|PyQt6|PySide2|PySide6|wx|kivy|pygame)"
    r"\b",
    re.MULTILINE,
)


def _detect_gui(
    files: list[PluginFileInfo],
) -> str | None:

    for f in files:
        if f.extension != ".py":
            continue

        try:
            with open(
                f.absolute_path,
                "r",
                encoding="utf-8-sig",
                errors="replace",
            ) as fh:
                match = GUI_IMPORT_RE.search(
                    fh.read(300_000)
                )

        except OSError:
            continue

        if match:
            return match.group(1)

    return None


def _venv_python(
    venv_dir: Path,
) -> str:

    return str(
        venv_dir
        / (
            "Scripts/python.exe"
            if os.name == "nt"
            else "bin/python"
        )
    )


def _normalize_name(
    name: str,
) -> str:

    return re.sub(
        r"[-_.]+",
        "_",
        name.strip().lower(),
    )


def _local_module_names(
    root: Path,
) -> set[str]:

    names = set()

    for path in root.rglob("*"):
        if path.is_dir():
            names.add(
                _normalize_name(path.name)
            )

        elif path.suffix == ".py":
            names.add(
                _normalize_name(path.stem)
            )

    return names


def _parse_requirement_lines(
    text: str,
) -> list[str]:

    lines = []

    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()

        if line and not line.startswith("-"):
            lines.append(line)

    return lines


def _filter_local_modules(
    lines: list[str],
    local_names: set[str],
    log,
) -> list[str]:

    kept = []

    for line in lines:
        match = re.match(
            r"[A-Za-z0-9_.\-]+",
            line,
        )

        if (
            match
            and _normalize_name(match.group(0))
            in local_names
        ):
            log(
                "   Hoppar över projektets egen modul "
                f"(inte ett PyPI-paket): {line}"
            )
            continue

        kept.append(line)

    return kept


def _kill_tree(
    proc: subprocess.Popen,
) -> None:

    if proc.poll() is not None:
        return

    try:
        if os.name == "nt":
            subprocess.run(
                [
                    "taskkill",
                    "/PID",
                    str(proc.pid),
                    "/T",
                    "/F",
                ],
                capture_output=True,
                creationflags=_creationflags(),
            )

        else:
            proc.terminate()

            try:
                proc.wait(timeout=3)

            except subprocess.TimeoutExpired:
                proc.kill()

    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def _unreported_top_dirs(
    source_root: str,
    included: list[PluginFileInfo],
) -> list[str]:

    used = {
        f.relative_path.split("/")[0]
        for f in included
        if "/" in f.relative_path
    }

    try:
        entries = sorted(
            os.listdir(source_root)
        )

    except OSError:
        return []

    return [
        e
        for e in entries
        if os.path.isdir(
            os.path.join(source_root, e)
        )
        and e not in used
        and e not in IGNORED_TOP_DIRS
    ]


def _pyinstaller_data_args(
    files: list[PluginFileInfo],
    staging: Path,
    log,
) -> list[str]:
    """
    Skapar PyInstaller --add-data-argument för alla ikryssade
    icke-Python-filer.

    Exempel:

        staging/manual/manual.html

    blir:

        --add-data
        staging/manual/manual.html;manual

    vilket ger:

        _MEIPASS/manual/manual.html
    """

    args: list[str] = []

    for f in files:
        if f.extension.lower() == ".py":
            continue

        relative_path = Path(
            f.relative_path.replace("\\", "/")
        )

        source_path = staging / relative_path

        if not source_path.is_file():
            continue

        parent = relative_path.parent.as_posix()

        if parent == ".":
            destination = "."
        else:
            destination = parent

        data_spec = (
            f"{source_path}{os.pathsep}{destination}"
        )

        args += [
            "--add-data",
            data_spec,
        ]

        log(
            f"   Data: {f.relative_path} -> {destination}"
        )

    return args


# ----------------------------------------------------------------------
# Byggaren
# ----------------------------------------------------------------------

class _ExeBuilder:

    def __init__(self):
        self._cancel = threading.Event()
        self._lock = threading.Lock()
        self._proc: subprocess.Popen | None = None

    def cancel(self) -> None:
        self._cancel.set()

        with self._lock:
            proc = self._proc

        if proc is not None:
            _kill_tree(proc)

    def _run(
        self,
        cmd,
        step,
        timeout,
        log,
        cwd=None,
        capture: list | None = None,
    ) -> None:

        if self._cancel.is_set():
            raise BuildAborted(
                "avbruten innan steget startade"
            )

        proc = subprocess.Popen(
            cmd,
            cwd=cwd,
            env=_clean_env(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            creationflags=_creationflags(),
        )

        with self._lock:
            self._proc = proc

        timed_out = threading.Event()

        def _on_timeout():
            timed_out.set()
            _kill_tree(proc)

        timer = threading.Timer(
            timeout,
            _on_timeout,
        )
        timer.daemon = True
        timer.start()

        tail: list[str] = []

        try:
            count = 0

            for raw in proc.stdout:
                line = raw.rstrip()

                if not line:
                    continue

                if capture is not None:
                    capture.append(line)

                tail.append(line)
                tail = tail[-40:]

                count += 1

                if (
                    INTERESTING.search(line)
                    or count % LOG_EVERY_N_LINES == 0
                ):
                    log(
                        f"   {line[:300]}"
                    )

            proc.wait()

        finally:
            timer.cancel()
            _kill_tree(proc)

            with self._lock:
                self._proc = None

        if self._cancel.is_set():
            raise BuildAborted(
                "avbruten (AIDE stängdes eller stopp begärdes)"
            )

        if timed_out.is_set():
            raise BuildAborted(
                f"steget '{step}' tog längre tid än "
                f"{timeout} s och avbröts"
            )

        if proc.returncode != 0:
            last = "\n".join(
                tail[-8:]
            )

            raise BuildAborted(
                f"steget '{step}' misslyckades "
                f"(exitkod {proc.returncode}). "
                f"Sista raderna:\n{last}"
            )

    def _discover_requirements(
        self,
        python_cmd,
        tmp_dir: Path,
        staging: Path,
        saved_req: str,
        timeouts: dict,
        ignore_unresolved: set,
        log,
    ) -> Path | None:

        log(
            "   Ingen requirements.txt — upptäcker beroenden "
            "med pipreqs (isolerad venv) ..."
        )

        scan_venv = tmp_dir / "venv_pipreqs"
        out_file = tmp_dir / "pipreqs_out.txt"

        pipreqs_output: list[str] = []

        try:
            self._run(
                python_cmd
                + [
                    "-m",
                    "venv",
                    str(scan_venv),
                ],
                "venv (pipreqs)",
                timeouts["venv"],
                log,
            )

            scan_py = _venv_python(
                scan_venv
            )

            self._run(
                [
                    scan_py,
                    "-m",
                    "pip",
                    "install",
                    "pipreqs",
                ],
                "pip (pipreqs)",
                timeouts["pip"],
                log,
            )

            self._run(
                [
                    scan_py,
                    "-m",
                    "pipreqs.pipreqs",
                    str(staging),
                    "--savepath",
                    str(out_file),
                    "--encoding",
                    "utf-8-sig",
                    "--pypi-server",
                    PYPI_JSON_SERVER,
                ],
                "pipreqs",
                timeouts["pipreqs"],
                log,
                capture=pipreqs_output,
            )

        except BuildAborted as exc:
            if self._cancel.is_set():
                raise

            raise BuildAborted(
                "kunde inte upptäcka beroenden automatiskt "
                f"({exc}). Kryssa i en requirements.txt, "
                "eller sätt \"requirements\": false i configen "
                "om projektet inte har några externa beroenden."
            )

        local_names = _local_module_names(
            staging
        )

        unresolved = sorted({
            m
            for line in pipreqs_output
            for m in UNRESOLVED_RE.findall(line)
            if _normalize_name(m) not in local_names
            and _normalize_name(m) not in ignore_unresolved
        })

        if unresolved:
            raise BuildAborted(
                "pipreqs kunde inte slå upp: "
                + ", ".join(unresolved)
                + ". Orsak: nätverksproblem, eller så finns "
                "paketet inte på PyPI. Kryssa i en "
                "requirements.txt, eller lägg namnen i "
                "\"ignore_unresolved\" i configen om de "
                "medvetet ska hoppas över."
            )

        raw = (
            out_file.read_text(
                encoding="utf-8",
                errors="replace",
            )
            if out_file.is_file()
            else ""
        )

        lines = _filter_local_modules(
            _parse_requirement_lines(raw),
            local_names,
            log,
        )

        if not lines:
            log(
                "   pipreqs hittade inga externa beroenden — "
                "projektet verkar bara använda standardbiblioteket."
            )
            return None

        header = (
            "# Skapad av AIDE EXE Builder (pipreqs). "
            "Redigera fritt — filen används vid nästa bygge.\n"
            "# Radera den för att köra pipreqs igen.\n"
        )

        try:
            with open(
                saved_req,
                "w",
                encoding="utf-8",
            ) as fh:
                fh.write(
                    header
                    + "\n".join(lines)
                    + "\n"
                )

            log(
                f"   Sparade beroendelista "
                f"({len(lines)} paket): {saved_req}"
            )

        except OSError as exc:
            log(
                f"⚠ Kunde inte spara beroendelistan: {exc}"
            )

            fallback = (
                tmp_dir
                / "requirements_discovered.txt"
            )

            fallback.write_text(
                "\n".join(lines) + "\n",
                encoding="utf-8",
            )

            return fallback

        return Path(saved_req)

    def export(
        self,
        project_name,
        source_roots,
        included_files,
        export_dir,
        conflict_strategy,
        log,
    ) -> str | None:

        self._cancel.clear()
        started = time.time()

        try:
            result = self._export(
                project_name,
                source_roots,
                included_files,
                export_dir,
                conflict_strategy,
                log,
            )

            if result:
                log(
                    f"EXE-bygge klart på "
                    f"{time.time() - started:.0f} s: {result}"
                )

            return result

        except BuildAborted as exc:
            log(
                "⚠ EXE-bygget avbröts, inget färdigt "
                f"paket skapades: {exc}"
            )
            return None

        except ExportBlocked as exc:
            log(
                "⚠ EXE-bygget avbröts "
                f"(osäker sökväg): {exc}"
            )
            return None

        except Exception as exc:
            log(
                "⚠ Oväntat fel i EXE-bygget: "
                f"{type(exc).__name__}: {exc}"
            )

            # AIDE körs som windowed EXE, så traceback syns inte
            # automatiskt i någon konsol. Skriv därför traceback-raderna
            # direkt till AIDE:s vanliga plugin-logg.
            log(
                "TRACEBACK:"
            )

            for line in traceback.format_exc().splitlines():
                log(
                    f"   {line}"
                )

            return None

    def _export(
        self,
        project_name,
        source_roots,
        included_files,
        export_dir,
        conflict_strategy,
        log,
    ) -> str | None:

        os.makedirs(
            export_dir,
            exist_ok=True,
        )

        safe_name = sanitize_filename(
            project_name
        )

        # ---- config ----------------------------------------------------

        cfg_path = ensure_within_export_dir(
            export_dir,
            f"{safe_name}.build_config.json",
        )

        cfg: dict = {}
        cfg_existed = os.path.isfile(cfg_path)

        if cfg_existed:
            try:
                with open(
                    cfg_path,
                    "r",
                    encoding="utf-8",
                ) as fh:
                    cfg = json.load(fh)

                if not isinstance(cfg, dict):
                    raise ValueError(
                        "toppnivån måste vara ett JSON-objekt"
                    )

            except (OSError, ValueError) as exc:
                raise BuildAborted(
                    f"kunde inte läsa {cfg_path}: {exc}"
                )

            log(
                f"Läste konfiguration: {cfg_path}"
            )

        saved_req = ensure_within_export_dir(
            export_dir,
            f"{safe_name}.requirements.txt",
        )

        timeouts = dict(
            DEFAULT_TIMEOUTS
        )

        timeouts.update(
            cfg.get("timeouts") or {}
        )

        # ---- urval -----------------------------------------------------

        sensitive = [
            f
            for f in included_files
            if f.is_sensitive
        ]

        files = [
            f
            for f in included_files
            if not f.is_sensitive
        ]

        for f in sensitive:
            log(
                "⚠ Hoppar över känslig fil "
                "(kopieras aldrig in i bygget): "
                f"{f.relative_path}"
            )

        if len(source_roots) > 1:
            log(
                "Obs: flera källmappar är valda — "
                "fas 1 använder den första som projektrot."
            )

        # ---- FÖRKONTROLL -----------------------------------------------

        problems: list[str] = []

        entry = _detect_entry(
            files,
            cfg.get("entry"),
        )

        if entry is None:
            wanted = (
                cfg.get("entry")
                or "/".join(ENTRY_CANDIDATES)
            )

            problems.append(
                "Ingen entry point bland de ikryssade "
                f"filerna (letade efter: {wanted}). "
                "Kryssa i startfilen, eller sätt "
                "\"entry\" i build_config.json."
            )

        cfg_req = cfg.get("requirements")

        req_file = _detect_requirements(
            files,
            cfg_req,
        )

        if (
            isinstance(cfg_req, str)
            and cfg_req
            and req_file is None
        ):
            problems.append(
                "requirements i configen pekar på "
                f"'{cfg_req}', men den filen är inte ikryssad."
            )

        if req_file is not None:
            req_desc = req_file.relative_path

        elif cfg_req is False:
            req_desc = "ingen (config: false)"

        elif os.path.isfile(saved_req):
            req_desc = "sparad lista"

        else:
            req_desc = "pipreqs-upptäckt"

        python_cmd, python_info = _find_python()

        if python_cmd is None:
            problems.append(
                f"Ingen användbar Python hittades "
                f"({python_info}). Installera Python 3.8+ "
                "från python.org (med venv) och se till "
                "att 'python' eller 'py' finns i PATH."
            )

        if cfg.get("windowed") is None:
            gui_lib = _detect_gui(
                files
            )

            windowed = gui_lib is not None

            if gui_lib:
                log(
                    f"Upptäckte GUI-biblioteket '{gui_lib}' "
                    "— bygger utan konsolfönster "
                    "(sätt \"windowed\": false i configen "
                    "för att behålla det)."
                )

        else:
            windowed = bool(
                cfg.get("windowed")
            )

        icon_arg = None

        if cfg.get("icon"):
            icon_path = cfg["icon"]

            if (
                not os.path.isabs(icon_path)
                and source_roots
            ):
                icon_path = os.path.join(
                    source_roots[0],
                    icon_path,
                )

            if os.path.isfile(icon_path):
                icon_arg = icon_path

            else:
                problems.append(
                    f"Ikonfilen finns inte: {icon_path}"
                )

        if problems:
            for p in problems:
                log(
                    f"⚠ Förkontroll: {p}"
                )

            raise BuildAborted(
                f"förkontrollen hittade "
                f"{len(problems)} problem — inget byggdes"
            )

        log(
            f"[förkontroll OK] {python_info}; "
            f"entry point: {entry.relative_path}; "
            f"beroenden: {req_desc}"
        )

        # ---- målmapp ---------------------------------------------------

        name = sanitize_filename(
            cfg.get("name") or safe_name
        )

        target = ensure_within_export_dir(
            export_dir,
            name,
        )

        if (
            os.path.normcase(target)
            == os.path.normcase(
                os.path.abspath(export_dir)
            )
        ):
            raise BuildAborted(
                "ogiltigt namn: målmappen skulle bli "
                "själva exportmappen"
            )

        resolved = resolve_target_path(
            target,
            conflict_strategy,
        )

        if resolved is None:
            log(
                f"Hoppade över befintlig mapp: {target}"
            )
            return None

        # ---- utkast till config ---------------------------------------

        if not cfg_existed:
            draft = {
                "_notes": (
                    "Redigera och bygg igen. Saknade fält "
                    "upptäcks automatiskt. requirements: "
                    "sökväg bland ikryssade filer, false = "
                    "bygg utan beroenden, null = "
                    "requirements.txt eller pipreqs."
                ),
                "name": name,
                "entry": entry.relative_path,
                "requirements": (
                    req_file.relative_path
                    if req_file
                    else None
                ),
                "windowed": windowed,
                "onefile": True,
                "icon": None,
                "ignore_unresolved": [],
                "hidden_imports": [],
                "collect_all": [],
                "extra_pyinstaller_args": [],
                "timeouts": DEFAULT_TIMEOUTS,
            }

            try:
                with open(
                    cfg_path,
                    "w",
                    encoding="utf-8",
                ) as fh:
                    json.dump(
                        draft,
                        fh,
                        ensure_ascii=False,
                        indent=2,
                    )

                log(
                    f"Skapade konfigurationsutkast: "
                    f"{cfg_path}"
                )

            except OSError as exc:
                log(
                    f"⚠ Kunde inte skriva "
                    f"konfigurationsutkast: {exc}"
                )

        # ---- bygget ----------------------------------------------------

        with tempfile.TemporaryDirectory(
            prefix="aide_exe_build_",
            ignore_cleanup_errors=True,
        ) as tmp:

            tmp_dir = Path(tmp)
            staging = tmp_dir / "src"
            staging.mkdir()

            log(
                f"[1/5] Kopierar {len(files)} "
                "fil(er) till staging ..."
            )

            staging_root = os.path.realpath(
                staging
            )

            for f in files:
                dest = os.path.realpath(
                    staging / f.relative_path
                )

                if not (
                    dest == staging_root
                    or dest.startswith(
                        staging_root + os.sep
                    )
                ):
                    raise BuildAborted(
                        "osäker sökväg i urvalet: "
                        f"{f.relative_path}"
                    )

                os.makedirs(
                    os.path.dirname(dest),
                    exist_ok=True,
                )

                shutil.copy2(
                    f.absolute_path,
                    dest,
                )

            # ----------------------------------------------------------
            # DATAFILER
            #
            # Alla ikryssade filer som inte är Python-källkod läggs
            # automatiskt till som PyInstaller-data.
            #
            # manual/manual.html
            # ->
            # _MEIPASS/manual/manual.html
            # ----------------------------------------------------------

            data_args = _pyinstaller_data_args(
                files,
                staging,
                log,
            )

            venv_dir = tmp_dir / "venv"

            log(
                "[2/5] Skapar tillfällig venv ..."
            )

            self._run(
                python_cmd
                + [
                    "-m",
                    "venv",
                    str(venv_dir),
                ],
                "venv",
                timeouts["venv"],
                log,
            )

            venv_py = _venv_python(
                venv_dir
            )

            log(
                "[3/5] Beroenden och PyInstaller ..."
            )

            req_path: Path | None = None

            if req_file is not None:
                req_path = (
                    staging
                    / req_file.relative_path
                )

            elif cfg_req is False:
                log(
                    "   Bygger utan beroendelista "
                    "(\"requirements\": false i configen)."
                )

            elif os.path.isfile(saved_req):
                req_path = Path(
                    saved_req
                )

                log(
                    "   Använder sparad "
                    f"beroendelista: {saved_req} "
                    "(radera den för att köra "
                    "pipreqs igen)"
                )

            else:
                ignore_unresolved = {
                    _normalize_name(str(n))
                    for n in (
                        cfg.get(
                            "ignore_unresolved"
                        )
                        or []
                    )
                }

                req_path = (
                    self._discover_requirements(
                        python_cmd,
                        tmp_dir,
                        staging,
                        saved_req,
                        timeouts,
                        ignore_unresolved,
                        log,
                    )
                )

            req_names: set[str] = set()

            if req_path is not None:
                req_names = _package_names(
                    req_path.read_text(
                        encoding="utf-8",
                        errors="replace",
                    )
                )

                self._run(
                    [
                        venv_py,
                        "-m",
                        "pip",
                        "install",
                        "-r",
                        str(req_path),
                    ],
                    "pip (requirements)",
                    timeouts["pip"],
                    log,
                )

            self._run(
                [
                    venv_py,
                    "-m",
                    "pip",
                    "install",
                    "pyinstaller",
                ],
                "pip (pyinstaller)",
                timeouts["pip"],
                log,
            )

            log(
                "[4/5] Kör PyInstaller ..."
            )

            dist = tmp_dir / "dist"
            work = tmp_dir / "work"
            spec = tmp_dir / "spec"

            onefile = (
                cfg.get("onefile", True)
                is not False
            )

            cmd = [
                venv_py,
                "-m",
                "PyInstaller",
                "--noconfirm",
                "--clean",
                "--name",
                name,
                "--distpath",
                str(dist),
                "--workpath",
                str(work),
                "--specpath",
                str(spec),
                "--paths",
                str(staging),
                "--onefile"
                if onefile
                else "--onedir",
                "--windowed"
                if windowed
                else "--console",
            ]

            if icon_arg:
                cmd += [
                    "--icon",
                    icon_arg,
                ]

            collect = list(
                cfg.get("collect_all") or []
            )

            for pkg, collect_name in (
                AUTO_COLLECT_ALL.items()
            ):
                if (
                    pkg in req_names
                    and collect_name not in collect
                ):
                    collect.append(
                        collect_name
                    )

                    log(
                        f"   Auto: --collect-all "
                        f"{collect_name}"
                    )

            for c in collect:
                cmd += [
                    "--collect-all",
                    c,
                ]

            for h in (
                cfg.get("hidden_imports") or []
            ):
                cmd += [
                    "--hidden-import",
                    h,
                ]

            # ----------------------------------------------------------
            # Ikryssade icke-Python-filer.
            # ----------------------------------------------------------

            cmd += data_args

            cmd += [
                str(a)
                for a in (
                    cfg.get(
                        "extra_pyinstaller_args"
                    )
                    or []
                )
            ]

            cmd.append(
                str(
                    staging
                    / entry.relative_path
                )
            )

            self._run(
                cmd,
                "pyinstaller",
                timeouts["pyinstaller"],
                log,
                cwd=str(tmp_dir),
            )

            built = dist / name

            if not built.is_dir():
                single = (
                    list(dist.iterdir())
                    if dist.exists()
                    else []
                )

                if not single:
                    raise BuildAborted(
                        "PyInstaller rapporterade klart "
                        "men skapade ingen utdata"
                    )

                built = dist

            if self._cancel.is_set():
                raise BuildAborted(
                    "avbruten före slutkopiering"
                )

            log(
                "[5/5] Lägger byggmappen "
                "i exportmappen ..."
            )

            if os.path.exists(resolved):
                shutil.rmtree(
                    resolved
                )

            shutil.copytree(
                built,
                resolved,
            )

        # ---- påminnelse om utkryssade mappar ---------------------------

        if source_roots:
            left_out = _unreported_top_dirs(
                source_roots[0],
                files,
            )

            if left_out:
                log(
                    "Påminnelse: dessa mappar i källan "
                    "var utkryssade och ligger inte i bygget: "
                    + ", ".join(
                        f"{d}/"
                        for d in left_out
                    )
                    + ". Lägg dem bredvid .exe:n "
                    "om programmet behöver dem."
                )

        if onefile:
            log(
                "Klart: allt är inbakat i .exe-filen. "
                "Flytta den till rätt plats och lägg "
                "dina utkryssade mappar bredvid den."
            )

        else:
            log(
                "Flytta HELA byggmappen "
                "(inte bara .exe-filen) till rätt plats — "
                "_internal hör ihop med .exe-filen."
            )

        return resolved


# ----------------------------------------------------------------------
# Plugin
# ----------------------------------------------------------------------

class ExeBuilderPlugin(AIDEPlugin):

    def __init__(self):
        self._builder = _ExeBuilder()

    @property
    def plugin_name(self) -> str:
        return "AIDE EXE Builder"

    @property
    def plugin_version(self) -> str:
        return "0.3.1"

    def initialize(self) -> None:
        print(
            f"[{self.plugin_name}] Initialiserad."
        )

    def shutdown(self) -> None:
        try:
            self._builder.cancel()
        except Exception:
            pass

    def get_exporters(self):
        return {
            "exe": self._builder.export
        }