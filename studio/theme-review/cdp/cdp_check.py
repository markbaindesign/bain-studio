"""Rendering and keyboard checks for a theme review, over the DevTools protocol.

Usage:
    python3 -I cdp_check.py <base-url> <theme-slug> [path ...]
        [--widths 390,1440] [--long-title] [--project DIR] [--json FILE]

For every width (390 and 1440 by default, run one after the other) and every path:

- **Overflow**: innerWidth, scrollWidth and the first elements past the right edge.
- **Page keyboard pass**, every time: Tab from the top of the page to the end, then
  Shift+Tab back. Reports the stops, focusable elements in the DOM, stops with no
  visible box, focus outlines under 2px, stops covered by another element, visual
  order inversions (a later stop placed above an earlier one in the same column), and
  whether Shift+Tab is the exact reverse.
- **Menu keyboard pass**, where a nav and opener pair matches and the opener takes
  focus: Tab to the opener, Enter, Tab until focus leaves the nav or cycles inside it,
  then Escape. Reports every link never focused.

`--long-title` runs every check twice, once with the site's own title and once with
a long one, set through `ddev wp` in `--project` (default: the current directory) and
restored afterwards, including on failure.

`--json FILE` writes every result as JSON for the review gate. The printed lines are
the same results for a person.

Two rules this script exists to enforce, both learned the hard way:

1. `mobile: false`. With `mobile: true` Chromium applies a virtual viewport that
   grows until the content fits, so a page with a horizontal overflow reports
   scrollWidth == innerWidth and nothing past the right edge. The test then passes in
   exactly the case it exists to catch. The width read-back is what detects it,
   because the grown viewport is never the width requested.

2. Assert the active theme on every page measured, not once per run. On a shared
   install another session can switch the theme between two halves of one script,
   and the symptom is a selector finding nothing - which reads like a finding and is
   not one.

Anything whose theme or viewport does not check out is reported as ABORT, with no
measurement, and counts against the run's exit status. Every loop ends on a
condition and says which one ended it. The script reports what happened, never what
it means: its output is candidates, not findings.
"""
import argparse
import datetime
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

DEFAULT_WIDTHS = (390, 1440)
HEIGHT = 844
PORT = 9371
LONG_TITLE = ("A Considerably Longer Site Title Than Any Theme Author Tested "
              "With, Still Going")
# Selector pairs (nav container, opener) for the menu pass, tried in order on each
# page; the first pair whose both halves exist is used, so one script covers a classic
# theme and a block theme. Add a theme's own pair at the front when it uses neither.
SELECTOR_SETS = [
    ("#site-navigation", ".menu-toggle"),
    (".wp-block-navigation__responsive-container",
     ".wp-block-navigation__responsive-container-open"),
    ("nav", "button[aria-expanded]"),
]
PAGE_PASS_GUARD = 600
MENU_PASS_GUARD = 200
OPENER_GUARD = 60

THEME_JS = ("(function(){var l=document.querySelector('link[rel=stylesheet][href*=\"/themes/\"]')"
            "||document.querySelector('link[href*=\"/themes/\"]');"
            "return l ? l.href.split('/themes/')[1].split('/')[0] : 'none';})()")

PAST_EDGE_JS = ("JSON.stringify([].slice.call(document.querySelectorAll('body *'))"
                ".filter(function(e){var r=e.getBoundingClientRect();"
                "return r.width>0&&r.right>window.innerWidth+1;}).slice(0,6)"
                ".map(function(e){return e.tagName+'.'+(e.className||'').toString().split(' ')[0];}))")

STOP_JS = """(function(){var e=document.activeElement;if(!e||e===document.body)return null;
  var r=e.getBoundingClientRect(),s=getComputedStyle(e);
  var cx=r.left+r.width/2, cy=r.top+r.height/2;
  var top=(cy>=0&&cy<innerHeight&&cx>=0&&cx<innerWidth)?document.elementFromPoint(cx,cy):null;
  return {tag:e.tagName,txt:(e.innerText||e.value||e.getAttribute('aria-label')||e.name||'').trim().slice(0,30),
    x:Math.round(r.left), y:Math.round(r.top+scrollY), w:Math.round(r.width), h:Math.round(r.height),
    ow:parseFloat(s.outlineWidth)||0, os:s.outlineStyle, vis:r.width>0&&r.height>0&&s.visibility!=='hidden',
    obscured: top ? !(e===top||e.contains(top)||top.contains(e)) : null,
    key: e.outerHTML.slice(0,80)};})()"""

FOCUSABLE_JS = ("document.querySelectorAll('a[href],button,input:not([type=hidden]),"
                "textarea,select').length")


# --------------------------------------------------------------------------
# Pure summaries - unit-tested in studio/tests/test_theme_review_cdp.py
# --------------------------------------------------------------------------

def parse_widths(text):
    widths = []
    for part in str(text).split(","):
        part = part.strip()
        if not part:
            continue
        w = int(part)
        if w <= 0:
            raise ValueError("width must be positive: %r" % part)
        widths.append(w)
    if not widths:
        raise ValueError("no widths given")
    return widths


def page_pass_summary(fwd, back, focusable, ended):
    """Summarise a Tab-forward / Shift+Tab-back pass. `fwd` and `back` are STOP_JS dicts."""
    thin = [s["txt"] for s in fwd if s["ow"] < 2 or s["os"] == "none"]
    inversions = [[a["txt"], b["txt"]] for a, b in zip(fwd, fwd[1:])
                  if b["y"] + b["h"] <= a["y"] - 2 and abs(b["x"] - a["x"]) < 60]
    fwd_keys = [s["key"] for s in fwd]
    back_keys = [s["key"] for s in back]
    # When the forward pass ended by leaving the page or wrapping to the first stop,
    # the back pass should read the forward list reversed, starting at the last stop.
    # After a wrap, focus is on the first stop and the first Shift+Tab may leave the
    # document; page_keyboard_pass skips that one step, so `back` still starts at the
    # last stop. When it ended on the guard, focus is still on the last
    # stop and the first Shift+Tab lands on the one before it.
    expected = fwd_keys[::-1][1:] if ended.startswith("hit the") else fwd_keys[::-1]
    exact = bool(fwd) and back_keys[:len(expected)] == expected and len(back_keys) >= len(expected)
    return {
        "ended": ended,
        "stops": len(fwd),
        "focusable_in_dom": focusable,
        "first": fwd[0]["txt"] if fwd else None,
        "invisible": [s["txt"] for s in fwd if not s["vis"]],
        "outline_lt_2px": thin,
        "obscured": [s["txt"] for s in fwd if s["obscured"]],
        "order_inversions": inversions,
        "shift_tab_exact_reverse": exact,
    }


def menu_pass_summary(nav, opener, seen, bad, in_dom, ended, escape_returns):
    missing = [x for x in in_dom if x not in seen]
    return {
        "nav": nav,
        "opener": opener,
        "ended": ended,
        "stops": len(seen),
        "links_in_nav": len(in_dom),
        "links_reached": len(in_dom) - len(missing),
        "never_focused": missing,
        "no_ring_or_out_of_view": bad,
        "escape_returns_to_opener": escape_returns,
    }


def page_line(r):
    """One printed line per page result, the same facts as the JSON."""
    head = "%s @%s [%s title]" % (r["path"], r["width"], r["title"])
    if r["status"] == "abort":
        return "%s ABORT %s" % (head, r["reason"])
    lines = ["%s theme=%s innerWidth=%s scrollWidth=%s past_edge=%s" % (
        head, r["theme"], r["inner_width"], r["scroll_width"], json.dumps(r["past_edge"]))]
    k = r["keyboard"]
    lines.append("  page keyboard: %d stops of %d focusable (%s), first %s, invisible %s, "
                 "outline<2px %s, obscured %s, order inversions %s, shift+tab exact reverse %s" % (
                     k["stops"], k["focusable_in_dom"], k["ended"], json.dumps(k["first"]),
                     json.dumps(k["invisible"]), json.dumps(k["outline_lt_2px"][:10]),
                     json.dumps(k["obscured"][:10]), json.dumps(k["order_inversions"][:10]),
                     k["shift_tab_exact_reverse"]))
    m = r["menu"]
    if m.get("skipped"):
        lines.append("  menu keyboard: %s" % m["skipped"])
    else:
        # Stops and links are counted separately: a close button is a stop, not a link,
        # so "6 of 5" would read like a defect. The exact claim is the missing list.
        lines.append("  menu keyboard: using %s / %s, %d stops covering %d of %d links (%s), "
                     "never focused %s, no focus ring or out of view %s, escape returns to opener %s" % (
                         m["nav"], m["opener"], m["stops"], m["links_reached"], m["links_in_nav"],
                         m["ended"], json.dumps(m["never_focused"]),
                         json.dumps(m["no_ring_or_out_of_view"]), m["escape_returns_to_opener"]))
    return "\n".join(lines)


def run_record(base, theme, widths, paths, long_title, pages):
    return {
        "tool": "cdp_check",
        "generated": datetime.datetime.now().isoformat(timespec="seconds"),
        "base": base,
        "theme": theme,
        "widths": widths,
        "paths": paths,
        "long_title": long_title,
        "aborted": sum(1 for p in pages if p["status"] == "abort"),
        "pages": pages,
    }


# --------------------------------------------------------------------------
# Browser
# --------------------------------------------------------------------------

class Browser:
    def __init__(self, width):
        import websocket  # imported here so the summaries above test without it

        self.width = width
        self.proc = subprocess.Popen(
            ["chromium-browser", "--headless", "--disable-gpu", "--no-sandbox",
             "--ignore-certificate-errors", "--hide-scrollbars",
             "--remote-debugging-port=%d" % PORT, "--window-size=%d,%d" % (width, HEIGHT),
             "about:blank"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        url = None
        for _ in range(60):
            try:
                pages = [t for t in json.load(urllib.request.urlopen(
                    "http://127.0.0.1:%d/json" % PORT)) if t.get("type") == "page"]
                if pages:
                    url = pages[0]["webSocketDebuggerUrl"]
                    break
            except Exception:
                pass
            time.sleep(0.3)
        if not url:
            self.proc.kill()
            raise RuntimeError("no debugger target on port %d" % PORT)
        self.ws = websocket.create_connection(url, timeout=60)
        self.n = 0
        self.send("Page.enable")

    def send(self, method, params=None):
        self.n += 1
        self.ws.send(json.dumps({"id": self.n, "method": method, "params": params or {}}))
        while True:
            r = json.loads(self.ws.recv())
            if r.get("id") == self.n:
                return r

    def ev(self, expr):
        return self.send("Runtime.evaluate", {"expression": expr, "returnByValue": True})[
            "result"]["result"].get("value")

    def key(self, name, code, vk, text=None, shift=False):
        p = {"type": "keyDown" if text else "rawKeyDown", "key": name, "code": code,
             "windowsVirtualKeyCode": vk, "nativeVirtualKeyCode": vk,
             "modifiers": 8 if shift else 0}
        if text:
            p["text"] = text
        self.send("Input.dispatchKeyEvent", p)
        up = {k: v for k, v in p.items() if k != "text"}
        up["type"] = "keyUp"
        self.send("Input.dispatchKeyEvent", up)
        time.sleep(0.06)

    def tab(self, shift=False):
        self.key("Tab", "Tab", 9, shift=shift)

    def load(self, url):
        self.send("Emulation.setDeviceMetricsOverride",
                  {"width": self.width, "height": HEIGHT, "deviceScaleFactor": 1, "mobile": False})
        self.send("Page.navigate", {"url": url})
        time.sleep(3.5)
        self.send("Emulation.setDeviceMetricsOverride",
                  {"width": self.width, "height": HEIGHT, "deviceScaleFactor": 1, "mobile": False})
        time.sleep(0.8)

    def close(self):
        try:
            self.ws.close()
        finally:
            self.proc.kill()
            self.proc.wait()


def page_keyboard_pass(b):
    fwd, ended = [], "hit the %d-stop runaway guard" % PAGE_PASS_GUARD
    for _ in range(PAGE_PASS_GUARD):
        b.tab()
        s = b.ev(STOP_JS)
        if s is None:
            ended = "focus left the page"
            break
        if len(fwd) > 1 and s["key"] == fwd[0]["key"]:
            ended = "focus came round to the first stop"
            break
        fwd.append(s)
    back = []
    # A walk that came round to the first stop leaves focus there, so the first
    # Shift+Tab can step out of the document before re-entering at the last stop.
    # That one leading None is not the end of the back pass (BSTD-915).
    may_skip = ended == "focus came round to the first stop"
    for _ in range(len(fwd) + (1 if may_skip else 0)):
        b.tab(shift=True)
        s = b.ev(STOP_JS)
        if s is None:
            if may_skip and not back:
                may_skip = False
                continue
            break
        back.append(s)
        if len(back) == len(fwd):
            break
    return page_pass_summary(fwd, back, b.ev(FOCUSABLE_JS), ended)


def menu_keyboard_pass(b):
    nav = opener = None
    for nav_sel, open_sel in SELECTOR_SETS:
        if b.ev("!!document.querySelector('%s') && !!document.querySelector('%s')" % (nav_sel, open_sel)):
            nav, opener = nav_sel, open_sel
            break
    if not nav:
        return {"skipped": "no nav and opener pair matched on this page"}
    for _ in range(OPENER_GUARD):
        b.tab()
        if b.ev("document.activeElement.matches('%s')" % opener):
            break
    else:
        # Says what happened, not what it means: at desktop width the opener is usually
        # hidden by design.
        return {"skipped": "using %s / %s: opener never took focus in %d Tab presses" % (
            nav, opener, OPENER_GUARD), "nav": nav, "opener": opener}
    b.key("Enter", "Enter", 13, "\r")
    time.sleep(0.6)
    probe = ("(function(){var a=document.activeElement,nav=document.querySelector('%s');"
             "if(!a||!nav.contains(a))return JSON.stringify({out:true});"
             "var cs=getComputedStyle(a),r=a.getBoundingClientRect(),nr=nav.getBoundingClientRect();"
             "var was=a.dataset.cdpSeen==='1';a.dataset.cdpSeen='1';"
             "return JSON.stringify({text:(a.textContent||'').trim().slice(0,30),cycled:was,"
             "ok:(a.matches(':focus-visible')&&cs.outlineStyle!=='none'"
             "&&r.top>=nr.top-1&&r.bottom<=nr.bottom+1&&r.top>=0&&r.bottom<=window.innerHeight)});})()") % nav
    seen, bad, ended = [], [], "hit the %d-element runaway guard" % MENU_PASS_GUARD
    while len(seen) < MENU_PASS_GUARD:
        b.tab()
        d = json.loads(b.ev(probe))
        if d.get("out"):
            ended = "focus left the nav"
            break
        if d.get("cycled"):
            # A focus trap in the open panel cycles rather than letting focus out.
            ended = "focus cycled back inside the panel"
            break
        seen.append(d["text"])
        if not d["ok"]:
            bad.append(d["text"])
    in_dom = json.loads(b.ev("JSON.stringify([].slice.call(document.querySelectorAll('%s a'))"
                             ".map(function(a){return a.textContent.trim().slice(0,30);}))" % nav))
    b.key("Escape", "Escape", 27)
    time.sleep(0.4)
    return menu_pass_summary(nav, opener, seen, bad, in_dom, ended,
                             b.ev("document.activeElement.matches('%s')" % opener))


def check_page(b, base, theme, path, title_kind):
    rec = {"path": path, "width": b.width, "title": title_kind}

    def verified():
        got_theme, inner = b.ev(THEME_JS), b.ev("window.innerWidth")
        if got_theme != theme or inner != b.width:
            rec.update(status="abort", reason="theme=%s innerWidth=%s" % (got_theme, inner))
            return False
        return True

    b.load(base + path)
    if not verified():
        return rec
    rec.update(status="ok", theme=theme, inner_width=b.width,
               scroll_width=b.ev("document.documentElement.scrollWidth"),
               past_edge=json.loads(b.ev(PAST_EDGE_JS)))
    rec["keyboard"] = page_keyboard_pass(b)
    # Fresh load for the menu pass, so the page pass's focus and scroll do not carry over,
    # and the theme asserted again because the reload is a new measurement.
    b.load(base + path)
    if not verified():
        rec.pop("keyboard", None)
        return rec
    rec["menu"] = menu_keyboard_pass(b)
    return rec


# --------------------------------------------------------------------------
# Site title
# --------------------------------------------------------------------------

def wp_option(project, *args):
    r = subprocess.run(["ddev", "wp", "option"] + list(args), cwd=str(project),
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("ddev wp option %s failed: %s" % (" ".join(args), r.stderr.strip()))
    return r.stdout.strip()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("base")
    ap.add_argument("theme")
    ap.add_argument("paths", nargs="*", default=["/"])
    ap.add_argument("--widths", default=",".join(str(w) for w in DEFAULT_WIDTHS),
                    help="comma-separated, default 390,1440")
    ap.add_argument("--long-title", action="store_true",
                    help="run everything again with a long site title, restored afterwards")
    ap.add_argument("--project", default=".", help="DDEV project for --long-title (default: cwd)")
    ap.add_argument("--json", dest="json_out", help="write the results here as JSON")
    a = ap.parse_args(argv)
    base = a.base.rstrip("/")
    widths = parse_widths(a.widths)
    paths = a.paths or ["/"]

    pages = []

    def sweep(title_kind):
        for w in widths:
            b = Browser(w)
            try:
                for path in paths:
                    rec = check_page(b, base, a.theme, path, title_kind)
                    print(page_line(rec), flush=True)
                    pages.append(rec)
            finally:
                b.close()

    sweep("default")
    if a.long_title:
        original = wp_option(a.project, "get", "blogname")
        try:
            wp_option(a.project, "update", "blogname", LONG_TITLE)
            sweep("long")
        finally:
            wp_option(a.project, "update", "blogname", original)
            print("site title restored to %s" % json.dumps(original))

    record = run_record(base, a.theme, widths, paths, a.long_title, pages)
    if a.json_out:
        Path(a.json_out).write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
        print("json written to %s" % a.json_out)
    return 1 if record["aborted"] else 0


if __name__ == "__main__":
    sys.exit(main())
