#!/usr/bin/env python3
"""Wise Pulse — daily balance polling with change detection and Slack notification.

Polls Wise business and personal account balances, compares to previous checkpoint,
notifies if any balance changes, and updates checkpoint for next run.
"""

import json
import sys
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional

# studio/ — derived, not hardcoded, so this runs from the release-pinned ops
# worktree that cron uses as well as from the dev checkout (ADR 014).
STUDIO_DIR = Path(__file__).resolve().parents[3] / "studio"
sys.path.insert(0, str(STUDIO_DIR))
from notifier import notify

# Account configuration — hardcoded based on verified setup
ACCOUNTS = [
    {"profile": 55828700, "type": "Business", "name": "Bain Design", "balances": [
        {"id": 93635981, "currency": "USD"},
        {"id": 93635748, "currency": "GBP"},
        {"id": 93635923, "currency": "EUR"},
    ]},
    {"profile": 2753862, "type": "Personal", "name": "Personal", "balances": [
        {"id": 32845501, "currency": "GBP"},
        {"id": 18115479, "currency": "USD"},
        {"id": 18115478, "currency": "EUR"},
    ]},
]

def setup_logging(log_dir: Path = None) -> None:
    if log_dir is None:
        log_dir = Path.home() / ".wise"
    log_dir.mkdir(parents=True, exist_ok=True)

def get_checkpoint_path() -> Path:
    return Path.home() / ".wise" / "balances-checkpoint.json"

def load_checkpoint() -> Dict[str, float]:
    """Load previous balance checkpoint. Returns empty dict on first run."""
    path = get_checkpoint_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception as e:
        print(f"WARNING: Could not read checkpoint: {e}", file=sys.stderr)
        return {}

def save_checkpoint(balances: Dict[str, Tuple[Dict, float, str]]) -> None:
    """Save current balances as the new checkpoint.

    Takes fetch_balances() output, {balance_id: (balance_obj, amount, currency)}.
    Format written: {"balance_id": amount}  # timestamp is implicit (now)
    """
    path = get_checkpoint_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    checkpoint_data = {}
    for bid, (_, amount, _currency) in balances.items():
        checkpoint_data[bid] = amount

    path.write_text(json.dumps(checkpoint_data, indent=2))

def get_wise_client_path() -> Path:
    """Locate the Wise API client."""
    path = Path.home() / ".config" / "wise" / "wise_client.py"
    if not path.exists():
        raise FileNotFoundError(f"Wise client not found at {path}")
    return path

def fetch_balances() -> Dict[str, Tuple[Dict, float, str]]:
    """Fetch balances from Wise API.

    Returns: {
        "balance_id": ({balance_obj}, amount_float, currency_code)
    }
    """
    client_path = get_wise_client_path()
    balances = {}

    for account in ACCOUNTS:
        profile_id = account["profile"]
        try:
            result = subprocess.run(
                [sys.executable, str(client_path), "balances", str(profile_id)],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                print(f"ERROR: Wise API call failed for profile {profile_id}: {result.stderr}",
                      file=sys.stderr)
                continue

            data = json.loads(result.stdout)
            # API returns a list directly, not wrapped in a "balances" key
            balance_list = data if isinstance(data, list) else data.get("balances", [])

            # Extract the requested balance IDs
            balance_ids = {b["id"] for b in account["balances"]}

            for balance_obj in balance_list:
                bid = balance_obj.get("id")
                if bid in balance_ids:
                    amount = float(balance_obj.get("amount", {}).get("value", 0))
                    currency = balance_obj.get("currency")
                    balances[str(bid)] = (balance_obj, amount, currency)

        except subprocess.TimeoutExpired:
            print(f"ERROR: Timeout fetching balances for profile {profile_id}", file=sys.stderr)
        except json.JSONDecodeError as e:
            print(f"ERROR: JSON parse error for profile {profile_id}: {e}", file=sys.stderr)
        except Exception as e:
            print(f"ERROR: Failed to fetch balances for profile {profile_id}: {e}", file=sys.stderr)

    return balances

def find_account_info(balance_id: str) -> Tuple[str, str, str]:
    """Find account type, name, and currency for a balance ID."""
    for account in ACCOUNTS:
        for balance in account["balances"]:
            if str(balance["id"]) == balance_id:
                return account["type"], account["name"], balance["currency"]
    return "Unknown", "Unknown", "?"

def notify_slack(changes: List[Dict]) -> bool:
    """Notify Slack of balance changes."""
    if not changes:
        return True  # Nothing to notify

    try:
        # Format message for each change
        lines = []
        for change in changes:
            acc_type = change["account_type"]
            acc_name = change["account_name"]
            currency = change["currency"]
            prev = change["previous"]
            curr = change["current"]
            delta = curr - prev
            sign = "+" if delta >= 0 else ""

            lines.append(
                f"{acc_type} {acc_name} {currency}: "
                f"{prev:.2f} → {curr:.2f} ({sign}{delta:.2f})"
            )

        return notify(
            f"Wise balance changes detected ({len(changes)}) — review and book in GnuCash.",
            subject="Wise balance changes",
            priority="normal",
            sender="financial-review",
            details="\n".join(lines),
        )
    except Exception as e:
        print(f"WARNING: Slack notification failed: {e}", file=sys.stderr)
        return False

def log_run(message: str) -> None:
    """Log to the pulse log file."""
    log_file = Path.home() / ".wise" / "pulse.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_file.open("a").write(f"{ts} {message}\n")

def pulse(verbose: bool = False, dry_run: bool = False) -> int:
    """Main pulse function."""
    setup_logging()

    print("Fetching Wise balances...", file=sys.stderr)
    current = fetch_balances()

    if not current:
        print("ERROR: No balances fetched", file=sys.stderr)
        log_run("ERROR: No balances fetched")
        return 1

    print(f"✓ Fetched {len(current)} balances", file=sys.stderr)

    # Load previous checkpoint
    checkpoint = load_checkpoint()
    is_first_run = not checkpoint

    # Detect changes
    changes = []
    for bid, (_, amount, currency) in current.items():
        prev_amount = checkpoint.get(bid)

        acc_type, acc_name, _ = find_account_info(bid)

        if verbose:
            if prev_amount is not None:
                if amount != prev_amount:
                    print(f"  → {acc_type}/{acc_name}/{currency}: {prev_amount} → {amount}",
                          file=sys.stderr)
                else:
                    print(f"  ✓ {acc_type}/{acc_name}/{currency}: {amount} (no change)",
                          file=sys.stderr)
            else:
                print(f"  ⊕ {acc_type}/{acc_name}/{currency}: {amount} (baseline)",
                      file=sys.stderr)

        if prev_amount is not None and amount != prev_amount:
            changes.append({
                "balance_id": bid,
                "account_type": acc_type,
                "account_name": acc_name,
                "currency": currency,
                "previous": prev_amount,
                "current": amount,
            })

    # Summary
    total = len(current)
    changed = len(changes)
    print(f"\nWise Pulse: {total} balances checked, {changed} changed", file=sys.stderr)

    if dry_run:
        print("(DRY RUN: not updating checkpoint or notifying)", file=sys.stderr)
        log_run(f"DRY RUN: {total} balances checked, {changed} changed")
        return 0

    if is_first_run:
        print("(First run: saving baseline checkpoint, not notifying)", file=sys.stderr)
        save_checkpoint(current)
        log_run(f"BASELINE: {total} balances established")
        return 0

    if changed:
        # Notify
        if notify_slack(changes):
            print("✓ Notified", file=sys.stderr)
            # Update checkpoint only after successful notification
            save_checkpoint(current)
            log_run(f"CHANGED: {changed}/{total} balances notified and checkpoint updated")
            return 0
        else:
            print("✗ Notification failed", file=sys.stderr)
            log_run(f"ERROR: {changed} balances changed but notification failed — checkpoint NOT updated")
            return 1
    else:
        # No changes
        log_run(f"OK: {total} balances checked, no changes")
        return 0

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Poll Wise balances and notify on changes")
    parser.add_argument("--verbose", action="store_true", help="Show detailed output")
    parser.add_argument("--dry-run", action="store_true", help="Check without updating or notifying")

    args = parser.parse_args()

    sys.exit(pulse(verbose=args.verbose, dry_run=args.dry_run))
