#!/usr/bin/env python3
"""Package this skill with its contents at the ZIP root."""

from __future__ import annotations

import argparse
import hashlib
import os
import tempfile
import zipfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REQUIRED_MEMBERS = {
    "SKILL.md",
    "scripts/fill_docx.py",
    "references/report-review-guide.md",
}
EXCLUDED_PARTS = {"__pycache__", ".pytest_cache", "tmp"}
RUNTIME_DIRECTORIES = ("agents", "references", "scripts")


def included_files() -> list[Path]:
    candidates = [PROJECT_ROOT / "SKILL.md"]
    for directory_name in RUNTIME_DIRECTORIES:
        directory = PROJECT_ROOT / directory_name
        if directory.is_dir():
            candidates.extend(directory.rglob("*"))
    return sorted(
        path for path in candidates
        if path.is_file()
        and path.suffix != ".pyc"
        and not EXCLUDED_PARTS.intersection(path.relative_to(PROJECT_ROOT).parts)
    )


def build_archive(output: Path, *, force: bool = False) -> str:
    output = output.resolve()
    if output.is_relative_to(PROJECT_ROOT):
        raise ValueError("ZIP 输出路径不能位于待打包目录内部")
    if output.exists() and not force:
        raise FileExistsError(f"输出文件已存在：{output}；需要覆盖时使用 --force")

    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=output.parent,
        prefix=f".{output.stem}.",
        suffix=".tmp.zip",
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in included_files():
                # arcname is relative to PROJECT_ROOT, so SKILL.md, scripts/,
                # references/, etc. sit directly at the archive root.
                archive.write(path, path.relative_to(PROJECT_ROOT).as_posix())

        with zipfile.ZipFile(temporary) as archive:
            names = set(archive.namelist())
            missing = sorted(REQUIRED_MEMBERS - names)
            if missing:
                raise ValueError(f"ZIP 缺少必需文件：{', '.join(missing)}")
            if any(name.startswith(f"{PROJECT_ROOT.name}/") for name in names):
                raise ValueError(f"ZIP 多出顶层目录：{PROJECT_ROOT.name}/")
            if bad_member := archive.testzip():
                raise ValueError(f"ZIP 成员校验失败：{bad_member}")

        temporary.replace(output)
        output.chmod(0o644)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise

    return hashlib.sha256(output.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="打包技能，文件直接位于ZIP根目录")
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT.parent / f"{PROJECT_ROOT.name}.zip",
        help="ZIP 输出路径",
    )
    parser.add_argument("--force", action="store_true", help="覆盖已存在的ZIP")
    args = parser.parse_args()
    try:
        digest = build_archive(args.output, force=args.force)
    except (OSError, ValueError) as error:
        raise SystemExit(f"打包失败：{error}") from error
    print(f"已生成：{args.output.resolve()}")
    print(f"SHA-256：{digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
