import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.scanner import ScannedFile
from core.security import (
    ConflictStrategy,
    ExportBlocked,
    ensure_within_export_dir,
    resolve_target_path,
    sanitize_filename,
)
from exporters.json_exporter import export_json_manifest
from exporters.markdown_exporter import export_markdown
from exporters.text_exporter import export_text


def _make_file(tmp_path, rel_path, content, category="Kod", language="python", sensitive=False, binary=False):
    abs_path = tmp_path / rel_path
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    if binary:
        abs_path.write_bytes(content)
    else:
        abs_path.write_text(content, encoding="utf-8")
    return ScannedFile(
        absolute_path=str(abs_path),
        relative_path=rel_path,
        source_root=str(tmp_path),
        filename=os.path.basename(rel_path),
        extension=os.path.splitext(rel_path)[1],
        category=category,
        language=language,
        size_bytes=abs_path.stat().st_size,
        modified_at=datetime.now(),
        is_sensitive=sensitive,
        is_binary=binary,
        is_hidden=False,
        readable=True,
        included=True,
    )


def test_markdown_export_contains_file_headers(tmp_path):
    src = tmp_path / "src"
    files = [_make_file(src, "main.py", "print('hej')\n")]
    export_dir = tmp_path / "export"

    path = export_markdown("Proj", [str(src)], files, str(export_dir), conflict_strategy=ConflictStrategy.OVERWRITE)
    text = open(path, encoding="utf-8").read()
    assert "FILE: main.py" in text
    assert "```python" in text
    assert "print('hej')" in text


def test_text_export_writes_file(tmp_path):
    src = tmp_path / "src"
    files = [_make_file(src, "a.txt", "hello", category="Text", language=None)]
    export_dir = tmp_path / "export"

    path = export_text("Proj", [str(src)], files, str(export_dir), conflict_strategy=ConflictStrategy.OVERWRITE)
    assert path is not None
    assert os.path.isfile(path)
    assert path.endswith(".txt")


def test_json_manifest_contains_metadata_not_content(tmp_path):
    src = tmp_path / "src"
    files = [_make_file(src, "a.py", "SECRET = 1")]
    export_dir = tmp_path / "export"

    path = export_json_manifest("Proj", [str(src)], files, str(export_dir), conflict_strategy=ConflictStrategy.OVERWRITE)
    data = json.loads(open(path, encoding="utf-8").read())
    assert data["files"] == 1
    assert data["included_files"][0]["path"] == "a.py"
    assert "SECRET" not in json.dumps(data)  # manifestet ska aldrig innehålla filinnehåll


def test_conflict_overwrite_replaces_file(tmp_path):
    target = tmp_path / "out.md"
    target.write_text("gammalt innehåll")
    resolved = resolve_target_path(str(target), ConflictStrategy.OVERWRITE)
    assert resolved == str(target)


def test_conflict_new_version_creates_numbered_file(tmp_path):
    target = tmp_path / "out.md"
    target.write_text("gammalt innehåll")
    resolved = resolve_target_path(str(target), ConflictStrategy.NEW_VERSION)
    assert resolved == str(tmp_path / "out (1).md")


def test_conflict_skip_returns_none(tmp_path):
    target = tmp_path / "out.md"
    target.write_text("gammalt innehåll")
    resolved = resolve_target_path(str(target), ConflictStrategy.SKIP)
    assert resolved is None


def test_conflict_no_existing_file_returns_target(tmp_path):
    target = tmp_path / "does_not_exist.md"
    resolved = resolve_target_path(str(target), ConflictStrategy.SKIP)
    assert resolved == str(target)


def test_export_never_escapes_export_dir(tmp_path):
    export_dir = tmp_path / "export"
    export_dir.mkdir()
    try:
        ensure_within_export_dir(str(export_dir), "../../etc/passwd")
        assert False, "should have raised ExportBlocked"
    except ExportBlocked:
        pass


def test_markdown_export_never_leaks_absolute_source_path(tmp_path):
    src = tmp_path / "hemlig_användarmapp" / "Desktop" / "MittProjekt"
    files = [_make_file(src, "main.py", "print(1)")]
    export_dir = tmp_path / "export"

    path = export_markdown("MittProjekt", [str(src)], files, str(export_dir), conflict_strategy=ConflictStrategy.OVERWRITE)
    text = open(path, encoding="utf-8").read()

    assert str(src) not in text
    assert "hemlig_användarmapp" not in text
    assert "MittProjekt" in text  # bara mappnamnet, inte hela sökvägen


def test_json_manifest_never_leaks_absolute_source_path(tmp_path):
    src = tmp_path / "hemlig_användarmapp" / "Desktop" / "MittProjekt"
    files = [_make_file(src, "main.py", "print(1)")]
    export_dir = tmp_path / "export"

    path = export_json_manifest("MittProjekt", [str(src)], files, str(export_dir), conflict_strategy=ConflictStrategy.OVERWRITE)
    data = json.loads(open(path, encoding="utf-8").read())

    assert str(src) not in json.dumps(data)
    assert "hemlig_användarmapp" not in json.dumps(data)
    assert data["source_folders"] == ["MittProjekt"]


def test_full_export_pipeline_creates_markdown_and_manifest(tmp_path):
    src = tmp_path / "src"
    files = [
        _make_file(src, "main.py", "print(1)"),
        _make_file(src, "readme.md", "# hej", category="Text", language="markdown"),
    ]
    export_dir = tmp_path / "export"

    md_path = export_markdown("Proj", [str(src)], files, str(export_dir), conflict_strategy=ConflictStrategy.OVERWRITE)
    manifest_path = export_json_manifest("Proj", [str(src)], files, str(export_dir), conflict_strategy=ConflictStrategy.OVERWRITE)

    assert os.path.isfile(md_path)
    assert os.path.isfile(manifest_path)


def test_sanitize_filename_removes_invalid_characters():
    assert sanitize_filename('mitt:proj/med<konstiga>tecken?') == "mitt_proj_med_konstiga_tecken_"


def test_sanitize_filename_handles_empty_input():
    assert sanitize_filename("") == "AIDE_Project"
    assert sanitize_filename("   ") == "AIDE_Project"


def test_sanitize_filename_keeps_normal_names_unchanged():
    assert sanitize_filename("gamebridge_v1") == "gamebridge_v1"
    assert sanitize_filename("Mitt Projekt") == "Mitt Projekt"
