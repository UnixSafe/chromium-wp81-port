#!/usr/bin/env python3
"""Check selected ARM imports against an installed Windows Phone 8.1 SDK.

The SDK libraries are supplied by the caller and are never copied into this
repository. This catches missing import-library symbols; it does not prove
that an app can call the API successfully at runtime.
"""

import argparse
import re
import subprocess
from pathlib import Path


DEFAULT_SYMBOLS = (
    "CreateFile2",
    "GetFileInformationByHandleEx",
    "GetOverlappedResultEx",
    "WaitForSingleObjectEx",
    "RoGetActivationFactory",
    "D3D11CreateDevice",
    "CreateDXGIFactory2",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lib-dir", type=Path, required=True)
    parser.add_argument("--llvm-nm", default="llvm-nm")
    parser.add_argument("symbols", nargs="*", default=DEFAULT_SYMBOLS)
    args = parser.parse_args()

    libraries = sorted(
        path for path in args.lib_dir.iterdir()
        if path.is_file() and path.suffix.lower() == ".lib"
    )
    if not libraries:
        parser.error(f"No import libraries found in {args.lib_dir}")

    result = subprocess.run(
        [args.llvm_nm, "--defined-only", *(str(path) for path in libraries)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        parser.error(result.stderr.strip() or "llvm-nm failed")

    defined = {
        match.group(1)
        for line in result.stdout.splitlines()
        if (match := re.search(r"\b(?:[A-Z])\s+([^\s]+)$", line))
    }
    missing = []
    for symbol in args.symbols:
        found = symbol in defined or f"__imp_{symbol}" in defined
        print(f"{'FOUND  ' if found else 'MISSING'} {symbol}")
        if not found:
            missing.append(symbol)
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
