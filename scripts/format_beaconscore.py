#!/usr/bin/env python3
"""
Format beaconcha.in BeaconScore/performance API response.

Usage:
    python scripts/format_beaconscore.py <json_file_or_stdin>

Accepts raw JSON from POST /api/v2/ethereum/validators/beacon-score
and outputs a formatted performance report with threshold indicators.
"""

import json
import sys


def score_indicator(score):
    if score >= 99.5:
        return "🟢 Exceptional"
    elif score >= 99.0:
        return "🟢 Good"
    elif score >= 97.0:
        return "🟡 Below target"
    elif score >= 95.0:
        return "🟠 Needs attention"
    else:
        return "🔴 Poor"


def format_pct(val, decimals=2):
    return f"{val:.{decimals}f}%"


def main():
    if len(sys.argv) > 1 and sys.argv[1] != "-":
        with open(sys.argv[1], "r") as f:
            raw = json.load(f)
    else:
        raw = json.load(sys.stdin)

    entries = raw.get("data", [])
    if not entries:
        print("No BeaconScore data found.")
        return

    print("╔══════════════════════════════════════════════╗")
    print("║   BeaconScore Performance Report             ║")
    print("╚══════════════════════════════════════════════╝")
    print()
    print("  Component weights: Attestation 84.4% | Proposals 12.5% | Sync 3.1%")
    print("  Target: ≥99.0% good, ≥99.5% exceptional")
    print()

    scores = []

    for entry in entries:
        idx = entry.get("validator", {}).get("index", "?")
        overall = entry.get("beacon_score", entry.get("score", 0))
        attester = entry.get("attester_efficiency", entry.get("attestation", 0))
        proposer = entry.get("proposer_efficiency", entry.get("proposal", 0))
        sync = entry.get("sync_efficiency", entry.get("sync_committee", 0))

        # Handle case where values are 0-1 floats vs 0-100 percentages
        if isinstance(overall, (int, float)) and overall <= 1.0 and overall > 0:
            overall *= 100
            attester *= 100
            proposer *= 100
            sync *= 100

        scores.append(overall)

        indicator = score_indicator(overall)

        print(f"  {indicator}  Validator {idx}")
        print(f"    Overall BeaconScore: {format_pct(overall)}")
        print(f"    ├─ Attestation:      {format_pct(attester)}")
        print(f"    ├─ Proposals:        {format_pct(proposer)}")
        print(f"    └─ Sync committee:   {format_pct(sync)}")
        print()

    if len(entries) > 1:
        avg = sum(scores) / len(scores)
        print("═══ Summary ═══")
        print(f"  Validators:     {len(entries)}")
        print(f"  Average score:  {format_pct(avg)} {score_indicator(avg)}")
        print(f"  Highest:        {format_pct(max(scores))}")
        print(f"  Lowest:         {format_pct(min(scores))}")
        below_target = sum(1 for s in scores if s < 99.0)
        if below_target:
            print(f"  ⚠️  {below_target} validator(s) below 99% target")


if __name__ == "__main__":
    main()
