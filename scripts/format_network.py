#!/usr/bin/env python3
"""
Format beaconcha.in network overview API response.

Usage:
    python scripts/format_network.py <json_file_or_stdin>

Accepts raw JSON from POST /api/v2/ethereum/network or
GET /api/v1/epoch/latest and outputs a formatted network health report.
"""

import json
import sys


def wei_to_eth(val):
    if isinstance(val, str):
        return int(val) / 1e18
    return val / 1e18 if val > 1e15 else val


def format_number(n):
    return f"{n:,}"


def participation_indicator(rate):
    """Rate expected as 0-100 percentage."""
    if rate >= 99.0:
        return "🟢 Healthy"
    elif rate >= 97.0:
        return "🟡 Acceptable"
    elif rate >= 95.0:
        return "🟠 Degraded"
    else:
        return "🔴 Critical"


def estimate_queue_wait(queue_length, active_validators):
    """Estimate wait time in hours given queue length and active validator count."""
    churn_limit = max(4, active_validators // 65536)
    if churn_limit == 0:
        return float('inf'), churn_limit
    wait_epochs = queue_length / churn_limit
    wait_hours = wait_epochs * 6.4 / 60
    return wait_hours, churn_limit


def format_wait(hours):
    if hours < 1:
        return f"{hours * 60:.0f} minutes"
    elif hours < 24:
        return f"{hours:.1f} hours"
    else:
        return f"{hours / 24:.1f} days"


def main():
    if len(sys.argv) > 1 and sys.argv[1] != "-":
        with open(sys.argv[1], "r") as f:
            raw = json.load(f)
    else:
        raw = json.load(sys.stdin)

    # Handle both V2 (nested under "data") and V1 (flat) formats
    data = raw.get("data", raw)
    if isinstance(data, list):
        data = data[0] if data else {}

    print("╔══════════════════════════════════════════════╗")
    print("║   Ethereum Network Health Report             ║")
    print("╚══════════════════════════════════════════════╝")
    print()

    # Extract fields (flexible naming to handle V1/V2 differences)
    active = data.get("active_validators", data.get("validatorscount", 0))
    participation = data.get("participation_rate", data.get("globalparticipationrate", 0))
    if isinstance(participation, float) and participation <= 1.0:
        participation *= 100  # Convert 0-1 to percentage

    finalized_epoch = data.get("finalized_epoch", data.get("finalizedepoch", "?"))
    avg_balance = data.get("average_balance", data.get("averagevalidatorbalance", 0))

    # Queue data
    entering = data.get("entering_validators", data.get("beaconchain_entering", 0))
    exiting = data.get("exiting_validators", data.get("beaconchain_exiting", 0))

    print(f"  Validators")
    print(f"    Active:          {format_number(active)}")
    if entering or exiting:
        print(f"    Entering queue:  {format_number(entering)}")
        print(f"    Exiting queue:   {format_number(exiting)}")
    print()

    print(f"  Network Health")
    print(f"    Participation:   {participation:.2f}% {participation_indicator(participation)}")
    print(f"    Finalized epoch: {finalized_epoch}")
    if avg_balance:
        bal = wei_to_eth(avg_balance) if avg_balance > 1e15 else avg_balance / 1e9 if avg_balance > 1e6 else avg_balance
        print(f"    Avg balance:     {bal:.4f} ETH")
    print()

    if active and (entering or exiting):
        churn_limit = max(4, active // 65536)
        print(f"  Queue Estimates (churn limit: {churn_limit}/epoch)")

        if entering:
            wait_h, _ = estimate_queue_wait(entering, active)
            print(f"    Activation wait: ~{format_wait(wait_h)} ({format_number(entering)} pending)")

        if exiting:
            wait_h, _ = estimate_queue_wait(exiting, active)
            print(f"    Exit wait:       ~{format_wait(wait_h)} ({format_number(exiting)} pending)")

        print()

    # Finality check
    if participation < 67:
        print("  🔴 FINALITY AT RISK: Participation below 66.7% threshold")
        print("     The chain cannot finalize. Inactive validators will face inactivity leak penalties.")
    elif participation < 80:
        print("  ⚠️  Low participation may delay finality if it continues to drop.")


if __name__ == "__main__":
    main()
