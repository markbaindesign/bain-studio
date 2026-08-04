#!/usr/bin/env python3
"""
ivas-prep.py — IVA quarterly preparation tool

1. Scaffolds Vendes/ and Compres/{subfolders} for the quarter
2. Downloads invoice PDFs from Harvest API → Vendes/
3. Sorts loose PDFs in the quarter root into the right child folders

Gmail step is handled by the /ivas-prep skill (requires MCP tools).

Usage:
    python3 studio/tools/ivas-prep/ivas-prep.py [--quarter N] [--year YYYY] [--dry-run]
"""

import argparse
import os
import re
import shutil
import sys
from datetime import date
from pathlib import Path

import requests
from dotenv import load_dotenv

# Load credentials — single consolidated env file (has HARVEST_TOKEN)
HERE = Path(__file__).resolve().parents[2]  # → bain-studio/studio/
load_dotenv(HERE / ".env")

HARVEST_TOKEN = os.getenv("HARVEST_TOKEN", "")
HARVEST_ACCOUNT_ID = os.getenv("HARVEST_ACCOUNT_ID", "")
FINANCIAL_DIR = Path(
    os.getenv("FINANCIAL_DIR", "/media/data/Dropbox/Work/Admin/Financial/XOR i MB")
)

QUARTER_DATES = {
    1: ("01-01", "03-31"),
    2: ("04-01", "06-30"),
    3: ("07-01", "09-30"),
    4: ("10-01", "12-31"),
}

DEFAULT_COMPRES_FOLDERS = [
    "Algolia", "Amazon", "Anthropic", "Asana", "Autonomos",
    "Cloudways", "Crashplan", "Gestor", "Github", "Google",
    "Harvest", "Misc", "Movistar", "Namecheap", "Upwork",
]

# Filename patterns → Compres subfolder (case-insensitive)
COMPRES_PATTERNS = [
    (r"cloudways", "Cloudways"),
    (r"anthropic|claude", "Anthropic"),
    (r"asana", "Asana"),
    (r"github|copilot", "Github"),
    (r"google", "Google"),
    (r"movistar", "Movistar"),
    (r"crashplan|digital.river", "Crashplan"),
    (r"algolia", "Algolia"),
    (r"namecheap", "Namecheap"),
    (r"harvest", "Harvest"),
    (r"upwork", "Upwork"),
    (r"amazon", "Amazon"),
    (r"gestor|gabinete|xavi", "Gestor"),
    (r"vimeo", "Vimeo"),
    (r"gitkraken", "Gitkraken"),
    (r"forecast", "Forecast"),
    (r"autonomos|autonoms|seguridad.social", "Autonomos"),
]

VENDES_PATTERN = re.compile(r"INVOICE_\d+_Mark_Crawford_Bain\.pdf", re.IGNORECASE)


def current_quarter():
    m = date.today().month
    return (m - 1) // 3 + 1


def quarter_path(q, y):
    return FINANCIAL_DIR / str(y) / f"T{q}-{y}"


def prev_quarter(q, y):
    return (4, y - 1) if q == 1 else (q - 1, y)


def get_compres_folders(q, y):
    pq, py = prev_quarter(q, y)
    prev = quarter_path(pq, py) / "Compres"
    if prev.exists():
        folders = sorted(d.name for d in prev.iterdir() if d.is_dir())
        return folders, f"T{pq}-{py}"
    return DEFAULT_COMPRES_FOLDERS, "defaults"


def scaffold(q, y, dry_run=False):
    qpath = quarter_path(q, y)
    if not qpath.exists():
        print(f"Quarter folder not found: {qpath}")
        sys.exit(1)

    vendes = qpath / "Vendes"
    compres = qpath / "Compres"
    folders, source = get_compres_folders(q, y)

    print(f"\nScaffolding {qpath.name} (Compres from {source})")

    for folder in [vendes, compres]:
        if not folder.exists():
            if not dry_run:
                folder.mkdir(parents=True, exist_ok=True)
            print(f"  + {folder.name}/")
        else:
            print(f"  = {folder.name}/ (exists)")

    for sf in folders:
        dest = compres / sf
        if not dest.exists():
            if not dry_run:
                dest.mkdir(exist_ok=True)
            print(f"  + Compres/{sf}/")

    return vendes, compres


def download_harvest_invoices(q, y, vendes, dry_run=False):
    """Download invoice PDFs from Harvest using the client_key public PDF URL."""
    if not HARVEST_TOKEN or not HARVEST_ACCOUNT_ID:
        print("\nHarvest not configured — skipping")
        return [], []

    start, end = QUARTER_DATES[q]
    from_date = f"{y}-{start}"
    to_date = f"{y}-{end}"

    print(f"\nHarvest invoices {from_date} to {to_date}")

    headers = {
        "Authorization": f"Bearer {HARVEST_TOKEN}",
        "Harvest-Account-Id": HARVEST_ACCOUNT_ID,
        "User-Agent": "BainStudio-IVASPrep/1.0",
    }

    r = requests.get(
        "https://api.harvestapp.com/v2/invoices",
        headers=headers,
        params={"from": from_date, "to": to_date, "per_page": 100},
        timeout=15,
    )
    r.raise_for_status()
    invoices = r.json().get("invoices", [])
    print(f"  {len(invoices)} invoice(s) found")

    present, missing = [], []
    for inv in invoices:
        number = inv.get("number", str(inv["id"]))
        client = inv.get("client", {}).get("name", "unknown")
        amount = inv.get("amount", 0)
        currency = inv.get("currency", "EUR")
        client_key = inv.get("client_key", "")
        fname = f"INVOICE_{number}_Mark_Crawford_Bain.pdf"
        dest = vendes / fname

        if dest.exists():
            print(f"  = {fname} ({client})")
            present.append(fname)
            continue

        print(f"  + {fname}  {client}  {currency} {amount:.2f}")
        if not dry_run and client_key:
            pdf_r = requests.get(
                f"https://baindesign.harvestapp.com/client/invoices/{client_key}.pdf",
                timeout=30,
            )
            if pdf_r.status_code == 200 and "pdf" in pdf_r.headers.get("Content-Type", ""):
                dest.write_bytes(pdf_r.content)
                print(f"    saved {len(pdf_r.content) // 1024}KB")
                present.append(fname)
            else:
                print(f"    failed: {pdf_r.status_code}")
                missing.append(fname)
        else:
            missing.append(fname)

    return present, missing


def classify_loose(filename):
    """Return ('vendes'|'compres', subfolder_or_None) for a loose PDF."""
    if VENDES_PATTERN.match(filename):
        return "vendes", None
    name_lower = filename.lower()
    for pattern, folder in COMPRES_PATTERNS:
        if re.search(pattern, name_lower):
            return "compres", folder
    return "compres", "Misc"


def sort_loose(q, y, vendes, compres, dry_run=False):
    qpath = quarter_path(q, y)
    loose = [f for f in qpath.iterdir() if f.is_file() and f.suffix.lower() == ".pdf"]
    if not loose:
        print("\nNo loose PDFs to sort")
        return

    print(f"\nSorting {len(loose)} loose PDF(s)")
    for f in loose:
        category, subfolder = classify_loose(f.name)
        if category == "vendes":
            dest = vendes / f.name
        else:
            target_dir = compres / subfolder
            if not target_dir.exists() and not dry_run:
                target_dir.mkdir(exist_ok=True)
            dest = target_dir / f.name

        rel = dest.relative_to(qpath)
        if dest.exists():
            print(f"  = {f.name} already at {rel.parent}/")
        else:
            print(f"  -> {f.name} -> {rel.parent}/")
            if not dry_run:
                shutil.move(str(f), str(dest))


def main():
    parser = argparse.ArgumentParser(description="IVA quarterly prep")
    parser.add_argument("--quarter", "-q", type=int, choices=[1, 2, 3, 4])
    parser.add_argument("--year", "-y", type=int, default=date.today().year)
    parser.add_argument("--dry-run", action="store_true", help="Preview only, no changes")
    parser.add_argument("--gmail", action="store_true", help="Also download Gmail invoice attachments")
    args = parser.parse_args()

    q = args.quarter or current_quarter()
    y = args.year
    dry = args.dry_run

    print(f"IVA Prep — Q{q} {y}" + (" [DRY RUN]" if dry else ""))

    vendes, compres = scaffold(q, y, dry)
    download_harvest_invoices(q, y, vendes, dry)
    sort_loose(q, y, vendes, compres, dry)

    if args.gmail:
        try:
            from gmail_download import run as gmail_run
            gmail_run(q, y, dry)
        except ImportError as e:
            print(f"\nGmail download unavailable: {e}")
            print("Run: python3 studio/tools/ivas-prep/gmail_download.py --quarter", q)
    else:
        print("\nDone. Run with --gmail to also pull expense invoices from Gmail.")
        print("  (requires credentials.json — see gmail_download.py for setup)")


if __name__ == "__main__":
    main()
