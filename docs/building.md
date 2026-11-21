# Reproducing the ARM32 compile probes

The baseline is Chromium `159.0.8154.13`. These steps compile selected ARM32
objects; they do **not** produce an installable Windows Phone application.

## Inputs

- A clean Chromium source tree at that version, with its normal `DEPS` tools.
- Licensed Windows Phone 8.1 SDK `Include` directory and ARM import libraries,
  including `WindowsPhoneCore.lib`. In Microsoft's Visual Studio media, these
  come from `WindowsPhoneSdk-x86.msi` and `WindowsPhoneSdk-ARM.msi` respectively.
- Windows 8.1 Store SDK resource headers (`winresrc.h` and the `.rh` files).
- A modern Windows cross-build sysroot with `crt` and `sdk` subdirectories,
  used only as an **interim** compiler scaffold. This is not the Phone CRT.
- Chromium's matching Clang 24 toolchain, GN, and Ninja.

The Microsoft SDK and CRT files are supplied by the builder and stay outside
this repository. The overlay script changes a local copy of the old WRL
headers to compile with current Clang; it does not edit the installed SDK.

Apply `patches/0001-experimental-arm32-build.patch` with `git apply`. Then make
an overlay, substituting your own absolute paths:

```sh
python3 tools/create-phone81-sysroot.py \
  --phone-headers "$PHONE81_INCLUDE" \
  --phone-arm-libs "$PHONE81_ARM_LIB" \
  --store-resource-headers "$STORE81_RESOURCE_INCLUDE" \
  --modern-sysroot "$MODERN_SYSROOT" \
  --clang-root "$CHROMIUM_CLANG_ROOT" \
  --out "$PHONE81_OVERLAY"
```

Generate a `winuwp` ARM graph using `target_winuwp_version="8.1"` and
`target_winuwp_family="phone"`, and set `phone81_port=true` and
`skia_use_dawn=false` for the Phone probe. Also set `angle_enable_d3d11=false`, `enable_swiftshader=false`, `enable_swiftshader_vulkan=false`, `dawn_use_swiftshader=false` `enable_libaom=false` (AV1 decoding stays on dav1d), `v8_enable_etw_stack_walking=false`, `v8_enable_system_instrumentation=false`, `rtc_enable_win_wgc=false`, `angle_shared_libvulkan=false`, `phone81_desktop_sdk_include="<Windows SDK>/Include/<version>"` and `wp81_linux_v8_tools="//out/wp81-snapshot-linuxhost/clang_x86_v8_arm"` (the Linux IA32 V8 generators): the Phone 8.1 SDK has no `d3d11_3.h`, and the Phone graph keeps only ANGLE's Null backend and no SwiftShader (the shell runs with `--disable-gpu`, `--disable-software-rasterizer` and a CPU compositor). Disable precompiled headers and Control Flow
Guard for this target. Set `CHROMIUM_PHONE81_SDK=1`,
`CHROMIUM_XWIN_SYSROOT=1`, `WINDOWSSDKDIR` and `GYP_MSVS_OVERRIDE_PATH` to the
overlay path, and `DEPOT_TOOLS_WIN_TOOLCHAIN=1` for **both** `gn gen` and Ninja:

```sh
CHROMIUM_PHONE81_SDK=1 CHROMIUM_XWIN_SYSROOT=1 \
WINDOWSSDKDIR="$PHONE81_OVERLAY" \
GYP_MSVS_OVERRIDE_PATH="$PHONE81_OVERLAY" \
DEPOT_TOOLS_WIN_TOOLCHAIN=1 gn gen out/phone81-arm

CHROMIUM_PHONE81_SDK=1 CHROMIUM_XWIN_SYSROOT=1 \
WINDOWSSDKDIR="$PHONE81_OVERLAY" \
GYP_MSVS_OVERRIDE_PATH="$PHONE81_OVERLAY" \
DEPOT_TOOLS_WIN_TOOLCHAIN=1 ninja -C out/phone81-arm -j8 \
  obj/base/base/message_pump_win.obj \
  obj/base/base/object_watcher.obj \
  obj/base/base/waitable_event_win.obj
```

### Linking

Phone executables and DLLs link the Visual C++ 2013 Store CRT rather than the
newer CRT whose headers the code is compiled with. Install Visual Studio 2013's
Windows Phone ARM libraries locally (never redistribute them) and point GN at
their `VC/lib/store/arm` directory, through a path without spaces:

```gn
phone81_vc120_store_lib_dir = "/abs/path/vc120/store-arm"
# Optional: empty archives named after desktop import libraries that some
# targets still list (advapi32.lib...), so their symbols show up as
# unresolved instead of the link stopping on a missing file.
phone81_desktop_stub_lib_dir = "/abs/path/desktop-stub-libs/arm"
```

`//build/win/phone81:crt_compat` supplies the newer-CRT entry points on top of
VC120. Check every linked image with `llvm-readobj --file-headers
--coff-imports`: it must show subsystem 6.3, the AppContainer flag, and only
`msvcr120_app.dll` plus DLLs that the phone provides.

`out/phone81-arm/args.gn` must be set before `gn gen`; see
[`progress.md`](progress.md) for the exact local experiment and remaining
blockers. A full build still lacks a linked browser executable, a validated
`CoreWindow` rendering path, an APPX package, and device validation.

## Checking Phone SDK imports

The compile probe checks declarations in the Phone SDK headers. The separate
import audit checks selected symbols in the **Phone 8.1 ARM libraries** before
linking. It never copies SDK files into the repository:

```sh
python3 tools/check-phone81-imports.py \
  --lib-dir "$PHONE81_ARM_LIB" \
  --llvm-nm /path/to/llvm-nm
```

The local SDK passed the default eight-symbol audit, including `CreateFile2`,
`GetOverlappedResultEx`, `RoGetActivationFactory`, `D3D11CreateDevice`,
`CreateDXGIFactory2`, and `DWriteCreateFactory`. An import symbol alone does not
prove the API behaves as the browser expects on a physical phone.

## V8 host generator bridge on macOS

V8 requires IA32 host generators for this ARM32 target. Build these four
executables in a separate Linux x86 Chromium output directory using the same
patched source and matching V8 flags: `mksnapshot`, `torque`,
`bytecode_builtins_list_generator`, and `gen-regexp-special-case`. The local
output directory is `out/wp81-snapshot-linuxhost/clang_x86_v8_arm`. It must
also contain the generated `wp81-v8-config.json`. The Linux environment needs
the Chromium revision's matching Clang and Rust toolchains; those toolchains
and generated executables are not distributed here.

Build the runtime image from this repository's Dockerfile:

```sh
docker build --platform linux/amd64 -t wp81-v8-host:bookworm \
  tools/v8-linuxhost
```

In a separate macOS GN output directory, set these arguments in addition to
the Phone ARM32 settings above:

```gn
v8_snapshot_toolchain = "//build/toolchain/mac:clang_arm64"
wp81_linux_v8_tools = "//out/wp81-snapshot-linuxhost/clang_x86_v8_arm"
```

The exact local verification command, run from Chromium's source root, was:

```sh
CHROMIUM_XWIN_SYSROOT=1 \
WINDOWSSDKDIR="$PWD/../../wp81-port/windows-kit" \
WDK_DIR="$PWD/../../wp81-port/windows-kit" \
GYP_MSVS_OVERRIDE_PATH="$PWD/../../wp81-port" \
ninja -C out/probe-phone81-host-bridge \
  gen/v8/embedded.S snapshot_blob.bin \
  gen/v8/torque-generated/builtin-definitions.h \
  gen/v8/src/regexp/special-case.cc
```

Adjust the SDK paths for your machine. The bridge compares the Linux host and
Phone target V8 settings before generating a launcher. The launcher accepts
only IA32 ELF binaries, mounts the Chromium source read-only and the output
directory read-write, and runs with Docker networking disabled. The generated
snapshot is still untested on a phone.

## Graphics headers for compile-only GPU code

Chromium's Windows GPU code is compiled for Phone even though the shell runs
with `--disable-gpu`. It needs DXGI 1.4-1.6, D3D11.3/11.4, D3D12 and
DirectComposition declarations that the Phone 8.1 SDK lacks or keeps in the
desktop partition. `tools/add-phone81-graphics-headers.sh <Windows SDK
Include/<version>> <overlay>/sdk/include/um` replaces the overlay's
DXGI/D3D11/D3DCommon/rpcndr headers with the coherent Windows SDK set (Phone
originals kept as `*.phone-orig`) and adds partition-lifting wrappers for
`dcomp.h`, `dwmapi.h` and `shellscalingapi.h`. Only declarations change; the
link still uses the Phone import libraries. Run it after
`create-phone81-sysroot.py`. Microsoft headers are never committed.

Targets that call desktop Win32 through code the Phone shell never runs add
`//build/config/win:phone81_desktop_declarations`; the final PE import audit
decides which of those imports may stay delay-loaded and which must be
replaced.
