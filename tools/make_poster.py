#!/usr/bin/env python3
"""Build CoatMenu's README/social artwork from the screenshots already in docs/.

Four things come out of here:

  docs/coatmenu-poster.jpg         1920x1080 README poster (top of README, forum)
  docs/coatmenu-social.png         1280x640 social preview (repo Settings > Social preview)
  docs/coatmenu-logo.png           logo mark, 512px, transparent (README heading, forum)
  docs/coatmenu-logo-128.png       the same mark at 128px

Sources: `docs/demo-*.jpg` (the author's own 3D-Coat screenshots) and the two
SVGs under `docs/` and `tools/poster/`.  Panels are cut out of the screenshots
with the crop boxes below, because the interesting part of a full-screen
screenshot is a fraction of the frame; the boxes are in the screenshots' own
pixels so they survive a re-shoot at a different window size roughly, and must
be re-measured if the shots are taken again.

The renderer is a headless Chromium family browser (Edge ships with Windows,
Chrome works the same) — the layout is CSS so text stays vector-sharp and the
artwork can be edited by hand in tools/poster/*.html.

    python tools/make_poster.py                 # everything
    python tools/make_poster.py --logo-only
    python tools/make_poster.py --browser "C:/path/to/msedge.exe"
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POSTER_DIR = ROOT / "tools" / "poster"
DOCS = ROOT / "docs"

# (source screenshot, x0, y0, x1, y1) in the screenshot's own pixels.
# Ratios must match the panel boxes in poster.html.
PANELS = {
    "hero":   ("docs/demo-quicktool.jpg",  (400, 50, 1880, 870)),   # sculpt + the list popup
    "pie":    ("docs/demo-list-pie.jpg",   (378, 100, 2004, 708)),  # Add list + the Shade pie
    "editor": ("docs/demo-editor.jpg",     (0, 15, 1860, 711)),     # the editor's rows column
    "social": ("docs/demo-quicktool.jpg",  (700, 30, 1620, 780)),   # closer: popup over the sculpt
}

LOGO_SIZES = (512, 128)
POSTER_JPEG_QUALITY = 92

BROWSER_CANDIDATES = (
    r"C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
    r"C:/Program Files/Microsoft/Edge/Application/msedge.exe",
    r"C:/Program Files/Google/Chrome/Application/chrome.exe",
    r"C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
)


def find_browser(explicit: str | None) -> str:
    if explicit:
        return explicit
    env = os.environ.get("COATMENU_BROWSER")
    if env:
        return env
    for name in ("msedge", "chrome", "chromium", "chromium-browser", "google-chrome"):
        found = shutil.which(name)
        if found:
            return found
    for path in BROWSER_CANDIDATES:
        if Path(path).exists():
            return path
    sys.exit(
        "no Chromium-family browser found for rendering.\n"
        "Pass one with --browser, or set COATMENU_BROWSER."
    )


def cut_panels() -> None:
    try:
        from PIL import Image
    except ImportError:
        sys.exit("Pillow is required to cut the panels out of the screenshots: pip install pillow")

    out = POSTER_DIR / "panels"
    out.mkdir(parents=True, exist_ok=True)
    for name, (rel, box) in PANELS.items():
        src = ROOT / rel
        im = Image.open(src).convert("RGB")
        w, h = im.size
        x0, y0, x1, y1 = box
        if x1 > w or y1 > h:
            sys.exit("%s is %dx%d but the %s crop box is %s — re-measure it" % (rel, w, h, name, box))
        im.crop(box).save(out / (name + ".png"))
        print("panel  %-7s <- %s %s" % (name, rel, box))


def render(browser: str, url: str, out: Path, width: int, height: int,
           transparent: bool = False, label: str | None = None) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="coatmenu-poster-") as profile:
        cmd = [
            browser,
            "--headless=new",
            "--disable-gpu",
            "--hide-scrollbars",
            "--no-first-run",
            "--no-default-browser-check",
            "--force-device-scale-factor=1",
            "--user-data-dir=" + profile.replace("\\", "/"),
            "--window-size=%d,%d" % (width, height),
            "--screenshot=" + str(out).replace("\\", "/"),
        ]
        if transparent:
            cmd.append("--default-background-color=00000000")
        cmd.append(url)
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if not out.exists():
        sys.exit("render failed for %s\n%s\n%s" % (url, result.stdout[-2000:], result.stderr[-2000:]))
    if label:
        try:
            shown = out.relative_to(ROOT)
        except ValueError:
            shown = out
        print("%-5s %s (%d bytes)" % (label, shown, out.stat().st_size))


def file_url(path: Path) -> str:
    return "file:///" + str(path.resolve()).replace("\\", "/")


def build_poster(browser: str, out_dir: Path) -> None:
    """Rendered as PNG then written as JPEG: the poster is a full frame with no
    transparency, and 4:4:4 JPEG is ~5x smaller with no visible loss on text."""
    from PIL import Image

    out_dir.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="coatmenu-poster-")) / "poster.png"
    render(browser, file_url(POSTER_DIR / "poster.html"), tmp, 1920, 1080)
    jpg = out_dir / "coatmenu-poster.jpg"
    Image.open(tmp).convert("RGB").save(jpg, quality=POSTER_JPEG_QUALITY, subsampling=0, optimize=True)
    shutil.rmtree(tmp.parent, ignore_errors=True)
    print("%-5s %s (%d bytes)" % ("jpg", jpg, jpg.stat().st_size))


def build_social(browser: str, out_dir: Path) -> None:
    """GitHub's social preview: 1280x640, and the file has to stay under 1 MB
    (that is the only hard limit GitHub puts on it)."""
    png = out_dir / "coatmenu-social.png"
    render(browser, file_url(POSTER_DIR / "social.html"), png, 1280, 640, label="png")
    if png.stat().st_size > 1024 * 1024:
        sys.exit("%s is over GitHub's 1 MB social preview limit" % png)


def build_logo(browser: str) -> None:
    """The mark has no bitmap source: render the SVG at each size it ships in.
    The artboard is trimmed to the mark, so the pngs keep the SVG's aspect
    ratio instead of being forced square."""
    svg = DOCS / "coatmenu-logo.svg"
    (POSTER_DIR / "panels").mkdir(parents=True, exist_ok=True)
    text = svg.read_text(encoding="utf-8")
    _, _, vw, vh = re.search(r'viewBox="([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)"', text).groups()
    ratio = float(vh) / float(vw)
    for size in LOGO_SIZES:
        height = round(size * ratio)
        wrapper = POSTER_DIR / "panels" / ("_logo-%d.html" % size)
        wrapper.write_text(
            "<!doctype html><meta charset=utf-8>"
            '<body style="margin:0;background:transparent">'
            '<img src="%s" width="%d" height="%d">' % (file_url(svg), size, height),
            encoding="utf-8",
        )
        name = "coatmenu-logo.png" if size == LOGO_SIZES[0] else "coatmenu-logo-%d.png" % size
        render(browser, file_url(wrapper), DOCS / name, size, height, transparent=True, label="png")


def main() -> None:
    global DOCS
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--browser", help="path to msedge/chrome (Chromium family)")
    ap.add_argument("--out-dir", default=str(DOCS), help="where the files go (default: docs/)")
    ap.add_argument("--logo-only", action="store_true")
    ap.add_argument("--social-only", action="store_true")
    args = ap.parse_args()

    DOCS = Path(args.out_dir).resolve()
    browser = find_browser(args.browser)

    if args.logo_only:
        build_logo(browser)
        return
    if args.social_only:
        cut_panels()
        build_social(browser, DOCS)
        return
    build_logo(browser)
    cut_panels()
    build_social(browser, DOCS)
    build_poster(browser, DOCS)


if __name__ == "__main__":
    main()
