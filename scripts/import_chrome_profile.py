"""One-Time Profile & Login Importer for Nexus Voice Assistant.

Copies saved login sessions, cookies, and preferences from your default Chrome profile
into the dedicated Nexus_Profile so that all sites (e.g. Instagram, YouTube, GitHub)
stay logged in inside Nexus's automated browser.

Usage:
    python scripts/import_chrome_profile.py [--force]
"""

import argparse
import os
import sys

# Ensure root directory is on Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.task_executor import import_existing_chrome_profile, is_chrome_running


def main():
    parser = argparse.ArgumentParser(description="Import Chrome profile and logins into Nexus_Profile.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force overwrite existing Nexus_Profile login data even if already initialized.",
    )
    args = parser.parse_args()

    print("=" * 65)
    print("      Nexus Voice Assistant - Chrome Profile & Login Importer     ")
    print("=" * 65)

    if is_chrome_running():
        print("\n[WARNING] Chrome is currently running!")
        print("Chrome locks its login and cookie databases while active.")
        print("Please close all open Chrome windows and press Enter to continue...")
        try:
            input("\nPress Enter once all Chrome windows are closed (or Ctrl+C to cancel)... ")
        except (KeyboardInterrupt, EOFError):
            print("\nOperation cancelled.")
            sys.exit(1)

    print("\nImporting Chrome profile data...")
    success, message = import_existing_chrome_profile(force=args.force)

    if success:
        print(f"\n[SUCCESS] {message}")
        print("\nNote: This import is a ONE-TIME setup. Going forward, Nexus_Profile is a")
        print("permanent Chrome profile. Any new logins or changes made inside Nexus's")
        print("Chrome window will persist automatically across future sessions.")
    else:
        print(f"\n[FAILED] {message}")
        sys.exit(1)


if __name__ == "__main__":
    main()
