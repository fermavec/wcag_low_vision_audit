"""Unit tests for the deterministic detectors.

These build PageMeasurement objects by hand — no browser needed — so the
geometry logic is verified in isolation and runs in milliseconds.
"""
from lvaudit.capture import PageMeasurement, ElementBox
from lvaudit.detectors import (
    detect_reflow,
    detect_offscreen_interactive,
    detect_text_clipping,
)
from lvaudit.models import Severity


def _measurement(zoom, vw, scroll_width, scroll_height=1000, interactive=None):
    return PageMeasurement(
        zoom=zoom, viewport_width=vw, viewport_height=800,
        scroll_width=scroll_width, scroll_height=scroll_height,
        interactive=interactive or [],
    )


def test_reflow_blocker_at_400():
    m = _measurement(zoom=400, vw=320, scroll_width=900)
    findings = detect_reflow(m)
    assert len(findings) == 1
    assert findings[0].severity is Severity.BLOCKER
    assert "1.4.10" in findings[0].wcag


def test_no_reflow_when_content_fits():
    m = _measurement(zoom=400, vw=320, scroll_width=320)
    assert detect_reflow(m) == []


def test_reflow_severe_at_200():
    m = _measurement(zoom=200, vw=640, scroll_width=900)
    findings = detect_reflow(m)
    assert len(findings) == 1
    assert findings[0].severity is Severity.SEVERE


def test_offscreen_interactive_flagged():
    boxes = [
        ElementBox(selector="button#pay", tag="button", x=700, y=10,
                   width=120, height=40, text="Pay now"),
        ElementBox(selector="a.home", tag="a", x=10, y=10,
                   width=80, height=20, text="Home"),
    ]
    m = _measurement(zoom=400, vw=320, scroll_width=900, interactive=boxes)
    findings = detect_offscreen_interactive(m)
    assert len(findings) == 1
    assert "Pay now" in findings[0].title
    assert findings[0].location == "button#pay"


def test_offscreen_ignored_below_200():
    boxes = [ElementBox(selector="b", tag="button", x=700, y=10,
                        width=120, height=40, text="x")]
    m = _measurement(zoom=100, vw=1280, scroll_width=1280, interactive=boxes)
    assert detect_offscreen_interactive(m) == []


def test_text_clipping_detected_when_height_shrinks():
    measurements = {
        100: _measurement(100, 1280, 1280, scroll_height=2000),
        200: _measurement(200, 640, 640, scroll_height=1500),  # shrank: bad
    }
    findings = detect_text_clipping(measurements)
    assert len(findings) == 1
    assert findings[0].severity is Severity.MODERATE


def test_text_clipping_not_flagged_when_height_grows():
    measurements = {
        100: _measurement(100, 1280, 1280, scroll_height=2000),
        200: _measurement(200, 640, 640, scroll_height=3200),  # grew: healthy
    }
    assert detect_text_clipping(measurements) == []
