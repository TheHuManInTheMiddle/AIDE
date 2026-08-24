import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.scanner import ScannedFile
from core.security import ConflictStrategy
from core.tree_renderer import build_ascii_tree
from exporters.tree_exporter import export_tree


def _make_file(tmp_path, rel_path, category="Kod"):
    abs_path = tmp_path / rel_path
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    abs_path.write_text("innehåll", encoding="utf-8")
    return ScannedFile(
        absolute_path=str(abs_path),
        relative_path=rel_path,
        source_root=str(tmp_path),
        filename=os.path.basename(rel_path),
        extension=os.path.splitext(rel_path)[1],
        category=category,
        language=None,
        size_bytes=abs_path.stat().st_size,
        modified_at=datetime.now(),
        is_sensitive=False,
        is_binary=False,
        is_hidden=False,
        readable=True,
        included=True,
    )


def test_ascii_tree_nests_folders_correctly(tmp_path):
    files = [
        _make_file(tmp_path, "src/main.py"),
        _make_file(tmp_path, "src/core/router.py"),
        _make_file(tmp_path, "docs/readme.md"),
    ]
    tree = build_ascii_tree("MittProjekt", files)

    assert tree.startswith("MittProjekt/")
    assert "├── docs/" in tree or "└── docs/" in tree
    assert "main.py" in tree
    assert "router.py" in tree
    assert "readme.md" in tree
    # core/ ska vara nästlad under src/, dvs indenterad djupare
    src_line_index = next(i for i, line in enumerate(tree.splitlines()) if "src/" in line)
    core_line_index = next(i for i, line in enumerate(tree.splitlines()) if "core/" in line)
    assert core_line_index > src_line_index


def test_ascii_tree_folders_before_files_alphabetically(tmp_path):
    files = [
        _make_file(tmp_path, "zeta.py"),
        _make_file(tmp_path, "alpha/inside.py"),
    ]
    tree = build_ascii_tree("Proj", files)
    lines = tree.splitlines()
    # "alpha/" (mapp) ska komma före "zeta.py" (fil) trots att z < a alfabetiskt är falskt,
    # men mappar ska ändå sorteras före filer oavsett bokstavsordning
    alpha_index = next(i for i, l in enumerate(lines) if "alpha/" in l)
    zeta_index = next(i for i, l in enumerate(lines) if "zeta.py" in l)
    assert alpha_index < zeta_index


def test_ascii_tree_empty_selection():
    tree = build_ascii_tree("TomtProjekt", [])
    assert "TomtProjekt/" in tree
    assert "inga filer markerade" in tree


def test_ascii_tree_never_contains_absolute_paths(tmp_path):
    files = [_make_file(tmp_path, "src/main.py")]
    tree = build_ascii_tree("Proj", files)
    assert str(tmp_path) not in tree


def test_export_tree_writes_file_without_content(tmp_path):
    src = tmp_path / "src"
    files = [_make_file(src, "main.py")]
    export_dir = tmp_path / "export"

    path = export_tree("Proj", [str(src)], files, str(export_dir), conflict_strategy=ConflictStrategy.OVERWRITE)
    text = open(path, encoding="utf-8").read()

    assert "main.py" in text
    assert "innehåll" not in text  # filinnehåll ska ALDRIG vara med i tree-exporten
    assert "Filer: 1" in text


def test_export_tree_respects_conflict_skip(tmp_path):
    src = tmp_path / "src"
    files = [_make_file(src, "main.py")]
    export_dir = tmp_path / "export"
    export_dir.mkdir()
    (export_dir / "project_tree.md").write_text("gammalt")

    path = export_tree("Proj", [str(src)], files, str(export_dir), conflict_strategy=ConflictStrategy.SKIP)
    assert path is None
    assert (export_dir / "project_tree.md").read_text() == "gammalt"
