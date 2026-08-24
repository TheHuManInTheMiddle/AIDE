"""
core/tree_renderer.py

Renderar en klassisk ASCII-trädvy (├──/└──/│) av de filer som är
markerade för export. Bygger på samma hierarkiska tanke som
ui/file_tree.py (mappstruktur, inte kategori), men helt fristående
från GUI-koden så den kan användas av vilken exportör som helst.

Trädet visar bara det som faktiskt är MARKERAT — det är en spegling av
vad som kommer att exporteras, inte en fullständig katalogkarta.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from core.scanner import ScannedFile


@dataclass
class _Node:
    name: str
    is_file: bool
    children: dict = field(default_factory=dict)  # name -> _Node, bara för mappar


def _build_tree(included_files: list[ScannedFile]) -> _Node:
    root = _Node(name="", is_file=False)
    for f in included_files:
        parts = f.relative_path.split("/")
        current = root
        for part in parts[:-1]:
            if part not in current.children:
                current.children[part] = _Node(name=part, is_file=False)
            current = current.children[part]
        filename = parts[-1]
        current.children[filename] = _Node(name=filename, is_file=True)
    return root


def _render(node: _Node, prefix: str, lines: list[str]) -> None:
    # Mappar först (alfabetiskt), sedan filer (alfabetiskt) — samma
    # ordning som de flesta filhanterare och `tree`-kommandot använder.
    entries = sorted(
        node.children.values(),
        key=lambda n: (n.is_file, n.name.lower()),
    )
    for index, child in enumerate(entries):
        is_last = index == len(entries) - 1
        connector = "└── " if is_last else "├── "
        suffix = "" if child.is_file else "/"
        lines.append(f"{prefix}{connector}{child.name}{suffix}")
        if not child.is_file:
            extension = "    " if is_last else "│   "
            _render(child, prefix + extension, lines)


def build_ascii_tree(project_name: str, included_files: list[ScannedFile]) -> str:
    """
    Bygger en ASCII-trädrepresentation av de markerade filerna, t.ex.:

        mittprojekt/
        ├── config/
        │   └── settings.json
        ├── src/
        │   ├── core/
        │   │   └── router.py
        │   └── main.py
        └── docs/
            └── README.md

    Endast filens NAMN används i trädet — precis som resten av AIDE:s
    export innehåller trädet aldrig absoluta lokala sökvägar.
    """
    lines = [f"{project_name}/"]
    if not included_files:
        lines.append("(inga filer markerade)")
        return "\n".join(lines)

    root = _build_tree(included_files)
    _render(root, "", lines)
    return "\n".join(lines)
