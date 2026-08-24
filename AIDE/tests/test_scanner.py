import os
import stat
import sys
import threading

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.scanner import scan_sources


def _write(path, content=""):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


def test_recursive_scan_finds_nested_files(tmp_path):
    root = tmp_path / "proj"
    _write(str(root / "src" / "main.py"), "print(1)")
    _write(str(root / "src" / "core" / "router.py"), "print(2)")
    _write(str(root / "docs" / "readme.md"), "# hi")

    result = scan_sources([str(root)])
    rels = sorted(f.relative_path for f in result.files)
    assert rels == ["docs/readme.md", "src/core/router.py", "src/main.py"]


def test_ignored_directories_are_skipped(tmp_path):
    root = tmp_path / "proj"
    _write(str(root / "src" / "main.py"), "print(1)")
    _write(str(root / "node_modules" / "pkg" / "index.js"), "x")
    _write(str(root / ".git" / "HEAD"), "ref: refs/heads/main")

    result = scan_sources([str(root)])
    rels = [f.relative_path for f in result.files]
    assert "src/main.py" in rels
    assert not any("node_modules" in r for r in rels)
    assert not any(r.startswith(".git") for r in rels)


def test_empty_directory_produces_no_files(tmp_path):
    root = tmp_path / "empty_proj"
    (root / "empty_sub").mkdir(parents=True)

    result = scan_sources([str(root)])
    assert result.files == []
    assert result.errors == []


def test_utf8_filenames_are_handled(tmp_path):
    root = tmp_path / "proj"
    _write(str(root / "åäö_mapp" / "fil_ö.txt"), "internationellt innehåll: 中文 日本語")

    result = scan_sources([str(root)])
    assert len(result.files) == 1
    assert result.files[0].relative_path == "åäö_mapp/fil_ö.txt"


def test_unreadable_file_does_not_crash_scan(tmp_path):
    root = tmp_path / "proj"
    good = root / "good.py"
    bad = root / "bad.py"
    _write(str(good), "print(1)")
    _write(str(bad), "print(2)")

    os.chmod(str(bad), 0o000)
    try:
        result = scan_sources([str(root)])
    finally:
        os.chmod(str(bad), 0o644)  # städa upp så tmp_path kan rensas

    rels = {f.relative_path: f for f in result.files}
    assert "good.py" in rels
    assert "bad.py" in rels
    # Root-processer kan fortfarande läsa trots chmod 000; testa bara att
    # skanningen inte kraschar och att filen ändå upptäcks.
    assert rels["good.py"].readable is True


def test_sensitive_hidden_file_is_still_discovered(tmp_path):
    root = tmp_path / "proj"
    _write(str(root / ".env"), "SECRET=1")

    result = scan_sources([str(root)], show_hidden=False)
    rels = {f.relative_path: f for f in result.files}
    assert ".env" in rels
    assert rels[".env"].is_sensitive is True


def test_cancel_stops_scan_early(tmp_path):
    root = tmp_path / "proj"
    for i in range(50):
        _write(str(root / f"file_{i}.py"), "print(1)")

    cancel_event = threading.Event()
    cancel_event.set()  # avbryt direkt

    result = scan_sources([str(root)], cancel_event=cancel_event)
    assert result.cancelled is True


def test_nonexistent_source_reports_error_not_crash():
    result = scan_sources(["/path/does/not/exist/at/all"])
    assert result.files == []
    assert len(result.errors) == 1
