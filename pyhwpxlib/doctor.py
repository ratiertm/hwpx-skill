"""Detect non-standard HWPX structures and optionally fix them.

The ``doctor`` workflow embodies the rhwp-aligned principle adopted in
v0.14.0: detect non-standard structures and notify the user, but never
silently rewrite a file. Fixes are applied only when the user explicitly
asks for them via ``--fix``.

Usage::

    pyhwpxlib doctor file.hwpx                  # diagnose only
    pyhwpxlib doctor file.hwpx --fix            # diagnose + fix to file.fixed.hwpx
    pyhwpxlib doctor file.hwpx --fix -o out.hwpx
    pyhwpxlib doctor file.hwpx --fix --inplace  # rewrite the source file

Programmatic API::

    from pyhwpxlib.doctor import diagnose, fix
    report = diagnose("file.hwpx")
    if report["needs_fix"]:
        fix("file.hwpx", "file.fixed.hwpx")
"""
from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path
from typing import Optional


def diagnose(hwpx_path: str | Path) -> dict:
    """Inspect a HWPX file for non-standard lineseg / structure issues.

    Returns a dict with:

    * ``file`` — input path
    * ``needs_fix`` — True if any issue can be repaired
    * ``issues`` — list of issue dicts (code/severity/count/detail)
    * ``summary`` — human-friendly headline
    """
    from pyhwpxlib.postprocess import (
        count_textpos_overflow,
        count_r3_violations,
    )
    p = Path(hwpx_path)
    if not p.exists():
        return {"file": str(p), "needs_fix": False, "ok": False,
                "summary": "file not found", "issues": []}
    if not zipfile.is_zipfile(p):
        return {"file": str(p), "needs_fix": False, "ok": False,
                "summary": "not a valid zip", "issues": []}

    issues = []
    overflow_total = 0
    r3_total = 0
    with zipfile.ZipFile(p) as z:
        section_names = sorted(n for n in z.namelist()
                               if n.startswith("Contents/section") and n.endswith(".xml"))
        for n in section_names:
            xml_str = z.read(n).decode("utf-8")
            o = count_textpos_overflow(xml_str)
            r = count_r3_violations(xml_str)
            overflow_total += o
            r3_total += r
            if o > 0:
                issues.append({
                    "code": "TEXTPOS_OVERFLOW",
                    "severity": "error",
                    "count": o,
                    "path": n,
                    "detail": f"{o} lineseg(s) with textpos > UTF-16 text length",
                    "fix_available": True,
                })
            if r > 0:
                issues.append({
                    "code": "RHWP_R3_RENDER_RISK",
                    "severity": "warning",
                    "count": r,
                    "path": n,
                    "detail": f"{r} paragraph(s) with single lineseg over long text — rhwp may overlap",
                    "fix_available": False,  # not auto-fixable; needs reflow
                })

    needs_fix = overflow_total > 0
    if overflow_total > 0:
        summary = (f"{overflow_total} non-standard lineseg(s) — Hancom will show security warning. "
                   f"Run with --fix to repair.")
    elif r3_total > 0:
        summary = (f"{r3_total} render risk(s) for external renderers (rhwp). "
                   f"Hancom OK; not auto-fixable.")
    else:
        summary = "No non-standard structures detected."

    return {
        "file": str(p),
        "needs_fix": needs_fix,
        "ok": overflow_total == 0,
        "issues": issues,
        "summary": summary,
        "totals": {"textpos_overflow": overflow_total, "r3_render_risk": r3_total},
    }


def fix(
    hwpx_path: str | Path,
    output_path: str | Path,
    *,
    mode: str = "precise",
) -> dict:
    """Apply a precise fix and write to output_path. Returns the fix report."""
    from pyhwpxlib.package_ops import read_zip_archive, write_zip_archive
    src = Path(hwpx_path)
    out = Path(output_path)
    archive = read_zip_archive(str(src))
    fixed = write_zip_archive(str(out), archive, strip_linesegs=mode)
    return {
        "input": str(src),
        "output": str(out),
        "mode": mode,
        "linesegs_fixed": fixed,
    }


def _render_text(report: dict, fix_result: Optional[dict] = None) -> str:
    """Human-readable rendering of diagnose+fix output."""
    lines = []
    lines.append(f"\n{'=' * 50}")
    lines.append(f"HWPX Doctor: {report['file']}")
    lines.append(f"{'=' * 50}")
    lines.append(f"Summary: {report['summary']}")
    if not report["issues"]:
        lines.append("✅ No issues found.")
    else:
        for it in report["issues"]:
            icon = {"error": "❌", "warning": "⚠️ ", "info": "ℹ️ "}.get(
                it["severity"], "•")
            tag = " [fixable]" if it.get("fix_available") else ""
            lines.append(f"  {icon} {it['code']}{tag}: {it['detail']}  ({it['path']})")
    if fix_result:
        lines.append(f"\n[FIXED] precise mode → {fix_result['output']}")
        lines.append(f"  linesegs corrected: {fix_result['linesegs_fixed']}")
    elif report["needs_fix"]:
        lines.append("\n[pyhwpxlib] To repair, rerun with --fix")
    return "\n".join(lines)


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        prog="pyhwpxlib doctor",
        description="Diagnose non-standard HWPX structures; optionally repair them.",
    )
    ap.add_argument("input", help=".hwpx file to inspect")
    ap.add_argument("--fix", action="store_true",
                    help="apply precise textpos-overflow fix (writes new file)")
    ap.add_argument("-o", "--output",
                    help="output path when --fix (default: <input>.fixed.hwpx)")
    ap.add_argument("--inplace", action="store_true",
                    help="overwrite the input file instead of writing a new one (only with --fix)")
    ap.add_argument("--mode", choices=["precise", "remove"], default="precise",
                    help="precise: remove only overflow linesegs (default). "
                         "remove: strip every <hp:linesegarray> block.")
    ap.add_argument("--json", action="store_true", help="JSON output")
    args = ap.parse_args(argv)

    report = diagnose(args.input)
    fix_result = None
    if args.fix and report["needs_fix"]:
        if args.inplace:
            output = args.input
        else:
            output = args.output or _default_fixed_path(args.input)
        fix_result = fix(args.input, output, mode=args.mode)
        # Re-diagnose after fix so the report reflects the new state
        post = diagnose(output)
        report["post_fix"] = post

    if args.json:
        print(json.dumps({
            "command": "doctor",
            "report": report,
            "fix_result": fix_result,
        }, ensure_ascii=False, indent=2))
    else:
        print(_render_text(report, fix_result))

    # Exit code: 0 if file is OK or fix succeeded; 1 if needs_fix and --fix not used.
    if report["needs_fix"] and not args.fix:
        return 1
    return 0


def _default_fixed_path(input_path: str) -> str:
    p = Path(input_path)
    return str(p.with_suffix("")) + ".fixed" + p.suffix


if __name__ == "__main__":
    raise SystemExit(main())
