# Build progress and open blockers

This document records local experiments against Chromium `159.0.8154.13` on 20 November 2026. It is not a release or a device test.

## Verified locally

- The patch in this repository passes `git apply --check` against the pristine Chromium source files it changes (69 files).
- GN generates a `winuwp` / ARM32 / Windows Phone 8.1 build graph. It does not prove that the linked binaries would use only APIs present on Windows Phone 8.1. The current cross-build uses Windows 10 SDK headers and libraries.
- V8's `mksnapshot` was built for a Linux x86 host with eight parallel Ninja jobs. Running it with `--target_os=win --target_arch=arm` generated a 2.8 MB snapshot blob and a 13 MB embedded assembly file.
- Clang compiled that embedded assembly into a 5.4 MB ARMv7 Thumb COFF object.
- The ARM32 Chromium `base` build reached remaining errors in twelve source files, listed below.

## Current `base` compile failures

The latest parallel `ninja -j8 base` attempt still fails in:

```text
base/files/file_enumerator_win.cc
base/files/file_path_watcher_win.cc
base/memory/protected_memory_win.cc
base/files/file_util_win.cc
base/files/file_win.cc
base/process/memory_win.cc
base/power_monitor/battery_level_provider_win.cc
base/message_loop/message_pump_win.cc
base/profiler/native_unwinder_win.cc
base/profiler/win32_stack_frame_unwinder.cc
base/process/launch_win.cc
base/process/process_metrics_win.cc
```

The build also still needs a Windows Phone application entry point, touch UI integration, packaging and signing, a compatible installation path, and device verification. The actual phone API surface and V8 snapshot behavior are unverified. No phone storage or firmware was modified.

The V8 experiment disables WebAssembly, TurboFan, and Temporal support to reach the ARM32 host-tool build. These disabled features reduce website compatibility, even if a browser can eventually be installed.
