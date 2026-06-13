# lvaudit — Low-Vision Layout Auditor

A command-line tool that finds the layout failures real low-vision users hit every day — the ones automated WCAG scanners miss because the page *technically* passes.

Give it a URL. It loads the page in a real browser at 100%, 200%, and 400% zoom, applies high-contrast and enlarged-text conditions, and reports where the layout breaks: horizontal scroll at 400% zoom, elements pushed off-screen, overlapping text, invisible focus indicators, and insufficient contrast.

Built by someone who navigates the web this way: a legally blind data scientist (10% acuity, one eye) who uses magnification, high contrast, and enlarged text daily.

---

## Why this exists

Automated accessibility scanners check rules. They tell you an image is missing alt text or a contrast ratio is 4.2:1. They do **not** tell you that at 200% zoom your "Pay" button moved off the visible area, or that your enlarged-text setting makes two labels overlap into an unreadable smear.

That gap — between "passes the checklist" and "a real low-vision user can actually complete the task" — is where this tool works. It measures the geometry and color of the rendered page with exact numbers, not guesses.

This is the WCAG low-vision battery (criteria 1.4.4, 1.4.10, 1.4.11, 1.4.12, 1.4.5, 2.4.7, 2.4.11) turned into reproducible, evidence-producing code.

---

## What it checks

| Check | WCAG | What it catches |
|---|---|---|
| Reflow | 1.4.10 | Horizontal scroll forced at 400% zoom (one-column reflow broken) |
| Off-viewport elements | 1.4.10 | Interactive elements pushed outside the visible area when zoomed |
| Text resize | 1.4.4 | Content clipped or lost when text scales to 200% |
| Overlap | 1.4.12 | Text/elements colliding under enlarged spacing |
| Contrast | 1.4.3 / 1.4.11 | Text and UI-component contrast below threshold (via axe-core) |
| Focus visibility | 2.4.7 / 2.4.11 | Keyboard focus indicator missing or too weak to see |

Geometry checks (reflow, off-viewport, overlap, resize) are done with exact DOM measurements. Contrast and labeling are delegated to **axe-core**, the industry-standard open-source engine. Everything runs offline in a real browser; no external AI, no API keys, no per-run cost.

---

## Install

**Requires Python 3.10 or newer.**

### 1. Clone the repository

```bash
git clone https://github.com/fermavec/lvaudit.git
cd lvaudit
```

### 2. Create a virtual environment

A virtual environment keeps lvaudit's dependencies isolated from the rest of your system.

```bash
python -m venv .venv
```

Activate it:

```bash
# macOS / Linux
source .venv/bin/activate

# Windows — PowerShell
.venv\Scripts\Activate.ps1

# Windows — Command Prompt
.venv\Scripts\activate.bat
```

You'll know it's active when your prompt shows `(.venv)`.

### 3. Install the package

```bash
pip install -e .
```

The `-e` flag installs in editable mode, which means changes to the source code take effect immediately without reinstalling. This reads `pyproject.toml` and installs all runtime dependencies automatically:

- **playwright** — drives the real Chromium browser for page capture
- **Pillow** — image processing for screenshot analysis (v0.2+)
- **numpy** — numerical geometry calculations (v0.3+)
- **Jinja2** — accessible HTML report rendering (v0.4+)

### 4. Install the Chromium browser

Playwright needs a browser binary to drive page captures. This step downloads it:

```bash
playwright install chromium
```

This is separate from the pip install because it's a browser binary, not a Python package. It only needs to be run once per machine.

---

## Running tests

Tests are in `tests/` and run without a browser — they verify the geometry detection logic in isolation using hand-built measurements.

Install pytest if you don't have it:

```bash
pip install pytest
```

Run the full suite:

```bash
pytest
```

Run with verbose output to see each test name:

```bash
pytest -v
```

---

## Usage

```bash
# Audit a URL at the default zoom levels (100%, 200%, 400%)
lvaudit https://example.com

# Choose specific zoom levels to test
lvaudit https://example.com --zoom 100 200 400

# Save full-page screenshots as visual evidence
lvaudit https://example.com --screenshots ./evidence/

# Open a visible browser window (useful for debugging)
lvaudit https://example.com --show-browser
```

Output is a prioritized list of findings ordered by severity (Blocker → Severe → Moderate → Polish), each with the exact location, the measurement that triggered it, and the WCAG reference — the same structure as a professional audit report.

### Exit codes

| Code | Meaning |
|---|---|
| `0` | No blockers or severe findings |
| `1` | Tool error (network failure, invalid URL, etc.) |
| `2` | At least one Blocker or Severe finding — designed for CI pipeline gating |

### Example: gating a CI pipeline

```yaml
# GitHub Actions example
- name: Run low-vision audit
  run: lvaudit https://staging.example.com --screenshots ./evidence/
  # Exits 2 if any Blocker or Severe finding is detected
```

---

## Roadmap

- **v0.1** — Reflow + off-viewport detection (the core, fully deterministic) ✓
- **v0.2** — axe-core integration for contrast and labels
- **v0.3** — Overlap and text-resize checks via DOM geometry
- **v0.4** — Accessible HTML report (predicate: the accessibility report is itself accessible)
- **v1.0** — Stable CLI, documented, tested
- **Later (optional)** — Natural-language description of *what* content broke, using a vision model — only as an additive layer, never a dependency

---

## License

MIT. Use it, fork it, audit with it.

## Author

Fernando — fermavec.com · fermavec.substack.com  
Legally blind accessibility auditor & data scientist.
