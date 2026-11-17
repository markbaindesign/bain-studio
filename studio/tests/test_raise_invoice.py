import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "tools" / "raise-invoice"))

from raise_invoice import (base_payload, bucket_uninvoiced, build_notes, payment_block,
                           pick_currency, suggest_type, summarise_entries, upwork_period,
                           vat_numbers)

PAYMENT = "*Payment details*\nEUR: IBAN XX00 0000"
RC_NOTES = ("Reverse charge: VAT to be accounted for by the recipient.\n"
            "Supplier VAT: ESX0000000X - Customer VAT: NL000000000B01\n\n"
            "_Please quote the invoice number as a reference_\n\n" + PAYMENT)


def test_suggest_type_uses_newest_invoice_first():
    history = [
        {"notes": "WordPress development services via Upwork - 1 May 2026 to 31 May 2026"},
        {"notes": RC_NOTES},
    ]
    assert suggest_type(history) == "upwork"
    assert suggest_type([{"tax": 21.0, "notes": PAYMENT}]) == "es"
    assert suggest_type([{"notes": RC_NOTES}]) == "eu"
    assert suggest_type([{"notes": PAYMENT}]) is None
    assert suggest_type([]) is None


def test_vat_numbers_from_reverse_charge_note():
    assert vat_numbers([{"notes": PAYMENT}, {"notes": RC_NOTES}]) == ("ESX0000000X", "NL000000000B01")
    assert vat_numbers([{"notes": None}]) is None


def test_payment_block_starts_at_payment_details():
    assert payment_block([{"notes": "via Upwork"}, {"notes": RC_NOTES}]) == PAYMENT
    assert payment_block([{"notes": None}]) is None


def test_upwork_period():
    assert upwork_period(None, None) == "WordPress development services via Upwork"
    assert upwork_period("2026-05-01", "2026-05-31") == \
        "WordPress development services via Upwork - 1 May 2026 to 31 May 2026"


def test_build_notes_per_type():
    intl = build_notes("intl", PAYMENT)
    assert intl.startswith("_Please quote") and intl.endswith(PAYMENT)
    eu = build_notes("eu", PAYMENT, ("ESX0000000X", "NL1"))
    assert "Supplier VAT: ESX0000000X - Customer VAT: NL1" in eu and PAYMENT in eu
    upwork = build_notes("upwork", None, from_date="2026-05-01", to_date="2026-05-31")
    assert upwork == "WordPress development services via Upwork - 1 May 2026 to 31 May 2026"
    # A Dutch B.V. client via Upwork keeps the reverse-charge block, still no payment details
    upwork_rc = build_notes("upwork", None, ("ESX0000000X", "NL1"), reverse_charge=True)
    assert "Customer VAT: NL1" in upwork_rc and "Payment details" not in upwork_rc


def test_build_notes_refuses_missing_parts():
    with pytest.raises(ValueError, match="customer's VAT"):
        build_notes("eu", PAYMENT, None)
    with pytest.raises(ValueError, match="studio's VAT"):
        build_notes("eu", PAYMENT, (None, "NL1"))
    with pytest.raises(ValueError, match="payment-details"):
        build_notes("intl", None)


def test_pick_currency_prefers_last_invoice_of_same_kind():
    client = {"currency": "USD"}
    history = [
        {"number": "910", "currency": "USD", "notes": "via Upwork"},
        {"number": "905", "currency": "EUR", "notes": PAYMENT},
    ]
    currency, warning = pick_currency(client, history, "eu")
    assert currency == "EUR" and "905" in warning
    assert pick_currency(client, history, "upwork") == ("USD", None)
    assert pick_currency(client, [], "intl") == ("USD", None)
    assert pick_currency(client, history, "eu", override="GBP") == ("GBP", None)


def test_base_payload_tax_and_subject():
    es = base_payload({"id": 1}, "es", "n", "2026-10-19", "EUR")
    assert (es["tax"], es["tax2"]) == (21.0, -15.0)
    assert es["subject"] and es["payment_term"] == "upon receipt"
    upwork = base_payload({"id": 1}, "upwork", "n", "2026-10-19", "USD")
    assert upwork["tax"] is None and "subject" not in upwork


def test_summarise_entries_uses_rounded_hours():
    entries = [
        {"hours": 1.1, "rounded_hours": 1.25, "billable_rate": 60, "task": {"name": "Development"}},
        {"hours": 0.5, "rounded_hours": None, "billable_rate": 60, "task": {"name": "Development"}},
        {"hours": 1.0, "rounded_hours": 1.0, "billable_rate": None, "task": {"name": "Meeting"}},
    ]
    assert summarise_entries(entries) == {"Development": (1.75, 105.0), "Meeting": (1.0, 0.0)}


def test_bucket_uninvoiced():
    def row(pid, hrs, amt, invoiced=0):
        return {"project_id": pid, "uninvoiced_hours": hrs, "uninvoiced_amount": amt,
                "invoiced_amount": invoiced}

    rows = [
        row(1, 2.0, 100),            # ready
        row(2, 3.0, 300),            # ready, larger: sorts first
        row(3, 1.0, 50, invoiced=500),  # partial
        row(4, 2.75, 2950),          # fixed fee
        row(5, 0.0, -108.88),        # credit
        row(6, 0.0, 0),              # nothing to bill
        row(7, 0.1, 6),              # rounding noise
    ]
    ready, partial, fixed, credits = bucket_uninvoiced(rows, fixed_fee_ids={4})
    assert [r["project_id"] for r in ready] == [2, 1]
    assert [r["project_id"] for r in partial] == [3]
    assert [r["project_id"] for r in fixed] == [4]
    assert [r["project_id"] for r in credits] == [5]
    ready, *_ = bucket_uninvoiced(rows, fixed_fee_ids={4}, include_small=True)
    assert 7 in [r["project_id"] for r in ready]
