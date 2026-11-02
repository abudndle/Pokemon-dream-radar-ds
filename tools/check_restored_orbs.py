#!/usr/bin/env python3
"""Require an independently decoded, positive Orb balance on a restarted ROM.

The screenshot decoder must produce the JSON; this check alone does not
establish that a second emulator process ran or that save media was writable.
"""
import argparse
import json
from pathlib import Path


def require_restored_orbs(observation):
    if not isinstance(observation, dict):
        raise ValueError("Restart Orb observation must be an object")
    balance = observation.get("saved_orbs")
    if type(balance) is not int or not 1 <= balance <= 0xffffffff:
        raise ValueError("Clean-restart acceptance failed: no restored saved Dream Orbs")
    return balance


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("observation", type=Path)
    args = parser.parse_args()
    try:
        balance = require_restored_orbs(json.loads(args.observation.read_text()))
    except (ValueError, OSError) as exc:
        parser.exit(1, f"{exc}\n")
    print(f"PASS: restarted emulator read {balance} previously saved Dream Orbs")


if __name__ == "__main__":
    main()
