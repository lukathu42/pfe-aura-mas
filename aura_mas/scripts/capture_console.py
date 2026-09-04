"""Capture operator-console screenshots for the thesis Governance chapter.

Playwright rather than `chrome --headless --screenshot`: both consoles are
websocket-driven single-page apps (Streamlit's script runner, Next.js's RSC
stream), and a one-shot headless screenshot reliably fires before hydration
finishes, producing skeleton placeholders. Playwright can wait on a concrete
DOM selector instead of a fixed timeout.

Usage (servers must already be running):
    streamlit run aura_mas/dashboard/app.py --server.port 8601   # PYTHONPATH=.
    npm --prefix frontend run dev                                # port 3000
    python -m aura_mas.scripts.capture_console
"""

from __future__ import annotations

import os
import sys

OUT = os.environ.get("SHOT_OUT", "results/figures")
STREAMLIT_URL = os.environ.get("STREAMLIT_URL", "http://localhost:8601")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")

TARGETS = [
    # (url, output name, selector to await, viewport, description)
    (
        STREAMLIT_URL,
        "shot_streamlit_console.png",
        "text=Alert feed",
        (1500, 1150),
        "Streamlit operator console",
    ),
    (
        FRONTEND_URL,
        "shot_frontend_console.png",
        "body",
        (1600, 1050),
        "Next.js command console",
    ),
]


def main() -> int:
    from playwright.sync_api import sync_playwright

    os.makedirs(OUT, exist_ok=True)
    written, failed = [], []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            args=[
                "--no-sandbox",
                # This box has no usable GPU for Chromium: without forcing the
                # software path the GPU process crash-loops and takes the whole
                # browser down ("GPU process isn't usable. Goodbye.").
                "--disable-gpu",
                "--disable-dev-shm-usage",
                "--in-process-gpu",
                "--use-gl=angle",
                "--use-angle=swiftshader",
            ]
        )
        for url, name, selector, (w, h), desc in TARGETS:
            page = browser.new_page(
                viewport={"width": w, "height": h}, device_scale_factor=2
            )
            try:
                page.goto(url, wait_until="networkidle", timeout=45000)
                try:
                    page.wait_for_selector(selector, timeout=25000)
                except Exception:
                    # selector never appeared; still capture so the failure is
                    # inspectable rather than silent
                    pass
                page.wait_for_timeout(3500)
                path = os.path.join(OUT, name)
                page.screenshot(path=path, full_page=False)
                written.append((name, os.path.getsize(path) // 1024, desc))
            except Exception as exc:  # noqa: BLE001
                failed.append((name, desc, str(exc).splitlines()[0]))
            finally:
                page.close()
        browser.close()

    for name, kb, desc in written:
        print(f"  wrote {name:34s} {kb:5d} KB   {desc}")
    for name, desc, err in failed:
        print(f"  FAILED {name:33s} {desc}: {err}", file=sys.stderr)
    return 0 if written else 1


if __name__ == "__main__":
    raise SystemExit(main())
