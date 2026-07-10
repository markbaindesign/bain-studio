---
description: Financial gate — margin checks, cashflow projection, invoicing, tax prep
invoke: /financial-review
role: Finance
tags:
- skill
---

# Financial Review

The studio's financial gate. Invoked at two points in every project: early (margin check on Athena's scope before a proposal goes out) and late (raising the invoice after delivery). Between those moments, expenses are tracked against the project.

## Invoke

```
/financial-review
```

Reads the Athena report from `{CONTENT_DIR}/pipeline/athena/{slug}-*.md`. If no slug is given, asks for one.

## Related finance skills

| Skill | Role |
|---|---|
| **Raise Invoice** (`/raise-invoice`) | Produces the formatted invoice after delivery |
| **Tax Prep** (`/tax-prep`) | Quarterly Modelo 303/130 filing pack |
| **Cashflow Projection** (`/cashflow-projection`) | 90-day income vs. outgoings, break-even risk, runway |
| **Account Forecast** (`/account-forecast`) | Per-account transaction forecast, insufficient-funds flags |

## Two modes

### 1. Margin check (pre-proposal)

The **Law of Margin**: no proposal leaves the studio without clearing this check.

Reads the Athena report, extracts estimated hours and price scenarios, and checks each against the studio's margin floor. Reads business context from `/media/data/Dropbox/Work/Admin/Financial/Accounting/aletheia-codex.md` — the authoritative record of money flow, IVA/IRPF methodology, and tax conventions.

Output per scenario:
```
Scenario: Mid  (120h at €X/h = €Y)
  IVA: 21% → €Z
  IRPF retention: 15% → €W
  Net receipt: €V
  Margin vs floor: PASS / FAIL
```

If any scenario fails the margin floor, flags it and suggests a price adjustment before the proposal goes out.

### 2. Invoice (post-delivery)

Raises the invoice after delivery. Reads the agreed price from the Athena report, calculates IVA and IRPF, and produces the invoice document.

## Quarterly outputs

Every quarter, produces three documents unprompted:
- Profit-per-project summary
- Cash flow projection
- Tax preparation pack (Modelo 303 IVA + Modelo 130 IRPF)

## Notes

- The Aletheia Codex (`/media/data/Dropbox/Work/Admin/Financial/Accounting/aletheia-codex.md`) governs all money calculations — do not make assumptions about tax rates or account topology; read the Codex first
- This skill does not approve work on ethics, taste, or fit — only viability. "Beautiful but unprofitable" is still a fail.

## See also

- [athena.md](athena.md) — produces the scope doc this skill checks
- [commission.md](commission.md) — follows after both Athena and financial review clear the project
