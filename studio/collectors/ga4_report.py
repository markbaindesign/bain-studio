#!/usr/bin/env python3
"""
GA4 benchmark data fetcher.
Authenticates via service account JSON, pulls standard metrics,
and outputs JSON for the /ga-report skill to compile into a report.

Usage:
    python3 ga4_report.py --property 542141660 --sa-json /path/to/sa.json [--days 90]

Auth setup:
    1. Create a service account in Google Cloud Console
    2. Enable Google Analytics Data API
    3. Add the service account email as a viewer on the GA4 property
    4. Download the JSON key and set GOOGLE_SA_JSON in studio/.env
"""

import argparse
import json
import sys
import time
import base64
import urllib.request
import urllib.error
from datetime import date, timedelta


def get_access_token(sa_json_path: str) -> str:
    """Get OAuth2 bearer token from service account JSON using manual JWT (cryptography lib)."""
    with open(sa_json_path) as f:
        sa = json.load(f)

    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding
        from cryptography.hazmat.backends import default_backend

        now = int(time.time())
        header_b64 = base64.urlsafe_b64encode(
            json.dumps({"alg": "RS256", "typ": "JWT"}).encode()
        ).rstrip(b"=")
        claims = {
            "iss": sa["client_email"],
            "scope": "https://www.googleapis.com/auth/analytics.readonly",
            "aud": "https://oauth2.googleapis.com/token",
            "iat": now,
            "exp": now + 3600,
        }
        claims_b64 = base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b"=")
        signing_input = header_b64 + b"." + claims_b64

        private_key = serialization.load_pem_private_key(
            sa["private_key"].encode(),
            password=None,
            backend=default_backend(),
        )
        sig = private_key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
        sig_b64 = base64.urlsafe_b64encode(sig).rstrip(b"=")
        jwt_token = (signing_input + b"." + sig_b64).decode()

    except ImportError:
        # Try google-auth fallback
        try:
            from google.oauth2 import service_account
            import google.auth.transport.requests

            creds = service_account.Credentials.from_service_account_file(
                sa_json_path,
                scopes=["https://www.googleapis.com/auth/analytics.readonly"],
            )
            creds.refresh(google.auth.transport.requests.Request())
            return creds.token
        except ImportError:
            sys.exit(
                "Error: neither 'cryptography' nor 'google-auth' is installed.\n"
                "Run: pip3 install cryptography  OR  pip3 install google-auth"
            )

    data = (
        "grant_type=urn%3Aietf%3Aparams%3Aoauth%3Agrant-type%3Ajwt-bearer"
        f"&assertion={jwt_token}"
    ).encode()
    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        resp = urllib.request.urlopen(req)
        return json.loads(resp.read())["access_token"]
    except urllib.error.HTTPError as e:
        sys.exit(f"Token exchange failed ({e.code}): {e.read().decode()}")


def run_report(token: str, property_id: str, date_ranges: list, metrics: list, dimensions: list, limit: int = 20) -> dict:
    url = f"https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:runReport"
    payload = {
        "dateRanges": date_ranges,
        "metrics": [{"name": m} for m in metrics],
        "limit": limit,
    }
    if dimensions:
        payload["dimensions"] = [{"name": d} for d in dimensions]

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        resp = urllib.request.urlopen(req)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        sys.exit(f"GA4 API error ({e.code}) for metrics {metrics}: {body}")


def parse_rows(report: dict, metrics: list, dimensions: list) -> list:
    rows = []
    for row in report.get("rows", []):
        entry = {}
        for i, d in enumerate(dimensions):
            entry[d] = row["dimensionValues"][i]["value"]
        for i, m in enumerate(metrics):
            entry[m] = row["metricValues"][i]["value"]
        rows.append(entry)
    return rows


def fetch_overview(token: str, property_id: str, start: str, end: str) -> dict:
    metrics = [
        "sessions", "totalUsers", "newUsers", "screenPageViews",
        "engagementRate", "averageSessionDuration", "bounceRate",
        "sessionsPerUser",
    ]
    r = run_report(token, property_id, [{"startDate": start, "endDate": end}], metrics, [])
    result = {}
    for row in r.get("rows", []):
        for i, m in enumerate(metrics):
            result[m] = row["metricValues"][i]["value"]
        break
    return result


def main():
    parser = argparse.ArgumentParser(description="Fetch GA4 benchmark data")
    parser.add_argument("--property", required=True, help="GA4 property ID (numeric)")
    parser.add_argument("--sa-json", required=True, help="Path to service account JSON")
    parser.add_argument("--days", type=int, default=90, help="Reporting period in days (default: 90)")
    args = parser.parse_args()

    today = date.today()
    end = today - timedelta(days=1)
    start = end - timedelta(days=args.days - 1)
    prev_end = start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=args.days - 1)

    token = get_access_token(args.sa_json)

    output = {
        "property_id": args.property,
        "period": {"start": str(start), "end": str(end), "days": args.days},
        "prev_period": {"start": str(prev_start), "end": str(prev_end)},
    }

    # Overview — current and previous periods
    output["current"] = fetch_overview(token, args.property, str(start), str(end))
    output["previous"] = fetch_overview(token, args.property, str(prev_start), str(prev_end))

    # Traffic by channel
    channels = run_report(
        token, args.property,
        [{"startDate": str(start), "endDate": str(end)}],
        ["sessions", "totalUsers", "engagementRate", "bounceRate"],
        ["sessionDefaultChannelGroup"],
    )
    output["channels"] = parse_rows(
        channels, ["sessions", "totalUsers", "engagementRate", "bounceRate"],
        ["sessionDefaultChannelGroup"]
    )

    # Top 10 pages
    pages = run_report(
        token, args.property,
        [{"startDate": str(start), "endDate": str(end)}],
        ["sessions", "screenPageViews", "averageSessionDuration", "bounceRate", "engagementRate"],
        ["pagePath", "pageTitle"],
        limit=10,
    )
    output["top_pages"] = parse_rows(
        pages,
        ["sessions", "screenPageViews", "averageSessionDuration", "bounceRate", "engagementRate"],
        ["pagePath", "pageTitle"],
    )

    # Device breakdown
    devices = run_report(
        token, args.property,
        [{"startDate": str(start), "endDate": str(end)}],
        ["sessions", "totalUsers", "engagementRate"],
        ["deviceCategory"],
    )
    output["devices"] = parse_rows(
        devices, ["sessions", "totalUsers", "engagementRate"], ["deviceCategory"]
    )

    # Top countries
    countries = run_report(
        token, args.property,
        [{"startDate": str(start), "endDate": str(end)}],
        ["sessions", "totalUsers"],
        ["country"],
        limit=8,
    )
    output["countries"] = parse_rows(
        countries, ["sessions", "totalUsers"], ["country"]
    )

    # Key events (exclude standard page/session events)
    NOISE_EVENTS = {"page_view", "session_start", "first_visit", "user_engagement", "scroll"}
    try:
        events = run_report(
            token, args.property,
            [{"startDate": str(start), "endDate": str(end)}],
            ["eventCount", "totalUsers"],
            ["eventName"],
        )
        output["events"] = [
            e for e in parse_rows(events, ["eventCount", "totalUsers"], ["eventName"])
            if e.get("eventName") not in NOISE_EVENTS
        ]
    except SystemExit:
        output["events"] = []

    # Landing pages — top entry points
    landing = run_report(
        token, args.property,
        [{"startDate": str(start), "endDate": str(end)}],
        ["sessions", "bounceRate", "engagementRate"],
        ["landingPage"],
        limit=10,
    )
    output["landing_pages"] = parse_rows(
        landing, ["sessions", "bounceRate", "engagementRate"], ["landingPage"]
    )

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
