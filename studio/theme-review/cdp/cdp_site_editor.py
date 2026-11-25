"""Site Editor block validation for a theme review, over the DevTools protocol.

Usage:
    python3 -I cdp_site_editor.py <base-url> <theme-slug> --json FILE [--project DIR]
        [--user ID]

Signs a headless Chromium in as an admin (an auth cookie made by `ddev wp eval` in
--project, default the current directory; --user defaults to 1), opens the Site
Editor, and runs the editor's own validator, as the review template's "Block
validation" section describes:

- every template and template part of <theme-slug> from the REST API, with its
  `source` and `has_theme_file`, so a copy saved in the database is visible;
- `wp.blocks.parse(content.raw)` walked through `innerBlocks`, collecting every block
  with `isValid === false` and its first validation issues;
- every registered pattern named `<theme-slug>/...`, parsed the same way;
- two controls that must come out invalid (a separator without its class, a heading
  whose level disagrees with its tag), so a validator that is not running cannot pass
  for one that found nothing.

`--json FILE` is the review gate's `<slug>-<version>-site-editor.json`. Exit status 0
when the run completed and the controls behaved, whatever it found; 1 when it could
not run or the controls did not come out invalid.
"""
import argparse
import datetime
import json
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cdp_check  # noqa: E402  (Browser)

COOKIE_PHP = r"""
$u = __USER__;
$exp = time() + 3600;
$out = array();
foreach ( array( array( SECURE_AUTH_COOKIE, 'secure_auth', '/wp-admin' ),
                 array( AUTH_COOKIE, 'auth', '/wp-admin' ),
                 array( LOGGED_IN_COOKIE, 'logged_in', '/' ) ) as $c ) {
    $out[] = array( 'name' => $c[0], 'value' => wp_generate_auth_cookie( $u, $exp, $c[1] ), 'path' => $c[2] );
}
echo wp_json_encode( $out );
"""

VALIDATE_JS = r"""
(async function(){
 function walk(bs, acc){ bs.forEach(function(b){
   if (b.isValid === false) acc.push({name: b.name, issues: (b.validationIssues || []).slice(0, 3)
     .map(function(i){ return i.args ? i.args.map(function(a){ return String(a).slice(0, 300); }).join(' | ') : String(i); })});
   walk(b.innerBlocks || [], acc); }); }
 var theme = __THEME__;
 var t = await wp.apiFetch({path: '/wp/v2/templates?per_page=100&context=edit'});
 var p = await wp.apiFetch({path: '/wp/v2/template-parts?per_page=100&context=edit'});
 var items = t.concat(p).filter(function(x){ return x.theme === theme; }).map(function(x){
   var acc = []; walk(wp.blocks.parse(x.content.raw), acc);
   return {id: x.id, type: x.type, source: x.source, has_theme_file: x.has_theme_file,
           invalid: acc.length, blocks: acc}; });
 var pats = await wp.apiFetch({path: '/wp/v2/block-patterns/patterns'});
 var patterns = pats.filter(function(x){ return x.name.indexOf(theme + '/') === 0; }).map(function(x){
   var acc = []; walk(wp.blocks.parse(x.content), acc);
   return {name: x.name, invalid: acc.length, blocks: acc}; });
 var controls = {
   separator_invalid: wp.blocks.parse('<!-- wp:separator --><hr/><!-- /wp:separator -->')[0].isValid === false,
   heading_level_invalid: wp.blocks.parse('<!-- wp:heading {"level":3} --><h2 class="wp-block-heading">x</h2><!-- /wp:heading -->')[0].isValid === false
 };
 return JSON.stringify({templates_and_parts: items, patterns: patterns, controls: controls});
})()
"""


def auth_cookies(project, user):
    r = subprocess.run(["ddev", "wp", "eval", COOKIE_PHP.replace("__USER__", str(int(user)))],
                       cwd=str(project), capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("ddev wp eval failed: %s" % r.stderr.strip()[:300])
    return json.loads(r.stdout.strip().splitlines()[-1])


def summarise(data, theme, version):
    items = data.get("templates_and_parts") or []
    pats = data.get("patterns") or []
    db_copies = [i["id"] for i in items if i.get("source") != "theme" or not i.get("has_theme_file")]
    return {
        "tool": "cdp_site_editor.py",
        "theme": theme,
        "version": version,
        "run_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "controls": data.get("controls") or {},
        "templates_and_parts": items,
        "patterns": pats,
        "database_copies": db_copies,
        "invalid_total": sum(i.get("invalid", 0) for i in items + pats),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("base")
    ap.add_argument("theme")
    ap.add_argument("--json", required=True, help="write the result here (the gate's site-editor file)")
    ap.add_argument("--project", default=".")
    ap.add_argument("--user", type=int, default=1)
    ap.add_argument("--version", default="", help="theme version, recorded in the result")
    a = ap.parse_args(argv)

    base = a.base.rstrip("/")
    host = urlparse(base).hostname
    cookies = auth_cookies(Path(a.project), a.user)
    b = cdp_check.Browser(1440)
    try:
        b.send("Network.enable")
        for c in cookies:
            b.send("Network.setCookie", {"name": c["name"], "value": c["value"], "domain": host,
                                         "path": c["path"], "secure": base.startswith("https"),
                                         "httpOnly": True})
        b.send("Page.navigate", {"url": base + "/wp-admin/site-editor.php"})
        for _ in range(60):
            time.sleep(0.5)
            if b.ev("typeof wp !== 'undefined' && !!wp.apiFetch && !!wp.blocks && "
                    "wp.blocks.getBlockTypes().length > 0"):
                break
        else:
            print("Site Editor did not load signed in (check --user, --project and the URL)",
                  file=sys.stderr)
            return 1
        r = b.send("Runtime.evaluate", {"expression": VALIDATE_JS.replace("__THEME__", json.dumps(a.theme)),
                                        "awaitPromise": True, "returnByValue": True})
        value = r.get("result", {}).get("result", {}).get("value")
        if not value:
            print("validator did not run: %s" % json.dumps(r)[:400], file=sys.stderr)
            return 1
    finally:
        b.close()

    out = summarise(json.loads(value), a.theme, a.version)
    Path(a.json).write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    ctl = out["controls"]
    ok = bool(ctl) and all(ctl.values())
    print("site editor: %d templates and parts, %d patterns, %d invalid block(s), %d database copies"
          % (len(out["templates_and_parts"]), len(out["patterns"]), out["invalid_total"],
             len(out["database_copies"])))
    for i in out["templates_and_parts"] + out["patterns"]:
        for blk in i.get("blocks") or []:
            print("  INVALID %s: %s %s" % (i.get("id") or i.get("name"), blk["name"], "; ".join(blk["issues"])[:200]))
    if not ok:
        print("CONTROLS FAILED: %s - the validator is not running; do not trust this result" % ctl)
    print("written to %s" % a.json)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
