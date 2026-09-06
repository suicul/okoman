#!/usr/bin/env python3
"""Build script for OKO БОД Manager.

Usage:
    python build.py          # Build for current platform
    python build.py --clean   # Clean build artifacts first
"""

import subprocess
import sys
import shutil
import os
from pathlib import Path


def clean() -> None:
    """Remove build artifacts."""
    for d in ("build", "dist"):
        path = Path(d)
        if path.exists():
            print(f"Removing {d}/")
            shutil.rmtree(path)
    for f in Path(".").glob("*.spec"):
        if f.name != "build.spec":
            f.unlink()
    print("Clean complete.")


def build() -> None:
    """Run PyInstaller."""
    print("Building OKO БОД Manager...")
    print(f"Python: {sys.version}")
    print(f"Platform: {sys.platform}")
    print()

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "build.spec",
        "--noconfirm",
        "--clean",
    ]

    result = subprocess.run(cmd, capture_output=False)

    if result.returncode == 0:
        print()
        print("=" * 60)
        print("Build successful!")
        print(f"Output: dist/oko_manager/")
        if sys.platform == "win32":
            print(f"Executable: dist/oko_manager/oko_manager.exe")
        else:
            print(f"Executable: dist/oko_manager/oko_manager")
        print("=" * 60)
    else:
        print()
        print("Build failed!")
        sys.exit(1)


def main() -> None:
    args = sys.argv[1:]

    if "--clean" in args:
        clean()
        return

    build()


if __name__ == "__main__":
    main()
