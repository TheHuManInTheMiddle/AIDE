"""
ui/settings_window.py

Separat inställningsfönster (avsnitt 23). Sparas lokalt via core/settings.py.
Visuellt stilmatchad mot huvudfönstret / G.A.M.E. B.R.I.D.G.E. (ui/theme.py).

Lokalisering: återanvänder huvudfönstrets LocalizationCore-instans
(via parent.localizer) istället för att skapa en egen — så språkvalet
alltid är konsekvent mellan fönstren. Faller tillbaka på en egen
instans om fönstret av någon anledning öppnas utan en förälder som
har en localizer (t.ex. i tester), så modulen aldrig kraschar bara
för att den körs fristående.

Genvägar: visar AIDE:s ombindningsbara genvägar (core/hotkey_utils.py)
och låter användaren spela in en ny tangentkombination per kommando.
Ändringar sparas lokalt i fönstret och committas till settings.hotkeys
först vid "Spara", precis som alla andra fält i det här fönstret.
"""

from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from core.hotkey_utils import HotkeyCapture, format_shortcut_for_display
from core.settings import Settings, save_settings
from ui import theme

# Vilka locales.json-nycklar som ska användas som visningsnamn för
# respektive ombindningsbart kommando i settings.hotkeys. Återanvänder
# huvudfönstrets egna knapptextnycklar så namnen alltid är konsekventa.
HOTKEY_COMMAND_LABEL_KEYS = {
    "scan": "btn_scan",
    "build_package": "btn_build_package",
    "preview": "btn_preview",
}

# Visningsnamn för språkväljaren. Medvetet tvåspråkiga etiketter här
# (inte lokaliserade via get_text) eftersom det här ÄR språkvalet
# självt — ett hönan/ägget-problem att lokalisera den egna kontrollen
# för att byta språk.
LANGUAGE_DISPLAY_NAMES = {
    "": "Automatiskt (systemspråk) / Auto (system language)",
    "sv": "Svenska",
    "en": "English",
}


class SettingsWindow(ctk.CTkToplevel):
    def __init__(
        self,
        parent,
        settings: Settings,
        on_saved=None,
        localizer=None,
        available_formats: list[str] | None = None,
    ):
        super().__init__(parent)

        self.localizer = localizer or getattr(parent, "localizer", None)
        if self.localizer is None:
            from core.localization_core import LocalizationCore
            self.localizer = LocalizationCore(forced_lang=settings.language or None)

        self.title(self.localizer.get_text("settings_window_title"))
        self.geometry("600x640")
        self.minsize(520, 420)
        self.configure(fg_color=theme.COLOR_BG_MAIN)
        self.settings = settings
        self.on_saved = on_saved
        self.resizable(True, True)
        self.transient(parent)

        # Lokal arbetskopia av genvägarna — committas till self.settings
        # först vid "Spara", precis som resten av fönstrets fält.
        self._hotkeys_working = {k: dict(v) for k, v in settings.hotkeys.items()}
        self._hotkey_capture = HotkeyCapture(self)
        self._hotkey_value_labels: dict[str, ctk.CTkLabel] = {}
        self._hotkey_rebind_buttons: dict[str, ctk.CTkButton] = {}

        # Knappraden packas FÖRST och med side="bottom" direkt på
        # fönstret (inte i den scrollbara ytan) — den reserverar sin
        # plats innan resten av innehållet läggs till, så Spara/Avbryt
        # alltid syns oavsett hur mycket annat innehåll fönstret får
        # (t.ex. fler genvägar i en framtida version). Tidigare låg allt
        # i en enda ej-scrollbar CTkFrame med fast fönsterhöjd, vilket
        # gjorde att knapparna helt enkelt hamnade utanför synligt
        # område när genvägssektionen lades till — knapparna fanns i
        # koden men gick aldrig att nå.
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=16, pady=(8, 12), side="bottom")
        ctk.CTkButton(
            btn_frame, text=self.localizer.get_text("settings_cancel"), command=self.destroy, width=110,
            fg_color=theme.COLOR_GRAY_DARK, hover_color=theme.COLOR_GRAY,
        ).pack(side="right", padx=(8, 0))
        ctk.CTkButton(
            btn_frame, text=self.localizer.get_text("settings_save"), command=self._save, width=110,
            fg_color=theme.COLOR_GREEN_DARK, hover_color=theme.COLOR_GREEN,
        ).pack(side="right")

        frame = ctk.CTkScrollableFrame(self, corner_radius=10, fg_color=theme.COLOR_BG_PANEL)
        frame.pack(fill="both", expand=True, padx=12, pady=(12, 0))

        ctk.CTkLabel(
            frame, text=self.localizer.get_text("settings_header"),
            font=theme.FONT_SECTION, text_color=theme.COLOR_TEXT_MUTED,
        ).pack(anchor="w", padx=16, pady=(14, 6))

        def label(text):
            ctk.CTkLabel(frame, text=text, font=theme.FONT_UI, text_color=theme.COLOR_TEXT_PRIMARY).pack(
                anchor="w", padx=16, pady=(10, 2)
            )

        def entry(var):
            e = ctk.CTkEntry(frame, textvariable=var, fg_color=theme.COLOR_BG_PANEL_ALT, width=550)
            e.pack(padx=16, pady=(0, 2), fill="x")
            return e

        # --- Språk ------------------------------------------------------

        label(self.localizer.get_text("settings_language"))
        current_display = LANGUAGE_DISPLAY_NAMES.get(
            settings.language, LANGUAGE_DISPLAY_NAMES[""]
        )
        self.language_var = tk.StringVar(value=current_display)
        language_menu = ctk.CTkOptionMenu(
            frame, values=list(LANGUAGE_DISPLAY_NAMES.values()),
            command=self.language_var.set,
            fg_color=theme.COLOR_GRAY_DARK, button_color=theme.COLOR_GRAY, width=550,
        )
        language_menu.set(current_display)
        language_menu.pack(padx=16, pady=(0, 2), fill="x")

        # --- Filhantering -------------------------------------------------

        label(self.localizer.get_text("settings_ignore_dirs"))
        self.ignore_dirs_var = tk.StringVar(value=", ".join(settings.ignore_dirs))
        entry(self.ignore_dirs_var)

        label(self.localizer.get_text("settings_ignore_files"))
        self.ignore_files_var = tk.StringVar(value=", ".join(settings.ignore_files))
        entry(self.ignore_files_var)

        label(self.localizer.get_text("settings_sensitive_patterns"))
        self.sensitive_var = tk.StringVar(value=", ".join(settings.sensitive_patterns))
        entry(self.sensitive_var)

        label(self.localizer.get_text("settings_default_format"))
        self.export_format_var = tk.StringVar(value=settings.default_export_format)

        # Dynamiskt: kommer från MainWindow:s faktiska plugin-register
        # (_available_export_formats()), inte en hårdkodad lista här —
        # så nya exportformat från plugins (zip, pdf, report, och vad
        # Gemini än hittar på framöver) dyker upp automatiskt utan att
        # den här filen behöver ändras varje gång.
        format_values = list(available_formats) if available_formats else ["markdown", "text", "tree", "json"]
        if settings.default_export_format not in format_values:
            # Ett tidigare sparat format vars plugin inte är installerad
            # just nu (eller är avstängd) — visa det ändå istället för
            # att tyst byta bort användarens val i bakgrunden.
            format_values = [settings.default_export_format] + format_values

        format_menu = ctk.CTkOptionMenu(
            frame, values=format_values,
            command=self.export_format_var.set,
            fg_color=theme.COLOR_GRAY_DARK, button_color=theme.COLOR_GRAY, width=550,
        )
        format_menu.set(settings.default_export_format)
        format_menu.pack(padx=16, pady=(0, 2), fill="x")

        label(self.localizer.get_text("settings_default_export_dir"))
        self.export_dir_var = tk.StringVar(value=settings.default_export_dir)
        entry(self.export_dir_var)

        switch_frame = ctk.CTkFrame(frame, fg_color="transparent")
        switch_frame.pack(fill="x", padx=16, pady=(16, 4))

        self.show_binary_var = tk.BooleanVar(value=settings.show_binary_files)
        self.show_binary_switch = ctk.CTkSwitch(
            switch_frame, text=self.localizer.get_text("settings_show_binary"), variable=self.show_binary_var,
            font=theme.FONT_UI, text_color=theme.COLOR_TEXT_PRIMARY, progress_color=theme.COLOR_BLUE,
        )
        self.show_binary_switch.pack(anchor="w", pady=4)

        self.show_hidden_var = tk.BooleanVar(value=settings.show_hidden_files)
        self.show_hidden_switch = ctk.CTkSwitch(
            switch_frame, text=self.localizer.get_text("settings_show_hidden"), variable=self.show_hidden_var,
            font=theme.FONT_UI, text_color=theme.COLOR_TEXT_PRIMARY, progress_color=theme.COLOR_BLUE,
        )
        self.show_hidden_switch.pack(anchor="w", pady=4)

        self.default_checkbox_var = tk.BooleanVar(value=settings.default_checkbox_state)
        self.default_checkbox_switch = ctk.CTkSwitch(
            switch_frame,
            text=self.localizer.get_text("settings_default_checkbox"),
            variable=self.default_checkbox_var,
            font=theme.FONT_UI, text_color=theme.COLOR_TEXT_PRIMARY, progress_color=theme.COLOR_GREEN,
        )
        self.default_checkbox_switch.pack(anchor="w", pady=4)

        # --- Tangentbordsgenvägar ------------------------------------------

        label(self.localizer.get_text("settings_hotkeys_header"))
        hotkeys_frame = ctk.CTkFrame(frame, fg_color=theme.COLOR_BG_PANEL_ALT, corner_radius=8)
        hotkeys_frame.pack(padx=16, pady=(0, 4), fill="x")

        for command_name, label_key in HOTKEY_COMMAND_LABEL_KEYS.items():
            self._build_hotkey_row(hotkeys_frame, command_name, label_key)

    # ------------------------------------------------------------------
    # Tangentbordsgenvägar
    # ------------------------------------------------------------------

    def _build_hotkey_row(self, parent, command_name: str, label_key: str) -> None:
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=6)

        ctk.CTkLabel(
            row, text=self.localizer.get_text(label_key), font=theme.FONT_UI,
            text_color=theme.COLOR_TEXT_PRIMARY, width=180, anchor="w",
        ).pack(side="left")

        current = self._hotkeys_working.get(command_name, {})
        value_label = ctk.CTkLabel(
            row,
            text=format_shortcut_for_display(current.get("modifiers", []), current.get("key", "")),
            font=theme.FONT_MONO, text_color=theme.COLOR_TEXT_MUTED, width=140, anchor="w",
        )
        value_label.pack(side="left", padx=(0, 10))
        self._hotkey_value_labels[command_name] = value_label

        rebind_btn = ctk.CTkButton(
            row, text="⌨", width=44, fg_color=theme.COLOR_GRAY_DARK, hover_color=theme.COLOR_GRAY,
            command=lambda: self._start_hotkey_capture(command_name),
        )
        rebind_btn.pack(side="right")
        self._hotkey_rebind_buttons[command_name] = rebind_btn

    def _start_hotkey_capture(self, command_name: str) -> None:
        button = self._hotkey_rebind_buttons[command_name]
        value_label = self._hotkey_value_labels[command_name]

        def _on_captured(modifiers: list[str], key: str) -> None:
            self._hotkeys_working[command_name] = {"modifiers": modifiers, "key": key}
            value_label.configure(text=format_shortcut_for_display(modifiers, key))
            button.configure(text="⌨", state="normal")

        button.configure(text="...", state="disabled")
        self._hotkey_capture.capture_next(on_captured=_on_captured)

    # ------------------------------------------------------------------
    # Spara
    # ------------------------------------------------------------------

    def _save(self):
        def split_csv(s: str) -> list[str]:
            return [x.strip() for x in s.split(",") if x.strip()]

        reverse_language_map = {v: k for k, v in LANGUAGE_DISPLAY_NAMES.items()}

        self.settings.ignore_dirs = split_csv(self.ignore_dirs_var.get())
        self.settings.ignore_files = split_csv(self.ignore_files_var.get())
        self.settings.sensitive_patterns = split_csv(self.sensitive_var.get())
        self.settings.default_export_format = self.export_format_var.get()
        self.settings.default_export_dir = self.export_dir_var.get().strip()
        self.settings.show_binary_files = self.show_binary_var.get()
        self.settings.show_hidden_files = self.show_hidden_var.get()
        self.settings.default_checkbox_state = self.default_checkbox_var.get()
        self.settings.language = reverse_language_map.get(self.language_var.get(), "")
        self.settings.hotkeys = {k: dict(v) for k, v in self._hotkeys_working.items()}

        save_settings(self.settings)
        if self.on_saved:
            self.on_saved(self.settings)
        self.destroy()
