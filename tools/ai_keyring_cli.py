#!/usr/bin/env python3
"""Interactive CLI to store provider API keys in the OS keyring.

Usage: python3 tools/ai_keyring_cli.py
"""
from __future__ import annotations

import getpass
import sys
from mcaoe.ai.provider import SUPPORTED_PROVIDERS, store_api_key_in_keyring, get_api_key


def choose_provider() -> str | None:
    print("Supported providers:")
    for i, p in enumerate(SUPPORTED_PROVIDERS, start=1):
        print(f"{i}. {p}")
    try:
        choice = input("Select provider number: ")
        idx = int(choice) - 1
        return SUPPORTED_PROVIDERS[idx]
    except Exception:
        print("Invalid selection")
        return None


def main() -> int:
    provider = choose_provider()
    if not provider:
        return 1

    existing = get_api_key(provider)
    if existing:
        print("A key already exists in your environment or keyring. Overwrite? (y/N)")
        resp = input().strip().lower()
        if resp != "y":
            print("Aborting.")
            return 0

    key = getpass.getpass(prompt=f"Enter API key for {provider}: ")
    if not key:
        print("Empty key provided. Aborting.")
        return 1

    ok = store_api_key_in_keyring(provider, key)
    if ok:
        print("Stored key securely in system keyring.")
        return 0
    print("Failed to store key in keyring. Consider setting an environment variable instead.")
    return 2


if __name__ == "__main__":
    sys.exit(main())
