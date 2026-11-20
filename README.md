# Chromium for Windows Phone 8.1

Community port of the open-source Chromium browser to Windows Phone 8.1 on ARM32. This project is **experimental**. There is currently no installable browser package and no confirmed on-device navigation.

The working source baseline is Chromium `159.0.8154.13`. The build experiments target `winuwp`, `arm`, and the Windows Phone 8.1 API family. Existing Windows desktop code, V8 snapshot generation, and the Windows Phone application model still require substantial porting. The first [experimental source patch](patches/0001-experimental-arm32-build.patch) applies to a clean source tree, but does not produce a browser yet. Build instructions and third-party notices will be completed before any release.

## Project scope

- Build Blink and V8 for the phone's ARM32 processor.
- Package the browser as a Windows Phone 8.1 application.
- Install and verify navigation on a physical device without a full firmware flash.

This is an independent Chromium port, **not Google Chrome**. Google Chrome branding, icons, and names are not part of this project.

## License

Chromium's source is distributed under its BSD-style license, included in [LICENSE](LICENSE). Third-party components have their own licenses and notices, which must be retained when source or binaries are distributed. No Microsoft SDK files, device firmware, or proprietary Google Chrome assets will be included.

## Status

Work in progress. Do not download or share this project as a functional browser release yet.
