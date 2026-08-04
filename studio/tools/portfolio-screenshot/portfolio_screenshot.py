"""
portfolio-screenshot — capture a website screenshot at portfolio dimensions.

Usage:
    portfolio-screenshot URL [output.png]
                         [--width 1320] [--height 857]
                         [--wait 2] [--full-page]
                         [--dismiss-cookies]
                         [--mockup]
"""

import argparse
import subprocess
import time
from pathlib import Path
from urllib.parse import urlparse


# Text patterns to click when dismissing cookie banners (case-insensitive)
_COOKIE_BUTTON_TEXTS = [
    "Accept All",
    "Accept all cookies",
    "Accept cookies",
    "Accept",
    "Allow all",
    "Allow All Cookies",
    "Agree",
    "I Agree",
    "Got it",
    "OK",
    "Okay",
    "Continue",
    "Consent",
    "Yes, I accept",
    "Reject All",   # fallback — closes the banner even if it declines
    "Reject all",
]

# CSS selectors for known consent frameworks
_COOKIE_SELECTORS = [
    "[id*='accept'][class*='cookie']",
    "[class*='accept'][class*='cookie']",
    "[class*='cookie'] button[class*='accept']",
    "[id*='CybotCookiebotDialogBodyButtonAccept']",   # Cookiebot
    ".cc-accept",                                      # Cookie Consent (Osano)
    "#onetrust-accept-btn-handler",                    # OneTrust
    ".cky-btn-accept",                                 # CookieYes
    "[data-cookiefirst-action='accept']",              # CookieFirst
    "button.fc-cta-consent",                           # Funding Choices
    ".js-accept-cookies",
    ".cmplz-accept",         # Complianz
    ".cmplz-btn",
]


def _dismiss_cookies(page):
    """Try to click a cookie consent dismiss button. Best-effort — never raises."""
    try:
        # Try text-based matching first (most reliable)
        for text in _COOKIE_BUTTON_TEXTS:
            try:
                btn = page.get_by_role("button", name=text, exact=False)
                if btn.count() > 0:
                    btn.first.click(timeout=2000)
                    time.sleep(0.8)
                    return True
            except Exception:
                continue

        # Fall back to known framework selectors
        for sel in _COOKIE_SELECTORS:
            try:
                el = page.locator(sel)
                if el.count() > 0:
                    el.first.click(timeout=2000)
                    time.sleep(0.8)
                    return True
            except Exception:
                continue

    except Exception:
        pass
    return False


def _dismiss_modals(page):
    """Close any modal popups (newsletter, signup, etc.) by clicking × or Close buttons."""
    modal_texts = ["×", "✕", "✗", "Close", "CLOSE", "No thanks", "No, thanks", "Maybe later", "Dismiss"]
    try:
        for text in modal_texts:
            try:
                btn = page.get_by_role("button", name=text, exact=True)
                if btn.count() > 0:
                    btn.first.click(timeout=1500)
                    time.sleep(0.5)
                    return
            except Exception:
                pass
        # Also try common close selectors
        for sel in [".pum-close", ".popmake-close",        # Popup Maker
                    ".modal .close", ".popup .close", "[aria-label='Close']",
                    ".modal__close", ".popup__close", ".divi-popup-close",
                    ".et_pb_popup_close", "[data-dismiss='modal']"]:
            try:
                el = page.locator(sel)
                if el.count() > 0:
                    el.first.click(timeout=1500)
                    time.sleep(0.5)
                    return
            except Exception:
                pass
    except Exception:
        pass


def url_to_filename(url):
    parsed = urlparse(url)
    host = parsed.netloc.replace("www.", "")
    path = parsed.path.strip("/").replace("/", "-") or "home"
    return f"{host}_{path}.png"


def capture_interactive(url, output_path, width, height, full_page):
    """Open a visible browser, let the user dismiss popups, capture on Enter."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False)
        ctx = browser.new_context(viewport={"width": width, "height": height})
        page = ctx.new_page()
        page.goto(url, wait_until="networkidle", timeout=30000)

        print()
        print("  Browser is open. Dismiss any popups or overlays as needed.")
        import sys
        if sys.stdin.isatty():
            print("  Press Enter here when the page is ready to capture...")
            input()
        else:
            print("  Close the browser window when ready to capture.")
            page.wait_for_event("close", timeout=300000)

        page.screenshot(path=str(output_path), full_page=full_page)
        browser.close()


def capture(url, output_path, width, height, wait_s, full_page, dismiss_cookies):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": width, "height": height})

        page.goto(url, wait_until="networkidle", timeout=30000)

        if dismiss_cookies:
            dismissed = _dismiss_cookies(page)
            if dismissed:
                page.wait_for_load_state("networkidle", timeout=5000)
                time.sleep(0.5)

        # Wait first — delayed popups (newsletter, etc.) appear after a few seconds
        if wait_s > 0:
            time.sleep(wait_s)

        # Dismiss modals AFTER the wait so delayed popups have had time to appear
        _dismiss_modals(page)

        # Nuclear fallback: hide any remaining popup overlays via JS
        page.evaluate("""() => {
            const selectors = [
                '.pum-overlay', '.pum-container',   // Popup Maker
                '.ml-popup', '.ml-overlay',          // MailerLite standalone
                '.mfp-wrap', '.mfp-overlay',         // Magnific Popup
                '[class*="popup-overlay"]',
                '[class*="modal-overlay"]',
            ];
            selectors.forEach(sel => {
                document.querySelectorAll(sel).forEach(el => el.remove());
            });
            // Also restore body scroll lock that popups often set
            document.body.style.overflow = '';
            document.documentElement.style.overflow = '';
        }""")
        time.sleep(0.3)

        page.screenshot(path=str(output_path), full_page=full_page)
        browser.close()


def capture_from_browser(output_path, full_page):
    """
    Connect to a running Chrome (launched with --remote-debugging-port=9222)
    and capture the active tab at its current viewport size.
    """
    import urllib.request, json
    from playwright.sync_api import sync_playwright

    # Find the active tab via CDP /json endpoint
    try:
        tabs = json.loads(urllib.request.urlopen("http://localhost:9222/json").read())
    except Exception:
        print("ERROR: Chrome not found on port 9222.")
        print("       Run 'portfolio-chrome' first, then navigate to your page.")
        raise SystemExit(1)

    pages = [t for t in tabs if t.get("type") == "page"]
    if not pages:
        print("ERROR: No page tabs found in Chrome session.")
        raise SystemExit(1)

    ws_url = pages[0]["webSocketDebuggerUrl"]
    print(f"  Connected to: {pages[0].get('url', '')}")

    with sync_playwright() as pw:
        browser = pw.chromium.connect_over_cdp("http://localhost:9222")
        ctx = browser.contexts[0]
        page = ctx.pages[0]
        page.screenshot(path=str(output_path), full_page=full_page)
        # Don't close — let the with block exit cleanly; Chrome stays open


def main():
    p = argparse.ArgumentParser(description="Capture a portfolio screenshot of a website.")
    p.add_argument("url", nargs="?", help="URL to capture (not needed with --from-browser)")
    p.add_argument("output", nargs="?", help="Output PNG path (default: auto-named in cwd)")
    p.add_argument("--width",  type=int, default=1320, help="Viewport width (default 1320)")
    p.add_argument("--height", type=int, default=857,  help="Viewport height (default 857)")
    p.add_argument("--wait",   type=float, default=2.0,
                   help="Extra seconds to wait after load (default 2)")
    p.add_argument("--full-page", action="store_true",
                   help="Capture full scrollable page height")
    p.add_argument("--dismiss-cookies", action="store_true",
                   help="Attempt to click cookie consent banner before capture")
    p.add_argument("--interactive", action="store_true",
                   help="Open visible browser — dismiss popups manually, press Enter to capture")
    p.add_argument("--from-browser", action="store_true",
                   help="Capture from running Chrome (start with portfolio-chrome first)")
    p.add_argument("--mockup", action="store_true",
                   help="Run portfolio-mockup on the result after capture")
    args = p.parse_args()

    if args.from_browser:
        # When using --from-browser, first positional arg is the output path
        raw = args.output or args.url or "screenshot.png"
        out = Path(raw).with_suffix(".png")
    else:
        out = Path(args.output) if args.output else Path(url_to_filename(args.url))
        out = out.with_suffix(".png")

    if args.from_browser:
        print(f"Capturing from browser → {out}")
        capture_from_browser(out, args.full_page)
    elif args.interactive:
        print(f"Opening {args.url}")
        capture_interactive(args.url, out, args.width, args.height, args.full_page)
    else:
        print(f"Capturing {args.url} → {out}")
        capture(args.url, out, args.width, args.height, args.wait,
                args.full_page, args.dismiss_cookies)
    print(f"Done → {out}")

    if args.mockup:
        mockup_out = out.with_name(out.stem + "-mockup.jpg")
        print(f"Running portfolio-mockup → {mockup_out}")
        subprocess.run(["portfolio-mockup", str(out), str(mockup_out)], check=True)
        print(f"Done → {mockup_out}")


if __name__ == "__main__":
    main()
