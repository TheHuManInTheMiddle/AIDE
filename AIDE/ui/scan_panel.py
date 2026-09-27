"""
ui/scan_panel.py

Självständig, återanvändbar scan-enhet: källmappar (flera, som i AIDE:s
normalläge), skanna-knapp, filträd, filter, statusrader, och automatisk
manifestskrivning till AIDE Box/scan/.

ANVÄNDNING:
  - Jämförelseläge i MainWindow: två ScanPanel-instanser sida vid sida
    ("A" och "B"), var och en med sina egna källmappar, eget träd, eget
    manifest. Endast en panel är "aktiv för export" åt gången — det styrs
    utifrån (MainWindow), inte av panelen själv.

ANSVARSGRÄNS:
  Panelen känner INTE till export-logik för md/text/tree/json. Den
  ansvarar bara för: välja källor, skanna, visa träd, räkna, och
  automatiskt skriva sitt eget manifest vid varje scan (samma mönster
  som AIDE:s normalläge). MainWindow läser panelens
  get_included_files() / source_roots när ett faktiskt paket ska byggas.

FILNAMN VID MANIFEST-SKRIVNING:
  Baseras på källmappens namn (samma som normalläget). Om två paneler
  råkar ha källmappar med IDENTISKT namn skriver de över samma fil i
  AIDE Box/scan/ — det är avsett beteende (manifestet ska alltid spegla
  senaste scan av den mappen, historik hanteras av separat planerad
  backup-funktion, inte av jämförelseläget).
"""

from __future__ import annotations

import os
import threading
import queue
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk

from core.scanner import ScanResult, ScannedFile, scan_sources
from core.security import ConflictStrategy, sanitize_filename
from exporters.json_exporter import export_json_manifest
from ui.file_tree import FileTreeView
from ui import theme


class ScanPanel(ctk.CTkFrame):
    """
    En självständig scan-panel. panel_id ("A"/"B") används för tydliga
    loggetiketter och visuell märkning — så det alltid är uppenbart
    vilken panel som skannas eller är aktiv för export.
    """

    def __init__(
        self,
        parent,
        panel_id: str,
        settings,
        aide_box_subdir_fn,
        log_callback,
        on_selection_changed=None,
        on_scan_started=None,
        on_scan_finished=None,
    ):
        super().__init__(parent, fg_color="transparent")
        self.panel_id = panel_id  # "A" eller "B"
        self.settings = settings
        self._aide_box_subdir = aide_box_subdir_fn
        self._log = log_callback
        self._on_selection_changed_cb = on_selection_changed
        self._on_scan_started_cb = on_scan_started
        self._on_scan_finished_cb = on_scan_finished

        self.source_roots: list[str] = []
        self._cancel_event: threading.Event | None = None
        self._worker_thread: threading.Thread | None = None
        self._ui_queue: "queue.Queue" = queue.Queue()

        self._build_ui()
        self._poll_queue()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        header = ctk.CTkFrame(self, corner_radius=10, fg_color=theme.COLOR_BG_PANEL)
        header.pack(fill="x", pady=(0, 6))

        title_row = ctk.CTkFrame(header, fg_color="transparent")
        title_row.pack(fill="x", padx=12, pady=(8, 2))

        ctk.CTkLabel(
            title_row, text=f"KÄLLMAPPAR — PANEL {self.panel_id}", font=theme.FONT_SECTION,
            text_color=theme.COLOR_TEXT_MUTED,
        ).pack(side="left")

        self.active_indicator = ctk.CTkLabel(
            title_row, text="", font=theme.FONT_SECTION,
            text_color=theme.COLOR_GREEN,
        )
        self.active_indicator.pack(side="right")

        self.sources_listbox = tk.Listbox(
            header, height=3, bg=theme.COLOR_BG_PANEL_ALT, fg=theme.COLOR_TEXT_PRIMARY,
            selectbackground=theme.COLOR_BLUE_DARK, borderwidth=0, highlightthickness=0,
        )
        self.sources_listbox.pack(fill="x", padx=12, pady=(0, 8))

        btn_row = ctk.CTkFrame(header, fg_color="transparent")
        btn_row.pack(fill="x", padx=12, pady=(0, 10))

        ctk.CTkButton(
            btn_row, text="Välj källmapp", command=self._choose_source, width=120,
            fg_color=theme.COLOR_GRAY_DARK, hover_color=theme.COLOR_GRAY,
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            btn_row, text="Ta bort", command=self._remove_source, width=90,
            fg_color=theme.COLOR_GRAY_DARK, hover_color=theme.COLOR_GRAY,
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            btn_row, text=f"Skanna {self.panel_id}", command=self._start_scan, width=110,
            fg_color=theme.COLOR_BLUE_DARK, hover_color=theme.COLOR_BLUE,
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            btn_row, text="Avbryt", command=self._cancel_operation, width=90,
            fg_color=theme.COLOR_RED_DARK, hover_color=theme.COLOR_RED,
        ).pack(side="left")

        filter_frame = ctk.CTkFrame(self, fg_color="transparent")
        filter_frame.pack(fill="x", pady=(0, 6))
        ctk.CTkLabel(filter_frame, text="Filter:", font=theme.FONT_UI).pack(side="left")
        self.filter_var = tk.StringVar()
        self.filter_var.trace_add("write", lambda *_: self.file_tree.apply_filter(self.filter_var.get()))
        ctk.CTkEntry(
            filter_frame, textvariable=self.filter_var, placeholder_text="Sök filnamn, sökväg, kategori...",
            fg_color=theme.COLOR_BG_PANEL_ALT,
        ).pack(side="left", fill="x", expand=True, padx=6)

        tree_container = ctk.CTkFrame(self, corner_radius=10, fg_color=theme.COLOR_BG_PANEL)
        tree_container.pack(fill="both", expand=True, pady=(0, 6))
        self.file_tree = FileTreeView(tree_container, on_selection_changed=self._on_tree_changed)
        self.file_tree.pack(fill="both", expand=True, padx=8, pady=8)

        status_frame = ctk.CTkFrame(self, corner_radius=10, fg_color=theme.COLOR_BG_PANEL)
        status_frame.pack(fill="x")
        self.found_label = self._status_row(status_frame, "Hittade filer: 0")
        self.included_label = self._status_row(status_frame, "Inkluderade: 0")
        self.sensitive_label = self._status_row(status_frame, "Känsliga filer: 0", color=theme.COLOR_RED)
        self.op_label = self._status_row(status_frame, "Aktuell operation: Inaktiv")

        self.progress = ctk.CTkProgressBar(status_frame, progress_color=theme.COLOR_BLUE)
        self.progress.pack(fill="x", padx=12, pady=(6, 10))
        self.progress.set(0)

    def _status_row(self, parent, text, color=None):
        label = ctk.CTkLabel(
            parent, text=text, font=theme.FONT_UI,
            text_color=color or theme.COLOR_TEXT_PRIMARY, anchor="w",
        )
        label.pack(anchor="w", padx=12, pady=1)
        return label

    # ------------------------------------------------------------------
    # Aktiv-markering (visuell — MainWindow bestämmer vilken panel som
    # är aktiv, panelen bara visar det tydligt)
    # ------------------------------------------------------------------

    def set_active_indicator(self, is_active: bool):
        self.active_indicator.configure(
            text="● AKTIV FÖR EXPORT" if is_active else ""
        )

    # ------------------------------------------------------------------
    # Källmappar
    # ------------------------------------------------------------------

    def _choose_source(self):
        directory = filedialog.askdirectory(title=f"Välj källmapp — Panel {self.panel_id}")
        if directory and directory not in self.source_roots:
            self.source_roots.append(directory)
            self.sources_listbox.insert("end", directory)

    def _remove_source(self):
        selection = self.sources_listbox.curselection()
        if not selection:
            return
        index = selection[0]
        self.sources_listbox.delete(index)
        del self.source_roots[index]

    # ------------------------------------------------------------------
    # Skanning
    # ------------------------------------------------------------------

    def _start_scan(self):
        if not self.source_roots:
            messagebox.showwarning(
                "Inga källor", f"Välj minst en källmapp i Panel {self.panel_id} innan skanning."
            )
            return
        if self._worker_thread and self._worker_thread.is_alive():
            messagebox.showinfo("Pågår redan", f"En skanning pågår redan i Panel {self.panel_id}.")
            return

        self._log(f"[Panel {self.panel_id}] Scan started: {', '.join(self.source_roots)}")
        self.op_label.configure(text="Aktuell operation: Skannar...")
        self.progress.configure(mode="indeterminate")
        self.progress.start()
        self._cancel_event = threading.Event()

        if self._on_scan_started_cb:
            self._on_scan_started_cb(self.panel_id)

        def worker():
            result = scan_sources(
                source_roots=self.source_roots,
                ignore_dirs=set(self.settings.ignore_dirs),
                ignore_files=set(self.settings.ignore_files),
                sensitive_patterns=self.settings.sensitive_patterns,
                show_hidden=self.settings.show_hidden_files,
                show_binary=self.settings.show_binary_files,
                progress_callback=lambda done, total, path: self._ui_queue.put(("scan_progress", done, path)),
                cancel_event=self._cancel_event,
            )
            self._ui_queue.put(("scan_done", result))

        self._worker_thread = threading.Thread(target=worker, daemon=True)
        self._worker_thread.start()

    def _on_scan_done(self, result: ScanResult):
        self.progress.stop()
        self.progress.configure(mode="determinate")
        self.progress.set(0)
        self.op_label.configure(text="Aktuell operation: Inaktiv")

        if result.cancelled:
            self._log(f"[Panel {self.panel_id}] Scan cancelled by user")
            if self._on_scan_finished_cb:
                self._on_scan_finished_cb(self.panel_id, cancelled=True)
            return

        for path, reason in result.errors:
            self._log(f"[Panel {self.panel_id}] ⚠ Kunde inte läsa: {path} — {reason}")

        sensitive_count = sum(1 for f in result.files if f.is_sensitive)
        self._log(f"[Panel {self.panel_id}] {len(result.files)} files discovered")
        if sensitive_count:
            self._log(f"[Panel {self.panel_id}] {sensitive_count} sensitive files detected")

        def default_checked(f):
            if f.is_sensitive:
                return False
            if f.is_binary and not self.settings.show_binary_files:
                return False
            return self.settings.default_checkbox_state

        self.file_tree.load_files(result.files, default_checked_fn=default_checked)

        selected_count = sum(1 for f in result.files if f.included)
        self._log(f"[Panel {self.panel_id}] {selected_count} files selected")

        self._update_counts()
        self._write_scan_manifest(result.files)

        if self._on_scan_finished_cb:
            self._on_scan_finished_cb(self.panel_id, cancelled=False)

    def _write_scan_manifest(self, all_files: list[ScannedFile]):
        """Skriver panelens manifest automatiskt till AIDE Box/scan/ (tyst överskrivning)."""
        if not self.source_roots:
            return

        included = [f for f in all_files if f.included]
        project_name = os.path.basename(self.source_roots[0].rstrip("/\\")) or "AIDE_Project"
        safe_name = sanitize_filename(project_name)

        try:
            path = export_json_manifest(
                project_name, self.source_roots, included,
                self._aide_box_subdir("scan"),
                filename=f"{safe_name}_manifest.json",
                conflict_strategy=ConflictStrategy.OVERWRITE,
                log_callback=self._log,
                include_absolute_paths=True,
            )
            if path:
                self._log(f"[Panel {self.panel_id}] Manifest uppdaterat: {path}")
        except Exception as exc:
            self._log(f"[Panel {self.panel_id}] ⚠ Kunde inte skriva scan-manifest: {exc}")

    def _cancel_operation(self):
        if self._cancel_event is not None:
            self._cancel_event.set()
            self._log(f"[Panel {self.panel_id}] Cancel requested by user")

    # ------------------------------------------------------------------
    # Status / räknare
    # ------------------------------------------------------------------

    def _on_tree_changed(self):
        self._update_counts()
        if self._on_selection_changed_cb:
            self._on_selection_changed_cb(self.panel_id)

    def _update_counts(self):
        all_files = self.file_tree.get_all_files()
        included = self.file_tree.get_included_files()
        self.found_label.configure(text=f"Hittade filer: {len(all_files)}")
        self.included_label.configure(text=f"Inkluderade: {len(included)}")
        self.sensitive_label.configure(
            text=f"Känsliga filer: {sum(1 for f in all_files if f.is_sensitive)}"
        )

    # ------------------------------------------------------------------
    # Publikt API mot MainWindow
    # ------------------------------------------------------------------

    def get_included_files(self) -> list[ScannedFile]:
        return self.file_tree.get_included_files()

    def get_all_files(self) -> list[ScannedFile]:
        return self.file_tree.get_all_files()

    def get_categories(self) -> list[str]:
        return self.file_tree.get_categories()

    def has_scanned_data(self) -> bool:
        return len(self.file_tree.get_all_files()) > 0

    def clear(self):
        self.source_roots.clear()
        self.sources_listbox.delete(0, "end")
        self.file_tree.load_files([])
        self._update_counts()

    # ------------------------------------------------------------------
    # Köhantering (bakgrundstråd -> huvudtråd)
    # ------------------------------------------------------------------

    def _poll_queue(self):
        try:
            while True:
                item = self._ui_queue.get_nowait()
                kind = item[0]
                if kind == "scan_done":
                    self._on_scan_done(item[1])
                # scan_progress ignoreras medvetet här — panelens op_label
                # räcker som statusindikation, ingen separat progressbar-text.
        except queue.Empty:
            pass
        self.after(100, self._poll_queue)
