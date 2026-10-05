import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "tools" / "ivas-prep"))

from issue_date import issue_date_from_text, quarter_of


def test_labelled_dates_in_supplier_layouts():
    # DigitalOcean/Cloudways: issued after the period it bills
    text = ("Final invoice for the September 2026 billing period\n"
            "105 Edgeview Drive, Suite 425      Date of issue:      October 1, 2026\n")
    assert issue_date_from_text(text) == date(2026, 10, 1)
    # Asana
    assert issue_date_from_text("Mark Bain Design   Billed On Jul 10, 2026") == date(2026, 7, 10)
    # Google: the billing summary line must not win over the label
    text = "Summary for Jul 1, 2026 - Jul 31, 2026\nInvoice date Jul 31, 2026   Total in EUR"
    assert issue_date_from_text(text) == date(2026, 7, 31)
    # Anthropic receipt
    assert issue_date_from_text("Date paid July 21, 2026") == date(2026, 7, 21)


def test_spanish_and_catalan_dates():
    # Gestor (Catalan), including the curly apostrophe form
    assert issue_date_from_text("   Data, 30 de setembre del 2026") == date(2026, 9, 30)
    assert issue_date_from_text("   Data, 17 d’abril del 2026") == date(2026, 4, 17)
    # Movistar: unlabelled, first date on the page
    text = " 01 de Julio de 2026   Página 1 de 2\n FM1VMGJ0416402 (18 May - 17 Jun)"
    assert issue_date_from_text(text) == date(2026, 7, 1)
    # Amazon.es
    text = "Fecha de la factura/Fecha de la entrega 22 septiembre 2026"
    assert issue_date_from_text(text) == date(2026, 9, 22)


def test_ordinal_day_first():
    # Crashplan via Paddle
    assert issue_date_from_text("9th September 2026 - $48.35 via Paddle.com") == date(2026, 9, 9)


def test_numeric_dates_are_not_guessed():
    assert issue_date_from_text("Invoice Date   Invoice No.\n31-01-26   7127670") is None
    assert issue_date_from_text("Invoice Date 9/30/2026") is None


def test_quarter_of():
    assert quarter_of(date(2026, 9, 30)) == (3, 2026)
    assert quarter_of(date(2026, 10, 1)) == (4, 2026)
    assert quarter_of(date(2025, 12, 31)) == (4, 2025)
