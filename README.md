# AIDE – AI Development Export Tool

AIDE is a standalone local desktop tool for collecting, reviewing,
sorting, and packaging files from one or more projects for use with
external AI tools (for example, pasting code into a chat) or for
general project documentation.

AIDE requires **no internet connection** and **no external AI service**.
Everything happens locally on your computer.

---

## 1. What AIDE Is

AIDE:

1. Lets you select one or more source folders.
2. Recursively scans the entire directory tree (all subdirectories,
   not just the top level).
3. Classifies every file (code, text, configuration, web, document,
   image, binary/unknown).
4. Flags potentially sensitive files (such as `.env`, `*.pem`, `*.key`,
   and files containing "secret" or "password" in their name) and
   leaves them unchecked by default.
5. Lets you select or deselect individual files or entire categories
   using checkboxes.
6. Lets you preview exactly what will be included before anything is
   written to disk.
7. Builds a text-based, human-readable package (Markdown, plain text
   and/or a JSON manifest) that can be supplied to any AI tool or saved
   as project documentation.

AIDE **never deletes or overwrites your original files**. All exports
are written to a separate folder that you choose.

---

## 2. Installation

Requirements: Python 3.10 or later, with `tkinter` installed.

* **Windows / macOS**: `tkinter` is normally included with the standard
  Python installation from python.org.
* **Linux (Debian/Ubuntu)**: install it if needed with:

```bash
sudo apt-get install python3-tk
```

Install the project's dependencies:

```bash
pip install -r requirements.txt
```

> AIDE's core logic (`core/`, `exporters/`) uses only Python's standard
> library. The interface is built with **CustomTkinter** to visually
> match the sibling tools in the same tool family — it remains a
> standalone local application with no internet requirement at runtime.

---

## 3. Starting AIDE

Run from the project's root folder:

```bash
python main.py
```

This opens AIDE's main window.

---

## 4. Basic Usage

1. Click **"Choose source folder"** and select the folder containing
   the files you want to collect. You can add multiple source folders.
2. Click **"Scan"**. AIDE scans the entire directory tree and displays
   the result as a real folder structure — just like a normal file
   manager, rather than grouping files by type.
3. Every file AND every folder has a checkbox. Click an individual file
   to toggle its selection, or click directly on a **folder** to
   select/deselect *its entire subtree* with one click — useful for
   quickly excluding an entire subfolder without clicking file by file.
   A folder has three states: `☑` (everything selected), `☐` (nothing
   selected), and `◪` (partially selected). You can also use
   **"Select All"**, **"Deselect All"**, **"Select Category"**, or
   **"Deselect Category"**.
4. Use the filter field to quickly find files by filename, path, or
   category.
5. Click **"Choose export folder"** and select where the package should
   be saved.
6. Click **"Preview"** to review what will be exported.
7. Click **"Build Package"**. The package automatically uses the same
   name as your source folder (for example, `myproject.md`) instead of
   a generic filename. If a file with the same name already exists,
   you can choose to overwrite it, create a new version, or skip it.
8. The log on the right shows what is happening step by step.

---

## 5. File Formats

AIDE classifies files into the following categories:

| Category           | Example file extensions                                                |
| ------------------ | ---------------------------------------------------------------------- |
| Code               | `.py .js .ts .java .cs .cpp .c .h .hpp .rs .go .php .rb .ps1 .bat .sh` |
| Text               | `.txt .md .rst .log .csv`                                              |
| Configuration/Data | `.json .jsonl .yaml .yml .toml .ini .xml .env`                         |
| Web                | `.html .css`                                                           |
| Documents          | `.pdf .docx .odt` (identified, but content is not dumped as text)      |
| Images             | `.png .jpg .jpeg .webp .gif .svg`                                      |
| Binary/Unknown     | Everything else, or files that appear binary during content testing    |

The list of text formats that can be packaged is not hard-coded to a
small set of file types — the architecture (`core/classifier.py`) is
designed to be easily extended.

---

## 6. Sensitive Files

AIDE flags files matching patterns such as:

```text
.env
credentials.json
secrets.json
*.pem
*.key
*password*
*secret*
```

These files:

* Are shown in the file list with a warning indicator (`⚠`).
* Are **unchecked by default** — AIDE never assumes that a sensitive
  file should be exported.
* Can still be selected manually if you deliberately want to include
  them.

You can add or remove patterns under **Settings**.

---

## 7. Export Formats

AIDE can build four types of exports in your selected export folder.
All filenames are automatically based on the name of your source
folder (for example, `myproject` for a source folder named
`MyProject`) rather than a generic filename:

* **Markdown** (`<source-folder>.md`) — the entire project as a
  readable, structured Markdown document with a code block for each
  file. It now automatically includes an ASCII file tree directly
  after the file count, so AI tools and readers see the project
  structure first.
* **Plain text** (`<source-folder>.txt`) — the same structure saved
  as a `.txt` file.
* **File tree only** (`<source-folder>_tree.md`) — a lightweight,
  standalone document containing ONLY an ASCII tree structure of the
  selected files, with no file contents. Useful for quickly
  communicating a project's structure, for example in a chat or PR
  description, without dumping any code. Example:

```text
myproject/
├── config/
│   └── settings.json
├── src/
│   ├── core/
│   │   └── router.py
│   └── main.py
└── docs/
    └── README.md
```

The tree shows only what is actually selected — it is a reflection
of what would be exported, not a complete directory map.

* **JSON manifest** (`<source-folder>_manifest.json`) — metadata about
  the included files (path, size, category, sensitivity status, etc.),
  without file contents. The manifest is always created as a companion
  to the main export, regardless of which format you choose.

When a filename conflict occurs in the export folder, you can choose:

* **Overwrite** — replaces the existing file.
* **Create New Version** — saves as something like
  `myproject (1).md`.
* **Skip** — leaves the existing file completely untouched.

AIDE never writes to or modifies files outside the selected export
folder.

### No Local Path Information Leaks into Exports

The package you build is intended to be pasted into external tools
(chats, other AI models, shared documents). Therefore, AIDE **never
writes a complete local filesystem path** into the export — neither
in the Markdown package, the text package, nor the JSON manifest.

Only the *name* of the source folder (for example, `MyProject`) is
included. AIDE never includes paths such as
`C:\Users\your-name\Desktop\...` or their equivalents.

This applies regardless of how deeply the source folder is located
within your directory structure.

---

## 8. Settings

Under **Settings**, you can control:

* Which directories should be ignored during scanning (default:
  `.git`, `__pycache__`, `node_modules`, `venv`, `.venv`, `.idea`,
  `.vscode`, `bin`, `obj`, `build`, `dist`).
* Which individual filenames should be ignored.
* Patterns for sensitive files.
* The default export format and default export folder.
* Whether binary files and hidden files/directories should be shown
  in the list.
* Whether files should be selected or deselected by default after a
  scan (sensitive files are always deselected regardless of this
  setting).

Settings are stored locally (in your user profile's configuration
directory) and automatically loaded the next time AIDE starts.

---

## 9. Project Structure

```text
AIDE/
├── main.py                    # entry point
├── requirements.txt
├── README.md
├── docs/
│   └── PLUGIN_GUIDE.md        # standalone guide for building plugins
├── core/
│   ├── scanner.py             # recursive directory scanning
│   ├── classifier.py          # file classification + sensitive file detection
│   ├── package_builder.py     # builds package text content
│   ├── manifest.py            # builds the JSON manifest
│   ├── security.py            # conflict handling, safe export path
│   ├── settings.py            # settings loading/saving
│   ├── plugin_base.py         # public, stable plugin contract (AIDEPlugin)
│   ├── plugin_loader.py       # dynamic plugin discovery from plugins/
│   └── tree_renderer.py       # ASCII file tree generation
├── ui/
│   ├── theme.py               # shared color palette/typography
│   ├── main_window.py         # main window, buttons, threading
│   ├── file_tree.py           # hierarchical folder tree with checkboxes and filter
│   ├── preview.py             # preview window
│   └── settings_window.py     # settings window
├── exporters/
│   ├── markdown_exporter.py
│   ├── text_exporter.py
│   ├── tree_exporter.py
│   └── json_exporter.py
├── plugins/
│   └── example_plugin/
│       └── main_plugin.py     # runnable reference implementation
└── tests/
    ├── test_scanner.py
    ├── test_classifier.py
    ├── test_export.py
    ├── test_plugin_loader.py
    └── test_tree_renderer.py
```

GUI, file analysis, and export are deliberately separated:
`ui/` modules call functions in `core/` and `exporters/`, never the
other way around.

---

## 10. Testing

Run the full test suite with:

```bash
pip install -r requirements.txt
pytest tests/ -v
```

The tests cover, among other things:

* recursive directory scanning (including ignored directories)
* file classification (code, text, image, binary, unknown)
* UTF-8 filenames and international characters
* empty directories
* unreadable files (error handling without crashing)
* sensitive file detection, including hidden files such as `.env`
* interrupted scanning
* Markdown, text, and JSON manifest export
* conflict handling for existing export files (overwrite / new version /
  skip)
* ensuring exports can never end up outside the selected export folder

---

## 11. Limitations

* Binary files (images, executables, databases, document formats such
  as `.pdf`/`.docx`) are currently included only as metadata/placeholders
  in the package, not as actual file contents.
* Automatic text extraction from `.pdf`/`.docx` (for example, including
  document body text in the package) is not implemented in this version.
* The plugin system (see `docs/PLUGIN_GUIDE.md`) currently loads all
  plugins in the `plugins/` directory automatically at startup — there
  is not yet a setting for enabling or disabling individual plugins.
* The GUI is built with CustomTkinter to remain fully standalone without
  external GUI dependencies beyond the one package; it is functional
  but deliberately simple in its visual design.

---

## 12. Future Development

The plugin system is now available (see `docs/PLUGIN_GUIDE.md`), but
possible next steps include:

* Full content extraction for document formats (PDF/DOCX) as an
  optional export variant.
* The ability to save/load "profiles" (combinations of sources, filters,
  and selections) for recurring projects.
* Drag-and-drop of folders directly into the main window.
* An alternative export mode that includes binary files as actual
  attached files (copied, not inline text) in the export folder.
* A settings panel in the GUI that lists installed plugins and allows
  users to enable/disable them individually (currently all plugins in
  the `plugins/` directory are loaded automatically).
* ZIP archives as virtual source folders (extract and scan their
  contents without a manual extraction step), as well as actual text
  extraction from PDFs — deliberately deprioritized for now.

---

## 13. Selected Changelog

* **Security fix:** previous versions wrote the source folder's
  *complete absolute path* directly into export files (Markdown, text,
  and JSON manifest) under the heading "SOURCE ROOTS". This meant that
  usernames and local folder structures could leak into packages
  intended to be shared or pasted into external AI tools. From this
  version onward, only the source folder's *name* is written — never
  its full path. See section 7.
* Export filenames are now based on the source folder's name
  (`<source-folder>.md`, etc.) instead of the generic
  `project_package.md`.
* The file tree has been changed from category grouping to a true
  hierarchical folder structure, with clickable folder-level checkboxes
  for excluding entire subtrees with a single click (see section 4).
* New: ASCII file trees, both embedded automatically in Markdown/text
  packages and available as a standalone export format ("File tree only").
  A small addition I (Claude) added beyond the explicitly requested
  functionality: a generated timestamp at the bottom of tree exports,
  making it easy to tell at a glance that the tree is current.
