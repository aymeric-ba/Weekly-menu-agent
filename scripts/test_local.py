#!/usr/bin/env python3
"""
Local test script.

Usage:
  # Test only the Anthropic menu generation (no Google credentials needed):
  python scripts/test_local.py --menu-only

  # Full end-to-end test (creates a real Google Tasks list):
  python scripts/test_local.py

Required env vars:
  ANTHROPIC_API_KEY          — always required
  GOOGLE_CLIENT_ID           — required for full test
  GOOGLE_CLIENT_SECRET       — required for full test
  GOOGLE_REFRESH_TOKEN       — required for full test

Tip: copy .env.example to .env, fill in the values, then:
  export $(cat .env | xargs) && python scripts/test_local.py
"""

import sys
import os

# Make sure we can import from the project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.generate_menu import main  # noqa: E402

if __name__ == "__main__":
    menu_only = "--menu-only" in sys.argv
    main(dry_run=menu_only)
