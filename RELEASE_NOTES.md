# Reference UI milestone

See `REFERENCE_SCREEN_MILESTONE.md` for screenshot mappings, native previews,
upgrade rules, hitboxes, known limitations and verification details.

# Release notes — boot-path / dual-target build milestone

- Filesystem initialization order fixed: FAT/SD mount first, then NitroFS and asset preloading.
- Added BlocksDS Docker and GitHub Actions build automation for separate DS and DSi camera-optional ROMs. Not yet run in a cross-compiler environment.
- Added `scripts/check_nds.py` for basic `.nds` structural validation; it does not test booting.
- Added background/sprite asset validator and associated host check.
- Improved private save recovery after damaged primary, late primary corruption, and legacy-save migration; strict file length validation.
- Nine portable C suites plus two Python checks pass. Both UI entrypoints pass host-only syntax checks.
- Original cartridge save files remain read-only; no completed Unova Link transfer.

**Remaining:** cross-compile both ROMs with a real BlocksDS SDK, run in melonDS DSi-mode and on original consoles, then extend original menus/music/models/encounter mechanics and verify retail compatibility.

# Camera-optional DS/DSi compatibility update

- DS and DS Lite no longer show camera settings or camera photo album.
- Game remains controlled by D-pad/stylus, regardless of camera initialization status.
- DSi failure to start the preview gracefully falls back to conventional aiming.
- Host-tested flashcart `fat:/` save-root detection, with `sd:/` preferred for DSi.
- Separate DS and DSi compiler configurations via `make PLATFORM=ds` / `make PLATFORM=dsi`.
- Tests: all nine host suites pass, both C syntax variants pass.
- Build/hardware compatibility and Unova Link transfer **not verified**.

# New milestone: original item catalog and Burnet dialogue

Seven host tests passed. Main code syntax check passed. No ARM9 `.nds` or hardware test.

- Extracted 23 original item names from provided English ROM MSBT table.
- Expanded item stack kinds from six generic values to the 23 localized names; the number of six slots remains fixed.
- Added a two-tab research inventory in Research Records.
- Added 30 optional original English Burnet talk messages, plus title-screen intro replay.
- Kept TWiLight SD-save pairing read only and the one-active-game rule intact.
- Kept optional replacement, backup recovery, version-3 save compatibility, and one-time legendary restrictions.

## Prior milestones

# Milestone release notes — 2026-10-30

This update extends the previous build/save/archive BlocksDS milestone rather than replacing it.

- **Build:** Uses BlocksDS-maintained `sys/default_makefiles/rom_arm9/Makefile` in DSi ARM9 mode. `make test-host` works without an installed SDK.
- **Backup protection:** Detects recovery from a good `.bak` and preserves it on the next write, even when the primary is corrupt.
- **Save data:** Rejects impossible fields and persists secret extension unlocks while staying on version-3 save layout.
- **TWiLight Menu++:** Read-only sampling additionally notices some same-size replacements after SD save scans. The active game is revalidated before a search; only one source is active.
- **Research archives:** New numbered non-overwriting text archives. Clearing the local demo queue requires successful export followed by SELECT and START and never touches Pokémon retail files.
- **Dialogue:** Restores missing whitespace after some message control boundaries.
- **Optional full-storage replacement:** New six-slot Pokémon/item replacement screen with two-tap / two-A confirmation. B/SELECT cancels. Replacing a stack discards its former contents; the user gets a warning before confirming.
- **Legendary safety:** A full queue no longer blocks starting special searches; a captured legendary is only marked once-ever obtained after an occupied storage slot is explicitly replaced. Canceling keeps it available for a later search.
- **Item stack persistence:** Item type IDs now occupy unused bytes in the existing version-3 private save layout; legacy saves migrate with original item indexes preserved.
- **Archive protection:** Storage changes invalidate the approval to release a previously archived queue; the signature now tracks item type IDs as well as amounts.
- **Testing:** Five host test suites and host-only `main.c` syntax test pass. No ARM compilation or emulator test was performed.

**Critical limitations:** It is not a completed Dream Radar port; it has no tested `.nds` binary, pixel-identical presentation or valid Black 2/White 2 transfer payload. Do not inject its text export into retail saves.

## ROM-derived UI geometry milestone

- Added reproducible CLYT decoder for 22 original `.bclyt` UI files and 764 named panes.
- Added nested scene tree with local positions, rotations, dimensions, alpha and origin flags.
- Added regression test verifying extracted file equivalence and title 400×240 canvas.
- The data is not yet consumed by the DS renderer. Animation and material mapping are not complete.
