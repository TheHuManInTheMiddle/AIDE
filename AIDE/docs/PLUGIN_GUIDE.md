# Bygga en plugin för A.I.D.E.

**Den här guiden är fristående.** Du behöver inte tillgång till AIDE:s
fullständiga källkod för att bygga en fungerande plugin — bara den här
filen, plus de två små kodstyckena som citeras nedan (`AIDEPlugin` och
`PluginFileInfo`). Om du implementerar mot kontraktet som beskrivs här
kommer din plugin att fungera när den släpps i en AIDE-installation.

---

## 1. Vad är AIDE?

AIDE (**A**rchive · **I**dentify · **D**etermine · **E**xport) är ett
lokalt, fristående desktopverktyg som:

1. **Archive** — samlar filer från en eller flera valda källmappar
   (rekursiv katalogskanning).
2. **Identify** — klassificerar varje fil (kod, text, konfiguration,
   bild, dokument, binär, okänd) och flaggar potentiellt känsliga
   filer.
3. **Determine** — låter användaren avgöra, via checkboxar, exakt
   vilka filer som ska ingå i slutresultatet.
4. **Export** — bygger ett färdigt paket (Markdown/text/JSON, eller ett
   format din plugin lägger till) till en mapp användaren själv valt.

En plugin hakar in i just dessa fyra faser — se avsnitt 3.

---

## 2. Var en plugin bor

```text
AIDE/
└── plugins/
    └── mitt_plugin_namn/       ← valfritt mappnamn, ingen konfigfil krävs
        └── main_plugin.py       ← MÅSTE heta exakt så
```

AIDE skannar `plugins/`-katalogen vid uppstart. Varje undermapp som
innehåller en fil `main_plugin.py` med minst en klass som ärver
`AIDEPlugin` laddas automatiskt. Inget registreringssteg, inget
manifest, ingen konfiguration krävs för att en plugin ska hittas.

En trasig plugin (t.ex. ett Python-undantag vid import) loggas och
hoppas över — den kraschar aldrig AIDE eller hindrar andra plugins
från att laddas.

---

## 3. Kontraktet: `AIDEPlugin`

Det här är hela gränsytan. Din pluginklass ärver `AIDEPlugin` och
behöver bara implementera `plugin_name` — allt annat är valfritt att
skriva över.

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, Optional


@dataclass(frozen=True)
class PluginFileInfo:
    """Skrivskyddad, stabil vy av en fil som AIDE skickar till plugins."""
    relative_path: str      # t.ex. "src/core/router.py"
    absolute_path: str      # fullständig sökväg på disk
    filename: str           # t.ex. "router.py"
    extension: str          # t.ex. ".py" (inkl. punkt, gemener)
    category: str           # AIDE:s kategori, t.ex. "Kod", "Text", "Okänd"
    size_bytes: int
    is_sensitive: bool      # flaggad av AIDE:s inbyggda känslighetsdetektion
    is_binary: bool


class AIDEPlugin(ABC):

    @property
    @abstractmethod
    def plugin_name(self) -> str:
        """Kort, unikt visningsnamn, t.ex. 'Min Export-plugin'."""
        raise NotImplementedError

    @property
    def plugin_version(self) -> str:
        return "0.1.0"

    # --- Livscykel ---

    def initialize(self) -> None:
        """Anropas en gång direkt efter att AIDE laddat pluginet."""
        pass

    def shutdown(self) -> None:
        """Anropas vid programavslut. Får aldrig kasta ett undantag."""
        pass

    # --- Identify-fasen ---

    def on_classify(self, file_info: PluginFileInfo) -> Optional[dict]:
        """
        Anropas för varje fil som AIDE:s inbyggda klassificerare gav
        kategorin "Okänd". Returnera None för att inte påverka den,
        eller en dict:
            {"category": "...", "language": "...", "is_sensitive": bool}
        """
        return None

    # --- Determine-fasen ---

    def on_scan_complete(self, files: list[PluginFileInfo]) -> None:
        """Informativ hook efter en skanning. Returvärdet ignoreras."""
        pass

    def on_before_export(
        self, files: list[PluginFileInfo]
    ) -> Optional[list[PluginFileInfo]]:
        """
        Anropas med de filer användaren markerat, precis innan export.
        Returnera None för att inte påverka urvalet, eller en ny
        (filtrerad/omordnad) lista. Får INTE skriva/radera filer här.
        """
        return None

    # --- Export-fasen ---

    def get_exporters(self) -> dict[str, Callable]:
        """
        Registrera egna exportformat: {"formatnamn": exportfunktion}.
        "formatnamn" dyker upp i AIDE:s format-väljare.
        Se signatur för exportfunktionen i avsnitt 5.
        """
        return {}
```

**Namnen `markdown`, `text` och `json` är reserverade** (AIDE:s
inbyggda format). Om din plugin registrerar ett format med något av
de namnen ignoreras det och en varning loggas.

---

## 4. Minimalt exempel

```python
# plugins/hello_plugin/main_plugin.py

from core.plugin_base import AIDEPlugin, PluginFileInfo


class HelloPlugin(AIDEPlugin):

    @property
    def plugin_name(self) -> str:
        return "Hello Plugin"

    def on_scan_complete(self, files: list[PluginFileInfo]) -> None:
        print(f"[Hello Plugin] Skanningen hittade {len(files)} filer.")
```

Det räcker för att pluginet ska upptäckas, laddas och köras vid nästa
skanning. Lägg mappen `hello_plugin/` i AIDE:s `plugins/`-katalog och
starta om AIDE.

> **Import-sökväg:** `from core.plugin_base import ...` fungerar
> eftersom din plugin körs med AIDE:s projektrot på Pythons
> sökväg — precis som vilken annan modul i AIDE som helst. Du behöver
> inte kopiera in `plugin_base.py` själv.

---

## 5. Bygga ett eget exportformat

Detta är den vanligaste typen av plugin: ett nytt sätt att paketera
de markerade filerna.

```python
def mitt_exportformat(
    project_name: str,
    source_roots: list[str],
    included_files: list[PluginFileInfo],
    export_dir: str,
    conflict_strategy,   # se avsnitt 6
    log_callback,        # Callable[[str], None] — skriv till AIDE:s logg
) -> str | None:
    """
    Bygg och skriv ditt paket. Returnera den skrivna sökvägen,
    eller None om inget skrevs (t.ex. vid "hoppa över"-konflikt).
    """
    ...
```

Registrera den i din plugin:

```python
class MittPlugin(AIDEPlugin):
    @property
    def plugin_name(self) -> str:
        return "Mitt Plugin"

    def get_exporters(self):
        return {"mitt_format": mitt_exportformat}
```

`"mitt_format"` dyker nu upp som ett valbart alternativ i AIDE:s
exportformat-väljare i huvudfönstret.

### Fullständigt, körbart exempel

AIDE levereras med `plugins/example_plugin/main_plugin.py` som en
referensimplementation — den visar alla fyra hooks i praktiken
(omklassificering av en filändelse, loggning vid skanning,
storleksfiltrering före export, och ett eget litet exportformat kallat
`"shout"`). Läs den filen som ett komplett, testat exempel att kopiera
och bygga vidare på.

---

## 6. Säkerhetsregler för plugins

AIDE:s grundprincip är att aldrig radera eller skriva över filer
automatiskt (se AIDE:s README, avsnitt "Vad AIDE är"). Din plugin
måste följa samma princip:

1. **Skriv aldrig utanför `export_dir`.** Bygg alltid din målsökväg
   inom den mapp AIDE skickar in.
2. **Respektera `conflict_strategy`.** Det är ett `ConflictStrategy`-
   objekt med tre möjliga lägen: skriv över, skapa ny version, eller
   hoppa över. Din exportfunktion ansvarar själv för att hantera det
   fall att målfilen redan finns — annars riskerar du att tysta
   skriva över användarens data.
3. **Rör aldrig `file_info.absolute_path` destruktivt.** Du får läsa
   från källfilerna, men aldrig radera, flytta eller skriva till dem.
4. **Krascha aldrig tyst.** Om något går fel, skriv till
   `log_callback(...)` och returnera `None` istället för att låta ett
   undantag brisera ut — AIDE fångar oväntade undantag defensivt, men
   ett tydligt loggmeddelande är mycket mer användbart för
   slutanvändaren än en stacktrace.
5. **Anta aldrig att du är den enda pluginet.** Flera plugins kan vara
   installerade samtidigt. `on_classify` använder första
   icke-`None`-svaret; skriv din hook så att den bara reagerar på
   filtyper/mönster du faktiskt känner igen.

---

## 7. Testa din plugin fristående

Du behöver inte hela AIDE-applikationen för att testa kontraktet:

```python
from core.plugin_loader import discover_plugins

plugins = discover_plugins("./plugins")
assert "Mitt Plugin" in plugins

plugin = plugins["Mitt Plugin"]
plugin.initialize()
# ... anropa hooks direkt med egenhändigt konstruerade PluginFileInfo-objekt
```

Se `tests/test_plugin_loader.py` i AIDE-projektet för fler exempel på
hur pluginladdningen kan testas isolerat, inklusive hur en trasig
plugin hanteras utan att krascha resten.

---

## 8. Checklista innan leverans

- [ ] `plugin_name` är unikt och beskrivande.
- [ ] Inga skriv-/raderingsoperationer sker utanför `export_dir`.
- [ ] `conflict_strategy` hanteras korrekt i alla egna exportfunktioner.
- [ ] Inga oväntade undantag läcker ut okontrollerat — fel loggas via
      `log_callback` där det är relevant.
- [ ] Pluginet fungerar även om det är det enda pluginet installerat
      OCH om flera andra plugins är installerade samtidigt.
- [ ] Testat mot `core.plugin_loader.discover_plugins(...)` fristående,
      utan att starta hela GUI:t.

---

Lycka till! Kontraktet ovan (`AIDEPlugin` + `PluginFileInfo`) är allt
du behöver — resten av AIDE:s interna implementation kan ändras fritt
utan att din plugin går sönder, så länge du håller dig till det.
