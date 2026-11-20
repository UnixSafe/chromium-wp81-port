# Windows Phone 8.1 development package

The template in `packaging/wp81` targets the native Windows Phone 8.1 WinRT application model. Its fixed development identity and product GUID belong to this prototype. Keep both stable for local upgrades and increase the four-part version. The publisher is the required subject of the developer's signing certificate. The unqualified PNGs are scale-100 assets and can be addressed directly from the manifest. The only declared network capability is outbound Internet access.

## Stage a linked build

Start with an empty payload directory outside this repository. Copy the **contents** of `packaging/wp81` there. Place the linked ARM32 `content_shell.exe` at the root. From the Chromium checkout, use the same GN binary and output directory as the link to enumerate the runtime dependencies:

```text
gn desc out/probe-phone81-arm //content/shell:content_shell runtime_deps
```

Review the results against the build configuration. Stage each required DLL, resource pack, ICU data, locale and V8 startup data using the relative path actually requested by the build. Resolve directory entries and generated files. Avoid copying an entire Ninja output directory. Dynamic loads and files opened by name need separate verification. The manifest's logical application entry point is `ChromiumWP81.App`; the current native startup implements `wWinMain` and calls `CoreApplication.Run` with its own view source. Package validation alone cannot verify OS activation.

Inspect headers, imports and delay imports of every staged EXE and DLL with the SDK's `dumpbin /headers /imports`. Require ARMNT, PE32 and an AppContainer Windows GUI executable targeting NT 6.3. Match imported functions against the Phone 8.1 API surface. The build currently mixes modern runtime components and legacy Phone libraries. The template assumes the eventual release build uses the VS2013 Phone CRT. If imports or ABI require a different runtime, resolve that before packing. A manifest dependency cannot supply a modern UCRT on Phone 8.1.

The sample Phone package declares `Microsoft.VCLibs.120.00.Phone` with minimum version `12.0.30113.0`. Inspect the signed ARM **Phone** framework's own AppxManifest.xml and DLL contents, and verify its signature. Supply the framework separately at deployment if the device lacks it. The ARM retail framework from the desktop Windows 8.1 ExtensionSDK has the distinct identity `Microsoft.VCLibs.120.00` and cannot satisfy this dependency.

## Pack and sign on Windows

Use a Phone 8.1 development environment and its 8.1 SDK MakeAppx and SignTool. From its developer command prompt, with the reviewed payload in C:\build\stage, an existing empty output location, and a code-signing certificate with a private key in the current user's Personal store:

```bat
makeappx pack /d C:\build\stage /p C:\build\ChromiumWP81.appx /h SHA256
signtool sign /fd SHA256 /s My /sha1 YOUR_CERTIFICATE_THUMBPRINT C:\build\ChromiumWP81.appx
signtool verify /pa /v C:\build\ChromiumWP81.appx
```

Stop after any failed command. Use the actual certificate thumbprint. Match the certificate subject exactly to the manifest Publisher. Verify on a machine that trusts the signing chain. Never put a PFX, SDK or framework archive in the payload. The app's own package, developer registration on the handset and availability of its signed dependencies are separate prerequisites. For a subsequent test on an already developer-unlocked RM-821 use the Windows Phone 8.1 SDK Application Deployment tool. Current device registration and trust have not been verified. No device operation is part of these packaging steps.

## Verification status and references

The template follows the manifest in the local reference Windows Phone 8.1 ARM Browser package. Its XML parses and its referenced PNGs have the required scale-100 dimensions. No Chromium shell executable has linked for this target. Full 8.1 SDK package validation, signature verification, handset activation, navigation and runtime dependency closure remain pending.

- [Microsoft PhoneIdentity guidance](https://learn.microsoft.com/en-us/uwp/schemas/appxpackage/uapmanifestschema/element-mp-phoneidentity)
- [Microsoft MakeAppx command reference](https://learn.microsoft.com/en-us/windows/uwp/packaging/create-app-package-with-makeappx-tool)
- [Microsoft Windows Phone 8.1 SDK setup](https://learn.microsoft.com/en-us/previous-versions/windows/desktop/msipcthin2/windows-phone-apps)
