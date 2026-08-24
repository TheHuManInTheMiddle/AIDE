# AIDE – AI Development Export tool

AIDE är ett fristående lokalt desktopverktyg för att samla, granska,
sortera och paketera filer från ett eller flera projekt inför arbete
med externa AI-verktyg (t.ex. att klistra in kod i en chatt) eller för
allmän dokumentation av ett projekts innehåll.

AIDE kräver **ingen internetanslutning** och **ingen extern AI-tjänst**.
Allt sker lokalt på din dator.

---

## 1. Vad AIDE är

AIDE:

1. Låter dig välja en eller flera källmappar.
2. Skannar rekursivt hela katalogträdet (alla undermappar, inte bara
   toppnivån).
3. Klassificerar varje fil (kod, text, konfiguration, webb, dokument,
   bild, binär/okänd).
4. Flaggar potentiellt känsliga filer (t.ex. `.env`, `*.pem`, `*.key`,
   filer med "secret"/"password" i namnet) och avmarkerar dem som
   standard.
5. Låter dig markera/avmarkera enskilda filer eller hela kategorier
   via checkboxar.
6. Låter dig förhandsgranska exakt vad som kommer inkluderas innan
   något skrivs till disk.
7. Bygger ett textbaserat, lättläst paket (Markdown, ren text och/eller
   ett JSON-manifest) som du kan mata in i valfritt AI-verktyg eller
   spara som dokumentation.

AIDE **raderar eller skriver aldrig över dina originalfiler**. All
export sker till en separat mapp du själv väljer.

---

## 2. Installation

Krav: Python 3.10 eller senare, med `tkinter` installerat.

- **Windows / macOS**: `tkinter` följer normalt med standardinstallationen
  av Python från python.org.
- **Linux (Debian/Ubuntu)**: installera vid behov med
  `sudo apt-get install python3-tk`.

Installera projektets beroenden:

```bash
pip install -r requirements.txt
```

> AIDE:s kärnlogik (`core/`, `exporters/`) använder enbart Pythons
> standardbibliotek. Gränssnittet bygger på **CustomTkinter** för att
> visuellt höra ihop med syskonverktyget i samma verktygsfamilj — det
> är fortfarande ett fristående lokalt program utan krav på internet
> vid körning.

---

## 3. Start

Kör från projektets rotmapp:

```bash
python main.py
```

Detta öppnar AIDE:s huvudfönster.

---

## 4. Grundläggande användning

1. Klicka på **"Välj källmapp"** och peka ut den mapp du vill samla
   filer från. Du kan lägga till flera källmappar.
2. Klicka på **"Skanna"**. AIDE går igenom hela katalogträdet och
   visar resultatet som en riktig mappstruktur — precis som i en
   vanlig filhanterare, inte grupperat per filtyp.
3. Varje fil OCH varje mapp har en checkbox. Klicka på en enskild fil
   för att växla dess status, eller klicka direkt på en **mapp** för
   att markera/avmarkera *hela dess delträd* i ett klick — perfekt för
   att snabbt exkludera en hel undermapp du inte vill ha med, utan att
   klicka fil för fil. En mapp visar tre lägen: `☑` (allt markerat),
   `☐` (inget markerat), `◪` (blandat innehåll). Du kan även använda
   **"Markera alla"**, **"Avmarkera alla"**, **"Markera kategori"**
   eller **"Avmarkera kategori"**.
4. Använd filterfältet för att snabbt hitta filer via filnamn, sökväg
   eller kategori.
5. Klicka på **"Välj exportmapp"** och peka ut var paketet ska sparas.
6. Klicka på **"Förhandsgranska"** för att se en sammanställning innan
   du exporterar.
7. Klicka på **"Bygg paket"**. Paketet får automatiskt samma namn som
   din källmapp (t.ex. `mittprojekt.md`) istället för ett generiskt
   filnamn. Vid namnkonflikt med befintliga filer får du välja: skriv
   över, skapa ny version, eller hoppa över.
8. Loggen till höger visar vad som händer, steg för steg.

---

## 5. Filformat

AIDE klassificerar filer i följande kategorier:

| Kategori              | Exempel på filändelser                                   |
|------------------------|-----------------------------------------------------------|
| Kod                    | `.py .js .ts .java .cs .cpp .c .h .hpp .rs .go .php .rb .ps1 .bat .sh` |
| Text                   | `.txt .md .rst .log .csv`                                 |
| Konfiguration/Data     | `.json .jsonl .yaml .yml .toml .ini .xml .env`             |
| Webb                   | `.html .css`                                               |
| Dokument               | `.pdf .docx .odt` (identifieras, men innehållet dumpas inte som text) |
| Bild                   | `.png .jpg .jpeg .webp .gif .svg`                          |
| Binär/Okänd            | Allt annat, eller filer som ser binära ut vid innehållstest |

Listan över textformat som kan paketeras är inte hårdkodad till ett
litet antal filer — arkitekturen (`core/classifier.py`) är byggd för
att enkelt kunna utökas.

---

## 6. Känsliga filer

AIDE flaggar filer som matchar mönster som:

```
.env
credentials.json
secrets.json
*.pem
*.key
*password*
*secret*
```

Dessa filer:

- Visas i listan med en varningsmarkering (`⚠`).
- Är **avmarkerade som standard** — AIDE antar aldrig att en känslig
  fil ska exporteras.
- Kan ändå markeras manuellt av dig om du medvetet vill inkludera dem.

Du kan lägga till eller ta bort mönster under **Inställningar**.

---

## 7. Exportformat

AIDE kan bygga fyra typer av export till din valda exportmapp. Alla
filnamn baseras automatiskt på din källmapps namn (t.ex. `mittprojekt`
för en källmapp som heter `MittProjekt`), inte ett generiskt namn:

- **Markdown** (`<källmapp>.md`) — hela projektet som ett läsbart,
  strukturerat Markdown-dokument med kodblock per fil. Innehåller
  numera automatiskt ett ASCII-filträd (se nedan) direkt efter
  filantalet, så att AI-verktyg och läsare ser strukturen först.
- **Ren text** (`<källmapp>.txt`) — samma struktur, sparad som `.txt`.
- **Endast filträd** (`<källmapp>_tree.md`) — ett fristående,
  lättviktigt dokument med ENBART en ASCII-trädstruktur av de
  markerade filerna, inget filinnehåll. Perfekt för att snabbt
  kommunicera ett projekts struktur, t.ex. i en chatt eller en
  PR-beskrivning, utan att dumpa någon kod. Exempel:

  ```text
  mittprojekt/
  ├── config/
  │   └── settings.json
  ├── src/
  │   ├── core/
  │   │   └── router.py
  │   └── main.py
  └── docs/
      └── README.md
  ```

  Trädet visar bara det som faktiskt är markerat — det är en spegling
  av vad som skulle exporteras, inte en fullständig katalogkarta.
- **JSON-manifest** (`<källmapp>_manifest.json`) — metadata om vilka
  filer som ingår (sökväg, storlek, kategori, känslighetsstatus etc.),
  utan filinnehåll. Manifestet skapas alltid som komplement till
  huvudexporten, oavsett vilket format du valt.

Vid namnkonflikt i exportmappen väljer du mellan:

- **Skriv över** — ersätter den befintliga filen.
- **Skapa ny version** — sparar som t.ex. `mittprojekt (1).md`.
- **Hoppa över** — rör inte den befintliga filen alls.

AIDE skriver aldrig till, eller rör, filer utanför den valda
exportmappen.

### Ingen lokal sökvägsinformation läcker ut i exporten

Paketet du bygger är tänkt att klistras in i externa verktyg (chattar,
andra AI-modeller, delade dokument). Därför skriver AIDE **aldrig ut
en fullständig lokal sökväg** — varken i Markdown-paketet, textpaketet
eller JSON-manifestet. Bara källmappens *namn* (t.ex. `MittProjekt`)
tas med, aldrig `C:\Users\ditt-namn\Desktop\...` eller motsvarande.
Det gäller oavsett hur djupt källmappen ligger i din mappstruktur.

---

## 8. Inställningar

Under **Inställningar** kan du styra:

- Vilka kataloger som ska ignoreras vid skanning (standard: `.git`,
  `__pycache__`, `node_modules`, `venv`, `.venv`, `.idea`, `.vscode`,
  `bin`, `obj`, `build`, `dist`).
- Vilka enskilda filnamn som ska ignoreras.
- Mönster för känsliga filer.
- Standard-exportformat och standard-exportmapp.
- Om binärfiler och dolda filer/kataloger ska visas i listan.
- Om filer ska vara markerade eller avmarkerade som standard efter
  en skanning (känsliga filer är alltid avmarkerade oavsett detta val).

Inställningarna sparas lokalt (i din användarprofils
konfigurationsmapp) och laddas automatiskt nästa gång AIDE startas.

---

## 9. Projektstruktur

```text
AIDE/
├── main.py                    # startpunkt
├── requirements.txt
├── README.md
├── docs/
│   └── PLUGIN_GUIDE.md          # fristående guide för att bygga plugins
├── core/
│   ├── scanner.py              # rekursiv katalogskanning
│   ├── classifier.py           # filklassificering + känslighetsdetektion
│   ├── package_builder.py      # bygger paketets textinnehåll
│   ├── manifest.py             # bygger JSON-manifestet
│   ├── security.py             # konflikthantering, säker exportväg
│   ├── settings.py             # läsning/sparning av inställningar
│   ├── plugin_base.py          # publikt, stabilt plugin-kontrakt (AIDEPlugin)
│   ├── plugin_loader.py        # dynamisk pluginupptäckt från plugins/
│   └── tree_renderer.py        # ASCII-filträdsgenerering
├── ui/
│   ├── theme.py                 # delad färgpalett/typografi
│   ├── main_window.py          # huvudfönster, knappar, trådhantering
│   ├── file_tree.py            # hierarkiskt mappträd med checkboxar och filter
│   ├── preview.py              # förhandsgranskningsfönster
│   └── settings_window.py      # inställningsfönster
├── exporters/
│   ├── markdown_exporter.py
│   ├── text_exporter.py
│   ├── tree_exporter.py
│   └── json_exporter.py
├── plugins/
│   └── example_plugin/
│       └── main_plugin.py      # körbar referensimplementation
└── tests/
    ├── test_scanner.py
    ├── test_classifier.py
    ├── test_export.py
    ├── test_plugin_loader.py
    └── test_tree_renderer.py
```

GUI, filanalys och export är medvetet separerade: `ui/`-modulerna
anropar bara funktioner i `core/` och `exporters/`, aldrig tvärtom.

---

## 10. Testning

Kör hela testsviten med:

```bash
pip install -r requirements.txt
pytest tests/ -v
```

Testerna täcker bland annat:

- rekursiv katalogskanning (inklusive ignorerade kataloger)
- filklassificering (kod, text, bild, binär, okänd)
- UTF-8-filnamn och internationella tecken
- tomma kataloger
- oläsbara filer (felhantering utan krasch)
- upptäckt av känsliga filer, även dolda som `.env`
- avbruten skanning
- Markdown-, text- och JSON-manifest-export
- konflikthantering vid befintlig exportfil (skriv över / ny version /
  hoppa över)
- att export aldrig kan hamna utanför vald exportmapp

---

## 11. Begränsningar

- Binärfiler (bilder, exe, databaser, dokumentformat som `.pdf`/`.docx`)
  inkluderas i nuläget endast som metadata/platshållare i paketet, inte
  som faktiskt filinnehåll.
- Automatisk textextraktion ur `.pdf`/`.docx` (t.ex. för att inkludera
  brödtext i paketet) är inte implementerad i denna version.
- Pluginsystemet (se `docs/PLUGIN_GUIDE.md`) laddar just nu alla
  plugins i `plugins/`-katalogen automatiskt vid uppstart — det finns
  ännu ingen inställning för att välja bort enskilda plugins.
- GUI:t är byggt med CustomTkinter för att vara helt fristående utan
  externa GUI-beroenden utöver det ena paketet; det är funktionellt
  men medvetet enkelt i sin visuella utformning.

---

## 12. Framtida utveckling

Pluginsystemet finns nu (se `docs/PLUGIN_GUIDE.md`), men möjliga
nästa steg utöver det:

- Riktig innehållsextraktion för dokumentformat (PDF/DOCX) som en
  valbar exportvariant.
- Möjlighet att spara/ladda "profiler" (kombinationer av källor,
  filter och urval) för återkommande projekt.
- Drag-and-drop av mappar direkt i huvudfönstret.
- Alternativ export som inkluderar binärfiler som faktiska bifogade
  filer (kopierade, inte inline-text) i exportmappen.
- En inställningspanel i GUI:t som listar installerade plugins och
  låter användaren aktivera/inaktivera dem individuellt (idag laddas
  alla plugins i `plugins/`-katalogen automatiskt).
- Zip-arkiv som virtuell källmapp (packa upp och skanna in innehållet
  utan manuellt extraheringssteg) samt riktig textextraktion ur PDF —
  medvetet nedprioriterat för närvarande.

---

## 13. Ändringslogg (utvalt)

- **Säkerhetsfix:** tidigare versioner skrev källmappens *fullständiga
  absoluta sökväg* rakt in i exportfilerna (Markdown, text och
  JSON-manifest) under rubriken "SOURCE ROOTS". Det innebar att
  användarnamn och lokal mappstruktur kunde läcka ut i paket tänkta
  att delas eller klistras in i externa AI-verktyg. Från och med denna
  version skrivs bara källmappens *namn* ut, aldrig dess fulla sökväg
  — se avsnitt 7.
- Exportfilnamn baseras nu på källmappens namn (`<källmapp>.md` etc.)
  istället för ett generiskt `project_package.md`.
- Filträdet är omgjort från kategorigruppering till en riktig
  hierarkisk mappstruktur, med klickbara checkboxar på mappnivå för
  att exkludera hela delträd i ett klick (se avsnitt 4).
- Nytt: ASCII-filträd, både inbakat automatiskt i Markdown/text-
  paketet och som ett eget fristående exportformat ("Endast filträd").
  Litet tillägg jag (Claude) lade till utöver det uttryckligen
  begärda: en genererad-tidsstämpel längst ner i trädexporten, så den
  är lätt att se är färsk vid en snabb blick.
