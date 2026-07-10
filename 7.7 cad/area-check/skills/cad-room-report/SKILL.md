---
name: cad-room-report
description: Parse local DWG floor plan files, convert them to DXF, detect enclosed spaces with Python, and generate a JSON room-count report. Use when the user wants room or enclosed-space counts from CAD drawings or wants a reusable DWG-to-report workflow.
---

# CAD Room Report

Use this skill when a local `.dwg` floor plan needs to be parsed into a room-count report.

## Workflow

1. Install Python dependencies from `requirements.txt`.
2. Ensure a DWG-to-DXF converter is available.
3. Run `python scripts/parse_rooms.py --input-dwg <file.dwg> --workdir <tmpdir> --output-json <report.json>`.
4. Read the JSON report and summarize:
   - `room_count_total`
   - conversion path used
   - raw region count vs filtered count
   - warnings

## Converter Requirements

`scripts/convert_dwg.py` expects one of these:

- `ODA_FILE_CONVERTER` environment variable pointing to the converter binary
- `ODAFileConverter` on `PATH`
- `odafc` on `PATH`

The parser intentionally uses `DWG -> DXF -> Python` instead of direct DWG parsing because modern DWG support is much more reliable through a converter.

## Counting Rule

For v1, count every enclosed leaf region that survives geometry cleanup and deduplication.

- Closed polylines count as candidate regions.
- Line and arc networks are stitched into loops and polygonized.
- Large wrapper polygons that only contain smaller enclosed regions are filtered out so the result tracks room-like spaces instead of the overall building outline.

## Outputs

The parser writes a JSON report with:

- `source_file`
- `converted_dxf`
- `room_count_total`
- `region_count_raw`
- `regions_discarded`
- `warnings`

If the drawing cannot be converted, the script exits with a clear dependency or conversion error instead of returning a silent zero count.
