#!/usr/bin/env python3
"""
gmail_download.py — Download invoice attachments from Gmail to Compres folders.

Auth: OAuth2 Desktop App flow (google-auth-oauthlib).

One-time setup:
  1. In Google Cloud Console (bain-studio project):
     - Enable Gmail API
     - Create OAuth2 Client ID (Desktop app type)
     - Download as credentials.json and place in this directory
  2. Run this script once — a browser window opens to authorise.
     Token is saved to ~/.config/bain-studio/gmail_token_{account}.json

Usage:
    python3 gmail_download.py [--quarter N] [--year YYYY] [--dry-run] [--account ADDR]
"""

from __future__ import annotations

import argparse
import base64
import os
import sys
from datetime import date, timedelta
from pathlib import Path

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from issue_date import issue_date, quarter_of

HERE = Path(__file__).resolve().parent
STUDIO = HERE.parents[1]
load_dotenv(STUDIO / ".env")  # single consolidated env file

FINANCIAL_DIR = Path(
    os.getenv("FINANCIAL_DIR", "/media/data/Dropbox/Work/Admin/Financial/XOR i MB")
)
TOKEN_DIR = Path.home() / ".config" / "bain-studio"
CREDENTIALS_FILE = HERE / "credentials.json"

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

QUARTER_DATES = {
    1: ("01/01", "04/01"),
    2: ("04/01", "07/01"),
    3: ("07/01", "10/01"),
    4: ("10/01", "01/01"),
}

# Grace period: some invoices arrive a few days after quarter end.
GRACE_DAYS = 7

# Real addresses live in studio/.env (gitignored) — placeholders here are
# never meant to resolve to anything; set the IVAS_* vars locally to use this.
GESTOR_EMAIL = os.getenv("IVAS_GESTOR_EMAIL", "gestor@example.com")
MOVISTAR_FORWARD_EMAIL = os.getenv("IVAS_MOVISTAR_FORWARD_EMAIL", "your-personal-email@example.com")
CLOUDWAYS_BILLING_EMAIL = os.getenv("IVAS_CLOUDWAYS_BILLING_EMAIL", "your-cloudways-email@example.com")

# (search_query_fragment, gmail_account, compres_subfolder, filename_template_or_None)
# filename_template: None = use original filename; string = prefix to rename
INVOICE_SOURCES = [
    # --- mark@bain.design ---
    ("from:billing@cloudways.com subject:invoice", "mark@bain.design", "Cloudways", None),
    ("from:customer-service@asana.com", "mark@bain.design", "Asana", None),
    ("from:payments-noreply@google.com", "mark@bain.design", "Google", None),
    ("from:mail.anthropic.com", "mark@bain.design", "Anthropic", None),
    (f"from:{GESTOR_EMAIL} subject:factura", "mark@bain.design", "Gestor", None),
    # Movistar bills are forwarded to mark@bain.design from the account below
    (f"from:{MOVISTAR_FORWARD_EMAIL} subject:\"Tu factura Movistar\"", "mark@bain.design", "Movistar", None),
    # --- Cloudways billing account ---
    ("from:billing@cloudways.com subject:invoice", CLOUDWAYS_BILLING_EMAIL, "Cloudways", None),
    ("from:paddle.com CrashPlan", CLOUDWAYS_BILLING_EMAIL, "Crashplan", None),
]


def quarter_path(q, y):
    return FINANCIAL_DIR / str(y) / f"T{q}-{y}"


def prev_quarter_end_year(q, y):
    if q == 1:
        return (4, y - 1)
    return (q - 1, y)


def get_credentials(account: str) -> Credentials:
    token_path = TOKEN_DIR / f"gmail_token_{account.replace('@', '_').replace('.', '_')}.json"
    TOKEN_DIR.mkdir(parents=True, exist_ok=True)

    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_FILE.exists():
                print(f"\nERROR: credentials.json not found at {CREDENTIALS_FILE}")
                print("\nOne-time setup required:")
                print("  1. Go to https://console.cloud.google.com/apis/credentials")
                print("     (project: bain-studio)")
                print("  2. Create OAuth 2.0 Client ID → Desktop app")
                print(f"  3. Download and save as: {CREDENTIALS_FILE}")
                print("  4. Re-run this script")
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
            print(f"\nAuthorising Gmail access for {account}...")
            creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json())
        print(f"Token saved: {token_path}")

    return creds


def next_quarter(q, y):
    if q == 4:
        return (1, y + 1)
    return (q + 1, y)


def _already_filed(filename: str, folder: str, q: int, y: int) -> tuple[int, int] | None:
    """Quarter (this, previous or next) whose Compres/{folder} already holds filename."""
    for cq, cy in ((q, y), prev_quarter_end_year(q, y), next_quarter(q, y)):
        if (quarter_path(cq, cy) / "Compres" / folder / filename).exists():
            return (cq, cy)
    return None


def search_and_download(service, query: str, after: str, before: str,
                        q: int, y: int, folder: str, dry_run: bool) -> list[str]:
    """Download matching PDF attachments, filing each by its issue date.

    The quarter comes from the invoice's own issue date (issue_date.py), not from when
    it was emailed: Xavi's Q3 invoice dated 30 Sep arrives in October, and a Cloudways
    invoice issued 1 Oct turns up inside the grace window. When no date can be read,
    the email date is used and flagged. Returns the filenames that belong to Q{q} {y}.
    """
    full_query = f"{query} has:attachment after:{after} before:{before}"
    results = service.users().messages().list(userId="me", q=full_query, maxResults=20).execute()
    messages = results.get("messages", [])

    saved = []
    for msg_ref in messages:
        msg = service.users().messages().get(
            userId="me", id=msg_ref["id"], format="full"
        ).execute()

        parts = _get_parts(msg.get("payload", {}))
        for part in parts:
            if part.get("mimeType") != "application/pdf":
                continue
            filename = part.get("filename", "")
            if not filename:
                continue
            attachment_id = part.get("body", {}).get("attachmentId")
            if not attachment_id:
                continue

            filed = _already_filed(filename, folder, q, y)
            if filed:
                where = "" if filed == (q, y) else f" in T{filed[0]}-{filed[1]}"
                print(f"    = {filename} (exists{where})")
                if filed == (q, y):
                    saved.append(filename)
                continue

            # Fetch even on a dry run: the issue date is inside the PDF.
            att = service.users().messages().attachments().get(
                userId="me", messageId=msg_ref["id"], id=attachment_id
            ).execute()
            data = base64.urlsafe_b64decode(att["data"])

            issued = issue_date(data)
            note = ""
            if issued is None:
                issued = date.fromtimestamp(int(msg["internalDate"]) / 1000)
                note = " [no issue date found in PDF - using email date, check it]"
            tq, ty = quarter_of(issued)
            if (tq, ty) != (q, y):
                earlier = (ty, tq) < (y, q)
                note += f" -> T{tq}-{ty}" + (" (earlier quarter - may already be filed)" if earlier else "")

            print(f"    + {filename}  issued {issued.isoformat()}{note}")
            if not dry_run:
                dest_dir = quarter_path(tq, ty) / "Compres" / folder
                dest_dir.mkdir(parents=True, exist_ok=True)
                (dest_dir / filename).write_bytes(data)
                print(f"      saved {len(data) // 1024}KB")
            if (tq, ty) == (q, y):
                saved.append(filename)

    return saved


def _get_parts(payload: dict) -> list[dict]:
    """Recursively collect all message parts."""
    parts = []
    if payload.get("body", {}).get("attachmentId"):
        parts.append(payload)
    for sub in payload.get("parts", []):
        parts.extend(_get_parts(sub))
    return parts


def run(q: int, y: int, dry_run: bool):
    qpath = quarter_path(q, y)
    if not qpath.exists():
        print(f"Quarter folder not found: {qpath}")
        sys.exit(1)

    after, before = QUARTER_DATES[q]
    # Handle Q4 wrapping: before is Jan of next year
    before_year = y + 1 if q == 4 else y
    after_str = f"{y}/{after}"
    # Add grace period: invoices for the last days of the quarter often arrive early next quarter
    before_date = date(before_year, int(before.split("/")[0]), int(before.split("/")[1]))
    before_date += timedelta(days=GRACE_DAYS)
    before_str = before_date.strftime("%Y/%m/%d")

    compres = qpath / "Compres"
    print(f"\nGmail download — Q{q} {y} ({after_str} to {before_str})")
    print(f"Compres: {compres}\n")

    # Group sources by account to minimise auth calls
    by_account: dict[str, list] = {}
    for query, account, folder, _ in INVOICE_SOURCES:
        by_account.setdefault(account, []).append((query, folder))

    totals: dict[str, list] = {}
    for account, sources in by_account.items():
        print(f"Account: {account}")
        creds = get_credentials(account)
        service = build("gmail", "v1", credentials=creds)

        for query, folder in sources:
            print(f"  [{folder}] {query}")
            saved = search_and_download(service, query, after_str, before_str, q, y, folder, dry_run)
            if saved:
                totals.setdefault(folder, []).extend(saved)

    print("\nSummary:")
    for folder, files in sorted(totals.items()):
        for f in files:
            print(f"  [x] {folder}/{f}")
    missing = [src[2] for src in INVOICE_SOURCES if src[2] not in totals]
    for folder in sorted(set(missing)):
        print(f"  [ ] {folder} — no invoices found")


def main():
    parser = argparse.ArgumentParser(description="Download Gmail invoice attachments to Compres")
    parser.add_argument("--quarter", "-q", type=int, choices=[1, 2, 3, 4])
    parser.add_argument("--year", "-y", type=int, default=date.today().year)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    q = args.quarter or ((date.today().month - 1) // 3 + 1)
    run(q, args.year, args.dry_run)


if __name__ == "__main__":
    main()
