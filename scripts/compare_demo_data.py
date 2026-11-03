"""Compare regenerated demo data with the committed benchmark in data/demo.

Gzip files are compared on their decompressed bytes, plus their header metadata, rather than
on the compressed stream. Deflate output depends on the zlib build (zlib vs zlib-ng, as shipped
by some Linux distributions and Python builds), so identical data can compress to different
bytes. All other generated files are compared byte for byte.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMITTED = ROOT / "data" / "demo"
GENERATED_FILES = (
    "p2p_event_log.csv.gz",
    "case_master.csv.gz",
    "p2p_event_log_sample.csv",
    "resources.csv",
    "ideal_process.json",
)
GZIP_FNAME_FLAG = 0x08


def gzip_header_problems(path: Path) -> list[str]:
    header = path.read_bytes()[:10]
    problems = []
    if header[:3] != b"\x1f\x8b\x08":
        problems.append("is not a deflate gzip file")
    elif int.from_bytes(header[4:8], "little") != 0:
        problems.append("has a non-zero gzip mtime")
    elif header[3] & GZIP_FNAME_FLAG:
        problems.append("embeds a file name in the gzip header")
    return problems


def payload(path: Path) -> bytes:
    if path.suffix == ".gz":
        with gzip.open(path, "rb") as handle:
            return handle.read()
    return path.read_bytes()


def compare(regenerated: Path, committed: Path = COMMITTED) -> list[str]:
    errors = []
    for name in GENERATED_FILES:
        expected, actual = committed / name, regenerated / name
        missing = [str(path) for path in (expected, actual) if not path.is_file()]
        if missing:
            errors.append(f"{name}: missing {', '.join(missing)}")
            continue
        if name.endswith(".gz"):
            for label, path in (("committed", expected), ("regenerated", actual)):
                errors.extend(
                    f"{name}: {label} file {problem}" for problem in gzip_header_problems(path)
                )
        expected_bytes, actual_bytes = payload(expected), payload(actual)
        digest = hashlib.sha256(actual_bytes).hexdigest()
        if expected_bytes != actual_bytes:
            errors.append(f"{name}: regenerated content differs from data/demo")
        else:
            print(f"OK  {name}  sha256(content)={digest}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("regenerated", type=Path, help="Directory written by generate_demo_data.py")
    args = parser.parse_args(argv)
    errors = compare(args.regenerated)
    for error in errors:
        print(f"FAIL {error}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
