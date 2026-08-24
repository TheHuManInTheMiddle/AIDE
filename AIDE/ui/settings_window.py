"""
ui/settings_window.py

Separat inställningsfönster (avsnitt 23). Sparas lokalt via core/settings.py.
Visuellt stilmatchad mot huvudfönstret / G.A.M.E. B.R.I.D.G.E. (ui/theme.py).
"""

from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from core.settings import Settings, save_settings
from ui import theme


class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, parent, settings: Settings, on_saved=None):
        super().__init__(parent)
        self.title("Inställningar — A.I.D.E.")
        self.geometry("600x600")
        self.configure(fg_color=theme.COLOR_BG_MAIN)
        self.settings = settings
        self.on_saved = on_saved
        self.resizable(False, False)
        self.transient(parent)

        frame = ctk.CTkFrame(self, corner_radius=10, fg_color=theme.COLOR_BG_PANEL)
        frame.pack(fill="both", expand=True, padx=12, pady=12)

        ctk.CTkLabel(
            frame, text="INSTÄLLNINGAR", font=theme.FONT_SECTION, text_color=theme.COLOR_TEXT_MUTED,
        ).pack(anchor="w", padx=16, pady=(14, 6))

        def label(text):
            ctk.CTkLabel(frame, text=text, font=theme.FONT_UI, text_color=theme.COLOR_TEXT_PRIMARY).pack(
                anchor="w", padx=16, pady=(10, 2)
            )

        def entry(var):
            e = ctk.CTkEntry(frame, textvariable=var, fg_color=theme.COLOR_BG_PANEL_ALT, width=550)
            e.pack(padx=16, pady=(0, 2), fill="x")
            return e

        label("Ignorerade kataloger (komma-separerat)")
        self.ignore_dirs_var = tk.StringVar(value=", ".join(settings.ignore_dirs))
        entry(self.ignore_dirs_var)

        label("Ignorerade filnamn (komma-separerat)")
        self.ignore_files_var = tk.StringVar(value=", ".join(settings.ignore_files))
        entry(self.ignore_files_var)

        label("Känsliga filmönster (komma-separerat, t.ex. *.pem)")
        self.sensitive_var = tk.StringVar(value=", ".join(settings.sensitive_patterns))
        entry(self.sensitive_var)

        label("Standard-exportformat")
        self.export_format_var = tk.StringVar(value=settings.default_export_format)
        ctk.CTkOptionMenu(
            frame, values=["markdown", "text", "json"], variable=self.export_format_var,
            fg_color=theme.COLOR_GRAY_DARK, button_color=theme.COLOR_GRAY, width=550,
        ).pack(padx=16, pady=(0, 2), fill="x")

        label("Standard-målmapp")
        self.export_dir_var = tk.StringVar(value=settings.default_export_dir)
        entry(self.export_dir_var)

        switch_frame = ctk.CTkFrame(frame, fg_color="transparent")
        switch_frame.pack(fill="x", padx=16, pady=(16, 4))

        self.show_binary_var = tk.BooleanVar(value=settings.show_binary_files)
        self.show_binary_switch = ctk.CTkSwitch(
            switch_frame, text="Visa binärfiler i listan", variable=self.show_binary_var,
            font=theme.FONT_UI, text_color=theme.COLOR_TEXT_PRIMARY, progress_color=theme.COLOR_BLUE,
        )
        self.show_binary_switch.pack(anchor="w", pady=4)

        self.show_hidden_var = tk.BooleanVar(value=settings.show_hidden_files)
        self.show_hidden_switch = ctk.CTkSwitch(
            switch_frame, text="Visa dolda filer/kataloger", variable=self.show_hidden_var,
            font=theme.FONT_UI, text_color=theme.COLOR_TEXT_PRIMARY, progress_color=theme.COLOR_BLUE,
        )
        self.show_hidden_switch.pack(anchor="w", pady=4)

        self.default_checkbox_var = tk.BooleanVar(value=settings.default_checkbox_state)
        self.default_checkbox_switch = ctk.CTkSwitch(
            switch_frame,
            text="Markera icke-känsliga filer automatiskt vid skanning",
            variable=self.default_checkbox_var,
            font=theme.FONT_UI, text_color=theme.COLOR_TEXT_PRIMARY, progress_color=theme.COLOR_GREEN,
        )
        self.default_checkbox_switch.pack(anchor="w", pady=4)

        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=16, pady=(20, 16), side="bottom")
        ctk.CTkButton(
            btn_frame, text="Avbryt", command=self.destroy, width=110,
            fg_color=theme.COLOR_GRAY_DARK, hover_color=theme.COLOR_GRAY,
        ).pack(side="right", padx=(8, 0))
        ctk.CTkButton(
            btn_frame, text="Spara", command=self._save, width=110,
            fg_color=theme.COLOR_GREEN_DARK, hover_color=theme.COLOR_GREEN,
        ).pack(side="right")

    def _save(self):
        def split_csv(s: str) -> list[str]:
            return [x.strip() for x in s.split(",") if x.strip()]

        self.settings.ignore_dirs = split_csv(self.ignore_dirs_var.get())
        self.settings.ignore_files = split_csv(self.ignore_files_var.get())
        self.settings.sensitive_patterns = split_csv(self.sensitive_var.get())
        self.settings.default_export_format = self.export_format_var.get()
        self.settings.default_export_dir = self.export_dir_var.get().strip()
        self.settings.show_binary_files = self.show_binary_var.get()
        self.settings.show_hidden_files = self.show_hidden_var.get()
        self.settings.default_checkbox_state = self.default_checkbox_var.get()

        save_settings(self.settings)
        if self.on_saved:
            self.on_saved(self.settings)
        self.destroy()
