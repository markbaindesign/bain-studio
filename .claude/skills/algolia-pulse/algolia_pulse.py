#!/usr/bin/env python3
"""
Algolia Pulse — keeps free-tier Algolia indices alive by querying them regularly.
Prevents auto-closure of inactive search indices.
"""

import json
import stat
import subprocess
import sys
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

try:
    from algoliasearch.search.client import SearchClientSync
except ImportError:
    print("ERROR: algoliasearch not installed. Install with: pip3 install algoliasearch")
    sys.exit(1)

def setup_logging(log_dir: Path = None) -> logging.Logger:
    """Setup logging to file and console."""
    if log_dir is None:
        log_dir = Path.home() / ".algolia"
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / "pulse.log"
    logger = logging.getLogger("algolia-pulse")
    logger.setLevel(logging.INFO)

    handler = logging.FileHandler(log_file)
    handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(handler)

    return logger


def load_config(config_path: str) -> Dict[str, Any]:
    """Load and validate the pulse config file."""
    path = Path(config_path).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    # The file holds live API keys: refuse to use it if anyone but the owner can read it
    mode = path.stat().st_mode
    if mode & (stat.S_IRWXG | stat.S_IRWXO):
        raise ValueError(
            f"{path} is readable by other users (mode {stat.S_IMODE(mode):o}). "
            f"Run: chmod 600 {path}"
        )

    with open(path) as f:
        config = json.load(f)

    # Validate structure
    if "apps" not in config or not isinstance(config["apps"], list):
        raise ValueError("Config must contain 'apps' array")

    for app in config["apps"]:
        required = ["name", "app_id", "admin_api_key", "indices"]
        if not all(k in app for k in required):
            raise ValueError(f"App missing required fields: {required}")

        if not isinstance(app["indices"], list) or not app["indices"]:
            raise ValueError(f"App '{app['name']}' must have at least one index")

        for idx in app["indices"]:
            if "name" not in idx or "query" not in idx:
                raise ValueError(f"Each index must have 'name' and 'query' fields")

    return config


NOTIFIER = Path(__file__).resolve().parents[3] / "studio" / "notifier.py"


def _send_slack(message: str, details: str, priority: str) -> None:
    """Post to Slack via the studio notifier. Never raises."""
    try:
        subprocess.run(
            [sys.executable, str(NOTIFIER), message, "--project", "BSTD",
             "--priority", priority, "--sender", "algolia-pulse",
             "--details", details],
            check=False, timeout=30,
        )
    except Exception as e:
        print(f"WARNING: Slack notification failed: {e}", file=sys.stderr)


def notify_slack(results: List[Dict[str, Any]], total: int, failed: int) -> None:
    """Post the run summary to Slack via the studio notifier. Never raises."""
    ok = total - failed
    lines = []
    for r in results:
        mark = "OK  " if not r["failed"] else "FAIL"
        lines.append(f"{mark} {r['name']}: {r['ok']}/{r['total']}")
        for idx in r["failed"]:
            lines.append(f"       missing/failed: {idx}")
    if failed:
        message = f"Algolia Pulse: {failed} of {total} indices FAILED"
        priority = "high"
    else:
        message = f"Algolia Pulse: {ok}/{total} indices OK across {len(results)} apps"
        priority = "low"
    _send_slack(message, "\n".join(lines), priority)


def query_index(client: "SearchClientSync", index_name: str, query: str, logger: logging.Logger) -> bool:
    """Query a single index. Returns True if successful."""
    try:
        result = client.search_single_index(
            index_name=index_name,
            search_params={"query": query, "hitsPerPage": 1},
        )
        n_hits = getattr(result, "nb_hits", None)
        if n_hits is None:
            n_hits = len(getattr(result, "hits", []))
        logger.info(f"✓ Index '{index_name}' queried: {n_hits} hits")
        return True
    except Exception as e:
        logger.error(f"✗ Index '{index_name}' query failed: {e}")
        return False


def pulse(config_path: str, dry_run: bool = False, verbose: bool = False, notify: bool = True) -> int:
    """Main pulse function. Returns exit code."""
    logger = setup_logging()

    # Load and validate config
    try:
        config = load_config(config_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        logger.error(f"Config error: {e}")
        # A cron run that dies on its config would otherwise fail unseen
        if notify and not dry_run:
            _send_slack("Algolia Pulse cannot run", str(e), "high")
        return 1

    apps = config.get("apps", [])
    total_queries = sum(len(app["indices"]) for app in apps)

    if dry_run:
        print(f"DRY RUN: Would query {total_queries} indices across {len(apps)} apps")
        for app in apps:
            print(f"  App: {app['name']} ({len(app['indices'])} indices)")
            for idx in app["indices"]:
                print(f"    - {idx['name']}: query='{idx['query']}'")
        return 0

    # Run queries
    logger.info(f"Pulse starting: {len(apps)} apps, {total_queries} indices")
    print(f"Querying {total_queries} indices across {len(apps)} apps...")

    successful = 0
    failed = 0
    results: List[Dict[str, Any]] = []

    for app in apps:
        app_id = app["app_id"]
        api_key = app["admin_api_key"]
        app_name = app["name"]
        result = {"name": app_name, "total": len(app["indices"]), "ok": 0, "failed": []}
        results.append(result)

        try:
            client = SearchClientSync(app_id, api_key)
            if verbose:
                print(f"\n  App: {app_name}")

            for idx in app["indices"]:
                if query_index(client, idx["name"], idx["query"], logger):
                    successful += 1
                    result["ok"] += 1
                    if verbose:
                        print(f"    ✓ {idx['name']}")
                else:
                    failed += 1
                    result["failed"].append(idx["name"])
                    if verbose:
                        print(f"    ✗ {idx['name']}")

        except Exception as e:
            logger.error(f"App '{app_name}' connection failed: {e}")
            failed += len(app["indices"])
            result["failed"] = [i["name"] for i in app["indices"]]
            print(f"  ✗ {app_name}: {e}")

    # Summary
    logger.info(f"Pulse complete: {successful} succeeded, {failed} failed")
    print(f"\nPulse complete: {successful}/{total_queries} indices queried successfully")

    if notify:
        notify_slack(results, total_queries, failed)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Keep Algolia free-tier indices alive")
    parser.add_argument("--config", required=True, help="Path to pulse-config.json")
    parser.add_argument("--dry-run", action="store_true", help="Validate config without querying")
    parser.add_argument("--verbose", action="store_true", help="Detailed output")
    parser.add_argument("--no-notify", action="store_true", help="Skip the Slack summary")

    args = parser.parse_args()

    sys.exit(pulse(args.config, dry_run=args.dry_run, verbose=args.verbose, notify=not args.no_notify))
