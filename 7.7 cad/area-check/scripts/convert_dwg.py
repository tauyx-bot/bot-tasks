#!/usr/bin/env python3
"""DWG to DXF conversion wrapper."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path


def discover_converter() -> str | None:
    configured = os.environ.get("ODA_FILE_CONVERTER")
    if configured:
        return configured
    for candidate in ("ODAFileConverter", "odafc"):
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    return None


def convert_dwg_to_dxf(input_dwg: Path, output_dir: Path, version: str = "ACAD2018") -> Path:
    converter = discover_converter()
    if not converter:
        raise RuntimeError(
            "No DWG converter found. Set ODA_FILE_CONVERTER or install ODAFileConverter/odafc."
        )

    input_dir = input_dwg.resolve().parent
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        converter,
        str(input_dir),
        str(output_dir),
        version,
        "DXF",
        "0",
        "1",
        input_dwg.name,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    output_path = output_dir / f"{input_dwg.stem}.dxf"
    if result.returncode != 0 and output_path.exists():
        return output_path
    if result.returncode != 0:
        raise RuntimeError(
            f"DWG conversion failed with exit code {result.returncode}: {result.stderr.strip() or result.stdout.strip()}"
        )

    if not output_path.exists():
        candidates = sorted(output_dir.glob("*.dxf"))
        if len(candidates) == 1:
            output_path = candidates[0]
        else:
            raise RuntimeError("DWG conversion finished but no DXF output was found.")

    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert DWG to DXF with ODA File Converter.")
    parser.add_argument("--input-dwg", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--version", default="ACAD2018")
    args = parser.parse_args()

    output = convert_dwg_to_dxf(args.input_dwg, args.output_dir, args.version)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
