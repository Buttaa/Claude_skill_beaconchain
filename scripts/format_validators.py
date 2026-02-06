#!/usr/bin/env python3
"""
Format beaconcha.in validator overview data into a human-readable summary.

Usage:
    python scripts/format_validators.py <json_file_or_stdin>

Accepts the raw JSON response from POST /api/v2/ethereum/validators
and outputs a formatted status report.
"""

import json
import sys
from collections import Counter


def wei_to_eth(wei_str):
    """Convert wei string to ETH float."""
    return int(wei_str) / 1e18


def format_eth(eth_value, decimals=4):
    return f"{eth_value:,.{decimals}f} ETH"


def status_emoji(status, online):
    """Return a status indicator."""
    if "slashing" in status:
        return "🔴 SLASHED"
    if "exited" in status or status == "withdrawal":
        return "⬜ EXITED"
    if "exiting" in status:
        return "🟡 EXITING"
    if "pending" in status:
        return "🔵 PENDING"
    if online:
        return "🟢 ONLINE"
    return "🔴 OFFLINE"


def main():
    if len(sys.argv) > 1 and sys.argv[1] != "-":
        with open(sys.argv[1], "r") as f:
            raw = json.load(f)
    else:
        raw = json.load(sys.stdin)

    entries = raw.get("data", [])
    if not entries:
        print("No validator data found.")
        return

    print("╔══════════════════════════════════════════════╗")
    print("║    Beaconcha.in Validator Status Report      ║")
    print("╚══════════════════════════════════════════════╝")
    print()

    status_counts = Counter()
    total_balance = 0
    total_effective = 0
    offline_validators = []

    for v in entries:
        idx = v["validator"]["index"]
        pubkey = v["validator"].get("public_key", "N/A")
        short_key = pubkey[:10] + "..." + pubkey[-6:] if len(pubkey) > 20 else pubkey
        status = v["status"]
        online = v.get("online", False)
        slashed = v.get("slashed", False)
        current_bal = wei_to_eth(v["balances"]["current"])
        effective_bal = wei_to_eth(v["balances"]["effective"])

        total_balance += current_bal
        total_effective += effective_bal
        status_counts[status] += 1

        indicator = status_emoji(status, online)

        lifecycle = v.get("life_cycle_epochs", {})

        print(f"  {indicator}  Validator {idx} ({short_key})")
        print(f"    Balance: {format_eth(current_bal)} (effective: {format_eth(effective_bal)})")
        print(f"    Status:  {status} | Slashed: {slashed}")

        if lifecycle.get("activation"):
            print(f"    Activated at epoch: {lifecycle['activation']}")
        if lifecycle.get("exit") and lifecycle["exit"] < 2**63:
            print(f"    Exit epoch: {lifecycle['exit']}")

        wc = v.get("withdrawal_credentials", {})
        if wc:
            print(f"    Withdrawal: {wc.get('type', '?')} (prefix {wc.get('prefix', '?')})")

        if not online and "active" in status:
            offline_validators.append(idx)

        print()

    # Summary
    print("═══ Summary ═══")
    print(f"  Total validators: {len(entries)}")
    print(f"  Total balance:    {format_eth(total_balance)}")
    print(f"  Total effective:  {format_eth(total_effective)}")
    print()
    print("  Status breakdown:")
    for status, count in sorted(status_counts.items()):
        print(f"    {status}: {count}")

    if offline_validators:
        print()
        print(f"  ⚠️  OFFLINE active validators: {offline_validators}")
        print(f"     Action: Check node connectivity and client health immediately.")


if __name__ == "__main__":
    main()
