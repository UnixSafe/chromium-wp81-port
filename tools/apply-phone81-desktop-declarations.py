#!/usr/bin/env python3
"""Add //build/config/win:phone81_desktop_declarations to the GN targets of
failed objects listed in a Ninja log (local helper for the Phone 8.1 port).

Usage: apply-desktop-decls.py <ninja.log> <chromium-src> [--dry-run]
Prints each (BUILD.gn, target) it changes; skips targets it cannot find or
that are already configured. Pristine copies must be extracted separately.
"""
import re
import sys
from pathlib import Path

CONFIG = '"//build/config/win:phone81_desktop_declarations"'
SKIP_DIRS = ("third_party/libc++", "buildtools/", "v8/", "base/")


def main():
    log, src = Path(sys.argv[1]), Path(sys.argv[2])
    dry = "--dry-run" in sys.argv
    pairs = set()
    for line in log.read_text(errors="replace").splitlines():
        m = re.match(r"FAILED: \[code=\d+\] obj/(.+)/([^/]+)/[^/ ]+\.obj", line)
        if m:
            pairs.add((m.group(1), m.group(2)))
    changed = []
    for d, target in sorted(pairs):
        if d.startswith(SKIP_DIRS) or d.startswith("gen/"):
            continue
        build = src / d / "BUILD.gn"
        if not build.exists():
            print(f"skip {d}:{target} (no BUILD.gn)")
            continue
        text = build.read_text()
        decl = re.search(
            r'^(?P<indent>[ \t]*)[A-Za-z_][A-Za-z0-9_]*\((?:[A-Za-z_][A-Za-z0-9_]*, )?"%s"\) \{\n'
            % re.escape(target),
            text, re.M)
        if not decl:
            print(f"skip {d}:{target} (declaration not found)")
            continue
        start = decl.end()
        if CONFIG in text[start:start + 400]:
            continue
        indent = decl.group("indent") + "  "
        insert = f"{indent}configs += [ {CONFIG} ]\n"
        text = text[:start] + insert + text[start:]
        changed.append(f"{d}/BUILD.gn:{target}")
        if not dry:
            build.write_text(text)
    for c in changed:
        print("configured", c)


if __name__ == "__main__":
    main()
