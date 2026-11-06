#!/usr/bin/env python3
"""
raise_invoice.py — check uninvoiced hours and raise Harvest draft invoices

Harvest is where invoices live: it numbers them, renders the PDF, sends them and
tracks payment. This tool only ever creates *drafts*. It never calls the send
endpoint and never marks an invoice sent — Mark reviews the draft in Harvest and
sends it from there (the Law of the Gate).

    uninvoiced   Projects with billable hours not yet on an invoice.
    hours        Draft invoice importing a project's uninvoiced time.
    milestone    Draft invoice with one fixed-price line Mark specifies.

`hours` and `milestone` print a preview and stop. Add --create to make the draft.
Importing time onto a draft takes those hours off the uninvoiced report until
the draft is deleted, so --create is never a dry run.

Tax treatment comes from an explicit client type (--type):

    es       Spanish B2B          IVA 21%, IRPF -15% (withheld by the payer)
    eu       EU B2B               no tax, reverse-charge note with both VAT numbers
    intl     international direct no tax
    upwork   Upwork contract      no tax, internal record of what Upwork paid

Without --type the tool suggests one from the client's previous invoices and
refuses to --create until it is given.

Usage:
    python3 studio/tools/raise-invoice/raise_invoice.py uninvoiced [--all]
    python3 studio/tools/raise-invoice/raise_invoice.py hours PROJECT [--from D --to D] [--type T] [--create]
    python3 studio/tools/raise-invoice/raise_invoice.py milestone PROJECT --amount N --description TEXT [--type T] [--create]

PROJECT is a Harvest project ID or a fragment of an active project's (or client's) name.
"""

import argparse
import os
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

import requests
from dotenv import load_dotenv

STUDIO = Path(__file__).resolve().parents[2]  # → bain-studio/studio/
sys.path.insert(0, str(STUDIO / "dashboard"))
from harvest_client import BASE, HarvestClient  # noqa: E402

load_dotenv(STUDIO / ".env")

TYPES = ("es", "eu", "intl", "upwork")
TAX = {"es": (21.0, -15.0), "eu": (None, None), "intl": (None, None), "upwork": (None, None)}
SUBJECT = "Web design & development services"
REFERENCE = "_Please quote the invoice number as a reference_"
REVERSE_CHARGE = (
    "Reverse charge: VAT to be accounted for by the recipient "
    "(Article 196, Council Directive 2006/112/EC).\n"
    "Inversión del sujeto pasivo - art. 69.Uno.1º Ley 37/1992.\n"
    "Supplier VAT: {supplier} - Customer VAT: {customer}"
)
VAT_RE = re.compile(r"Supplier VAT:\s*(\S+)\s*-\s*Customer VAT:\s*(\S+)")
MIN_HOURS = 0.25  # below this an uninvoiced row is rounding noise, not work to bill


class InvoiceClient(HarvestClient):
    """The dashboard client plus the few calls an invoice needs."""

    def _send(self, method, path, payload):
        r = requests.request(method, f"{BASE}{path}", headers=self.headers, json=payload, timeout=30)
        if not r.ok:
            raise SystemExit(f"Harvest {method} {path} failed: {r.status_code} {r.text}")
        return r.json()

    def project(self, ref):
        if str(ref).isdigit():
            return self._get(f"/projects/{ref}")
        needle = ref.lower()
        matches = [p for p in self._get("/projects", {"is_active": "true", "per_page": 2000})["projects"]
                   if needle in p["name"].lower() or needle in p["client"]["name"].lower()]
        if len(matches) != 1:
            names = "\n".join(f"  {p['id']}  {p['client']['name']} / {p['name']}" for p in matches) or "  (none)"
            raise SystemExit(f"'{ref}' matches {len(matches)} active projects — pass the ID:\n{names}")
        return matches[0]

    def client_record(self, client_id):
        return self._get(f"/clients/{client_id}")

    def invoices(self, **params):
        return self._get("/invoices", {"per_page": 2000, **params})["invoices"]

    def unbilled_entries(self, project_id, from_date=None, to_date=None):
        params = {"project_id": project_id, "is_billed": "false", "is_running": "false", "per_page": 2000}
        if from_date:
            params.update({"from": from_date, "to": to_date})
        data = self._get("/time_entries", params)
        if data.get("next_page"):
            raise SystemExit("More than 2000 unbilled entries — narrow with --from/--to.")
        return [e for e in data["time_entries"] if e["billable"]]

    def uninvoiced_report(self):
        today = date.today()
        return self._get("/reports/uninvoiced", {
            "from": today.replace(year=today.year - 1).isoformat(), "to": today.isoformat(),
        })["results"]

    def base_uri(self):
        return self._get("/company")["base_uri"]

    def create_invoice(self, payload):
        return self._send("POST", "/invoices", payload)

    def update_invoice(self, invoice_id, payload):
        return self._send("PATCH", f"/invoices/{invoice_id}", payload)


# ── Pure helpers (tested in studio/tests/test_raise_invoice.py) ──────────────

def suggest_type(history):
    """Best guess at the client type from their invoices, newest first."""
    for inv in history:
        notes = inv.get("notes") or ""
        if "via Upwork" in notes:
            return "upwork"
        if inv.get("tax") == 21.0:
            return "es"
        if "Reverse charge" in notes:
            return "eu"
    return None


def vat_numbers(invoices):
    """(supplier, customer) VAT numbers from the most recent reverse-charge note."""
    for inv in invoices:
        m = VAT_RE.search(inv.get("notes") or "")
        if m:
            return m.group(1), m.group(2)
    return None


def payment_block(invoices):
    """The bank-details block from the most recent invoice that carries one."""
    for inv in invoices:
        notes = inv.get("notes") or ""
        i = notes.find("*Payment details")
        if i != -1:
            return notes[i:].strip()
    return None


def upwork_period(from_date, to_date):
    if not from_date:
        return "WordPress development services via Upwork"
    f, t = date.fromisoformat(from_date), date.fromisoformat(to_date)
    return f"WordPress development services via Upwork - {f.day} {f:%B %Y} to {t.day} {t:%B %Y}"


def build_notes(kind, payment, vat=None, from_date=None, to_date=None, reverse_charge=False):
    """Invoice notes for a client type. Raises ValueError when a required part is missing."""
    parts = []
    if kind == "upwork":
        parts.append(upwork_period(from_date, to_date))
    if kind == "eu" or reverse_charge:
        if not vat or not vat[1]:
            raise ValueError("EU reverse charge needs the customer's VAT number (--customer-vat)")
        if not vat[0]:
            raise ValueError("EU reverse charge needs the studio's VAT number, and no recent "
                             "invoice carries one — add the note to the draft in Harvest by hand")
        parts.append(REVERSE_CHARGE.format(supplier=vat[0], customer=vat[1]))
    if kind != "upwork":
        if not payment:
            raise ValueError("No payment-details block found on any previous invoice")
        parts.append(f"{REFERENCE}\n\n{payment}")
    return "\n\n".join(parts)


def pick_currency(client, history, kind, override=None):
    """(currency, warning). The client record's currency is not reliable on its
    own: a client's record may say USD while direct invoices to them are in EUR.
    So prefer the currency of the client's last invoice of the same kind
    (Upwork or direct), and say so when it disagrees with the record."""
    if override:
        return override, None
    same_kind = [i for i in history if ("via Upwork" in (i.get("notes") or "")) == (kind == "upwork")]
    if not same_kind:
        return client["currency"], None
    last = same_kind[0]["currency"]
    if last != client["currency"]:
        return last, (f"Using {last}, as on invoice {same_kind[0]['number']}; the Harvest client record "
                      f"says {client['currency']}. Override with --currency.")
    return last, None


def base_payload(client, kind, notes, issue_date, currency):
    tax, tax2 = TAX[kind]
    payload = {
        "client_id": client["id"],
        "currency": currency,
        "issue_date": issue_date,
        "payment_term": "upon receipt",
        "notes": notes,
        "tax": tax,
        "tax2": tax2,
    }
    if kind != "upwork":
        payload["subject"] = SUBJECT
    return payload


def summarise_entries(entries):
    """{task name: (hours, amount)} using Harvest's rounded hours, as an invoice import does."""
    out = defaultdict(lambda: [0.0, 0.0])
    for e in entries:
        hrs = e.get("rounded_hours") or e["hours"]
        out[e["task"]["name"]][0] += hrs
        out[e["task"]["name"]][1] += hrs * (e.get("billable_rate") or 0)
    return {k: (round(h, 2), round(a, 2)) for k, (h, a) in out.items()}


def bucket_uninvoiced(rows, fixed_fee_ids=(), include_small=False):
    """Split the uninvoiced report the way the dashboard does, plus a fixed-fee
    bucket: ready to bill (hourly, nothing invoiced yet), partial (hourly, some
    already invoiced), fixed fee (the amount is the unbilled fee, billed by
    milestone, not hours) and credits (deposits/overpayments)."""
    ready, partial, fixed, credits = [], [], [], []
    for r in rows:
        amt = r.get("uninvoiced_amount") or 0
        hrs = r.get("uninvoiced_hours") or 0
        if amt < 0:
            credits.append(r)
        elif amt == 0:
            continue
        elif r.get("project_id") in fixed_fee_ids:
            fixed.append(r)
        elif hrs < MIN_HOURS and not include_small:
            continue
        elif r.get("invoiced_amount"):
            partial.append(r)
        else:
            ready.append(r)
    key = lambda r: -(r.get("uninvoiced_amount") or 0)  # noqa: E731
    return sorted(ready, key=key), sorted(partial, key=key), sorted(fixed, key=key), credits


# ── Commands ─────────────────────────────────────────────────────────────────

def fmt_row(r):
    return (f"  {r['project_id']:>9}  {r['client_name'][:26]:<26} {r['project_name'][:32]:<32} "
            f"{r['uninvoiced_hours']:>6.2f} h  {r['currency']} {r['uninvoiced_amount']:>9.2f}")


def cmd_uninvoiced(api, args):
    fixed_ids = {p["id"] for p in api.get_active_projects() if p["is_fixed_fee"]}
    ready, partial, fixed, credits = bucket_uninvoiced(api.uninvoiced_report(), fixed_ids, args.all)
    print("Hourly, ready to bill (nothing invoiced on the project yet):")
    print("\n".join(fmt_row(r) for r in ready) or "  none")
    print("\nHourly, partly invoiced (the rest is unbilled time):")
    print("\n".join(fmt_row(r) for r in partial) or "  none")
    print("\nFixed fee (amount is the unbilled part of the fee; raise a milestone, not hours):")
    print("\n".join(fmt_row(r) for r in fixed) or "  none")
    if credits:
        print("\nCredits (deposit or overpayment — offset before billing that client):")
        print("\n".join(fmt_row(r) for r in credits))
    if not args.all:
        print(f"\nRows under {MIN_HOURS} h hidden; --all shows them.")


def resolve(api, args):
    """Project, client, effective type, notes context — shared by hours/milestone."""
    project = api.project(args.project)
    client = api.client_record(project["client"]["id"])
    history = api.invoices(client_id=client["id"])
    drafts = [i for i in history if i["state"] == "draft"]
    if drafts and not args.allow_draft:
        nums = ", ".join(i["number"] for i in drafts)
        raise SystemExit(f"{client['name']} already has a draft invoice ({nums}). "
                         "Finish or delete it in Harvest, or pass --allow-draft.")
    recent = api.invoices(per_page=200)
    vat = vat_numbers(history)
    if args.customer_vat:
        supplier = (vat_numbers(recent) or (None,))[0]
        vat = (supplier, args.customer_vat)
    suggested = suggest_type(history)
    effective = args.type or suggested or "intl"
    reverse_charge = effective == "upwork" and vat is not None
    try:
        notes = build_notes(effective, payment_block(recent), vat,
                            args.from_date, args.to_date, reverse_charge)
    except ValueError as e:
        raise SystemExit(str(e))
    currency, currency_warning = pick_currency(client, history, effective, args.currency)
    payload = base_payload(client, effective, notes, args.issue_date, currency)
    return project, client, suggested, effective, payload, [currency_warning] if currency_warning else []


def preview(project, client, kind, suggested, payload, lines, warnings):
    print(f"Client:   {client['name']}  (Harvest client {client['id']})")
    print(f"Project:  {project['name']}  (Harvest project {project['id']})")
    print(f"Currency: {payload['currency']}   Issue date: {payload['issue_date']}   Terms: {payload['payment_term']}")
    shown = kind or f"NOT SET — suggested from past invoices: {suggested or 'none (previewing as intl)'}"
    tax = f"IVA {payload['tax']}%, IRPF {payload['tax2']}%" if payload["tax"] else "none"
    print(f"Type:     {shown}   Tax: {tax}")
    if payload.get("subject"):
        print(f"Subject:  {payload['subject']}")
    print("\nLines:")
    subtotal = 0.0
    for desc, qty, price in lines:
        subtotal += qty * price
        print(f"  {desc[:70]:<70} {qty:>7.2f} × {price:>8.2f} = {qty * price:>9.2f}")
    print(f"  {'Subtotal':<70} {'':>21} {subtotal:>9.2f}")
    if payload["tax"]:
        iva, irpf = subtotal * payload["tax"] / 100, subtotal * payload["tax2"] / 100
        print(f"  {'IVA ' + str(payload['tax']) + '%':<70} {'':>21} {iva:>9.2f}")
        print(f"  {'IRPF ' + str(payload['tax2']) + '%':<70} {'':>21} {irpf:>9.2f}")
        print(f"  {'Total':<70} {'':>21} {subtotal + iva + irpf:>9.2f}")
    print("\nNotes (confirm before sending):")
    print("  " + (payload["notes"] or "(none)").replace("\n", "\n  "))
    for w in warnings:
        print(f"\nWARNING: {w}")


def finish(api, args, payload, retax=False):
    if not args.create:
        print("\nPreview only. Re-run with --type set and --create to make the Harvest draft.")
        return
    if not args.type:
        raise SystemExit("\n--create needs an explicit --type (es, eu, intl or upwork).")
    inv = api.create_invoice(payload)
    if retax:
        # IVA/IRPF only apply to lines marked taxed; imported time lines may not be.
        untaxed = [li for li in inv["line_items"] if not (li["taxed"] and li["taxed2"])]
        if untaxed:
            inv = api.update_invoice(inv["id"], {"line_items": [
                {"id": li["id"], "taxed": True, "taxed2": True} for li in untaxed]})
    print(f"\nDraft invoice {inv['number']} created: {inv['currency']} {inv['amount']:.2f} "
          f"(state: {inv['state']})")
    print(f"Review and send in Harvest: {api.base_uri()}/invoices/{inv['id']}")


def cmd_hours(api, args):
    project = api.project(args.project)
    entries = api.unbilled_entries(project["id"], args.from_date, args.to_date)
    if not entries:
        raise SystemExit(f"No unbilled billable hours on {project['name']}.")
    days = sorted(e["spent_date"] for e in entries)
    if not args.from_date:  # the period shown in an Upwork note and the preview
        args.from_date, args.to_date, import_range = days[0], days[-1], {}
    else:
        import_range = {"from": args.from_date, "to": args.to_date}
    args.project = str(project["id"])
    project, client, suggested, effective, payload, warnings = resolve(api, args)
    payload["line_items_import"] = {
        "project_ids": [project["id"]],
        "time": {"summary_type": args.summary, **import_range},
    }
    lines = [(f"{task} ({args.from_date} to {args.to_date})", h, a / h if h else 0)
             for task, (h, a) in summarise_entries(entries).items()]
    if project.get("is_fixed_fee") or project.get("bill_by") == "none":
        warnings.append("This is a fixed-fee / non-hourly project. Hours may already be covered by "
                        "a milestone — consider `milestone` instead.")
    for r in api.uninvoiced_report():
        if r["client_id"] == client["id"] and (r.get("uninvoiced_amount") or 0) < 0:
            warnings.append(f"{client['name']} has a credit of {r['currency']} {r['uninvoiced_amount']:.2f} "
                            f"on '{r['project_name']}' (deposit or overpayment). Offset it before sending.")
    if any(not e.get("billable_rate") for e in entries):
        warnings.append("Some entries have no billable rate and will import at 0.")
    preview(project, client, args.type, suggested, payload, lines, warnings)
    finish(api, args, payload, retax=TAX[effective][0] is not None)


def cmd_milestone(api, args):
    project, client, suggested, effective, payload, warnings = resolve(api, args)
    taxed = TAX[effective][0] is not None
    payload["line_items"] = [{
        "project_id": project["id"],
        "kind": "Service" if effective == "upwork" else "Development",
        "description": args.description,
        "quantity": 1,
        "unit_price": args.amount,
        "taxed": taxed,
        "taxed2": taxed,
    }]
    if project.get("is_fixed_fee") and project.get("fee"):
        warnings.append(f"Fixed fee on this project: {project['fee']:.2f}. "
                        "Check this milestone against what has already been invoiced.")
    preview(project, client, args.type, suggested, payload, [(args.description, 1, args.amount)], warnings)
    finish(api, args, payload)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0].strip())
    sub = p.add_subparsers(dest="cmd", required=True)

    u = sub.add_parser("uninvoiced", help="list uninvoiced billable hours")
    u.add_argument("--all", action="store_true", help=f"include rows under {MIN_HOURS} h")

    for name in ("hours", "milestone"):
        s = sub.add_parser(name)
        s.add_argument("project", help="Harvest project ID or name fragment")
        s.add_argument("--type", choices=TYPES, help="client type (sets tax and notes)")
        s.add_argument("--customer-vat", help="customer VAT number for an EU reverse-charge note")
        s.add_argument("--currency", help="invoice currency (default: the client's last invoice of this type)")
        s.add_argument("--issue-date", default=date.today().isoformat())
        s.add_argument("--allow-draft", action="store_true", help="create even if the client has a draft")
        s.add_argument("--create", action="store_true", help="create the Harvest draft (default: preview)")
        if name == "hours":
            s.add_argument("--from", dest="from_date", help="YYYY-MM-DD (with --to)")
            s.add_argument("--to", dest="to_date", help="YYYY-MM-DD (with --from)")
            s.add_argument("--summary", default="task", choices=("project", "task", "people", "detailed"),
                           help="how Harvest groups imported time into lines (default: task)")
        else:
            s.add_argument("--amount", type=float, required=True, help="net amount, before tax")
            s.add_argument("--description", required=True, help="line description, as the client sees it")
            s.set_defaults(from_date=None, to_date=None)

    args = p.parse_args(argv)
    if args.cmd == "hours" and bool(args.from_date) != bool(args.to_date):
        p.error("--from and --to go together")

    token, account = os.getenv("HARVEST_TOKEN"), os.getenv("HARVEST_ACCOUNT_ID")
    if not token or not account:
        raise SystemExit("HARVEST_TOKEN and HARVEST_ACCOUNT_ID must be set in studio/.env")
    api = InvoiceClient(token, account)
    {"uninvoiced": cmd_uninvoiced, "hours": cmd_hours, "milestone": cmd_milestone}[args.cmd](api, args)


if __name__ == "__main__":
    main()
