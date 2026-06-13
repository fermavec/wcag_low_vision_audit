"""Deterministic layout-failure detectors.

Each detector takes one or more PageMeasurement objects and returns Findings.
The logic here is pure geometry: no browser, no network, no AI. That makes it
exactly reproducible and unit-testable, and it's the part of the tool that no
automated WCAG scanner does well.
"""
from __future__ import annotations

from .capture import PageMeasurement
from .models import Finding, Severity


def detect_reflow(m: PageMeasurement) -> list[Finding]:
    """WCAG 1.4.10 — at high zoom, content must reflow to one column with no
    horizontal scroll. Horizontal scroll at 400% is the classic low-vision
    blocker: the user has to scroll sideways on every single line to read."""
    findings: list[Finding] = []
    if m.zoom >= 400 and m.has_horizontal_scroll:
        overflow = round(m.scroll_width - m.viewport_width)
        findings.append(Finding(
            title="Page forces horizontal scrolling when zoomed in",
            severity=Severity.BLOCKER,
            wcag="1.4.10 Reflow",
            condition=f"{m.zoom}% zoom ({m.viewport_width}px viewport)",
            detail=(
                f"Content is {round(m.scroll_width)}px wide in a "
                f"{m.viewport_width}px viewport — {overflow}px of overflow. "
                f"A low-vision user must scroll sideways to read every line."
            ),
        ))
    elif m.zoom >= 200 and m.has_horizontal_scroll:
        overflow = round(m.scroll_width - m.viewport_width)
        findings.append(Finding(
            title="Horizontal scrolling appears at moderate zoom",
            severity=Severity.SEVERE,
            wcag="1.4.10 Reflow",
            condition=f"{m.zoom}% zoom ({m.viewport_width}px viewport)",
            detail=(
                f"{overflow}px of horizontal overflow at {m.zoom}% zoom. "
                f"Reflow is already breaking before the 400% threshold."
            ),
        ))
    return findings


def detect_offscreen_interactive(m: PageMeasurement) -> list[Finding]:
    """WCAG 1.4.10 — interactive elements (buttons, links, inputs) that land
    outside the visible viewport width when zoomed are effectively unreachable
    for a user who can't see the off-screen region. We flag elements whose box
    extends meaningfully past the right edge of the viewport."""
    findings: list[Finding] = []
    if m.zoom < 200:
        return findings  # only meaningful once zoom should have reflowed

    margin = 4  # ignore tiny sub-pixel overhangs
    offenders = [
        b for b in m.interactive
        if b.right > m.viewport_width + margin
    ]
    # Report the worst few, not every one, to keep the report actionable.
    offenders.sort(key=lambda b: b.right, reverse=True)
    for b in offenders[:5]:
        past = round(b.right - m.viewport_width)
        label = b.text or b.selector
        findings.append(Finding(
            title=f"Interactive element off-screen when zoomed: “{label}”",
            severity=Severity.SEVERE,
            wcag="1.4.10 Reflow",
            condition=f"{m.zoom}% zoom ({m.viewport_width}px viewport)",
            detail=(
                f"The {b.tag} extends {past}px past the right edge of the "
                f"viewport. A magnification user may never see it to use it."
            ),
            location=b.selector,
        ))
    return findings


def detect_text_clipping(measurements: dict[int, PageMeasurement]) -> list[Finding]:
    """WCAG 1.4.4 — heuristic: if total content height barely grows (or shrinks)
    from 100% to 200% zoom while width is constrained, text is likely being
    clipped or hidden rather than reflowing. A healthy responsive page gets
    *taller* as text enlarges and columns narrow."""
    findings: list[Finding] = []
    if 100 not in measurements or 200 not in measurements:
        return findings
    base = measurements[100]
    zoomed = measurements[200]
    if base.scroll_height == 0:
        return findings
    growth = zoomed.scroll_height / base.scroll_height
    if growth < 0.95:
        findings.append(Finding(
            title="Content may be clipped when text is enlarged",
            severity=Severity.MODERATE,
            wcag="1.4.4 Resize text",
            condition="200% zoom vs 100%",
            detail=(
                f"Content height went from {round(base.scroll_height)}px to "
                f"{round(zoomed.scroll_height)}px when enlarged ({growth:.0%}). "
                f"Healthy reflow makes pages taller, not shorter — this suggests "
                f"text is being cut off or hidden instead of wrapping."
            ),
        ))
    return findings


def run_geometry_detectors(
    measurements: dict[int, PageMeasurement]
) -> list[Finding]:
    """Run every deterministic detector over a set of zoom measurements."""
    findings: list[Finding] = []
    for m in measurements.values():
        findings.extend(detect_reflow(m))
        findings.extend(detect_offscreen_interactive(m))
    findings.extend(detect_text_clipping(measurements))
    return findings
