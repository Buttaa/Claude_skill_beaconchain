#!/usr/bin/env python3
"""
Convert between Ethereum Beacon Chain epochs, slots, and timestamps.

Usage:
    python scripts/epoch_converter.py --epoch 347566
    python scripts/epoch_converter.py --slot 11122112
    python scripts/epoch_converter.py --timestamp 1740289367
    python scripts/epoch_converter.py --date "2025-02-23T12:00:00"
    python scripts/epoch_converter.py --range "2025-01-01" "2025-12-31"

All outputs include UTC and optionally a local timezone.
"""

import argparse
import sys
from datetime import datetime, timezone, timedelta

# Beacon chain constants
GENESIS_TIMESTAMP = 1606824023  # Dec 1, 2020, 12:00:23 UTC
SECONDS_PER_SLOT = 12
SLOTS_PER_EPOCH = 32
SECONDS_PER_EPOCH = SECONDS_PER_SLOT * SLOTS_PER_EPOCH  # 384
EPOCHS_PER_DAY = 225  # ~24h / 6.4min
EPOCHS_PER_YEAR = 82125  # ~365.25 * 225


def epoch_to_timestamp(epoch):
    return GENESIS_TIMESTAMP + (epoch * SECONDS_PER_EPOCH)


def timestamp_to_epoch(ts):
    return max(0, (ts - GENESIS_TIMESTAMP) // SECONDS_PER_EPOCH)


def slot_to_epoch(slot):
    return slot // SLOTS_PER_EPOCH


def epoch_to_slot_range(epoch):
    start = epoch * SLOTS_PER_EPOCH
    end = start + SLOTS_PER_EPOCH - 1
    return start, end


def slot_to_timestamp(slot):
    return GENESIS_TIMESTAMP + (slot * SECONDS_PER_SLOT)


def timestamp_to_slot(ts):
    return max(0, (ts - GENESIS_TIMESTAMP) // SECONDS_PER_SLOT)


def format_timestamp(ts):
    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")


def parse_date(date_str):
    """Parse a date string into a Unix timestamp."""
    for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]:
        try:
            dt = datetime.strptime(date_str, fmt).replace(tzinfo=timezone.utc)
            return int(dt.timestamp())
        except ValueError:
            continue
    raise ValueError(f"Cannot parse date: {date_str}. Use YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS")


def print_epoch_info(epoch):
    ts = epoch_to_timestamp(epoch)
    slot_start, slot_end = epoch_to_slot_range(epoch)
    print(f"  Epoch:      {epoch:,}")
    print(f"  Slots:      {slot_start:,} – {slot_end:,}")
    print(f"  Timestamp:  {ts} ({format_timestamp(ts)})")
    print(f"  Duration:   {SECONDS_PER_EPOCH}s (6.4 minutes)")


def print_slot_info(slot):
    epoch = slot_to_epoch(slot)
    ts = slot_to_timestamp(slot)
    slot_in_epoch = slot % SLOTS_PER_EPOCH
    print(f"  Slot:       {slot:,}")
    print(f"  Epoch:      {epoch:,} (slot {slot_in_epoch} of {SLOTS_PER_EPOCH})")
    print(f"  Timestamp:  {ts} ({format_timestamp(ts)})")


def print_range_info(start_str, end_str):
    ts_start = parse_date(start_str)
    ts_end = parse_date(end_str)
    epoch_start = timestamp_to_epoch(ts_start)
    epoch_end = timestamp_to_epoch(ts_end)
    total_epochs = epoch_end - epoch_start

    print(f"  Date range:   {format_timestamp(ts_start)} → {format_timestamp(ts_end)}")
    print(f"  Epoch range:  {epoch_start:,} → {epoch_end:,}")
    print(f"  Total epochs: {total_epochs:,}")
    print(f"  Total slots:  {total_epochs * SLOTS_PER_EPOCH:,}")
    print(f"  Duration:     {(ts_end - ts_start) / 86400:.1f} days")
    print()
    print(f"  API calls needed (page_size=100): ~{(total_epochs + 99) // 100}")
    print(f"  Free tier feasibility: {'⚠️ Exceeds 1000 req/mo' if total_epochs > 100000 else '✅ Feasible'}")


def main():
    parser = argparse.ArgumentParser(description="Beacon Chain epoch/slot/timestamp converter")
    parser.add_argument("--epoch", type=int, help="Convert epoch to timestamp/slots")
    parser.add_argument("--slot", type=int, help="Convert slot to epoch/timestamp")
    parser.add_argument("--timestamp", type=int, help="Convert Unix timestamp to epoch/slot")
    parser.add_argument("--date", type=str, help="Convert date string to epoch/slot")
    parser.add_argument("--range", type=str, nargs=2, metavar=("START", "END"),
                        help="Calculate epoch range for a date range")

    args = parser.parse_args()

    if args.epoch is not None:
        print(f"─── Epoch {args.epoch} ───")
        print_epoch_info(args.epoch)

    elif args.slot is not None:
        print(f"─── Slot {args.slot} ───")
        print_slot_info(args.slot)

    elif args.timestamp is not None:
        epoch = timestamp_to_epoch(args.timestamp)
        slot = timestamp_to_slot(args.timestamp)
        print(f"─── Timestamp {args.timestamp} ({format_timestamp(args.timestamp)}) ───")
        print(f"  Epoch: {epoch:,}")
        print(f"  Slot:  {slot:,}")

    elif args.date is not None:
        ts = parse_date(args.date)
        epoch = timestamp_to_epoch(ts)
        slot = timestamp_to_slot(ts)
        print(f"─── {args.date} ({format_timestamp(ts)}) ───")
        print(f"  Unix timestamp: {ts}")
        print(f"  Epoch: {epoch:,}")
        print(f"  Slot:  {slot:,}")

    elif args.range is not None:
        print(f"─── Date Range ───")
        print_range_info(args.range[0], args.range[1])

    else:
        parser.print_help()
        print("\nConstants:")
        print(f"  Genesis timestamp: {GENESIS_TIMESTAMP} ({format_timestamp(GENESIS_TIMESTAMP)})")
        print(f"  Seconds per slot:  {SECONDS_PER_SLOT}")
        print(f"  Slots per epoch:   {SLOTS_PER_EPOCH}")
        print(f"  Seconds per epoch: {SECONDS_PER_EPOCH}")
        print(f"  Epochs per day:    ~{EPOCHS_PER_DAY}")
        print(f"  Epochs per year:   ~{EPOCHS_PER_YEAR}")


if __name__ == "__main__":
    main()
