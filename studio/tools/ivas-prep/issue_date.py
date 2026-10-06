"""
issue_date.py — Read an invoice's issue date from its PDF text.

The quarter an invoice belongs to is decided by its issue date, not by when it was
emailed or which period it bills (see docs/Finances/iva-mod303.md). Gmail delivers some
invoices days after quarter end, so the downloader uses this to file each one correctly.

Uses `pdftotext -layout` (poppler-utils). Handles English, Spanish and Catalan
month-name dates. Numeric dates (9/30/2026) are ignored: day/month order differs
between suppliers, so a guess could file an invoice in the wrong quarter.
"""

from __future__ import annotations

import re
import subprocess
from datetime import date
from pathlib import Path

MONTHS = {
    # English
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7, "aug": 8,
    "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
    # Spanish
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7,
    "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10, "noviembre": 11,
    "diciembre": 12,
    # Catalan
    "gener": 1, "febrer": 2, "març": 3, "marc": 3, "maig": 5, "juny": 6, "juliol": 7,
    "agost": 8, "setembre": 9, "octubre": 10, "novembre": 11, "desembre": 12,
}

_MONTH = r"([A-Za-zçÇ]{3,10})\.?"
# "August 1, 2026" / "Jul 10, 2026"
_MDY = re.compile(_MONTH + r"\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(20\d{2})")
# "9th September 2026" / "01 de Julio de 2026" / "20 de juliol del 2026" / "17 d’abril del 2026"
_DMY = re.compile(r"(\d{1,2})(?:st|nd|rd|th)?\s+(?:de\s+|d['’])?" + _MONTH + r"\s+(?:del?\s+)?(20\d{2})")

# Labels that introduce the issue date, most specific first. The date is looked for on
# the rest of the same line.
LABELS = [
    r"date of issue",
    r"invoice date",
    r"fecha de (?:la )?factura",
    r"fecha de emisi[oó]n",
    r"data de la factura",
    r"billed on",
    r"date paid",
    r"data,",
]


def _to_date(month_word: str, day: str, year: str) -> date | None:
    month = MONTHS.get(month_word.lower())
    if not month:
        return None
    try:
        return date(int(year), month, int(day))
    except ValueError:
        return None


def find_date(text: str) -> date | None:
    """First month-name date in `text`, or None."""
    hits = []
    for m in _MDY.finditer(text):
        d = _to_date(m.group(1), m.group(2), m.group(3))
        if d:
            hits.append((m.start(), d))
    for m in _DMY.finditer(text):
        d = _to_date(m.group(2), m.group(1), m.group(3))
        if d:
            hits.append((m.start(), d))
    return min(hits)[1] if hits else None


def issue_date_from_text(text: str) -> date | None:
    """Issue date from invoice text: a labelled date if present, else the first date."""
    for label in LABELS:
        for m in re.finditer(label, text, re.IGNORECASE):
            line_end = text.find("\n", m.end())
            d = find_date(text[m.end(): line_end if line_end != -1 else None])
            if d:
                return d
    return find_date(text)


def pdf_text(pdf: Path | bytes) -> str:
    """Text of a PDF (path or raw bytes) via pdftotext; empty string on failure."""
    try:
        if isinstance(pdf, (bytes, bytearray)):
            out = subprocess.run(["pdftotext", "-layout", "-", "-"], input=bytes(pdf),
                                 capture_output=True, timeout=30)
        else:
            out = subprocess.run(["pdftotext", "-layout", str(pdf), "-"],
                                 capture_output=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return out.stdout.decode("utf-8", errors="replace") if out.returncode == 0 else ""


def issue_date(pdf: Path | bytes) -> date | None:
    return issue_date_from_text(pdf_text(pdf))


def quarter_of(d: date) -> tuple[int, int]:
    return (d.month - 1) // 3 + 1, d.year


if __name__ == "__main__":
    import sys
    for arg in sys.argv[1:]:
        print(f"{issue_date(Path(arg))}  {arg}")
