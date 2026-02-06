#!/usr/bin/env python3
"""
Format beaconcha.in rewards-aggregate API response.

Usage:
    python scripts/format_aggregate.py <json_file_or_stdin>

Accepts raw JSON from POST /api/v2/ethereum/validators/rewards-aggregate
and outputs a formatted multi-period comparison with trend indicators.
"""

import json
import sys


def wei_to_eth(wei_str):
    if isinstance(wei_str, (int, float)):
        return wei_str / 1e18 if wei_str > 1e15 else wei_str
    return int(wei_str) / 1e18


def format_eth(val, decimals=6):
    return f"{val:,.{decimals}f} ETH"


def trend_indicator(short_avg, long_avg):
    """Compare short period daily avg vs long period daily avg."""
    if long_avg == 0:
        return ""
    pct_diff = ((short_avg - long_avg) / long_avg) * 100
    if pct_diff > 5:
        return f" ↑ +{pct_diff:.1f}% vs avg"
    elif pct_diff < -5:
        return f" ↓ {pct_diff:.1f}% vs avg"
    else:
        return f" ≈ {pct_diff:+.1f}% vs avg"


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
    print("║   Rewards Aggregate Summary                   ║")
    print("╚══════════════════════════════════════════════╝")
    print()

    periods = [
        ("24h", "1d", 1),
        ("7d", "7d", 7),
        ("30d", "30d", 30),
        ("90d", "90d", 90),
    ]

    daily_avgs = {}
    period_totals = {}

    for label, key, days in periods:
        period_data = data.get(key, data.get(label, data.get(f"rewards_{key}", None)))
        if period_data is None:
            # Try alternate field structures
            for alt_key in [f"total_{key}", f"period_{key}", key.replace("d", "")]:
                period_data = data.get(alt_key)
                if period_data is not None:
                    break

        if period_data is None:
            continue

        if isinstance(period_data, dict):
            total = wei_to_eth(period_data.get("total_reward", period_data.get("total", "0")))
            cl = wei_to_eth(period_data.get("cl_reward", period_data.get("attestation", "0")))
            el = wei_to_eth(period_data.get("el_reward", period_data.get("execution_layer_reward", "0")))
        else:
            total = wei_to_eth(period_data)
            cl = 0
            el = 0

        daily_avg = total / days if days > 0 else total
        daily_avgs[label] = daily_avg
        period_totals[label] = total

    # If we got structured data, print the comparison
    if period_totals:
        # Get longest period daily avg for trend comparison
        long_avg = daily_avgs.get("90d", daily_avgs.get("30d", 0))

        print(f"  {'Period':<8} {'Total':>18} {'Daily Avg':>18} {'Trend':>20}")
        print(f"  {'─'*8} {'─'*18} {'─'*18} {'─'*20}")

        for label, _, days in periods:
            if label in period_totals:
                total = period_totals[label]
                daily = daily_avgs[label]
                trend = trend_indicator(daily, long_avg) if label != "90d" and long_avg > 0 else ""
                print(f"  {label:<8} {format_eth(total):>18} {format_eth(daily):>18} {trend}")

        print()

        if "24h" in period_totals and "30d" in period_totals:
            day_total = period_totals["24h"]
            apr_est = (day_total * 365.25 / 32) * 100  # Rough APR assuming 32 ETH stake
            print(f"  Estimated APR (from 24h): ~{apr_est:.2f}% (rough, based on 32 ETH stake)")

    else:
        # Fallback: dump whatever we got in a readable format
        print("  Raw aggregate data:")
        for key, val in data.items():
            if isinstance(val, str) and val.isdigit():
                print(f"    {key}: {format_eth(wei_to_eth(val))}")
            elif isinstance(val, dict):
                print(f"    {key}:")
                for k, v in val.items():
                    if isinstance(v, str) and v.isdigit():
                        print(f"      {k}: {format_eth(wei_to_eth(v))}")
                    else:
                        print(f"      {k}: {v}")
            else:
                print(f"    {key}: {val}")


if __name__ == "__main__":
    main()
