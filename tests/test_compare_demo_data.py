from __future__ import annotations

import gzip
import importlib.util
import io
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "compare_demo_data", ROOT / "scripts/compare_demo_data.py"
)
compare_demo_data = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(compare_demo_data)


def regzip(path: Path, *, level: int = 9, mtime: int = 0, content: bytes | None = None) -> None:
    data = content if content is not None else gzip.decompress(path.read_bytes())
    buffer = io.BytesIO()
    with gzip.GzipFile(
        filename="", mode="wb", fileobj=buffer, mtime=mtime, compresslevel=level
    ) as zipped:
        zipped.write(data)
    path.write_bytes(buffer.getvalue())


@pytest.fixture
def regenerated(tmp_path: Path) -> Path:
    for name in compare_demo_data.GENERATED_FILES:
        shutil.copy(compare_demo_data.COMMITTED / name, tmp_path / name)
    return tmp_path


def test_committed_copy_matches(regenerated: Path) -> None:
    assert compare_demo_data.compare(regenerated) == []


def test_same_content_with_different_compressed_bytes_matches(regenerated: Path) -> None:
    target = regenerated / "case_master.csv.gz"
    regzip(target, level=1)
    assert target.read_bytes() != (compare_demo_data.COMMITTED / "case_master.csv.gz").read_bytes()
    assert compare_demo_data.compare(regenerated) == []


def test_changed_gzip_content_fails(regenerated: Path) -> None:
    target = regenerated / "p2p_event_log.csv.gz"
    regzip(target, content=gzip.decompress(target.read_bytes()) + b"extra\n")
    assert compare_demo_data.compare(regenerated) == [
        "p2p_event_log.csv.gz: regenerated content differs from data/demo"
    ]


def test_nonzero_gzip_mtime_fails(regenerated: Path) -> None:
    regzip(regenerated / "case_master.csv.gz", mtime=1_700_000_000)
    assert compare_demo_data.compare(regenerated) == [
        "case_master.csv.gz: regenerated file has a non-zero gzip mtime"
    ]


def test_changed_or_missing_plain_files_fail(regenerated: Path) -> None:
    (regenerated / "resources.csv").write_text("changed\n", encoding="utf-8")
    (regenerated / "ideal_process.json").unlink()
    errors = compare_demo_data.compare(regenerated)
    assert "resources.csv: regenerated content differs from data/demo" in errors
    assert any(error.startswith("ideal_process.json: missing") for error in errors)


def test_cli_exit_codes(regenerated: Path) -> None:
    assert compare_demo_data.main([str(regenerated)]) == 0
    (regenerated / "resources.csv").write_text("changed\n", encoding="utf-8")
    assert compare_demo_data.main([str(regenerated)]) == 1
