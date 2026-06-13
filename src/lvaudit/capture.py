"""Browser capture layer.

Wraps Playwright so the rest of the tool can ask simple questions like
"is there horizontal scroll at 400% zoom?" and "which interactive elements
fall outside the viewport?" — answered with exact pixel measurements from a
real Chromium render, not heuristics.

Zoom is simulated the way a low-vision user actually triggers it: by shrinking
the layout viewport while keeping the CSS pixel ratio, which is equivalent to
browser zoom for reflow purposes. We use a fixed reference width (1280px at
100%) and divide by the zoom factor, because WCAG 1.4.10 defines reflow against
a 1280px-wide viewport at 400% zoom (i.e. a 320px CSS-pixel-equivalent width).
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass

# Playwright is imported lazily inside the context manager so that importing
# this module (e.g. for tests of pure logic) doesn't require a browser install.

REFERENCE_WIDTH = 1280   # WCAG 1.4.10 reference viewport width in px
REFERENCE_HEIGHT = 1024


@dataclass
class ElementBox:
    """Bounding box and identity of one DOM element, in layout pixels."""
    selector: str
    tag: str
    x: float
    y: float
    width: float
    height: float
    text: str = ""

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y + self.height


@dataclass
class PageMeasurement:
    """Everything we measured at a single zoom condition."""
    zoom: int
    viewport_width: int
    viewport_height: int
    scroll_width: float          # full content width; > viewport => h-scroll
    scroll_height: float
    interactive: list[ElementBox]
    screenshot_path: str | None = None

    @property
    def has_horizontal_scroll(self) -> bool:
        # 1px tolerance for sub-pixel rounding.
        return self.scroll_width > self.viewport_width + 1


# JS evaluated in the page to collect interactive elements and their boxes.
# Interactive = the things a user must reach to complete a task.
_COLLECT_JS = """
() => {
  const sel = 'a, button, input, select, textarea, [role=button], [role=link]';
  const nodes = Array.from(document.querySelectorAll(sel));
  const boxes = nodes.map(n => {
    const r = n.getBoundingClientRect();
    // Build a short, stable selector hint for the report.
    let hint = n.tagName.toLowerCase();
    if (n.id) hint += '#' + n.id;
    else if (n.className && typeof n.className === 'string')
      hint += '.' + n.className.trim().split(/\\s+/).slice(0,2).join('.');
    return {
      selector: hint,
      tag: n.tagName.toLowerCase(),
      x: r.x + window.scrollX,
      y: r.y + window.scrollY,
      width: r.width,
      height: r.height,
      text: (n.innerText || n.value || '').trim().slice(0, 60)
    };
  }).filter(b => b.width > 0 && b.height > 0);  // skip hidden elements
  return {
    scrollWidth: document.documentElement.scrollWidth,
    scrollHeight: document.documentElement.scrollHeight,
    boxes
  };
}
"""


@contextmanager
def browser_session(headless: bool = True):
    """Yield a Playwright page inside a managed browser context."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context()
        page = context.new_page()
        try:
            yield page
        finally:
            context.close()
            browser.close()


def measure_at_zoom(
    page,
    url: str,
    zoom: int,
    screenshot_path: str | None = None,
    load_timeout_ms: int = 20000,
) -> PageMeasurement:
    """Load `url` at the given zoom level and return exact measurements.

    Zoom 100 => 1280px viewport. Zoom 400 => 320px viewport (the WCAG reflow
    reference). The page is given its full reference height divided by zoom so
    vertical scrolling behaves naturally.
    """
    vw = max(1, round(REFERENCE_WIDTH / (zoom / 100)))
    vh = max(1, round(REFERENCE_HEIGHT / (zoom / 100)))
    page.set_viewport_size({"width": vw, "height": vh})
    page.goto(url, wait_until="load", timeout=load_timeout_ms)
    page.wait_for_timeout(500)  # let late layout/JS settle

    data = page.evaluate(_COLLECT_JS)

    if screenshot_path:
        page.screenshot(path=screenshot_path, full_page=True)

    boxes = [
        ElementBox(
            selector=b["selector"], tag=b["tag"],
            x=b["x"], y=b["y"], width=b["width"], height=b["height"],
            text=b["text"],
        )
        for b in data["boxes"]
    ]
    return PageMeasurement(
        zoom=zoom,
        viewport_width=vw,
        viewport_height=vh,
        scroll_width=data["scrollWidth"],
        scroll_height=data["scrollHeight"],
        interactive=boxes,
        screenshot_path=screenshot_path,
    )
