"""
ui/file_tree.py

Hierarkisk mappträdsvy med klickbara checkboxar på både filer och
mappar (avsnitt 9-10), plus möjlighet att exkludera hela delträd direkt
i trädet — inte bara via kategori eller ignore-listan i inställningarna.

Klick på en MAPP växlar hela dess delträd (alla filer och undermappar)
mellan markerat/omarkerat — exakt samma klick-är-toggle-princip som
filer redan använder. En mapp visar tre lägen:

    ☑  alla filer i delträdet är markerade
    ☐  inga filer i delträdet är markerade
    ◪  delträdet är blandat (vissa markerade, andra inte)

ttk har inga inbyggda checkboxar i Treeview, så vi renderar
checkbox-tecken i första kolumnen och togglar dem vid klick.
"""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import ttk

CHECKED = "☑"
UNCHECKED = "☐"
PARTIAL = "◪"
SENSITIVE_MARK = "⚠"


def _human_size(size_bytes: int) -> str:
    size = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


class _DirNode:
    __slots__ = ("iid", "name", "parent_iid", "files", "child_dirs")

    def __init__(self, iid, name, parent_iid):
        self.iid = iid
        self.name = name
        self.parent_iid = parent_iid
        self.files = []       # list[tuple[iid, ScannedFile]] direkt i denna mapp
        self.child_dirs = []  # list[iid] till direkta undermappar


class FileTreeView(ttk.Frame):
    def __init__(self, parent, on_selection_changed=None, localizer=None):
        super().__init__(parent)
        self.on_selection_changed = on_selection_changed

        self.localizer = localizer or getattr(parent, "localizer", None)
        if self.localizer is None:
            from core.localization_core import LocalizationCore
            self.localizer = LocalizationCore()

        self._scanned_files = []  # list[ScannedFile]
        self._file_items = {}     # iid -> ScannedFile
        self._dir_nodes = {}      # iid -> _DirNode
        self._dir_lookup = {}     # (parent_iid, name) -> iid
        self._filter_text = ""

        columns = ("size", "category", "status")
        self.tree = ttk.Treeview(self, columns=columns, show="tree headings", selectmode="extended")
        self.tree.heading("#0", text=self.localizer.get_text("tree_col_name"))
        self.tree.heading("size", text=self.localizer.get_text("tree_col_size"))
        self.tree.heading("category", text=self.localizer.get_text("tree_col_category"))
        self.tree.heading("status", text=self.localizer.get_text("tree_col_status"))
        self.tree.column("#0", width=420, stretch=True)
        self.tree.column("size", width=90, anchor="e")
        self.tree.column("category", width=140)
        self.tree.column("status", width=140)

        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self.tree.bind("<Button-1>", self._on_click)

    # ------------------------------------------------------------------
    # Publikt API
    # ------------------------------------------------------------------

    def load_files(self, scanned_files, default_checked_fn=None):
        """Fyller trädet hierarkiskt (mappstruktur) utifrån relativa sökvägar."""
        self._scanned_files = scanned_files
        self._file_items.clear()
        self._dir_nodes.clear()
        self._dir_lookup.clear()
        self.tree.delete(*self.tree.get_children())

        if default_checked_fn is not None:
            for f in scanned_files:
                f.included = default_checked_fn(f)

        multiple_roots = len({f.source_root for f in scanned_files}) > 1

        for f in sorted(scanned_files, key=lambda x: (x.source_root, x.relative_path.lower())):
            parts = f.relative_path.split("/")
            folder_parts = parts[:-1]
            filename = parts[-1]

            parent_iid = ""
            if multiple_roots:
                root_name = os.path.basename(f.source_root.rstrip("/\\")) or f.source_root
                parent_iid = self._ensure_dir_node(parent_iid, root_name)
            for part in folder_parts:
                parent_iid = self._ensure_dir_node(parent_iid, part)

            warn = f" {SENSITIVE_MARK}" if f.is_sensitive else ""
            if f.is_sensitive:
                status = self.localizer.get_text("tree_status_sensitive")
            elif f.is_binary:
                status = self.localizer.get_text("tree_status_binary")
            else:
                status = ""
            if f.error:
                status = self.localizer.get_text("tree_status_error")
            item_iid = self.tree.insert(
                parent_iid, "end", text=f"{UNCHECKED} {filename}{warn}",
                values=(f.size_human, f.category, status), tags=("file",),
            )
            self._file_items[item_iid] = f
            if parent_iid in self._dir_nodes:
                self._dir_nodes[parent_iid].files.append((item_iid, f))

        self._refresh_all_labels()
        self._notify_changed()

    def _ensure_dir_node(self, parent_iid: str, name: str) -> str:
        key = (parent_iid, name)
        if key in self._dir_lookup:
            return self._dir_lookup[key]
        iid = self.tree.insert(parent_iid, "end", text=f"{UNCHECKED} {name}/", open=True, tags=("dir",))
        node = _DirNode(iid, name, parent_iid)
        self._dir_nodes[iid] = node
        self._dir_lookup[key] = iid
        if parent_iid and parent_iid in self._dir_nodes:
            self._dir_nodes[parent_iid].child_dirs.append(iid)
        return iid

    def apply_filter(self, text: str):
        """Filtrerar synliga rader efter filnamn/sökväg/kategori (avsnitt 11)."""
        self._filter_text = text.lower().strip()

        def process_dir(iid) -> bool:
            node = self._dir_nodes[iid]
            visible_any = False
            for item_iid, f in node.files:
                if self._file_matches(f):
                    self.tree.reattach(item_iid, iid, "end")
                    visible_any = True
                else:
                    self.tree.detach(item_iid)
            for child_iid in node.child_dirs:
                if process_dir(child_iid):
                    self.tree.reattach(child_iid, iid, "end")
                    visible_any = True
                else:
                    self.tree.detach(child_iid)
            return visible_any

        roots = [iid for iid, node in self._dir_nodes.items() if node.parent_iid == ""]
        for r in roots:
            if process_dir(r):
                self.tree.reattach(r, "", "end")
            else:
                self.tree.detach(r)

    def _file_matches(self, f) -> bool:
        if not self._filter_text:
            return True
        haystack = f"{f.filename} {f.relative_path} {f.category} {f.extension}".lower()
        return self._filter_text in haystack

    def set_all(self, included: bool):
        for f in self._scanned_files:
            f.included = included
        self._refresh_all_labels()
        self._notify_changed()

    def set_category(self, category: str, included: bool):
        for f in self._scanned_files:
            if f.category == category:
                f.included = included
        self._refresh_all_labels()
        self._notify_changed()

    def get_included_files(self):
        return [f for f in self._scanned_files if f.included]

    def get_all_files(self):
        return list(self._scanned_files)

    def get_categories(self):
        return sorted({f.category for f in self._scanned_files})

    # ------------------------------------------------------------------
    # Internt
    # ------------------------------------------------------------------

    def _gather_files(self, iid):
        """Returnerar [(iid, ScannedFile), ...] för alla filer i ett delträd."""
        node = self._dir_nodes[iid]
        items = list(node.files)
        for child_iid in node.child_dirs:
            items.extend(self._gather_files(child_iid))
        return items

    def _refresh_all_labels(self):
        for iid, f in self._file_items.items():
            mark = CHECKED if f.included else UNCHECKED
            warn = f" {SENSITIVE_MARK}" if f.is_sensitive else ""
            self.tree.item(iid, text=f"{mark} {f.filename}{warn}")

        def compute(iid):
            node = self._dir_nodes[iid]
            included_count = 0
            total_count = 0
            total_size = 0
            for _, f in node.files:
                total_count += 1
                total_size += f.size_bytes
                if f.included:
                    included_count += 1
            for child_iid in node.child_dirs:
                c_inc, c_tot, c_size = compute(child_iid)
                included_count += c_inc
                total_count += c_tot
                total_size += c_size

            if total_count == 0 or included_count == 0:
                mark = UNCHECKED
            elif included_count == total_count:
                mark = CHECKED
            else:
                mark = PARTIAL

            self.tree.item(
                iid,
                text=f"{mark} {node.name}/",
                values=(
                    _human_size(total_size),
                    "",
                    self.localizer.get_text("tree_dir_file_count", n=total_count),
                ),
            )
            return included_count, total_count, total_size

        roots = [iid for iid, node in self._dir_nodes.items() if node.parent_iid == ""]
        for r in roots:
            compute(r)

    def _on_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region != "tree":
            return
        item_iid = self.tree.identify_row(event.y)
        if not item_iid:
            return

        if item_iid in self._file_items:
            f = self._file_items[item_iid]
            f.included = not f.included
            self._refresh_all_labels()
            self._notify_changed()
        elif item_iid in self._dir_nodes:
            files = [f for _, f in self._gather_files(item_iid)]
            all_included = all(f.included for f in files) if files else False
            new_state = not all_included
            for f in files:
                f.included = new_state
            self._refresh_all_labels()
            self._notify_changed()

    def _notify_changed(self):
        if self.on_selection_changed:
            self.on_selection_changed()
