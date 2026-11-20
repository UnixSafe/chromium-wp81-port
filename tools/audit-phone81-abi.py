#!/usr/bin/env python3
"""Compare ARMNT COFF externals or PE imports with caller-supplied DLL exports."""
import argparse
import re
import subprocess
from collections import defaultdict
from pathlib import Path


def run(tool, *args):
    return subprocess.run([tool, *args], capture_output=True, text=True,
                          errors="replace", check=True).stdout


def inspect(tool, path, option):
    data = run(tool, "--file-headers", option, path)
    if "Machine: IMAGE_FILE_MACHINE_ARMNT " not in data:
        raise ValueError(f"{path.name}: expected ARMNT")
    return data


def blocks(data, kind):
    return re.findall(r"^" + kind + r" \{\n(.*?)^\}", data, re.M | re.S)


def field(block, key):
    match = re.search(r"^  " + key + r":[ \t]*(.*)$", block, re.M)
    if not match:
        raise ValueError(f"Missing LLVM field {key}")
    return match[1].strip()


def exports(tool, directories):
    providers = {}
    for directory in directories:
        for path in sorted(directory.iterdir()):
            if not path.is_file() or path.suffix.lower() != ".dll":
                continue
            name = path.name.lower()
            if name in providers:
                raise ValueError(f"Duplicate provider {name}")
            data = inspect(tool, path, "--coff-exports")
            if "ImageOptionalHeader {" not in data:
                raise ValueError(f"{path.name}: expected a PE image")
            symbols = set()
            for block in blocks(data, "Export"):
                if int(field(block, "RVA"), 0):
                    symbols.add("#" + field(block, "Ordinal"))
                    symbol = field(block, "Name")
                    if symbol:
                        symbols.add(symbol)
            providers[name] = symbols
    if not providers:
        raise ValueError("No provider DLLs found")
    return providers


def audit_image(data, providers):
    complete = True
    for kind in ("Import", "DelayImport"):
        for block in blocks(data, kind):
            dll = field(block, "Name").lower()
            for raw in re.findall(r"^\s*Symbol:[ \t]*(.*)$", block, re.M):
                parsed = re.fullmatch(r"(.*?)\s*\((\d+)\)", raw.strip())
                if not parsed:
                    raise ValueError(f"Unexpected LLVM import record: {raw}")
                symbol = parsed[1] or "#" + parsed[2]
                if dll not in providers:
                    status = "DLL-NOT-SUPPLIED"
                elif symbol not in providers[dll]:
                    status = "EXPORT-MISSING"
                else:
                    status = "FOUND"
                print(f"{status}\t{kind}\t{dll}!{symbol}")
                complete &= status == "FOUND"
    return complete


def audit_object(tool, path, providers):
    by_symbol = defaultdict(list)
    for dll, symbols in providers.items():
        for symbol in symbols:
            by_symbol[symbol].append(dll)
    complete = True
    for line in run(tool, "--undefined-only", "--format=posix", path).splitlines():
        raw, binding, *_ = line.rsplit(None, 3)
        symbol = raw.removeprefix("__imp_")
        matches = by_symbol.get(symbol, [])
        status = "EXPORT-CANDIDATE" if matches else "REVIEW"
        print("\t".join([status, binding, raw, *matches]))
        complete &= bool(matches)
    return complete


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--dll-dir", action="append", type=Path, required=True)
    parser.add_argument("--llvm-readobj", default="llvm-readobj")
    parser.add_argument("--llvm-nm", default="llvm-nm")
    args = parser.parse_args()
    try:
        providers = exports(args.llvm_readobj, args.dll_dir)
        data = inspect(args.llvm_readobj, args.input, "--coff-imports")
        if "ImageOptionalHeader {" in data:
            complete = audit_image(data, providers)
        else:
            complete = audit_object(args.llvm_nm, args.input, providers)
    except subprocess.CalledProcessError as error:
        parser.exit(2, f"{error.stderr or error}\n")
    except (OSError, ValueError) as error:
        parser.exit(2, f"{error}\n")
    return 0 if complete else 1


if __name__ == "__main__":
    raise SystemExit(main())
