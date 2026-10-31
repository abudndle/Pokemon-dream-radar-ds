# DS-Homebrew references for Dream Radar DS/DSi

Upstream references only: no source has been copied or integrated.

## Relevant repositories

- [TWiLight Menu++](https://github.com/DS-Homebrew/TWiLightMenu): DS/DSi homebrew launch, SD/flashcart handling, menu and image viewer (imageview) patterns.
- [nds-bootstrap](https://github.com/DS-Homebrew/nds-bootstrap): loader configuration, SD launch behavior and compatibility testing.
- [GodMode9i](https://github.com/DS-Homebrew/GodMode9i): filesystem navigation and defensive file operations.
- [DS-Homebrew wiki](https://github.com/DS-Homebrew/wiki): DSi/flashcart installation and limitations.

## Integration checklist

1. Verify the built homebrew .nds can be launched from TWiLight Menu++ using the appropriate loader configuration.
2. Compare the current BMP photo album with the TWiLightMenu imageview design without assuming identical file-format or filesystem requirements.
3. Test storage separately on DSi SD, DS flashcart, and emulator. Do not assume that all DS-mode software can access the console SD.
4. Treat DSi camera support as optional; preserve stylus controls on hardware and emulator fallback.
5. Verify launch and gameplay on actual melonDS DSi configuration and real console before claiming runtime compatibility.
6. Keep Black 2/White 2 retail transfer distinct from nds-bootstrap save discovery. The current private text archive is not Unova Link.

## Upstream reuse policy

Check each repository's license, source-file license headers and applicable attribution obligations before reusing actual source code. Record the upstream revision if code is adapted. This document imports no upstream code.

## Status

Reference assessment only; no integration, emulator boot or end-to-end functionality is verified by this change.