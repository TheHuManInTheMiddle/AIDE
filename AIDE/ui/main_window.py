"""
ui/main_window.py

Huvudfönstret för AIDE. Kopplar samman scanner, classifier, file_tree,
preview, settings_window och exporters till en fungerande desktopapp.

Visuellt stilmatchad mot syskonverktyget G.A.M.E. B.R.I.D.G.E. (se
ui/theme.py för den delade färgpaletten/typografin) — samma mörka
CustomTkinter-identitet, statuslampa, panelstruktur och knappstil.

GUI-koden är medvetet hållen skild från filanalys/export-logiken:
den anropar bara funktioner i core/ och exporters/ (avsnitt 30).
"""

from __future__ import annotations

import os
import queue
import threading
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk

from core.classifier import CATEGORY_UNKNOWN
from core.easter_eggs import maybe_log_daddle
from core.hotkey_utils import format_shortcut_for_tk
from core.localization_core import LocalizationCore
from core.path_core import PathCore
from core.plugin_base import PluginFileInfo
from core.plugin_loader import discover_plugins
from core.scanner import ScanResult, ScannedFile, scan_sources
from core.security import ConflictStrategy, sanitize_filename
from core.settings import Settings, load_settings
from exporters.json_exporter import export_json_manifest
from exporters.markdown_exporter import export_markdown
from exporters.text_exporter import export_text
from exporters.tree_exporter import export_tree
from ui import theme
from ui.file_tree import FileTreeView
from ui.preview import PreviewWindow
from ui.settings_window import SettingsWindow


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

PROJECT_ROOT = PathCore.PROJECT_ROOT
PLUGINS_DIR = PathCore.get_plugins_root()
AIDE_BOX_DIR = PathCore.get_absolute_path("AIDE Box")


def _aide_box_subdir(name: str) -> str:
    """
    Returnerar (och skapar vid behov) en undermapp under AIDE Box.

    All automatisk export hamnar i en känd, förutsägbar struktur under
    AIDE:s egen installationsmapp — ingen manuell exportmapp krävs.
    """
    path = os.path.join(AIDE_BOX_DIR, name)
    os.makedirs(path, exist_ok=True)
    return path


def _to_plugin_file_info(f: ScannedFile) -> PluginFileInfo:
    return PluginFileInfo(
        relative_path=f.relative_path,
        absolute_path=f.absolute_path,
        filename=f.filename,
        extension=f.extension,
        category=f.category,
        size_bytes=f.size_bytes,
        is_sensitive=f.is_sensitive,
        is_binary=f.is_binary,
    )


class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.settings: Settings = load_settings()
        self.localizer = LocalizationCore(forced_lang=self.settings.language or None)

        self.title(self.localizer.get_text("app_title"))
        self.geometry("1220x780")
        self.minsize(960, 620)
        self.configure(fg_color=theme.COLOR_BG_MAIN)

        self.source_roots: list[str] = []

        # Export sker automatiskt till AIDE Box.
        self._cancel_event: threading.Event | None = None
        self._worker_thread: threading.Thread | None = None
        self._ui_queue: "queue.Queue" = queue.Queue()
        self._plugin_exporters: dict[str, callable] = {}

        self._configure_treeview_style()
        self._build_top_bar()
        self._build_matrix_bar()
        self._build_body()
        self._build_bottom_bar()
        self._build_status_bar()
        self._bind_hotkeys()

        self.plugins = discover_plugins(
            PLUGINS_DIR,
            log_callback=self._log,
        )
        self._register_plugin_exporters()

        self._poll_queue()

        # Förbereds för framtida AI-rapporter.
        _aide_box_subdir("reports")

    # ------------------------------------------------------------------
    # ttk-tema för filträdet
    # ------------------------------------------------------------------

    def _configure_treeview_style(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        style.configure(
            "Treeview",
            background=theme.COLOR_BG_PANEL_ALT,
            fieldbackground=theme.COLOR_BG_PANEL_ALT,
            foreground=theme.COLOR_TEXT_PRIMARY,
            borderwidth=0,
            rowheight=24,
            font=theme.FONT_UI,
        )

        style.configure(
            "Treeview.Heading",
            background=theme.COLOR_BG_PANEL,
            foreground=theme.COLOR_TEXT_MUTED,
            borderwidth=0,
            font=theme.FONT_SECTION,
        )

        style.map(
            "Treeview",
            background=[("selected", theme.COLOR_BLUE_DARK)],
            foreground=[("selected", "#FFFFFF")],
        )

        style.map(
            "Treeview.Heading",
            background=[("active", theme.COLOR_BG_PANEL)],
        )

        style.configure(
            "Vertical.TScrollbar",
            background=theme.COLOR_BG_PANEL,
            troughcolor=theme.COLOR_BG_MAIN,
        )

        style.configure(
            "Horizontal.TScrollbar",
            background=theme.COLOR_BG_PANEL,
            troughcolor=theme.COLOR_BG_MAIN,
        )

        style.configure(
            "TFrame",
            background=theme.COLOR_BG_MAIN,
        )

        style.configure(
            "TLabel",
            background=theme.COLOR_BG_MAIN,
            foreground=theme.COLOR_TEXT_PRIMARY,
        )

        style.configure(
            "TEntry",
            fieldbackground=theme.COLOR_BG_PANEL_ALT,
            foreground=theme.COLOR_TEXT_PRIMARY,
        )

    # ------------------------------------------------------------------
    # Tangentbordsgenvägar
    # ------------------------------------------------------------------

    def _bind_hotkeys(self):
        """
        Binder AIDE:s ombindningsbara genvägar (core/hotkey_utils.py)
        utifrån sparade inställningar (Settings.hotkeys). Anropas igen
        efter att Inställningar sparats, ifall en genväg ombundits.
        """
        handlers = {
            "scan": self._start_scan,
            "build_package": self._start_build,
            "preview": self._preview,
        }
        for name, handler in handlers.items():
            binding = self.settings.hotkeys.get(name)
            if not binding:
                continue
            tk_sequence = format_shortcut_for_tk(
                binding.get("modifiers", []), binding.get("key", "")
            )
            self.bind_all(tk_sequence, lambda event, h=handler: h())

    # ------------------------------------------------------------------
    # Övre panel
    # ------------------------------------------------------------------

    def _build_top_bar(self):
        top = ctk.CTkFrame(
            self,
            corner_radius=10,
            fg_color=theme.COLOR_BG_PANEL,
        )
        top.pack(pady=(10, 5), padx=10, fill="x")

        self.status_lamp = ctk.CTkLabel(
            top,
            text="●",
            text_color=theme.status_lamp_color("idle"),
            font=("Arial", 22),
        )
        self.status_lamp.pack(
            side="left",
            padx=(15, 5),
            pady=10,
        )

        self.status_label = ctk.CTkLabel(
            top,
            text=self.localizer.get_text("status_ready"),
            font=theme.FONT_TITLE,
        )
        self.status_label.pack(
            side="left",
            padx=5,
            pady=10,
        )

        ctk.CTkButton(
            top,
            text=self.localizer.get_text("btn_build_package"),
            command=self._start_build,
            width=140,
            fg_color=theme.COLOR_GREEN_DARK,
            hover_color=theme.COLOR_GREEN,
        ).pack(
            side="right",
            padx=(5, 15),
            pady=10,
        )

        ctk.CTkButton(
            top,
            text=self.localizer.get_text("btn_cancel"),
            command=self._cancel_operation,
            width=110,
            fg_color=theme.COLOR_RED_DARK,
            hover_color=theme.COLOR_RED,
        ).pack(
            side="right",
            padx=5,
            pady=10,
        )

        ctk.CTkButton(
            top,
            text=self.localizer.get_text("btn_scan"),
            command=self._start_scan,
            width=120,
            fg_color=theme.COLOR_BLUE_DARK,
            hover_color=theme.COLOR_BLUE,
        ).pack(
            side="right",
            padx=5,
            pady=10,
        )

        self.export_format_var = tk.StringVar(
            value=self.settings.default_export_format
        )

        self.export_format_menu = ctk.CTkOptionMenu(
            top,
            values=["markdown", "text", "tree", "json"],
            variable=self.export_format_var,
            width=110,
            fg_color=theme.COLOR_GRAY_DARK,
            button_color=theme.COLOR_GRAY,
            command=self._on_export_format_change,
        )

        self.export_format_menu.pack(
            side="right",
            padx=10,
            pady=10,
        )

    # ------------------------------------------------------------------
    # Matrix-panel
    # ------------------------------------------------------------------

    def _build_matrix_bar(self):
        matrix = ctk.CTkFrame(
            self,
            corner_radius=10,
            fg_color=theme.COLOR_BG_PANEL,
        )
        matrix.pack(
            pady=5,
            padx=10,
            fill="x",
        )

        ctk.CTkLabel(
            matrix,
            text=self.localizer.get_text("section_scan_control"),
            font=theme.FONT_SECTION,
            text_color=theme.COLOR_TEXT_MUTED,
        ).pack(
            anchor="w",
            padx=15,
            pady=(8, 2),
        )

        grid = ctk.CTkFrame(
            matrix,
            fg_color="transparent",
        )
        grid.pack(
            fill="x",
            padx=15,
            pady=(0, 10),
        )

        ctk.CTkButton(
            grid,
            text=self.localizer.get_text("btn_choose_source"),
            command=self._choose_source,
            width=130,
            fg_color=theme.COLOR_GRAY_DARK,
            hover_color=theme.COLOR_GRAY,
        ).grid(
            row=0,
            column=0,
            padx=(0, 8),
            pady=8,
            sticky="w",
        )

        ctk.CTkButton(
            grid,
            text=self.localizer.get_text("btn_remove_source"),
            command=self._remove_source,
            width=140,
            fg_color=theme.COLOR_GRAY_DARK,
            hover_color=theme.COLOR_GRAY,
        ).grid(
            row=0,
            column=1,
            padx=8,
            pady=8,
            sticky="w",
        )

        ctk.CTkButton(
            grid,
            text=self.localizer.get_text("btn_choose_export_dir"),
            command=self._choose_export_dir,
            width=140,
            fg_color=theme.COLOR_GRAY_DARK,
            hover_color=theme.COLOR_GRAY,
        ).grid(
            row=0,
            column=2,
            padx=8,
            pady=8,
            sticky="w",
        )

        ctk.CTkButton(
            grid,
            text=self.localizer.get_text("btn_preview"),
            command=self._preview,
            width=140,
            fg_color=theme.COLOR_GRAY_DARK,
            hover_color=theme.COLOR_GRAY,
        ).grid(
            row=0,
            column=3,
            padx=8,
            pady=8,
            sticky="w",
        )

        ctk.CTkButton(
            grid,
            text=self.localizer.get_text("btn_clear"),
            command=self._clear_all,
            width=90,
            fg_color=theme.COLOR_RED_DARK,
            hover_color=theme.COLOR_RED,
        ).grid(
            row=0,
            column=4,
            padx=8,
            pady=8,
            sticky="w",
        )

        ctk.CTkButton(
            grid,
            text=self.localizer.get_text("btn_settings"),
            command=self._open_settings,
            width=120,
            fg_color=theme.COLOR_GRAY_DARK,
            hover_color=theme.COLOR_GRAY,
        ).grid(
            row=0,
            column=5,
            padx=8,
            pady=8,
            sticky="w",
        )

        ctk.CTkButton(
            grid,
            text=self.localizer.get_text("btn_select_all"),
            command=lambda: self._set_all(True),
            width=110,
            fg_color=theme.COLOR_GRAY_DARK,
            hover_color=theme.COLOR_GRAY,
        ).grid(
            row=1,
            column=0,
            padx=(0, 8),
            pady=(0, 8),
            sticky="w",
        )

        ctk.CTkButton(
            grid,
            text=self.localizer.get_text("btn_deselect_all"),
            command=lambda: self._set_all(False),
            width=120,
            fg_color=theme.COLOR_GRAY_DARK,
            hover_color=theme.COLOR_GRAY,
        ).grid(
            row=1,
            column=1,
            padx=8,
            pady=(0, 8),
            sticky="w",
        )

        self.category_var = tk.StringVar()

        self.category_combo = ctk.CTkOptionMenu(
            grid,
            values=["–"],
            variable=self.category_var,
            width=130,
            fg_color=theme.COLOR_GRAY_DARK,
            button_color=theme.COLOR_GRAY,
        )
        self.category_combo.grid(
            row=1,
            column=2,
            padx=8,
            pady=(0, 8),
            sticky="w",
        )

        ctk.CTkButton(
            grid,
            text=self.localizer.get_text("btn_select_category"),
            command=lambda: self._set_category(True),
            width=140,
            fg_color=theme.COLOR_GRAY_DARK,
            hover_color=theme.COLOR_GRAY,
        ).grid(
            row=1,
            column=3,
            padx=8,
            pady=(0, 8),
            sticky="w",
        )

        ctk.CTkButton(
            grid,
            text=self.localizer.get_text("btn_deselect_category"),
            command=lambda: self._set_category(False),
            width=150,
            fg_color=theme.COLOR_GRAY_DARK,
            hover_color=theme.COLOR_GRAY,
        ).grid(
            row=1,
            column=4,
            padx=8,
            pady=(0, 8),
            sticky="w",
        )

        self.show_binary_switch = ctk.CTkSwitch(
            grid,
            text=self.localizer.get_text("switch_show_binary"),
            command=self._on_quick_toggle,
            font=theme.FONT_UI,
            text_color=theme.COLOR_TEXT_PRIMARY,
            progress_color=theme.COLOR_BLUE,
        )
        self.show_binary_switch.grid(
            row=1,
            column=5,
            padx=8,
            pady=(0, 8),
            sticky="w",
        )

        if self.settings.show_binary_files:
            self.show_binary_switch.select()

        ctk.CTkButton(
            grid, text=self.localizer.get_text("btn_register_gamebridge"), command=self._register_for_gamebridge, width=190,
            fg_color=theme.COLOR_BLUE_DARK, hover_color=theme.COLOR_BLUE,
        ).grid(row=1, column=6, padx=8, pady=(0, 8), sticky="w")

    # ------------------------------------------------------------------
    # Kropp
    # ------------------------------------------------------------------

    def _build_body(self):
        body = ctk.CTkFrame(
            self,
            fg_color="transparent",
        )
        body.pack(
            fill="both",
            expand=True,
            padx=10,
        )

        left = ctk.CTkFrame(
            body,
            fg_color="transparent",
        )
        left.pack(
            side="left",
            fill="both",
            expand=True,
        )

        src_frame = ctk.CTkFrame(
            left,
            corner_radius=10,
            fg_color=theme.COLOR_BG_PANEL,
        )
        src_frame.pack(
            fill="x",
            pady=(0, 6),
        )

        ctk.CTkLabel(
            src_frame,
            text=self.localizer.get_text("section_sources"),
            font=theme.FONT_SECTION,
            text_color=theme.COLOR_TEXT_MUTED,
        ).pack(
            anchor="w",
            padx=12,
            pady=(8, 2),
        )

        self.sources_listbox = tk.Listbox(
            src_frame,
            height=3,
            bg=theme.COLOR_BG_PANEL_ALT,
            fg=theme.COLOR_TEXT_PRIMARY,
            selectbackground=theme.COLOR_BLUE_DARK,
            borderwidth=0,
            highlightthickness=0,
        )
        self.sources_listbox.pack(
            fill="x",
            padx=12,
            pady=(0, 10),
        )

        filter_frame = ctk.CTkFrame(
            left,
            fg_color="transparent",
        )
        filter_frame.pack(
            fill="x",
            pady=(0, 6),
        )

        ctk.CTkLabel(
            filter_frame,
            text=self.localizer.get_text("filter_label"),
            font=theme.FONT_UI,
        ).pack(side="left")

        self.filter_var = tk.StringVar()
        self.filter_var.trace_add(
            "write",
            lambda *_: self.file_tree.apply_filter(
                self.filter_var.get()
            ),
        )

        ctk.CTkEntry(
            filter_frame,
            textvariable=self.filter_var,
            placeholder_text=self.localizer.get_text("filter_placeholder"),
            fg_color=theme.COLOR_BG_PANEL_ALT,
        ).pack(
            side="left",
            fill="x",
            expand=True,
            padx=6,
        )

        tree_container = ctk.CTkFrame(
            left,
            corner_radius=10,
            fg_color=theme.COLOR_BG_PANEL,
        )
        tree_container.pack(
            fill="both",
            expand=True,
        )

        self.file_tree = FileTreeView(
            tree_container,
            on_selection_changed=self._update_counts,
            localizer=self.localizer,
        )
        self.file_tree.pack(
            fill="both",
            expand=True,
            padx=8,
            pady=8,
        )

        right = ctk.CTkFrame(
            body,
            width=320,
            fg_color="transparent",
        )
        right.pack(
            side="left",
            fill="y",
            padx=(10, 0),
        )
        right.pack_propagate(False)

        info_frame = ctk.CTkFrame(
            right,
            corner_radius=10,
            fg_color=theme.COLOR_BG_PANEL,
        )
        info_frame.pack(fill="x")

        ctk.CTkLabel(
            info_frame,
            text=self.localizer.get_text("section_status"),
            font=theme.FONT_SECTION,
            text_color=theme.COLOR_TEXT_MUTED,
        ).pack(
            anchor="w",
            padx=12,
            pady=(10, 4),
        )

        self.export_dir_label = self._status_row(
            info_frame,
            self.localizer.get_text("label_export_dir_unset"),
        )
        self.found_label = self._status_row(
            info_frame,
            self.localizer.get_text("label_found_files", n=0),
        )
        self.included_label = self._status_row(
            info_frame,
            self.localizer.get_text("label_included", n=0),
        )
        self.excluded_label = self._status_row(
            info_frame,
            self.localizer.get_text("label_excluded", n=0),
        )
        self.sensitive_label = self._status_row(
            info_frame,
            self.localizer.get_text("label_sensitive_files", n=0),
            color=theme.COLOR_RED,
        )
        self.op_label = self._status_row(
            info_frame,
            self.localizer.get_text("label_current_op_idle"),
        )

        self.progress = ctk.CTkProgressBar(
            info_frame,
            progress_color=theme.COLOR_BLUE,
        )
        self.progress.pack(
            fill="x",
            padx=12,
            pady=(6, 12),
        )
        self.progress.set(0)

        log_frame = ctk.CTkFrame(
            right,
            corner_radius=10,
            fg_color=theme.COLOR_BG_PANEL,
        )
        log_frame.pack(
            fill="both",
            expand=True,
            pady=(10, 0),
        )

        ctk.CTkLabel(
            log_frame,
            text=self.localizer.get_text("section_log"),
            font=theme.FONT_SECTION,
            text_color=theme.COLOR_TEXT_MUTED,
        ).pack(
            anchor="w",
            padx=12,
            pady=(10, 4),
        )

        self.log_text = ctk.CTkTextbox(
            log_frame,
            font=theme.FONT_MONO,
            corner_radius=8,
            fg_color=theme.COLOR_BG_PANEL_ALT,
            text_color=theme.COLOR_TEXT_PRIMARY,
        )
        self.log_text.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=(0, 10),
        )
        self.log_text.configure(state="disabled")

    def _status_row(self, parent, text, color=None):
        label = ctk.CTkLabel(
            parent,
            text=text,
            font=theme.FONT_UI,
            text_color=color or theme.COLOR_TEXT_PRIMARY,
            anchor="w",
        )
        label.pack(
            anchor="w",
            padx=12,
            pady=1,
        )
        return label

    # ------------------------------------------------------------------
    # Nedre panel
    # ------------------------------------------------------------------

    def _build_bottom_bar(self):
        control = ctk.CTkFrame(
            self,
            fg_color="transparent",
        )
        control.pack(
            pady=(0, 5),
            padx=10,
            fill="x",
            side="bottom",
        )

        self.lock_switch = ctk.CTkSwitch(
            control,
            text=self.localizer.get_text("switch_lock_selection"),
            font=theme.FONT_UI,
            text_color=theme.COLOR_TEXT_PRIMARY,
            progress_color=theme.COLOR_RED,
            command=self._on_lock_toggle,
        )
        self.lock_switch.pack(
            side="left",
            padx=5,
        )

        version_label = ctk.CTkLabel(
            control,
            text=f"AIDE v{theme.APP_VERSION}",
            font=theme.FONT_UI,
            text_color=theme.COLOR_TEXT_MUTED,
        )
        version_label.pack(
            side="right",
            padx=5,
        )

    def _build_status_bar(self):
        self.status_var = tk.StringVar(value="Redo.")

        bar = ctk.CTkLabel(
            self,
            textvariable=self.status_var,
            anchor="w",
            font=theme.FONT_UI,
            text_color=theme.COLOR_TEXT_MUTED,
            fg_color=theme.COLOR_BG_PANEL,
            corner_radius=0,
        )
        bar.pack(
            fill="x",
            side="bottom",
        )

    # ------------------------------------------------------------------
    # Plugins
    # ------------------------------------------------------------------

    def _register_plugin_exporters(self):
        """Samlar in exportformat som plugins registrerar och gör dem valbara."""
        self._plugin_exporters.clear()

        for plugin in self.plugins.values():
            try:
                exporters = plugin.get_exporters()
            except Exception as exc:
                self._log(
                    f"⚠ Plugin '{plugin.plugin_name}' "
                    f"kraschade i get_exporters(): {exc}"
                )
                continue

            for fmt_name, fn in (exporters or {}).items():
                if fmt_name in ("markdown", "text", "tree", "json"):
                    self._log(
                        f"⚠ Plugin '{plugin.plugin_name}' försökte registrera "
                        f"reserverat formatnamn '{fmt_name}', hoppar över."
                    )
                    continue

                self._plugin_exporters[fmt_name] = fn

        self.export_format_menu.configure(
            values=self._available_export_formats()
        )

    def _available_export_formats(self) -> list[str]:
        """
        Samlade exportformat: AIDE:s inbyggda plus vad som helst
        plugins registrerat via get_exporters(). Enda källan till
        sanning för detta — används både av exportformat-menyn här
        och av standardformat-väljaren i Inställningar, så de två
        aldrig kan hamna i otakt med varandra.
        """
        base_formats = ["markdown", "text", "tree", "json"]
        return base_formats + sorted(self._plugin_exporters.keys())

    def _apply_plugin_classification(self, files: list[ScannedFile]):
        """Låter plugins komplettera klassificeringen av 'Okänd'-filer."""
        unknown_files = [
            f for f in files
            if f.category == CATEGORY_UNKNOWN
        ]

        if not unknown_files or not self.plugins:
            return

        for f in unknown_files:
            info = _to_plugin_file_info(f)

            for plugin in self.plugins.values():
                try:
                    result = plugin.on_classify(info)
                except Exception as exc:
                    self._log(
                        f"⚠ Plugin '{plugin.plugin_name}' "
                        f"kraschade i on_classify(): {exc}"
                    )
                    continue

                if result:
                    f.category = result.get(
                        "category",
                        f.category,
                    )
                    f.language = result.get(
                        "language",
                        f.language,
                    )
                    f.is_sensitive = result.get(
                        "is_sensitive",
                        f.is_sensitive,
                    )
                    break

    def _notify_plugins_scan_complete(
        self,
        files: list[ScannedFile],
    ):
        if not self.plugins:
            return

        infos = [
            _to_plugin_file_info(f)
            for f in files
        ]

        for plugin in self.plugins.values():
            try:
                plugin.on_scan_complete(infos)
            except Exception as exc:
                self._log(
                    f"⚠ Plugin '{plugin.plugin_name}' "
                    f"kraschade i on_scan_complete(): {exc}"
                )

    def _apply_plugin_before_export(
        self,
        files: list[ScannedFile],
    ) -> list[ScannedFile]:
        """Ger plugins chansen att filtrera urvalet strax innan export."""
        if not self.plugins:
            return files

        by_path = {
            f.absolute_path: f
            for f in files
        }

        current = files

        for plugin in self.plugins.values():
            try:
                infos = [
                    _to_plugin_file_info(f)
                    for f in current
                ]
                result = plugin.on_before_export(infos)
            except Exception as exc:
                self._log(
                    f"⚠ Plugin '{plugin.plugin_name}' "
                    f"kraschade i on_before_export(): {exc}"
                )
                continue

            if result is not None:
                new_current = [
                    by_path[info.absolute_path]
                    for info in result
                    if info.absolute_path in by_path
                ]

                self._log(
                    f"Plugin '{plugin.plugin_name}' justerade "
                    f"exporturvalet: {len(current)} → "
                    f"{len(new_current)} filer."
                )

                current = new_current

        return current

    # ------------------------------------------------------------------
    # Källmappar
    # ------------------------------------------------------------------

    def _choose_source(self):
        directory = filedialog.askdirectory(
            title=self.localizer.get_text("btn_choose_source")
        )

        if directory and directory not in self.source_roots:
            self.source_roots.append(directory)
            self.sources_listbox.insert(
                "end",
                directory,
            )

    def _remove_source(self):
        selection = self.sources_listbox.curselection()

        if not selection:
            return

        index = selection[0]

        self.sources_listbox.delete(index)
        del self.source_roots[index]

    def _choose_export_dir(self):
        directory = filedialog.askdirectory(
            title=self.localizer.get_text("btn_choose_export_dir")
        )

        if directory:
            self.export_dir = directory
            self.export_dir_label.configure(
                text=self.localizer.get_text("label_export_dir", path=directory)
            )

    def _on_export_format_change(self, value):
        self.settings.default_export_format = value

    def _on_quick_toggle(self):
        self.settings.show_binary_files = (
            self.show_binary_switch.get() == 1
        )

    def _on_lock_toggle(self):
        locked = self.lock_switch.get() == 1
        self._log(
            "Urval låst."
            if locked
            else "Urval upplåst."
        )

    # ------------------------------------------------------------------
    # Skanning
    # ------------------------------------------------------------------

    def _start_scan(self):
        if self.lock_switch.get() == 1:
            messagebox.showinfo(
                self.localizer.get_text("dialog_selection_locked_title"),
                self.localizer.get_text("dialog_selection_locked_msg"),
            )
            return

        if not self.source_roots:
            messagebox.showwarning(
                self.localizer.get_text("dialog_no_sources_title"),
                self.localizer.get_text("dialog_no_sources_msg"),
            )
            return

        if (
            self._worker_thread
            and self._worker_thread.is_alive()
        ):
            messagebox.showinfo(
                self.localizer.get_text("dialog_busy_title"),
                self.localizer.get_text("dialog_busy_msg"),
            )
            return

        self._log(
            f"Scan started: {', '.join(self.source_roots)}"
        )

        self.op_label.configure(
            text=self.localizer.get_text("label_current_op_scanning")
        )
        self.status_label.configure(
            text=self.localizer.get_text("status_processing")
        )
        self.status_lamp.configure(
            text_color=theme.status_lamp_color("busy")
        )

        self.progress.configure(
            mode="indeterminate"
        )
        self.progress.start()

        self._cancel_event = threading.Event()

        def worker():
            result = scan_sources(
                source_roots=self.source_roots,
                ignore_dirs=set(self.settings.ignore_dirs),
                ignore_files=set(self.settings.ignore_files),
                sensitive_patterns=self.settings.sensitive_patterns,
                show_hidden=self.settings.show_hidden_files,
                show_binary=self.settings.show_binary_files,
                progress_callback=lambda done, total, path: (
                    self._ui_queue.put(
                        ("scan_progress", done, path)
                    )
                ),
                cancel_event=self._cancel_event,
            )

            self._ui_queue.put(
                ("scan_done", result)
            )

        self._worker_thread = threading.Thread(
            target=worker,
            daemon=True,
        )
        self._worker_thread.start()

    def _on_scan_done(self, result: ScanResult):
        self.progress.stop()
        self.progress.configure(
            mode="determinate"
        )
        self.progress.set(0)

        self.op_label.configure(
            text=self.localizer.get_text("label_current_op_idle")
        )
        self.status_label.configure(
            text=self.localizer.get_text("status_ready")
        )

        if result.cancelled:
            self._log(
                "Scan cancelled by user"
            )
            self.status_var.set(
                "Skanning avbruten."
            )
            self.status_lamp.configure(
                text_color=theme.status_lamp_color("idle")
            )
            return

        for path, reason in result.errors:
            self._log(
                f"⚠ Kunde inte läsa: {path} — {reason}"
            )

        sensitive_count = sum(
            1
            for f in result.files
            if f.is_sensitive
        )

        self._log(
            f"{len(result.files)} files discovered"
        )
        maybe_log_daddle(self._log)

        if sensitive_count:
            self._log(
                f"{sensitive_count} sensitive files detected"
            )

        self._apply_plugin_classification(
            result.files
        )
        self._notify_plugins_scan_complete(
            result.files
        )

        def default_checked(f):
            if f.is_sensitive:
                return False

            if (
                f.is_binary
                and not self.settings.show_binary_files
            ):
                return False

            return self.settings.default_checkbox_state

        self.file_tree.load_files(
            result.files,
            default_checked_fn=default_checked,
        )

        categories = (
            self.file_tree.get_categories()
            or ["–"]
        )

        self.category_combo.configure(
            values=categories
        )
        self.category_var.set(
            categories[0]
        )

        selected_count = sum(
            1
            for f in result.files
            if f.included
        )

        self._log(
            f"{selected_count} files selected"
        )

        self.status_var.set(
            f"Skanning klar: {len(result.files)} filer hittade."
        )

        self.status_lamp.configure(
            text_color=theme.status_lamp_color("ok")
        )

        self._update_counts()

        # Manifest skrivs automatiskt efter varje scan.
        self._write_scan_manifest(
            result.files
        )

    def _write_scan_manifest(
        self,
        all_files: list[ScannedFile],
    ):
        """
        Skriver manifestet automatiskt till AIDE Box/scan/ vid varje scan,
        så GameBridge/adaptern alltid ser färskaste state — oavsett om
        användaren senare bygger ett fullt paket eller inte.

        Skrivs alltid tyst över (ingen konfliktdialog): manifestet är en
        spegling av nuläget, inte ett artefakt att versionera.
        """
        if not self.source_roots:
            return

        included = [
            f
            for f in all_files
            if f.included
        ]

        project_name = (
            os.path.basename(
                self.source_roots[0].rstrip("/\\")
            )
            or "AIDE_Project"
        )

        safe_name = sanitize_filename(
            project_name
        )

        try:
            path = export_json_manifest(
                project_name,
                self.source_roots,
                included,
                _aide_box_subdir("scan"),
                filename=f"{safe_name}_manifest.json",
                conflict_strategy=ConflictStrategy.OVERWRITE,
                log_callback=self._log,
                include_absolute_paths=True,
            )

            if path:
                self._log(
                    f"Manifest uppdaterat: {path}"
                )

        except Exception as exc:
            self._log(
                f"⚠ Kunde inte skriva scan-manifest: {exc}"
            )

    # ------------------------------------------------------------------
    # Checkbox-styrning
    # ------------------------------------------------------------------

    def _set_all(self, included: bool):
        if self.lock_switch.get() == 1:
            return

        self.file_tree.set_all(
            included
        )

    def _set_category(self, included: bool):
        if self.lock_switch.get() == 1:
            return

        category = self.category_var.get()

        if category and category != "–":
            self.file_tree.set_category(
                category,
                included,
            )

    def _clear_all(self):
        self.source_roots.clear()
        self.sources_listbox.delete(
            0,
            "end",
        )

        self.file_tree.load_files([])

        self.category_combo.configure(
            values=["–"]
        )
        self.category_var.set("–")

        self._update_counts()
        self._log(
            "Cleared sources and file list"
        )
        self.status_var.set(
            "Rensat."
        )
        self.status_lamp.configure(
            text_color=theme.status_lamp_color("idle")
        )

    def _update_counts(self):
        all_files = self.file_tree.get_all_files()
        included = self.file_tree.get_included_files()

        self.found_label.configure(
            text=self.localizer.get_text("label_found_files", n=len(all_files))
        )

        self.included_label.configure(
            text=self.localizer.get_text("label_included", n=len(included))
        )

        self.excluded_label.configure(
            text=self.localizer.get_text(
                "label_excluded", n=len(all_files) - len(included)
            )
        )

        self.sensitive_label.configure(
            text=self.localizer.get_text(
                "label_sensitive_files",
                n=sum(1 for f in all_files if f.is_sensitive),
            )
        )

    # ------------------------------------------------------------------
    # Förhandsgranskning & export
    # ------------------------------------------------------------------

    def _preview(self):
        included = self.file_tree.get_included_files()

        if not included:
            messagebox.showinfo(
                self.localizer.get_text("dialog_nothing_selected_title"),
                self.localizer.get_text("dialog_nothing_selected_preview_msg"),
            )
            return

        PreviewWindow(
            self,
            self.file_tree.get_all_files(),
            self.source_roots,
            localizer=self.localizer,
        )

    def _start_build(self):
        included = self.file_tree.get_included_files()

        if not included:
            messagebox.showwarning(
                self.localizer.get_text("dialog_nothing_selected_title"),
                self.localizer.get_text("dialog_nothing_selected_msg"),
            )
            return

        if (
            self._worker_thread
            and self._worker_thread.is_alive()
        ):
            messagebox.showinfo(
                self.localizer.get_text("dialog_busy_title"),
                self.localizer.get_text("dialog_busy_msg"),
            )
            return

        included = self._apply_plugin_before_export(
            included
        )

        if not included:
            messagebox.showwarning(
                self.localizer.get_text("dialog_nothing_selected_title"),
                self.localizer.get_text("dialog_nothing_left_after_plugin_msg"),
            )
            return

        strategy = self._ask_conflict_strategy()

        if strategy is None:
            return

        self.op_label.configure(
            text=self.localizer.get_text("label_current_op_packaging")
        )
        self.status_label.configure(
            text=self.localizer.get_text("status_processing")
        )
        self.status_lamp.configure(
            text_color=theme.status_lamp_color("busy")
        )

        self.progress.configure(
            mode="indeterminate"
        )
        self.progress.start()

        project_name = (
            os.path.basename(
                self.source_roots[0]
            )
            if self.source_roots
            else "AIDE_Project"
        )

        safe_name = sanitize_filename(
            project_name
        )

        def worker():
            written = []
            fmt = self.settings.default_export_format

            log = lambda msg: self._ui_queue.put(
                ("log", msg)
            )

            try:
                if fmt == "markdown":
                    path = export_markdown(
                        project_name,
                        self.source_roots,
                        included,
                        _aide_box_subdir("md"),
                        filename=f"{safe_name}.md",
                        conflict_strategy=strategy,
                        log_callback=log,
                    )

                elif fmt == "text":
                    path = export_text(
                        project_name,
                        self.source_roots,
                        included,
                        _aide_box_subdir("text"),
                        filename=f"{safe_name}.txt",
                        conflict_strategy=strategy,
                        log_callback=log,
                    )

                elif fmt == "tree":
                    path = export_tree(
                        project_name,
                        self.source_roots,
                        included,
                        _aide_box_subdir("tree"),
                        filename=f"{safe_name}_tree.md",
                        conflict_strategy=strategy,
                        log_callback=log,
                    )

                elif fmt == "json":
                    path = export_json_manifest(
                        project_name,
                        self.source_roots,
                        included,
                        _aide_box_subdir("scan"),
                        filename=f"{safe_name}_manifest.json",
                        conflict_strategy=ConflictStrategy.OVERWRITE,
                        log_callback=log,
                    )

                elif fmt in self._plugin_exporters:
                    plugin_infos = [
                        _to_plugin_file_info(f)
                        for f in included
                    ]

                    path = self._plugin_exporters[fmt](
                        project_name,
                        self.source_roots,
                        plugin_infos,
                        _aide_box_subdir(fmt),
                        strategy,
                        log,
                    )

                else:
                    log(
                        f"⚠ Okänt exportformat '{fmt}', "
                        "faller tillbaka på markdown."
                    )

                    path = export_markdown(
                        project_name,
                        self.source_roots,
                        included,
                        _aide_box_subdir("md"),
                        filename=f"{safe_name}.md",
                        conflict_strategy=strategy,
                        log_callback=log,
                    )

                if path:
                    written.append(path)

                # Manifestet vid build ska alltid speglas i scan/.
                # Tyst överskrivning, oavsett vald konfliktstrategi
                # för själva paketet.
                manifest_path = export_json_manifest(
                    project_name,
                    self.source_roots,
                    included,
                    _aide_box_subdir("scan"),
                    filename=f"{safe_name}_manifest.json",
                    conflict_strategy=ConflictStrategy.OVERWRITE,
                    log_callback=log,
                    include_absolute_paths=True,
                )

                if (
                    manifest_path
                    and manifest_path not in written
                ):
                    written.append(
                        manifest_path
                    )

                self._ui_queue.put(
                    ("build_done", written)
                )

            except Exception as exc:
                self._ui_queue.put(
                    ("build_error", str(exc))
                )

        self._worker_thread = threading.Thread(
            target=worker,
            daemon=True,
        )
        self._worker_thread.start()

    def _ask_conflict_strategy(
        self,
    ) -> ConflictStrategy | None:
        answer = messagebox.askyesnocancel(
            self.localizer.get_text("dialog_conflict_title"),
            self.localizer.get_text("dialog_conflict_msg"),
        )

        if answer is None:
            return ConflictStrategy.SKIP

        return (
            ConflictStrategy.OVERWRITE
            if answer
            else ConflictStrategy.NEW_VERSION
        )

    def _on_build_done(
        self,
        written_paths: list[str],
    ):
        self.progress.stop()
        self.progress.configure(
            mode="determinate"
        )
        self.progress.set(0)

        self.op_label.configure(
            text=self.localizer.get_text("label_current_op_idle")
        )
        self.status_label.configure(
            text=self.localizer.get_text("status_ready")
        )

        self._log(
            "Package created"
        )

        if written_paths:
            self.status_var.set(
                f"Paket skapat: {len(written_paths)} fil(er) skrivna."
            )

            self.status_lamp.configure(
                text_color=theme.status_lamp_color("ok")
            )

            messagebox.showinfo(
                self.localizer.get_text("dialog_done_title"),
                self.localizer.get_text("dialog_done_msg")
                + "\n".join(written_paths),
            )

        else:
            self.status_var.set(
                "Ingen fil skrevs (allt hoppades över)."
            )

            self.status_lamp.configure(
                text_color=theme.status_lamp_color("idle")
            )

    def _on_build_error(
        self,
        message: str,
    ):
        self.progress.stop()
        self.progress.configure(
            mode="determinate"
        )
        self.progress.set(0)

        self.op_label.configure(
            text=self.localizer.get_text("label_current_op_idle")
        )
        self.status_label.configure(
            text=self.localizer.get_text("status_ready")
        )
        self.status_lamp.configure(
            text_color=theme.status_lamp_color("error")
        )

        self._log(
            f"⚠ Fel vid paketering: {message}"
        )

        messagebox.showerror(
            self.localizer.get_text("dialog_error_title"),
            self.localizer.get_text("dialog_error_msg") + message,
        )

    def _cancel_operation(self):
        if self._cancel_event is not None:
            self._cancel_event.set()
            self._log(
                "Cancel requested by user"
            )

    # ------------------------------------------------------------------
    # Inställningar
    # ------------------------------------------------------------------

    def _open_settings(self):
        SettingsWindow(
            self,
            self.settings,
            on_saved=self._on_settings_saved,
            available_formats=self._available_export_formats(),
        )

    def _register_for_gamebridge(self):
        from core.plugin_registration import register_for_gamebridge

        path = register_for_gamebridge(PROJECT_ROOT, log_callback=self._log)
        self.status_var.set(f"Registrerad för GameBridge: {path}")

    def _on_settings_saved(
        self,
        settings: Settings,
    ):
        self.settings = settings

        # Ny sparad LocalizationCore-instans i fallet språket byttes;
        # get_text-anropen i redan byggda widgets uppdateras inte
        # retroaktivt (kräver en fönster-omritning för att synas fullt
        # ut), men nya dialoger/fönster som öppnas efter det här
        # använder rätt språk direkt.
        self.localizer.set_language(settings.language) if settings.language else None

        self.export_format_var.set(
            settings.default_export_format
        )

        if settings.show_binary_files:
            self.show_binary_switch.select()
        else:
            self.show_binary_switch.deselect()

        self._bind_hotkeys()

        self._log(
            "Settings updated"
        )

    # ------------------------------------------------------------------
    # Logg och köhantering
    # ------------------------------------------------------------------

    def _log(self, message: str):
        timestamp = datetime.now().strftime(
            "%H:%M:%S"
        )

        self.log_text.configure(
            state="normal"
        )

        self.log_text.insert(
            "end",
            f"{timestamp}  {message}\n",
        )

        self.log_text.see("end")

        self.log_text.configure(
            state="disabled"
        )

    def _poll_queue(self):
        try:
            while True:
                item = self._ui_queue.get_nowait()
                kind = item[0]

                if kind == "scan_progress":
                    _, done, path = item
                    self.status_var.set(
                        f"Skannar... {done} filer ({path})"
                    )

                elif kind == "scan_done":
                    self._on_scan_done(
                        item[1]
                    )

                elif kind == "build_done":
                    self._on_build_done(
                        item[1]
                    )

                elif kind == "build_error":
                    self._on_build_error(
                        item[1]
                    )

                elif kind == "log":
                    self._log(
                        item[1]
                    )

        except queue.Empty:
            pass

        self.after(
            100,
            self._poll_queue,
        )

    def on_close(self):
        if self._cancel_event is not None:
            self._cancel_event.set()

        for plugin in self.plugins.values():
            try:
                plugin.shutdown()
            except Exception:
                pass

        self.destroy()
