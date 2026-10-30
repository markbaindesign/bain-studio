#!/usr/bin/env python3
"""
LinkedIn Post — publish a post to Mark's personal LinkedIn profile via the Posts API.

Usage:
    python3 studio/linkedin_post.py auth                      # one-time OAuth (re-run every ~60 days)
    python3 studio/linkedin_post.py whoami                    # show token owner + expiry
    python3 studio/linkedin_post.py post "text"               # preview only (dry run)
    python3 studio/linkedin_post.py post --file draft.txt --image img.png --alt "..." --yes

`post` never publishes without --yes. Text is plain prose: reserved little-text characters are
escaped automatically and #words become real hashtags.

Setup (studio/.env):
    LINKEDIN_CLIENT_ID=...
    LINKEDIN_CLIENT_SECRET=...
    LINKEDIN_API_VERSION=202609      # optional, YYYYMM; LinkedIn sunsets versions after ~1 year

The developer app needs the "Share on LinkedIn" and "Sign In with LinkedIn using OpenID Connect"
products, and http://localhost:8765/callback registered as an authorized redirect URL.
"""

import argparse
import http.server
import json
import os
import re
import secrets
import sys
import time
import urllib.parse
import webbrowser
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / '.env')

CLIENT_ID = os.getenv('LINKEDIN_CLIENT_ID', '')
CLIENT_SECRET = os.getenv('LINKEDIN_CLIENT_SECRET', '')
API_VERSION = os.getenv('LINKEDIN_API_VERSION', '202609')

TOKEN_PATH = Path.home() / '.config' / 'bain-studio' / 'linkedin_token.json'
REDIRECT_PORT = 8765
REDIRECT_URI = f'http://localhost:{REDIRECT_PORT}/callback'
SCOPES = 'openid profile w_member_social'

AUTH_URL = 'https://www.linkedin.com/oauth/v2/authorization'
TOKEN_URL = 'https://www.linkedin.com/oauth/v2/accessToken'
USERINFO_URL = 'https://api.linkedin.com/v2/userinfo'
API_BASE = 'https://api.linkedin.com/rest'

MAX_COMMENTARY = 3000
EXPIRY_WARN_DAYS = 7

# little text format: these must be backslash-escaped to render as plain text
RESERVED = set('\\|{}@[]()<>#*_~')
HASHTAG_RE = re.compile(r'(?<![\w#])#(\w+)')


class LinkedInError(Exception):
    pass


# ── Text ─────────────────────────────────────────────────────────────────────

def escape_little(text):
    return ''.join('\\' + c if c in RESERVED else c for c in text)


def to_commentary(text):
    """Plain prose → little text. #word becomes a hashtag template, everything else is escaped."""
    out, pos = [], 0
    for m in HASHTAG_RE.finditer(text):
        out.append(escape_little(text[pos:m.start()]))
        out.append('{hashtag|\\#|' + escape_little(m.group(1)) + '}')
        pos = m.end()
    out.append(escape_little(text[pos:]))
    return ''.join(out)


def lint(text):
    """Return warnings about the post text. Empty list means clean."""
    warnings = []
    if '—' in text:
        warnings.append('contains an m-dash (—); studio typography rule says use a hyphen in social posts')
    if len(text) > MAX_COMMENTARY:
        warnings.append(f'{len(text)} characters; LinkedIn truncates/rejects above {MAX_COMMENTARY}')
    tags = HASHTAG_RE.findall(text)
    if len(tags) > 2:
        warnings.append(f'{len(tags)} hashtags; studio voice allows 2 at most')
    return warnings


# ── Token ────────────────────────────────────────────────────────────────────

def load_token():
    if not TOKEN_PATH.exists():
        raise LinkedInError('Not authorised. Run: python3 studio/linkedin_post.py auth')
    token = json.loads(TOKEN_PATH.read_text())
    if token['expires_at'] <= time.time():
        raise LinkedInError('LinkedIn token has expired. Run: python3 studio/linkedin_post.py auth')
    return token


def save_token(token):
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(json.dumps(token, indent=2))
    TOKEN_PATH.chmod(0o600)


def days_left(token):
    return (token['expires_at'] - time.time()) / 86400


# ── OAuth ────────────────────────────────────────────────────────────────────

def _wait_for_code(expected_state):
    result = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            result.update({k: v[0] for k, v in qs.items()})
            ok = 'code' in result and result.get('state') == expected_state
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.end_headers()
            msg = 'LinkedIn authorised. You can close this tab.' if ok else 'Authorisation failed. Check the terminal.'
            self.wfile.write(msg.encode())

        def log_message(self, *args):
            pass

    with http.server.HTTPServer(('localhost', REDIRECT_PORT), Handler) as server:
        server.timeout = 300
        server.handle_request()

    if 'error' in result:
        raise LinkedInError(f"LinkedIn returned {result['error']}: {result.get('error_description', '')}")
    if result.get('state') != expected_state:
        raise LinkedInError('OAuth state mismatch; aborting.')
    if 'code' not in result:
        raise LinkedInError('No authorisation code received (timed out after 5 minutes?).')
    return result['code']


def auth():
    if not CLIENT_ID or not CLIENT_SECRET:
        raise LinkedInError('Set LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET in studio/.env first.')
    state = secrets.token_urlsafe(16)
    url = AUTH_URL + '?' + urllib.parse.urlencode({
        'response_type': 'code', 'client_id': CLIENT_ID, 'redirect_uri': REDIRECT_URI,
        'state': state, 'scope': SCOPES,
    })
    print(f'Opening LinkedIn in your browser. If it does not open, visit:\n{url}\n')
    webbrowser.open(url)
    code = _wait_for_code(state)

    r = requests.post(TOKEN_URL, data={
        'grant_type': 'authorization_code', 'code': code, 'redirect_uri': REDIRECT_URI,
        'client_id': CLIENT_ID, 'client_secret': CLIENT_SECRET,
    }, timeout=30)
    _raise_for(r, 'token exchange')
    data = r.json()

    me = requests.get(USERINFO_URL, headers={'Authorization': f"Bearer {data['access_token']}"}, timeout=30)
    _raise_for(me, 'userinfo lookup')
    info = me.json()

    token = {
        'access_token': data['access_token'],
        'expires_at': int(time.time()) + int(data['expires_in']),
        'person_urn': f"urn:li:person:{info['sub']}",
        'name': info.get('name', ''),
        'scope': data.get('scope', ''),
    }
    save_token(token)
    print(f"Authorised as {token['name']} ({token['person_urn']}). Token valid for {days_left(token):.0f} days.")


# ── API ──────────────────────────────────────────────────────────────────────

def _raise_for(r, what):
    if r.ok:
        return
    detail = r.text[:500]
    if r.status_code == 401:
        detail += '\nToken rejected. Run: python3 studio/linkedin_post.py auth'
    elif r.status_code == 426 or 'NONEXISTENT_VERSION' in r.text:
        detail += f'\nLinkedIn-Version {API_VERSION} may be sunset. Set LINKEDIN_API_VERSION in studio/.env.'
    raise LinkedInError(f'LinkedIn {what} failed ({r.status_code}): {detail}')


def _headers(token):
    return {
        'Authorization': f"Bearer {token['access_token']}",
        'LinkedIn-Version': API_VERSION,
        'X-Restli-Protocol-Version': '2.0.0',
        'Content-Type': 'application/json',
    }


def upload_image(token, path):
    r = requests.post(f'{API_BASE}/images?action=initializeUpload', headers=_headers(token),
                      json={'initializeUploadRequest': {'owner': token['person_urn']}}, timeout=30)
    _raise_for(r, 'image upload init')
    value = r.json()['value']
    up = requests.put(value['uploadUrl'], data=Path(path).read_bytes(),
                      headers={'Authorization': f"Bearer {token['access_token']}"}, timeout=120)
    _raise_for(up, 'image upload')
    return value['image']


def build_post(author, text, image_urn=None, alt=None):
    body = {
        'author': author,
        'commentary': to_commentary(text),
        'visibility': 'PUBLIC',
        'distribution': {'feedDistribution': 'MAIN_FEED', 'targetEntities': [], 'thirdPartyDistributionChannels': []},
        'lifecycleState': 'PUBLISHED',
        'isReshareDisabledByAuthor': False,
    }
    if image_urn:
        media = {'id': image_urn}
        if alt:
            media['altText'] = alt
        body['content'] = {'media': media}
    return body


def publish(token, text, image=None, alt=None):
    image_urn = upload_image(token, image) if image else None
    r = requests.post(f'{API_BASE}/posts', headers=_headers(token),
                      json=build_post(token['person_urn'], text, image_urn, alt), timeout=30)
    _raise_for(r, 'post')
    urn = r.headers.get('x-restli-id', '')
    return urn, f'https://www.linkedin.com/feed/update/{urn}/'


# ── CLI ──────────────────────────────────────────────────────────────────────

def cmd_post(args):
    text = Path(args.file).read_text() if args.file else args.text
    if not text or not text.strip():
        raise LinkedInError('No post text given (pass text or --file).')
    text = text.strip()
    if args.image and not Path(args.image).is_file():
        raise LinkedInError(f'Image not found: {args.image}')

    token = load_token()
    print('─' * 60)
    print(text)
    print('─' * 60)
    meta = f"Author: {token['name']} ({token['person_urn']})  ·  {len(text)} chars"
    if args.image:
        meta += f'  ·  image: {args.image}'
    print(meta)
    for w in lint(text):
        print(f'WARNING: {w}')
    if days_left(token) < EXPIRY_WARN_DAYS:
        print(f'NOTE: LinkedIn token expires in {days_left(token):.1f} days; re-run auth soon.')

    if not args.yes:
        print('\nDry run: nothing posted. Re-run with --yes to publish.')
        return
    urn, url = publish(token, text, args.image, args.alt)
    print(f'\nPublished: {url}')
    if args.json:
        print(json.dumps({'urn': urn, 'url': url}))


def cmd_whoami(_args):
    token = load_token()
    print(f"{token['name']} ({token['person_urn']}), token valid for {days_left(token):.1f} more days")


def main(argv=None):
    p = argparse.ArgumentParser(description='Post to LinkedIn from the studio.')
    sub = p.add_subparsers(dest='cmd', required=True)
    sub.add_parser('auth', help='one-time OAuth login (re-run when the token expires)')
    sub.add_parser('whoami', help='show token owner and expiry')
    pp = sub.add_parser('post', help='preview, or publish with --yes')
    pp.add_argument('text', nargs='?', help='post text (or use --file)')
    pp.add_argument('--file', help='read post text from a file')
    pp.add_argument('--image', help='attach one JPG/PNG/GIF')
    pp.add_argument('--alt', help='alt text for the image')
    pp.add_argument('--yes', action='store_true', help='actually publish (default is dry run)')
    pp.add_argument('--json', action='store_true', help='also print {urn, url} as JSON on success')
    args = p.parse_args(argv)

    try:
        {'auth': lambda a: auth(), 'whoami': cmd_whoami, 'post': cmd_post}[args.cmd](args)
    except LinkedInError as e:
        print(f'ERROR: {e}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
