import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.report_writer import create_report
from core.security import ConflictStrategy


def test_create_report_writes_file(tmp_path):
    export_dir = tmp_path / "AIDE Box"
    path = create_report(str(export_dir), "## Jämförelse\n\nFil A och B skiljer sig åt.")
    assert path is not None
    assert os.path.isfile(path)
    assert path.endswith("report.md")


def test_create_report_lands_in_report_subfolder(tmp_path):
    export_dir = tmp_path / "AIDE Box"
    path = create_report(str(export_dir), "innehåll")
    assert os.path.basename(os.path.dirname(path)) == "report"


def test_create_report_no_double_subfolder_if_already_there(tmp_path):
    export_dir = tmp_path / "AIDE Box" / "report"
    path = create_report(str(export_dir), "innehåll")
    # ska INTE bli .../report/report/report.md
    assert os.path.dirname(path) == str(export_dir)


def test_create_report_includes_project_header_when_given(tmp_path):
    export_dir = tmp_path / "AIDE Box"
    path = create_report(str(export_dir), "kroppstext", project_name="MittProjekt")
    text = open(path, encoding="utf-8").read()
    assert "MittProjekt" in text
    assert "kroppstext" in text


def test_create_report_omits_header_without_project_name(tmp_path):
    export_dir = tmp_path / "AIDE Box"
    path = create_report(str(export_dir), "kroppstext")
    text = open(path, encoding="utf-8").read()
    assert text.strip() == "kroppstext"


def test_create_report_rejects_empty_content(tmp_path):
    export_dir = tmp_path / "AIDE Box"
    path = create_report(str(export_dir), "   ")
    assert path is None
    assert not (export_dir / "report").exists()


def test_create_report_conflict_new_version(tmp_path):
    export_dir = tmp_path / "AIDE Box"
    first = create_report(str(export_dir), "första rapporten")
    second = create_report(str(export_dir), "andra rapporten", conflict_strategy=ConflictStrategy.NEW_VERSION)
    assert first != second
    assert os.path.isfile(first)
    assert os.path.isfile(second)


def test_create_report_conflict_skip_keeps_existing(tmp_path):
    export_dir = tmp_path / "AIDE Box"
    first = create_report(str(export_dir), "original")
    second = create_report(str(export_dir), "ny text", conflict_strategy=ConflictStrategy.SKIP)
    assert second is None
    assert open(first, encoding="utf-8").read().strip() == "original"


def test_create_report_conflict_overwrite_replaces(tmp_path):
    export_dir = tmp_path / "AIDE Box"
    first = create_report(str(export_dir), "original")
    second = create_report(str(export_dir), "uppdaterad", conflict_strategy=ConflictStrategy.OVERWRITE)
    assert first == second
    assert open(first, encoding="utf-8").read().strip() == "uppdaterad"


def test_create_report_never_escapes_export_dir(tmp_path):
    export_dir = tmp_path / "AIDE Box"
    export_dir.mkdir()
    path = create_report(str(export_dir), "innehåll", filename="../../etc/passwd")
    assert path is None
