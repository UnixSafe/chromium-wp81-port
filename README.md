# Chromium for Windows Phone 8.1

Community port of the open-source Chromium browser to Windows Phone 8.1 on ARM32. This project is **experimental**. There is currently no installable browser package and no confirmed on-device navigation.

The working source baseline is Chromium `159.0.8154.13`. The build experiments target `winuwp`, `arm`, and the Windows Phone 8.1 API family. The [experimental source patch](patches/0001-experimental-arm32-build.patch) applies to a clean source tree, but does not produce a browser yet. [Build notes](docs/building.md) describe the current compile probes. Third-party notices will be completed before any binary release.

## Project scope

- Build Blink and V8 for the phone's ARM32 processor.
- Package the browser as a Windows Phone 8.1 application.
- Install and verify navigation on a physical device without a full firmware flash.

This is an independent Chromium port, **not Google Chrome**. Google Chrome branding, icons, and names are not part of this project.

## License

Chromium's source is distributed under its BSD-style license, included in [LICENSE](LICENSE). Third-party components have their own licenses and notices, which must be retained when source or binaries are distributed. No Microsoft SDK files, device firmware, or proprietary Google Chrome assets will be included.

## Status

As of 20 November 2026, GN generates 36,378 ARM32 targets against the actual Windows Phone 8.1 SDK. Ninja has built the `base.lib` static archive, including ARMv7 Thumb COFF objects for the Phone clock and threading implementation. The WinRT `content_shell` entry point and browser runner also compile as ARM32 objects. Linux IA32 V8 generators run from the macOS GN graph through a Docker launcher: they generated a Windows ARM32 V8 snapshot and embedded assembly. Clang separately assembled the embedded output as an ARMv7 COFF object.

The browser entry point uses `IFrameworkView` and `--single-process`. This is a work in progress: renderer isolation is absent and the full browser has not linked. A Phone-specific Aura host, `CoreWindow` presenter, and touch adapter are in the patch; the presenter and touch adapter compile as ARM32 objects, but the integrated display and navigation have not compiled or run yet. Windows Phone apps cannot use Chromium's IO completion port backend; this patch uses an event based task pump, while direct IO completion port registrations fail explicitly. The shell's default memory cache and Winsock event transport do not require that registration. Immutable ICU, V8 and `.pak` assets have a bounded copy reader. A process-local Mojo data pipe now compiles and its ring storage passed an isolated host test; it has not been exercised by a page load or on the phone.

There is no linked browser, APPX, or on-device navigation test. Eleven incremental `content_shell` runs with six parallel Ninja jobs have progressed to 4,978 build steps. Phone-targeted WebRTC, ICU, font, Mojo, SQLite, networking, and selected Skia and UI objects have compiled, but these isolated results do not establish a working browser. SQLite has a Phone-specific file-system adapter for app-local storage; its database transactions have not been tested on the device. A WinRT connectivity adapter, a Chromium Root Store path, system DNS fallback, Winsock TCP, and the simple disk cache compile in isolated ARM32 probes. Crashpad and desktop ETW are disabled in the Phone browser graph, and a twelfth broad build is in progress. No phone storage or firmware was written during this work. The experimental V8 configuration disables WebAssembly, which limits modern-site compatibility.

See [current build evidence and blockers](docs/progress.md). Do not present this repository as a functional browser release.
