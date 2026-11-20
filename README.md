# Chromium for Windows Phone 8.1

Community port of the open-source Chromium browser to Windows Phone 8.1 on ARM32. This project is **experimental**. There is currently no installable browser package and no confirmed on-device navigation.

The working source baseline is Chromium `159.0.8154.13`. The build experiments target `winuwp`, `arm`, and the Windows Phone 8.1 API family. The [experimental source patch](patches/0001-experimental-arm32-build.patch) applies to a clean source tree, but does not produce a browser yet. Build instructions and third-party notices will be completed before any release.

## Project scope

- Build Blink and V8 for the phone's ARM32 processor.
- Package the browser as a Windows Phone 8.1 application.
- Install and verify navigation on a physical device without a full firmware flash.

This is an independent Chromium port, **not Google Chrome**. Google Chrome branding, icons, and names are not part of this project.

## License

Chromium's source is distributed under its BSD-style license, included in [LICENSE](LICENSE). Third-party components have their own licenses and notices, which must be retained when source or binaries are distributed. No Microsoft SDK files, device firmware, or proprietary Google Chrome assets will be included.

## Status

As of 20 November 2026, the ARM32 Windows configuration generates with GN. A Linux x86 host build produced V8's `mksnapshot`; it generated a Windows ARM32 snapshot, and Clang assembled its embedded output as an ARMv7 COFF object. Ninja ran eight jobs in parallel. This validates build steps, not the snapshot's behavior on the phone.

The Chromium `base` library still has fourteen failing Windows Phone source files in the latest build attempt, including file access, message dispatch, process launch, IPC, battery reporting, and profiling. There is no linked browser, phone package, or on-device navigation test. No firmware was flashed or written during this work. The experimental V8 configuration also disables WebAssembly, which limits modern-site compatibility.

See [current build evidence and blockers](docs/progress.md). Do not present this repository as a functional browser release.
