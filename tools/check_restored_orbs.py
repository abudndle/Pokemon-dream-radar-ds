#!/usr/bin/env python3
"""Require an independently decoded, positive Orb balance on a restarted ROM.

An optional expected balance makes the second-process check exact. The
screenshot decoder must produce the JSON; this check alone does not establish
that a second emulator process ran or that save media was writable.
"""
import argparse
import json
from pathlib import Path


def require_restored_orbs(observation, expected_balance=None):
    if not isinstance(observation, dict):
        raise ValueError("Restart Orb observation must be an object")
    balance = observation.get("saved_orbs")
    if type(balance) is not int or not 1 <= balance <= 0xffffffff:
        raise ValueError("Clean-restart acceptance failed: no restored saved Dream Orbs")
    if expected_balance is not None:
        if type(expected_balance) is not int or not 1 <= expected_balance <= 0xffffffff:
            raise ValueError("Expected restored Dream Orb balance must be a positive uint32")
        if balance != expected_balance:
            raise ValueError(
                f"Clean-restart acceptance failed: expected {expected_balance} saved Dream Orbs, observed {balance}"
            )
    return balance


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("observation", type=Path)
    parser.add_argument("--expected-balance", type=int, default=None,
                        help="Require an exact first-session balance; positive alone is insufficient")
    args = parser.parse_args()
    try:
        balance = require_restored_orbs(
            json.loads(args.observation.read_text()), args.expected_balance
        )
    except (ValueError, OSError) as exc:
        parser.exit(1, f"{exc}\n")
    if args.expected_balance is None:
        print(f"PASS: restarted emulator read {balance} positive saved Dream Orbs (exact persistence unverified)")
    else:
        print(f"PASS: restarted emulator read {balance} saved Dream Orbs (exact first-session balance matched)")


if __name__ == "__main__":
    main()
