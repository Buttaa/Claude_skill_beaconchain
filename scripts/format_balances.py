#!/usr/bin/env python3
"""
Format beaconcha.in balance-list API response into a trend analysis.

Usage:
    python scripts/format_balances.py <json_file_or_stdin>

Accepts raw JSON from POST /api/v2/ethereum/validators/balance-list
and outputs a formatted balance history with trend analysis.
"""

import json
import sys
from datetime import datetime, timezone

GENESIS_TS = 1606824023
SECONDS_PER_EPOCH = 384


def wei_to_eth(wei_str):
    return int(wei_str) / 1e18


def format_eth(val, decimals=6):
    return f"{val:,.{decimals}f} ETH"


def epoch_to_time(epoch):
    ts = GENESIS_TS + (epoch * SECONDS_PER_EPOCH)
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def main():
    if len(sys.argv) > 1 and sys.argv[1] != "-":
        with open(sys.argv[1], "r") as f:
            raw = json.load(f)
    else:
        raw = json.load(sys.stdin)

    entries = raw.get("data", [])
    if not entries:
        print("No balance data found.")
        return

    print("╔══════════════════════════════════════════════╗")
    print("║   Validator Balance History                   ║")
    print("╚══════════════════════════════════════════════╝")
    print()

    # Group by validator
    by_validator = {}
    for entry in entries:
        idx = entry.get("validator", {}).get("index", entry.get("validator_index", "?"))
        if idx not in by_validator:
            by_validator[idx] = []
        by_validator[idx].append(entry)

    for idx, snapshots in by_validator.items():
        print(f"═══ Validator {idx} ═══")

        # Sort by epoch
        snapshots.sort(key=lambda e: e.get("epoch", 0))

        balances = []
        prev_bal = None

        for snap in snapshots:
            epoch = snap.get("epoch", "?")
            balance = wei_to_eth(snap.get("balance", snap.get("current", "0")))
            effective = wei_to_eth(snap.get("effective_balance", snap.get("effective", "0")))
            balances.append(balance)

            # Change indicator
            change_str = ""
            if prev_bal is not None:
                diff = balance - prev_bal
                if diff > 0.001:
                    change_str = f"  ↑ +{format_eth(diff)}"
                elif diff < -0.001:
                    change_str = f"  ↓ {format_eth(diff)}"

            time_str = epoch_to_time(epoch) if isinstance(epoch, int) else ""
            print(f"  Epoch {epoch:>8}  {time_str}  {format_eth(balance, 4)} (eff: {format_eth(effective, 4)}){change_str}")
            prev_bal = balance

        print()

        if len(balances) >= 2:
            net_change = balances[-1] - balances[0]
            max_bal = max(balances)
            min_bal = min(balances)
            max_drop = min(0, min(balances[i+1] - balances[i] for i in range(len(balances)-1)))

            print(f"  Trend Analysis:")
            print(f"    First balance:    {format_eth(balances[0], 4)}")
            print(f"    Latest balance:   {format_eth(balances[-1], 4)}")
            print(f"    Net change:       {format_eth(net_change)}")
            print(f"    Peak:             {format_eth(max_bal, 4)}")
            print(f"    Trough:           {format_eth(min_bal, 4)}")

            if max_drop < -0.01:
                print(f"    ⚠️  Largest single drop: {format_eth(max_drop)} (check for penalties/slashing)")

            print()


if __name__ == "__main__":
    main()
