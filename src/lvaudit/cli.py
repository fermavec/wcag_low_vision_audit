"""Command-line entry point for lvaudit.

    lvaudit https://example.com --zoom 100 200 400 --screenshots ./evidence/

Loads the URL once per zoom level, runs the deterministic geometry detectors,
and prints an impact-ranked report. axe-core integration and the HTML report
land in later versions (see README roadmap); the CLI is structured so they
slot in without changing this flow.
"""
from __future__ import annotations

import argparse
import os
import sys

from .capture import browser_session, measure_at_zoom
from .detectors import run_geometry_detectors
from .models import AuditResult, Severity


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="lvaudit",
        description="Find layout failures real low-vision users hit.",
    )
    p.add_argument("url", help="URL to audit (include https://).")
    p.add_argument(
        "--zoom", type=int, nargs="+", default=[100, 200, 400],
        metavar="PCT", help="Zoom levels to test (default: 100 200 400).",
    )
    p.add_argument(
        "--screenshots", metavar="DIR", default=None,
        help="Directory to save full-page screenshots as evidence.",
    )
    p.add_argument(
        "--show-browser", action="store_true",
        help="Run with a visible browser window (debugging).",
    )
    return p.parse_args(argv)


def audit(url: str, zooms: list[int], screenshots_dir: str | None,
          headless: bool = True) -> AuditResult:
    result = AuditResult(url=url)
    measurements = {}

    if screenshots_dir:
        os.makedirs(screenshots_dir, exist_ok=True)

    with browser_session(headless=headless) as page:
        for z in sorted(zooms):
            shot = None
            if screenshots_dir:
                shot = os.path.join(screenshots_dir, f"zoom-{z}.png")
            measurements[z] = measure_at_zoom(page, url, z, screenshot_path=shot)

    for f in run_geometry_detectors(measurements):
        result.add(f)
    return result


# ---- Console reporting -------------------------------------------------------

_COLORS = {
    Severity.BLOCKER: "\033[1;31m",   # bold red
    Severity.SEVERE: "\033[31m",      # red
    Severity.MODERATE: "\033[33m",    # yellow
    Severity.POLISH: "\033[36m",      # cyan
}
_RESET = "\033[0m"


def _supports_color() -> bool:
    return sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


def print_report(result: AuditResult) -> None:
    color = _supports_color()
    print(f"\nLow-Vision Layout Audit — {result.url}\n" + "=" * 60)

    summary = result.summary()
    print("Summary:", ", ".join(f"{v} {k}" for k, v in summary.items() if v) or "no findings")
    print()

    findings = result.sorted_findings()
    if not findings:
        print("No layout failures detected by the geometry checks. "
              "(Contrast and label checks arrive with axe-core in v0.2.)")
        return

    for i, f in enumerate(findings, 1):
        tag = f.severity.label.upper()
        if color:
            tag = f"{_COLORS[f.severity]}{tag}{_RESET}"
        print(f"{i}. [{tag}] {f.title}")
        print(f"   WCAG {f.wcag}  ·  {f.condition}")
        if f.location:
            print(f"   Where: {f.location}")
        print(f"   {f.detail}")
        if f.evidence:
            print(f"   Evidence: {f.evidence}")
        print()


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = audit(
            args.url, args.zoom, args.screenshots,
            headless=not args.show_browser,
        )
    except Exception as e:  # noqa: BLE001 — surface a clean message, not a stack dump
        print(f"lvaudit: could not audit {args.url!r}: {e}", file=sys.stderr)
        return 1
    print_report(result)
    # Exit non-zero if any blocker/severe finding, so CI pipelines can gate on it.
    worst = min((f.severity for f in result.findings), default=Severity.POLISH)
    return 2 if worst <= Severity.SEVERE else 0


if __name__ == "__main__":
    raise SystemExit(main())
