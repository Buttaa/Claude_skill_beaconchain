#!/usr/bin/env python3
"""
Format beaconcha.in queue data with wait time estimates.

Usage:
    python scripts/format_queues.py <json_file_or_stdin>

Accepts raw JSON from POST /api/v2/ethereum/queues or
GET /api/v1/validators/queue and outputs formatted queue status with wait estimates.
"""

import json
import sys


def format_number(n):
    return f"{n:,}"


def format_wait(hours):
    if hours < 1:
        return f"~{hours * 60:.0f} minutes"
    elif hours < 24:
        return f"~{hours:.1f} hours"
    elif hours < 48:
        return f"~{hours:.0f} hours ({hours/24:.1f} days)"
    else:
        return f"~{hours/24:.1f} days"


def calc_wait(queue_length, active_validators):
    """Calculate estimated wait time in hours."""
    churn_limit = max(4, active_validators // 65536)
    if churn_limit == 0:
        return 0, 0
    wait_epochs = queue_length / churn_limit
    wait_hours = wait_epochs * 6.4 / 60
    return wait_hours, churn_limit


def queue_indicator(queue_length, queue_type="activation"):
    """Indicate queue severity."""
    if queue_length == 0:
        return "🟢 Empty"
    elif queue_length < 100:
        return "🟢 Short"
    elif queue_length < 1000:
        return "🟡 Moderate"
    elif queue_length < 10000:
        return "🟠 Long"
    else:
        return "🔴 Very long"


def main():
    if len(sys.argv) > 1 and sys.argv[1] != "-":
        with open(sys.argv[1], "r") as f:
            raw = json.load(f)
    else:
        raw = json.load(sys.stdin)

    data = raw.get("data", raw)
    if isinstance(data, list):
        data = data[0] if data else {}

    print("╔══════════════════════════════════════════════╗")
    print("║   Validator Queue Status                      ║")
    print("╚══════════════════════════════════════════════╝")
    print()

    # Extract queue data (handle V1 and V2 field names)
    activation = (data.get("beaconchain_entering", 0) or
                  data.get("activation_queue", 0) or
                  data.get("entering", 0) or
                  data.get("entry_queue", 0))

    exit_q = (data.get("beaconchain_exiting", 0) or
              data.get("exit_queue", 0) or
              data.get("exiting", 0))

    withdrawal = (data.get("withdrawal_queue", 0) or
                  data.get("withdrawals", 0))

    active = (data.get("active_validators", 0) or
              data.get("validatorscount", 0) or
              data.get("active", 0))

    # If we don't have active count, use a reasonable estimate
    if not active:
        active = 970000  # Approximate as of early 2026
        print(f"  ℹ️  Using estimated active validator count: {format_number(active)}")
        print()

    churn_limit = max(4, active // 65536)
    activations_per_day = churn_limit * 225  # 225 epochs per day

    print(f"  Network Info")
    print(f"    Active validators:  {format_number(active)}")
    print(f"    Churn limit:        {churn_limit} per epoch ({format_number(activations_per_day)} per day)")
    print()

    queues = [
        ("Activation", activation, "Validators waiting to enter the active set"),
        ("Exit", exit_q, "Validators waiting to leave the active set"),
        ("Withdrawal", withdrawal, "Validators waiting for balance sweep"),
    ]

    for name, length, desc in queues:
        if length is None:
            continue

        indicator = queue_indicator(length, name.lower())
        wait_hours, _ = calc_wait(length, active)

        print(f"  {name} Queue  {indicator}")
        print(f"    Pending:  {format_number(length)}")
        if length > 0:
            print(f"    Wait:     {format_wait(wait_hours)}")
        print(f"    Info:     {desc}")
        print()

    # Practical advice
    print("═══ Planning Advice ═══")
    if activation > 0:
        wait_h, _ = calc_wait(activation, active)
        print(f"  Staking:   If you deposit now, expect ~{format_wait(wait_h)} before earning rewards.")
    else:
        print(f"  Staking:   No activation queue — new validators activate within minutes.")

    if exit_q > 1000:
        wait_h, _ = calc_wait(exit_q, active)
        print(f"  Exiting:   Queue is long. Plan for ~{format_wait(wait_h)} before exit completes.")
    elif exit_q > 0:
        wait_h, _ = calc_wait(exit_q, active)
        print(f"  Exiting:   Queue is short. Exit should complete in {format_wait(wait_h)}.")
    else:
        print(f"  Exiting:   No exit queue — exits process immediately.")


if __name__ == "__main__":
    main()
