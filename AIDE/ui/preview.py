"""
ui/preview.py

Förhandsgranskningsfönster (avsnitt 15). Visar sammanställning av vad
som kommer inkluderas/exkluderas innan export, samt eventuella
varningar. Visuellt stilmatchad mot huvudfönstret (ui/theme.py).
"""

from __future__ import annotations

from tkinter import ttk

import customtkinter as ctk

from ui import theme


class PreviewWindow(ctk.CTkToplevel):
    def __init__(self, parent, all_files, source_roots, localizer=None):
        super().__init__(parent)

        self.localizer = localizer or getattr(parent, "localizer", None)
        if self.localizer is None:
            from core.localization_core import LocalizationCore
            self.localizer = LocalizationCore()

        self.title(self.localizer.get_text("preview_window_title"))
        self.geometry("760x600")
        self.configure(fg_color=theme.COLOR_BG_MAIN)
        self.transient(parent)

        included = [f for f in all_files if f.included]
        excluded = [f for f in all_files if not f.included]
        total_size = sum(f.size_bytes for f in included)
        sensitive_included = [f for f in included if f.is_sensitive]

        by_category = {}
        for f in included:
            by_category[f.category] = by_category.get(f.category, 0) + 1

        header = ctk.CTkFrame(self, corner_radius=10, fg_color=theme.COLOR_BG_PANEL)
        header.pack(fill="x", padx=12, pady=(12, 6))

        ctk.CTkLabel(
            header, text=self.localizer.get_text("preview_summary"), font=theme.FONT_SECTION,
            text_color=theme.COLOR_TEXT_MUTED,
        ).pack(anchor="w", padx=14, pady=(12, 4))

        def row(text, color=None):
            ctk.CTkLabel(
                header, text=text, font=theme.FONT_UI,
                text_color=color or theme.COLOR_TEXT_PRIMARY, anchor="w",
            ).pack(anchor="w", padx=14, pady=1)

        row(self.localizer.get_text(
            "preview_sources", sources=", ".join(str(s) for s in source_roots)
        ))
        row(self.localizer.get_text("preview_included", n=len(included)))
        row(self.localizer.get_text("preview_excluded", n=len(excluded)))
        row(self.localizer.get_text("preview_total_size", size=_human_size(total_size)))

        cat_text = ", ".join(f"{cat}: {count}" for cat, count in sorted(by_category.items()))
        row(self.localizer.get_text("preview_category_breakdown", breakdown=cat_text or "–"))

        if sensitive_included:
            row(
                self.localizer.get_text("preview_sensitive_warning", n=len(sensitive_included)),
                color=theme.COLOR_RED,
            )

        ctk.CTkFrame(header, fg_color="transparent", height=8).pack()

        # Lista
        list_frame = ctk.CTkFrame(self, corner_radius=10, fg_color=theme.COLOR_BG_PANEL)
        list_frame.pack(fill="both", expand=True, padx=12, pady=(0, 6))

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(
            "Preview.Treeview",
            background=theme.COLOR_BG_PANEL_ALT,
            fieldbackground=theme.COLOR_BG_PANEL_ALT,
            foreground=theme.COLOR_TEXT_PRIMARY,
            borderwidth=0,
            rowheight=22,
            font=theme.FONT_UI,
        )
        style.configure(
            "Preview.Treeview.Heading",
            background=theme.COLOR_BG_PANEL,
            foreground=theme.COLOR_TEXT_MUTED,
            font=theme.FONT_SECTION,
        )

        columns = ("status", "category", "size")
        tree = ttk.Treeview(list_frame, columns=columns, show="tree headings", style="Preview.Treeview")
        tree.heading("#0", text=self.localizer.get_text("preview_col_file"))
        tree.heading("status", text=self.localizer.get_text("preview_col_status"))
        tree.heading("category", text=self.localizer.get_text("preview_col_category"))
        tree.heading("size", text=self.localizer.get_text("preview_col_size"))
        tree.column("#0", width=380)
        tree.column("status", width=110)
        tree.column("category", width=140)
        tree.column("size", width=80, anchor="e")

        tree.pack(side="left", fill="both", expand=True, padx=8, pady=8)

        for f in sorted(all_files, key=lambda x: x.relative_path.lower()):
            status = (
                self.localizer.get_text("preview_status_included")
                if f.included
                else self.localizer.get_text("preview_status_excluded")
            )
            if f.is_sensitive:
                status += " ⚠"
            tree.insert("", "end", text=f.relative_path, values=(status, f.category, f.size_human))

        ctk.CTkButton(
            self, text=self.localizer.get_text("preview_close"), command=self.destroy, width=120,
            fg_color=theme.COLOR_GRAY_DARK, hover_color=theme.COLOR_GRAY,
        ).pack(pady=(0, 12))


def _human_size(size_bytes: int) -> str:
    size = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} {unit}"
        size /= 1024
    return f"{size:.1f} GB"
