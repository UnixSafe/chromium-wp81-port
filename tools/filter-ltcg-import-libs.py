#!/usr/bin/env python3
"""Local, non-redistributed step for the Windows Phone 8.1 port.

Two Phone 8.1 SDK ARM libraries contain members compiled with MSVC link-time
code generation (/GL), which lld-link cannot read: uuid.lib (Enhanced
Storage GUIDs) and ws2_32.lib (in*addr_* constants). Remove those members in
place, keeping the originals as *.phone-orig; Chromium's Phone build defines
the few symbols it needs from them itself.
"""
import shutil
import subprocess
from pathlib import Path

AR = "/opt/homebrew/opt/llvm/bin/llvm-ar"
LIB = Path(__file__).resolve().parent / "phone81-toolchain/sdk/lib/um/arm"
MEMBERS = {
    "uuid.lib": "\\ehstorguids\\objfre\\arm\\guids.obj",
    "ws2_32.lib": "\\minio\\netio\\published\\objfre\\arm\\indef.obj",
}

for name, suffix in MEMBERS.items():
    lib = LIB / name
    orig = LIB / (name + ".phone-orig")
    if not orig.exists():
        shutil.copy2(lib, orig)
    shutil.copy2(orig, lib)
    members = subprocess.run([AR, "t", str(lib)], capture_output=True,
                             text=True, check=True).stdout.splitlines()
    removed = [m for m in members if m.endswith(suffix)]
    for m in removed:
        subprocess.run([AR, "d", str(lib), m], check=True)
    print(f"{name}: removed {len(removed)} LTCG member(s)")
