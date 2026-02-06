#!/usr/bin/env python3
"""
Format beaconcha.in rewards-list data for tax reporting.

Usage:
    python scripts/format_tax_export.py <json_file_or_stdin> [--timezone UTC+1] [--csv output.csv]

Accepts raw JSON from POST /api/v2/ethereum/validators/rewards-list
and outputs a tax-ready table with timestamps and ETH values.
Optionally exports to CSV for spreadsheet import.
"""

import json
import sys
import argparse
import csv
from datetime import datetime, timezone, timedelta

GENESIS_TS = 1606824023
SECONDS_PER_EPOCH = 384


def wei_to_eth(wei_str):
    return int(wei_str) / 1e18


def epoch_to_timestamp(epoch):
    return GENESIS_TS + (epoch * SECONDS_PER_EPOCH)


def format_ts(ts, tz_offset_hours=0):
    tz = timezone(timedelta(hours=tz_offset_hours))
    dt = datetime.fromtimestamp(ts, tz=tz)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def parse_tz(tz_str):
    """Parse timezone string like 'UTC+1', 'UTC-5', 'UTC'."""
    if not tz_str or tz_str == "UTC":
        return 0
    tz_str = tz_str.upper().replace("UTC", "").replace(" ", "")
    try:
        return int(tz_str)
    except ValueError:
        try:
            return float(tz_str)
        except ValueError:
            return 0


def main():
    parser = argparse.ArgumentParser(description="Tax export formatter for beaconcha.in rewards")
    parser.add_argument("input", nargs="?", default="-", help="JSON file or - for stdin")
    parser.add_argument("--timezone", type=str, default="UTC", help="Timezone offset (e.g., UTC+1, UTC-5)")
    parser.add_argument("--csv", type=str, default=None, help="Output CSV filepath")
    args = parser.parse_args()

    if args.input == "-":
        raw = json.load(sys.stdin)
    else:
        with open(args.input, "r") as f:
            raw = json.load(f)

    tz_offset = parse_tz(args.timezone)
    entries = raw.get("data", [])

    if not entries:
        print("No reward data found.")
        return

    # Build rows
    rows = []
    for entry in entries:
        idx = entry["validator"]["index"]
        epoch = entry.get("epoch", "?")

        # Try to get epoch from range if not directly available
        if epoch == "?" and "range" in raw:
            epoch = raw["range"].get("epoch", {}).get("start", "?")

        ts = epoch_to_timestamp(epoch) if isinstance(epoch, int) else 0

        total_reward = wei_to_eth(entry["total_reward"])
        total_penalty = wei_to_eth(entry["total_penalty"])
        net = total_reward - total_penalty

        cl_reward = wei_to_eth(entry["attestation"]["total"])
        sync_reward = wei_to_eth(entry["sync_committee"]["reward"])
        el_reward = wei_to_eth(entry["proposal"].get("execution_layer_reward", "0"))
        proposal_cl = wei_to_eth(entry["proposal"]["total"]) - el_reward

        rows.append({
            "validator_index": idx,
            "epoch": epoch,
            "date": format_ts(ts, tz_offset) if ts else "?",
            "timestamp_utc": ts,
            "total_reward_eth": total_reward,
            "total_penalty_eth": total_penalty,
            "net_reward_eth": net,
            "attestation_eth": cl_reward,
            "sync_committee_eth": sync_reward,
            "proposal_cl_eth": proposal_cl,
            "proposal_el_eth": el_reward,
            "finality": entry.get("finality", "unknown"),
        })

    # CSV export
    if args.csv:
        fieldnames = list(rows[0].keys())
        with open(args.csv, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"Exported {len(rows)} rows to {args.csv}")
        print(f"Timezone: {args.timezone}")
        print()

    # Console output
    print("╔══════════════════════════════════════════════╗")
    print("║   Staking Rewards — Tax Export               ║")
    print("╚══════════════════════════════════════════════╝")
    print(f"  Timezone: {args.timezone}")
    print(f"  Rows: {len(rows)}")
    print()

    # Summary by validator
    by_validator = {}
    for r in rows:
        idx = r["validator_index"]
        if idx not in by_validator:
            by_validator[idx] = {"total": 0, "penalty": 0, "net": 0, "cl": 0, "el": 0, "count": 0}
        by_validator[idx]["total"] += r["total_reward_eth"]
        by_validator[idx]["penalty"] += r["total_penalty_eth"]
        by_validator[idx]["net"] += r["net_reward_eth"]
        by_validator[idx]["cl"] += r["attestation_eth"] + r["sync_committee_eth"] + r["proposal_cl_eth"]
        by_validator[idx]["el"] += r["proposal_el_eth"]
        by_validator[idx]["count"] += 1

    for idx, summary in sorted(by_validator.items()):
        print(f"  Validator {idx} ({summary['count']} epochs)")
        print(f"    Total income:  {summary['total']:.6f} ETH")
        print(f"    CL rewards:    {summary['cl']:.6f} ETH")
        print(f"    EL rewards:    {summary['el']:.6f} ETH")
        print(f"    Penalties:     {summary['penalty']:.6f} ETH")
        print(f"    Net income:    {summary['net']:.6f} ETH")
        print()

    grand_total = sum(v["net"] for v in by_validator.values())
    print(f"  Grand total net income: {grand_total:.6f} ETH")
    print()
    print("  ⚠️  Fiat conversion requires an external price feed (not provided by beaconcha.in).")
    print("  ⚠️  This is raw data only. Consult a tax professional for reporting requirements.")


if __name__ == "__main__":
    main()
