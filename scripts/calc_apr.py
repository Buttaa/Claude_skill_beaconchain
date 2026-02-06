#!/usr/bin/env python3
"""
Calculate APR/APY from beaconcha.in rewards data.

Usage:
    python scripts/calc_apr.py <json_file_or_stdin> [--stake 32]

Accepts raw JSON from rewards-list, rewards-aggregate, or apy-roi endpoints
and calculates annualized return metrics with CL/EL breakdown.
"""

import json
import sys
import argparse
import math

EPOCHS_PER_YEAR = 82125  # ~365.25 * 225


def wei_to_eth(val):
    if isinstance(val, str):
        return int(val) / 1e18
    return val / 1e18 if val > 1e15 else val


def format_eth(val, decimals=6):
    return f"{val:,.{decimals}f} ETH"


def calc_apr(rewards_eth, balance_eth, epochs):
    """Calculate annualized percentage rate."""
    if balance_eth == 0 or epochs == 0:
        return 0
    period_rate = rewards_eth / balance_eth
    return period_rate * (EPOCHS_PER_YEAR / epochs) * 100


def apr_to_apy(apr_pct):
    """Convert APR to APY with continuous compounding approximation."""
    return (math.exp(apr_pct / 100) - 1) * 100


def main():
    parser = argparse.ArgumentParser(description="APR/APY calculator for beaconcha.in rewards")
    parser.add_argument("input", nargs="?", default="-", help="JSON file or - for stdin")
    parser.add_argument("--stake", type=float, default=32.0, help="Assumed stake per validator in ETH (default: 32)")
    args = parser.parse_args()

    if args.input == "-":
        raw = json.load(sys.stdin)
    else:
        with open(args.input, "r") as f:
            raw = json.load(f)

    entries = raw.get("data", [])

    print("╔══════════════════════════════════════════════╗")
    print("║   APR / APY Calculator                        ║")
    print("╚══════════════════════════════════════════════╝")
    print()

    if not entries:
        # Maybe it's an apy-roi response with different structure
        if "apr" in raw or "apy" in raw or "data" in raw:
            data = raw.get("data", raw)
            if isinstance(data, dict):
                print("  From apy-roi endpoint:")
                for key, val in data.items():
                    if isinstance(val, (int, float)):
                        print(f"    {key}: {val:.4f}%")
                    elif isinstance(val, dict):
                        print(f"    {key}:")
                        for k, v in val.items():
                            if isinstance(v, (int, float)):
                                print(f"      {k}: {v:.4f}%")
                return
        print("No reward data found.")
        return

    # Get epoch range
    epoch_range = raw.get("range", {}).get("epoch", {})
    start_epoch = epoch_range.get("start", 0)
    end_epoch = epoch_range.get("end", 0)
    num_epochs = max(1, end_epoch - start_epoch + 1) if start_epoch and end_epoch else len(entries)

    # Aggregate rewards
    total_reward = 0
    total_cl = 0
    total_el = 0
    total_penalty = 0
    validators = set()

    for entry in entries:
        idx = entry.get("validator", {}).get("index", 0)
        validators.add(idx)

        total_reward += wei_to_eth(entry["total_reward"])
        total_penalty += wei_to_eth(entry["total_penalty"])

        att_reward = wei_to_eth(entry["attestation"]["total"])
        sync_reward = wei_to_eth(entry["sync_committee"]["reward"])
        el_reward = wei_to_eth(entry["proposal"].get("execution_layer_reward", "0"))
        proposal_cl = wei_to_eth(entry["proposal"]["total"]) - el_reward

        total_cl += att_reward + sync_reward + proposal_cl
        total_el += el_reward

    net_reward = total_reward - total_penalty
    num_validators = len(validators)
    assumed_balance = num_validators * args.stake

    # Calculate rates
    total_apr = calc_apr(net_reward, assumed_balance, num_epochs)
    cl_apr = calc_apr(total_cl, assumed_balance, num_epochs)
    el_apr = calc_apr(total_el, assumed_balance, num_epochs)
    total_apy = apr_to_apy(total_apr)

    # Period info
    period_days = num_epochs * 384 / 86400

    print(f"  Period:          {num_epochs:,} epochs (~{period_days:.1f} days)")
    print(f"  Validators:      {num_validators}")
    print(f"  Assumed stake:   {format_eth(assumed_balance, 1)}")
    print()
    print(f"  Rewards Summary")
    print(f"    Total earned:  {format_eth(total_reward)}")
    print(f"    Total penalty: {format_eth(total_penalty)}")
    print(f"    Net reward:    {format_eth(net_reward)}")
    print(f"    CL rewards:    {format_eth(total_cl)} ({total_cl/net_reward*100:.1f}%)" if net_reward else "")
    print(f"    EL rewards:    {format_eth(total_el)} ({total_el/net_reward*100:.1f}%)" if net_reward else "")
    print()
    print(f"  Annualized Returns")
    print(f"    Total APR:     {total_apr:.2f}%")
    print(f"    Total APY:     {total_apy:.2f}%")
    print(f"    CL APR:        {cl_apr:.2f}%")
    print(f"    EL APR:        {el_apr:.2f}%")
    print()

    # Daily extrapolation
    daily_reward = net_reward / period_days if period_days > 0 else 0
    monthly_est = daily_reward * 30
    yearly_est = daily_reward * 365.25

    print(f"  Extrapolated Earnings (per {num_validators} validator{'s' if num_validators > 1 else ''})")
    print(f"    Daily:         ~{format_eth(daily_reward)}")
    print(f"    Monthly:       ~{format_eth(monthly_est)}")
    print(f"    Yearly:        ~{format_eth(yearly_est)}")
    print()

    if period_days < 7:
        print("  ⚠️  Short sample period — APR extrapolation may be unreliable.")
        print("     Proposal rewards are luck-based and can skew short-period estimates.")
    if total_el > total_cl * 0.5:
        print("  ℹ️  EL rewards (proposals/MEV) are a large portion of income.")
        print("     These are highly variable and depend on block proposal luck.")


if __name__ == "__main__":
    main()
