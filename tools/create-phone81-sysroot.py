#!/usr/bin/env python3
"""Build a local cross-build overlay from licensed WP8.1 SDK files.

The Microsoft SDK is never copied into the public source patch.  Recent Clang
needs one declaration-order fix in WRL event.h; the original MSI is untouched.
The VC/UCRT pieces remain from a newer toolchain pending a compatible runtime.
"""

import argparse
import json
import shutil
from pathlib import Path


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--phone-headers", required=True, type=Path)
parser.add_argument("--phone-arm-libs", required=True, type=Path)
parser.add_argument("--store-resource-headers", required=True, type=Path)
parser.add_argument("--modern-sysroot", required=True, type=Path)
parser.add_argument("--clang-root", required=True, type=Path)
parser.add_argument("--out", required=True, type=Path)
args = parser.parse_args()

root = args.out.resolve()
modern = args.modern_sysroot.resolve()
phone_headers = args.phone_headers.resolve()
phone_lib = args.phone_arm_libs.resolve()
store_resource_headers = args.store_resource_headers.resolve()
clang_root = args.clang_root.resolve()

for required in (
    phone_headers / "windows.h",
    phone_headers / "wrl/event.h",
    phone_lib / "WindowsPhoneCore.lib",
    store_resource_headers / "winresrc.h",
    modern / "crt/include",
    modern / "sdk/include/winrt/wrl",
    clang_root / "bin/clang-cl",
):
    if not required.exists():
        parser.error(f"Missing input: {required}")


def replace_symlink(dst: Path, src: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.is_symlink() or dst.exists():
        dst.unlink()
    dst.symlink_to(src.resolve())


replace_symlink(root / "crt", modern / "crt")
replace_symlink(root / "gn-bin/cl.exe", clang_root / "bin/clang-cl")
headers = root / "sdk/include/um"
if not headers.exists():
    shutil.copytree(phone_headers, headers)

# The old Phone COM header refers to IUnknown in a nondependent template before
# its definition. A forward declaration is sufficient for current Clang.
combase = headers / "combaseapi.h"
combase_source = combase.read_text()
combase_marker = "#include <rpcndr.h>\n"
combase_declaration = "#if defined(__cplusplus) && defined(WINUWP_8_1)\nstruct IUnknown;\n#endif\n"
if combase_declaration not in combase_source:
    assert combase_source.count(combase_marker) == 1
    combase.write_text(combase_source.replace(combase_marker, combase_marker + combase_declaration, 1))

# The Phone kit omits resource-only .rh definitions used by Chromium's GRIT
# output. The same-era Store SDK supplies these constants to the host RC tool.
for name in ("winresrc.h", "winuser.rh", "commctrl.rh", "dde.rh", "winnt.rh"):
    replace_symlink(headers / name, store_resource_headers / name)

# The 2013 WRL templates also rely on pre-standard lookup and assignment
# rules. Use current generic WRL scaffolding with the Phone 8.1 event helper;
# current event.h itself needs WinRT IDeferral interfaces absent in Phone 8.1.
wrl = headers / "wrl"
if wrl.is_symlink():
    wrl.unlink()
elif wrl.exists():
    shutil.rmtree(wrl)
wrl.mkdir()
for item in (modern / "sdk/include/winrt/wrl").iterdir():
    replace_symlink(wrl / item.name, item)

client = wrl / "client.h"
client_source = (modern / "sdk/include/winrt/wrl/client.h").read_text()
agile_region = (
    "#pragma region Application Family or OneCore Family\n"
    "#if WINAPI_FAMILY_PARTITION(WINAPI_PARTITION_APP | WINAPI_PARTITION_SYSTEM)\n\n"
    "template<typename T>\nHRESULT AsAgile(_In_opt_"
)
assert client_source.count(agile_region) == 1
client_source = client_source.replace(
    agile_region,
    agile_region.replace(
        "#if WINAPI_FAMILY_PARTITION(WINAPI_PARTITION_APP | WINAPI_PARTITION_SYSTEM)",
        "#if WINAPI_FAMILY_PARTITION(WINAPI_PARTITION_APP | WINAPI_PARTITION_SYSTEM) && !defined(WINUWP_8_1)",
    ),
    1,
)
client.unlink()
client.write_text(client_source)

# WP8.1 WRL looks up this nondependent name before declaring it.  Relocate
# the exact declaration in a private copy so Clang 24 can compile the header.
event = wrl / "event.h"
source = (phone_headers / "wrl/event.h").read_text()
declaration = (
    "extern __declspec(selectany) const DelegateCheckMode "
    "DefaultDelegateCheckMode = NoCheck;"
)
marker = "template<DelegateCheckMode delegateCheckMode> struct DelegateTraits;"
assert source.count(declaration) == 1
assert source.count(marker) == 1
source = source.replace(declaration, "", 1)
source = source.replace(
    marker,
    "#ifndef BUILD_WINDOWS\n" + declaration + "\n#endif\n\n" + marker,
    1,
)
if event.is_symlink() or event.exists():
    event.unlink()
event.write_text(source)

replace_symlink(root / "sdk/include/shared", headers)
replace_symlink(root / "sdk/include/winrt", headers / "abi")
replace_symlink(root / "sdk/include/minwin", headers / "minwin")
replace_symlink(root / "sdk/include/mincore", headers / "mincore")
replace_symlink(root / "sdk/include/ucrt", modern / "sdk/include/ucrt")
replace_symlink(root / "sdk/include/cppwinrt", modern / "sdk/include/cppwinrt")
replace_symlink(root / "sdk/lib/um/arm", phone_lib)
replace_symlink(root / "sdk/lib/ucrt", modern / "sdk/lib/ucrt")
# Disabling PCH exposes a mismatch: the newer UCRT stddef.h does not define
# max_align_t when it wins over Clang's builtin header. Keep the compiler's
# resource headers first, including the __stddef_* helpers they reference.

include = [
    clang_root / "lib/clang/24/include",
    root / "crt/include",
    root / "sdk/include/um",
    root / "sdk/include/minwin",
    root / "sdk/include/mincore",
    root / "sdk/include/winrt",
    root / "sdk/include/ucrt",
    root / "sdk/include/cppwinrt",
]
arm_lib = [
    root / "crt/lib/onecore/arm",
    root / "crt/lib/arm",
    root / "sdk/lib/um/arm",
    root / "sdk/lib/ucrt/arm",
]
for cpu in ("x86", "x64", "arm", "arm64"):
    env = {
        "VSINSTALLDIR": [["."]],
        "INCLUDE": [[str(path)] for path in include],
        "LIB": [[str(path)] for path in arm_lib],
        "LIBPATH": [],
        "PATH": [[str(root / "gn-bin")], [str(clang_root / "bin")]],
    }
    path = root / "bin" / f"SetEnv.{cpu}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"env": env}, indent=2))

print(f"Created actual WP8.1 Phone SDK overlay at {root}")
