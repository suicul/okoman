#!/usr/bin/env python3
"""Build script for OKO БОД Manager Mobile (Android).

Requirements:
    pip install kivy buildozer

Usage:
    python build_mobile.py          # Build for current platform
    python build_mobile.py --android # Build for Android (requires buildozer)
"""

import subprocess
import sys
import os


def build_android() -> None:
    """Build APK using Buildozer."""
    print("Building OKO БОД Manager for Android...")
    print("Requires: buildozer, Android SDK, Android NDK")
    print()

    # Check if buildozer is installed
    try:
        import buildozer
    except ImportError:
        print("ERROR: buildozer is not installed.")
        print("Install with: pip install buildozer")
        print()
        print("For Android build, also need:")
        print("  1. sudo apt-get install python3-pip git zip unzip")
        print("  2. sudo apt-get install autoconf libtool pkg-config")
        print("  3. sudo apt-get install libssl1.1  # or libssl3")
        print("  4. sudo apt-get install openjdk-8-jdk")
        print()
        print("Then run: buildozer init && buildozer android debug")
        return

    # Initialize buildozer spec if not exists
    spec_file = "buildozer.spec"
    if not os.path.exists(spec_file):
        print("Creating buildozer.spec...")
        subprocess.run(["buildozer", "init"], check=False)

    print("Running buildozer android debug...")
    result = subprocess.run(
        ["buildozer", "android", "debug"],
        cwd=os.path.dirname(os.path.abspath(__file__)),
    )

    if result.returncode == 0:
        print()
        print("Build successful!")
        print("APK will be in: dist/")
    else:
        print()
        print("Build failed. Check buildozer.log for details.")


def build_desktop() -> None:
    """Build for desktop using PyInstaller."""
    print("Building OKO БОД Manager for desktop...")

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "build.spec",
        "--noconfirm",
        "--clean",
    ]

    result = subprocess.run(cmd)

    if result.returncode == 0:
        print()
        print("Build successful!")
        print("Output: dist/oko_manager/")
    else:
        print()
        print("Build failed!")
        sys.exit(1)


def main() -> None:
    args = sys.argv[1:]

    if "--android" in args:
        build_android()
    elif "--desktop" in args:
        build_desktop()
    else:
        # Default: show help
        print("OKO БОД Manager — Build Script")
        print()
        print("Usage:")
        print("  python build_mobile.py              # Show this help")
        print("  python build_mobile.py --desktop    # Build for desktop")
        print("  python build_mobile.py --android    # Build for Android")
        print()
        print("For Android, ensure buildozer and Android SDK are installed.")


if __name__ == "__main__":
    main()
