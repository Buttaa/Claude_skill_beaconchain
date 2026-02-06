#!/usr/bin/env python3
"""
Format beaconcha.in API reward data into a human-readable summary.

Usage:
    python scripts/format_rewards.py <json_file_or_stdin> [--cl-only] [--el-only]

Accepts the raw JSON response from POST /api/v2/ethereum/validators/rewards-list
and outputs a formatted summary table with ETH values, efficiency, and breakdown.

Options:
    --cl-only   Show only consensus layer rewards (attestation + sync + proposal CL)
    --el-only   Show only execution layer rewards (proposal EL/MEV)
"""

import json
import sys


def wei_to_eth(wei_str):
    """Convert wei string to ETH float."""
    return int(wei_str) / 1e18


def format_eth(eth_value, decimals=6):
    """Format ETH value with specified decimal places."""
    return f"{eth_value:,.{decimals}f} ETH"


def calc_efficiency(reward, penalty, missed):
    """Calculate efficiency as reward / (reward + penalty + missed)."""
    total_possible = reward + penalty + missed
    if total_possible == 0:
        return 100.0
    return (reward / total_possible) * 100


def format_reward_entry(entry):
    """Format a single validator reward entry."""
    validator = entry["validator"]
    idx = validator["index"]
    pubkey = validator.get("public_key", "N/A")
    short_key = pubkey[:10] + "..." + pubkey[-6:] if len(pubkey) > 20 else pubkey

    total_reward = wei_to_eth(entry["total_reward"])
    total_penalty = wei_to_eth(entry["total_penalty"])
    total_missed = wei_to_eth(entry["total_missed"])

    # Attestation breakdown
    att = entry["attestation"]
    att_reward = wei_to_eth(att["total"]) if int(att["total"]) > 0 else 0
    att_head = wei_to_eth(att["head"]["reward"])
    att_source = wei_to_eth(att["source"]["reward"])
    att_target = wei_to_eth(att["target"]["reward"])

    # Sync committee
    sync = entry["sync_committee"]
    sync_reward = wei_to_eth(sync["reward"])
    sync_penalty = wei_to_eth(sync["penalty"])

    # Proposal
    prop = entry["proposal"]
    prop_total = wei_to_eth(prop["total"])
    prop_el = wei_to_eth(prop.get("execution_layer_reward", "0"))
    prop_att_incl = wei_to_eth(prop.get("attestation_inclusion_reward", "0"))

    efficiency = calc_efficiency(total_reward, total_penalty, wei_to_eth(entry["total_missed"]))

    lines = [
        f"═══ Validator {idx} ({short_key}) ═══",
        f"  Finality:    {entry.get('finality', 'unknown')}",
        f"  Total reward:  {format_eth(total_reward)}",
        f"  Total penalty: {format_eth(total_penalty)}",
        f"  Total missed:  {format_eth(wei_to_eth(entry['total_missed']))}",
        f"  Efficiency:    {efficiency:.2f}%",
        f"",
        f"  Attestation:   {format_eth(att_reward)}",
        f"    Head:   {format_eth(att_head)}",
        f"    Source: {format_eth(att_source)}",
        f"    Target: {format_eth(att_target)}",
        f"",
        f"  Sync Committee: reward={format_eth(sync_reward)}, penalty={format_eth(sync_penalty)}",
        f"",
        f"  Proposals:     {format_eth(prop_total)}",
        f"    EL reward:   {format_eth(prop_el)}",
        f"    Att. incl.:  {format_eth(prop_att_incl)}",
    ]
    return "\n".join(lines)


def format_range(data):
    """Format the epoch/slot range from the response."""
    r = data.get("range", {})
    epoch = r.get("epoch", {})
    slot = r.get("slot", {})
    lines = []
    if epoch:
        lines.append(f"Epoch range: {epoch.get('start', '?')} – {epoch.get('end', '?')}")
    if slot:
        lines.append(f"Slot range:  {slot.get('start', '?')} – {slot.get('end', '?')}")
    return "\n".join(lines)


def main():
    # Parse flags
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    cl_only = "--cl-only" in sys.argv
    el_only = "--el-only" in sys.argv

    if args and args[0] != "-":
        with open(args[0], "r") as f:
            raw = json.load(f)
    else:
        raw = json.load(sys.stdin)

    mode = "CL Only" if cl_only else "EL Only" if el_only else "CL + EL"
    print("╔══════════════════════════════════════════╗")
    print(f"║   Validator Rewards Report ({mode:>9})   ║")
    print("╚══════════════════════════════════════════╝")
    print()

    if "range" in raw:
        print(format_range(raw))
        print()

    entries = raw.get("data", [])
    if not entries:
        print("No reward data found.")
        return

    total_reward_sum = 0
    total_penalty_sum = 0

    for entry in entries:
        if cl_only or el_only:
            # Calculate CL and EL components
            att_total = wei_to_eth(entry["attestation"]["total"])
            sync_reward = wei_to_eth(entry["sync_committee"]["reward"])
            el_reward = wei_to_eth(entry["proposal"].get("execution_layer_reward", "0"))
            proposal_total = wei_to_eth(entry["proposal"]["total"])
            proposal_cl = proposal_total - el_reward

            cl_total = att_total + sync_reward + proposal_cl
            validator = entry["validator"]
            idx = validator["index"]
            pubkey = validator.get("public_key", "N/A")
            short_key = pubkey[:10] + "..." + pubkey[-6:] if len(pubkey) > 20 else pubkey

            if cl_only:
                print(f"═══ Validator {idx} ({short_key}) — CL Only ═══")
                print(f"  CL reward:     {format_eth(cl_total)}")
                print(f"    Attestation: {format_eth(att_total)}")
                print(f"    Sync:        {format_eth(sync_reward)}")
                print(f"    Proposal CL: {format_eth(proposal_cl)}")
                total_reward_sum += cl_total
            else:
                print(f"═══ Validator {idx} ({short_key}) — EL Only ═══")
                print(f"  EL reward:     {format_eth(el_reward)}")
                total_reward_sum += el_reward
        else:
            print(format_reward_entry(entry))
            total_reward_sum += wei_to_eth(entry["total_reward"])
            total_penalty_sum += wei_to_eth(entry["total_penalty"])
        print()

    if len(entries) > 1:
        print("─── Aggregate ───")
        print(f"  Validators:    {len(entries)}")
        print(f"  Total rewards: {format_eth(total_reward_sum)}")
        if not cl_only and not el_only:
            print(f"  Total penalty: {format_eth(total_penalty_sum)}")
            print(f"  Net:           {format_eth(total_reward_sum - total_penalty_sum)}")


if __name__ == "__main__":
    main()
