#!/usr/bin/env python3
"""
Analyze missed rewards from beaconcha.in rewards-list API response.

Usage:
    python scripts/analyze_missed.py <json_file_or_stdin>

Accepts raw JSON from POST /api/v2/ethereum/validators/rewards-list
and outputs a breakdown of missed rewards by duty type with actionable diagnostics.
"""

import json
import sys


def wei_to_eth(wei_str):
    return int(wei_str) / 1e18


def format_eth(val, decimals=6):
    return f"{val:,.{decimals}f} ETH"


def pct(part, total):
    if total == 0:
        return 0.0
    return (part / total) * 100


def analyze_entry(entry):
    """Analyze missed rewards for a single validator across one or more epochs."""
    validator = entry["validator"]
    idx = validator["index"]

    total_reward = wei_to_eth(entry["total_reward"])
    total_missed = wei_to_eth(entry["total_missed"])
    total_penalty = wei_to_eth(entry["total_penalty"])
    total_possible = total_reward + total_missed + total_penalty

    att = entry["attestation"]
    missed = {
        "head": wei_to_eth(att["head"].get("missed_reward", "0")),
        "source": wei_to_eth(att["source"].get("missed_reward", "0")),
        "target": wei_to_eth(att["target"].get("missed_reward", "0")),
        "sync": wei_to_eth(entry["sync_committee"].get("missed_reward", "0")),
        "proposal_cl": wei_to_eth(entry["proposal"].get("missed_cl_reward", "0")),
        "proposal_el": wei_to_eth(entry["proposal"].get("missed_el_reward", "0")),
    }

    penalties = {
        "head": wei_to_eth(att["head"].get("penalty", "0")),
        "source": wei_to_eth(att["source"].get("penalty", "0")),
        "target": wei_to_eth(att["target"].get("penalty", "0")),
        "sync": wei_to_eth(entry["sync_committee"].get("penalty", "0")),
        "inactivity_leak": wei_to_eth(att.get("inactivity_leak_penalty", "0")),
    }

    return {
        "index": idx,
        "total_reward": total_reward,
        "total_missed": total_missed,
        "total_penalty": total_penalty,
        "total_possible": total_possible,
        "capture_rate": pct(total_reward, total_possible),
        "missed": missed,
        "penalties": penalties,
    }


def diagnose(analysis):
    """Generate actionable diagnostics based on missed reward patterns."""
    issues = []
    m = analysis["missed"]
    p = analysis["penalties"]

    if m["head"] > 0:
        issues.append(("⚠️  Missed head votes", "Check network latency and peer count. Ensure beacon node has good connectivity."))

    if m["source"] > 0:
        issues.append(("⚠️  Missed source votes", "Verify beacon node is synced and not falling behind."))

    if m["target"] > 0:
        issues.append(("🔴 Missed target votes", "Most costly miss. Check node sync status and attestation timing. May indicate extended downtime."))

    if m["sync"] > 0:
        issues.append(("⚠️  Missed sync committee duties", "Validator was selected for sync committee but missed participation. Check uptime during sync period."))

    if m["proposal_cl"] > 0 or m["proposal_el"] > 0:
        total_proposal_missed = m["proposal_cl"] + m["proposal_el"]
        issues.append((f"🔴 Missed block proposal ({format_eth(total_proposal_missed)})",
                        "Validator was offline or slow when assigned to propose. Check node was running and MEV relay configured."))

    if p["inactivity_leak"] > 0:
        issues.append(("🔴 INACTIVITY LEAK PENALTY", "Network is experiencing finality issues and your validator was offline. This is a severe penalty. Ensure uptime immediately."))

    if analysis["capture_rate"] >= 99.5:
        issues.append(("✅ Exceptional performance", f"Capture rate: {analysis['capture_rate']:.2f}%. No action needed."))
    elif analysis["capture_rate"] >= 99.0:
        issues.append(("✅ Good performance", f"Capture rate: {analysis['capture_rate']:.2f}%. Minor optimizations possible."))
    elif analysis["capture_rate"] >= 95.0:
        issues.append(("⚠️  Below target", f"Capture rate: {analysis['capture_rate']:.2f}%. Investigate missed duties above."))
    else:
        issues.append(("🔴 Poor performance", f"Capture rate: {analysis['capture_rate']:.2f}%. Immediate attention required."))

    return issues


def main():
    if len(sys.argv) > 1 and sys.argv[1] != "-":
        with open(sys.argv[1], "r") as f:
            raw = json.load(f)
    else:
        raw = json.load(sys.stdin)

    entries = raw.get("data", [])
    if not entries:
        print("No reward data found.")
        return

    print("╔══════════════════════════════════════════════╗")
    print("║   Missed Rewards Analysis                    ║")
    print("╚══════════════════════════════════════════════╝")
    print()

    all_missed = {"head": 0, "source": 0, "target": 0, "sync": 0, "proposal_cl": 0, "proposal_el": 0}
    total_earned = 0
    total_missed = 0

    for entry in entries:
        a = analyze_entry(entry)
        total_earned += a["total_reward"]
        total_missed += a["total_missed"]

        for key in all_missed:
            all_missed[key] += a["missed"][key]

        print(f"═══ Validator {a['index']} ═══")
        print(f"  Earned:       {format_eth(a['total_reward'])}")
        print(f"  Missed:       {format_eth(a['total_missed'])}")
        print(f"  Penalties:    {format_eth(a['total_penalty'])}")
        print(f"  Capture rate: {a['capture_rate']:.2f}%")
        print()

        print("  Missed by duty type:")
        print(f"    Attestation (head):    {format_eth(a['missed']['head'])}")
        print(f"    Attestation (source):  {format_eth(a['missed']['source'])}")
        print(f"    Attestation (target):  {format_eth(a['missed']['target'])}")
        print(f"    Sync committee:        {format_eth(a['missed']['sync'])}")
        print(f"    Proposals (CL):        {format_eth(a['missed']['proposal_cl'])}")
        print(f"    Proposals (EL/MEV):    {format_eth(a['missed']['proposal_el'])}")
        print()

        diagnostics = diagnose(a)
        print("  Diagnostics:")
        for label, advice in diagnostics:
            print(f"    {label}")
            print(f"      → {advice}")
        print()

    if len(entries) > 1:
        print("═══ Aggregate Missed Rewards ═══")
        total_possible = total_earned + total_missed
        print(f"  Total earned:  {format_eth(total_earned)}")
        print(f"  Total missed:  {format_eth(total_missed)}")
        print(f"  Capture rate:  {pct(total_earned, total_possible):.2f}%")
        print()
        print("  Missed by duty (all validators):")
        for key, val in all_missed.items():
            if val > 0:
                print(f"    {key}: {format_eth(val)}")


if __name__ == "__main__":
    main()
