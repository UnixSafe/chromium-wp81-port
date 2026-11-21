#!/usr/bin/env python3
"""Generates the Windows Phone 8.1 replacements for symbols that the final
content_shell link cannot resolve (see build/win/phone81/desktop_stubs.h).

Usage: gen-phone81-desktop-stubs.py <link-log> <out-dir> <src-dir>

Inputs: the lld-link output (with /errorlimit:0) listing undefined symbols
and the objects that reference them. Outputs, in <src>/build/win/phone81/:
  desktop_stubs_list.cc  typed failing replacements for dllimport Win32 APIs
                         (compiled with the Windows 10 SDK declarations)
  desktop_traps.cc       header-free replacements for everything else:
                         - C functions not declared dllimport: return a
                           failure value (untyped; ARM AAPCS returns in r0),
                         - C++ functions of code that cannot run on the phone
                           (disabled features, desktop-only paths): record
                           the name and terminate the process,
                         - data (GUIDs, constants): zero-filled storage.
Refuses to generate anything for symbols that must never be faked
(randomness, TLS, allocator, delay-load helpers).
"""

import collections
import re
import subprocess
import sys
from pathlib import Path

LLVM = "/opt/homebrew/opt/llvm/bin"

# Never fake these: they must have a real implementation.
FORBIDDEN = re.compile(
    r"ProcessPrng|BCryptGenRandom|SystemFunction036|RtlGenRandom|"
    r"CryptGenRandom|_tls_used|__delayLoadHelper2|partition_alloc::"
    r"PartitionRoot|PartitionAllocator::init|p_thread_callback")

E_NOTIMPL = "static_cast<long>(0x80004001L)"
NOT_IMPLEMENTED = "120"  # ERROR_CALL_NOT_IMPLEMENTED
NTSTATUS_NOT_IMPLEMENTED = "static_cast<long>(0xC0000002L)"

# Failure values by API name (typed stubs cast them to the API's own type).
RULES = [
    (r"^Reg[A-Z]", NOT_IMPLEMENTED),           # LSTATUS
    (r"^(SHGetKnownFolderPath|SHCreate|SHGetDesktopFolder|SHGetFolderPath|"
     r"SHGetPropertyStoreForWindow|SHParseDisplayName|SHOpenFolderAndSelect|"
     r"SHGetSpecialFolderLocation|SHCreateItem|SHGetIDListFromObject|"
     r"SHLoadIndirectString|SHStrDup|SHAutoComplete|SHGetFileInfo$)",
     E_NOTIMPL),
    (r"^(Co|Ole|OleCreate|Dwm|Uia|Var|SafeArray(Destroy|PutElement|"
     r"GetElement|AccessData|UnaccessData|GetLBound|GetUBound|Copy)|"
     r"Create(StreamOnHGlobal|StdAccessibleObject|DXGIFactory)|D3D12|D3D11|"
     r"DComposition|LoadRegTypeLib|LoadTypeLib|AccessibleObjectFromWindow|"
     r"AccessibleChildren|WindowFromAccessibleObject|SwDevice|QISearch|"
     r"MF[A-Z]|PropVariant|PSGetPropertyKeyFromName|DwmIsComposition|"
     r"GetThemeMetric|__HrLoadAllImportsForDll|RoGetActivationFactory|"
     r"GetDpiForMonitor|SetProcessDpiAwareness|GetScaleFactorForMonitor|"
     r"CreateBindCtx|CreateURLMoniker|StgCreate|StringFromCLSID|"
     r"CLSIDFromString|IIDFromString|ImpersonateAnonymousToken$)",
     E_NOTIMPL),
    (r"^(CreateFile|CreateNamedPipe|FindFirst|SetupDiGetClassDevs|"
     r"CreateToolhelp32Snapshot|CreateMailslot|RegisterDeviceNotification$)",
     "INVALID_HANDLE_VALUE"),
    (r"^(WaitFor|MsgWaitFor)", "WAIT_FAILED"),
    (r"^GetFileAttributes(W|A)?$", "INVALID_FILE_ATTRIBUTES"),
    (r"^(midi|waveOut|waveIn|mixer|timeBeginPeriod|timeEndPeriod)",
     "8"),  # MMSYSERR_NOTSUPPORTED / TIMERR_NOCANDO is 97; both fail
    (r"^CM_", "0x13"),  # CR_FAILURE
    (r"^(Nt|Rtl)[A-Z]", NTSTATUS_NOT_IMPLEMENTED),
    (r"^HidP_", NTSTATUS_NOT_IMPLEMENTED),
    (r"^(Net[A-Z]|DsGetDcName|NetGetJoinInformation)", NOT_IMPLEMENTED),
    (r"^(WNet|WTSQuery)", "0"),
    (r"^(GetLastInputInfo)$", "0"),
]
DEFAULT_FAILURE = "0"  # FALSE / NULL / 0 for the rest

# dllimport symbols that no SDK header declares (Rust's std links these ntdll
# functions through raw-dylib): replaced without a type, in desktop_traps.cc.
UNDECLARED_IMPORTS = {"NtCreateNamedPipeFile", "NtSetInformationFile"}


def failure_value(name):
  for pattern, value in RULES:
    if re.search(pattern, name):
      return value
  return DEFAULT_FAILURE


GUID_PREFIXES = re.compile(
    r"^(IID_|CLSID_|LIBID_|DIID_|GUID_|MEDIATYPE_|MEDIASUBTYPE_|FORMAT_|"
    r"PIN_CATEGORY_|AMPROPSETID_|LOOK_|TIME_FORMAT_|SENSOR_|PKEY_|"
    r"FOLDERID_|BHID_|CATID_|MF_|MFT_|MFMediaType_|MFVideoFormat_|"
    r"MFAudioFormat_|KSDATAFORMAT_|DEVPKEY_|DEVINTERFACE_)")


def parse_link_log(path):
  text = re.sub(r"\x1b\[[0-9;]*m", "", Path(path).read_text(errors="replace"))
  refs = collections.defaultdict(set)
  current = None
  for line in text.splitlines():
    m = re.match(r".*undefined symbol: (.*)$", line)
    if m:
      current = m.group(1)
      refs[current]  # Record it even if only Rust/rlib members reference it.
      continue
    m = re.match(r">>> referenced by (\S+?\.obj)", line)
    if m and current:
      refs[current].add(m.group(1))
  return refs


def mangled_names(out_dir, objects):
  """Maps demangled -> mangled for every undefined symbol of `objects`."""
  result = {}
  objs = sorted(objects)
  for i in range(0, len(objs), 300):
    out = subprocess.run([f"{LLVM}/llvm-nm", "-u", "--no-sort"] + objs[i:i + 300],
                         cwd=out_dir, capture_output=True, text=True).stdout
    names = sorted({l.split()[-1] for l in out.splitlines()
                    if l.strip().startswith("U ")})
    if not names:
      continue
    dem = subprocess.run([f"{LLVM}/llvm-undname"], input="\n".join(names),
                         capture_output=True, text=True).stdout.splitlines()
    # llvm-undname echoes "<mangled>\n<demangled>\n\n" per input.
    it = iter(dem)
    for line in it:
      if not line.strip():
        continue
      mangled = line.strip()
      demangled = next(it, "").strip()
      if demangled.startswith("error:") or not demangled:
        demangled = mangled
      result[demangled] = mangled
  return result


def c_ident(i):
  return f"phone81_sym_{i}"


def main():
  log, out_dir, src = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
  refs = parse_link_log(log)
  imports, others, undeclared = [], [], []
  for sym in sorted(refs):
    if FORBIDDEN.search(sym):
      sys.exit(f"refusing to fake security- or runtime-critical symbol: {sym}")
    m = re.match(r"__declspec\(dllimport\) (\w+)$", sym)
    if m and m.group(1) in UNDECLARED_IMPORTS:
      undeclared.append(m.group(1))
    elif m:
      imports.append(m.group(1))
    else:
      others.append(sym)

  # Typed failing replacements for dllimport APIs.
  lines = [
      "// Copyright 2026 The Chromium Authors",
      "// Use of this source code is governed by a BSD-style license that can be",
      "// found in the LICENSE file.",
      "",
      "// GENERATED by wp81-port/gen-phone81-desktop-stubs.py from the",
      "// content_shell link: desktop Win32 imports that Windows Phone 8.1 does",
      "// not export, each with the failure value it returns.",
      "",
      '#include "build/win/phone81/desktop_stubs_headers.h"',
      "",
  ]
  for name in imports:
    lines.append(f"PHONE81_DESKTOP_STUB({name}, {failure_value(name)})")
  (src / "build/win/phone81/desktop_stubs_list.cc").write_text(
      "\n".join(lines) + "\n")

  # Everything else.
  cxx = [s for s in others if "::" in s or "(" in s or " " in s]
  plain = [s for s in others if s not in cxx]
  objects = set()
  for s in cxx:
    objects |= refs[s]
  mangled = mangled_names(out_dir, objects)

  out = [
      "// Copyright 2026 The Chromium Authors",
      "// Use of this source code is governed by a BSD-style license that can be",
      "// found in the LICENSE file.",
      "",
      "// GENERATED by wp81-port/gen-phone81-desktop-stubs.py from the",
      "// content_shell link. Symbols of desktop-only or disabled code that the",
      "// Windows Phone 8.1 link cannot resolve. This file includes no Windows",
      "// header, so that it can define symbols the SDK headers declare",
      "// differently.",
      "",
      "#include <stdint.h>",
      "",
      'extern "C" {',
      "__declspec(dllimport) void __stdcall SetLastError(unsigned long);",
      "}",
      "",
      "namespace phone81 {",
      "void ReportDesktopStub(const char* name);",
      "[[noreturn]] void DesktopTrap(const char* name);",
      "}  // namespace phone81",
      "",
  ]
  unresolved = []
  for i, s in enumerate(plain):
    ident = c_ident(i)
    if GUID_PREFIXES.match(s) or s.startswith("k") or s.endswith("_isa"):
      out.append(f'extern "C" __attribute__((aligned(8))) uint8_t {ident}[64] '
                 f'__asm__("{s}") = {{}};')
    else:
      value = failure_value(s)
      if value == "INVALID_HANDLE_VALUE":
        value = "static_cast<long>(-1)"
      elif value in ("WAIT_FAILED", "INVALID_FILE_ATTRIBUTES"):
        value = "static_cast<long>(0xFFFFFFFFL)"
      out.append(f'extern "C" long {ident}() __asm__("{s}");')
      out.append(f'extern "C" long {ident}() {{')
      out.append(f'  static long reported = 0;')
      out.append(f'  if (!__atomic_exchange_n(&reported, 1, __ATOMIC_RELAXED)) {{')
      out.append(f'    phone81::ReportDesktopStub("{s}");')
      out.append(f'  }}')
      out.append(f'  SetLastError(120);')
      out.append(f'  return {value};')
      out.append(f'}}')
  for name in undeclared:
    value = failure_value(name)
    out.append(f'extern "C" long phone81_imp_{name}() {{')
    out.append(f'  static long reported = 0;')
    out.append(f'  if (!__atomic_exchange_n(&reported, 1, __ATOMIC_RELAXED)) {{')
    out.append(f'    phone81::ReportDesktopStub("{name}");')
    out.append(f'  }}')
    out.append(f'  SetLastError(120);')
    out.append(f'  return {value};')
    out.append(f'}}')
    out.append(f'extern "C" __attribute__((used)) void* const __imp_{name} =')
    out.append(f'    reinterpret_cast<void*>(&phone81_imp_{name});')
  base = len(plain)
  for j, s in enumerate(cxx):
    m = mangled.get(s)
    if not m:
      unresolved.append(s)
      continue
    ident = c_ident(base + j)
    escaped = s.replace("\\", "\\\\").replace('"', '\\"')
    if "(" not in s:
      out.append(f'extern "C" __attribute__((aligned(8))) uint8_t {ident}[64] '
                 f'__asm__("{m}") = {{}};')
    else:
      out.append(f'extern "C" void {ident}() __asm__("{m}");')
      out.append(f'extern "C" void {ident}() {{ phone81::DesktopTrap("{escaped}"); }}')
  (src / "build/win/phone81/desktop_traps.cc").write_text("\n".join(out) + "\n")
  print(f"{len(imports)} typed import stubs, {len(plain)} C symbols, "
        f"{len(cxx) - len(unresolved)} C++ traps")
  for s in unresolved:
    print("UNRESOLVED (no mangled name found):", s)


if __name__ == "__main__":
  main()
