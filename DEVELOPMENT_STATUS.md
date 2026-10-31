**Latest UI work:** Cloud radar top screen, native three-item search bottom screen, transfer dialog/tray, 26 original Pokemon thumbnails and 23 original item thumbnails. Eleven host suites pass; `.nds` build still unverified. See `SCREENSHOT_SEARCH_TRANSFER_MILESTONE.md`.

## Original layout milestone (Oct 30, 2026)

- Updated title/main menu: original four entries and dynamic cloud meter.
- Original game-screenshot touchscreen with three interactive Support Items.
- Development Lab top: 3 gold equipment assets, 5-level bars, selected
  dialogue panel and live consumable counts.
- Visoscope cloud cap fixed to 10/15/20/25/30, first session 5 still allowed.
- User's cloud art remains the no-camera background, DS/DS Lite compatible.
- All ten host test suites and both main C syntax checks pass. Real `.nds`
  build, boot test, original animation tracks and authentic transfers outstanding.

# October 30, 2026 — build and recovery milestone

## Completed and verified locally

- Fixed the order of SD/DLDI filesystem initialization and NitroFS asset loading.
- Improved backup recovery and migration behavior without writing to retail `.sav` files.
- Added ARM/NitroFS ROM header test fixture and a NitroFS asset size verifier.
- Added a dual-target build script for Nintendo DS (camera-free) and Nintendo DSi (camera optional).
- Added an *unexecuted* GitHub Actions workflow using the official BlocksDS Docker image.
- Nine C host test programs pass; two Python checks pass; normal and `DR_DS_ONLY` C syntactic smoke checks pass.

## Blockers not resolved by these changes

- BlocksDS/Wonderful cross toolchain is not present in this runtime, so `check-sdk` fails as expected, no `.nds` was produced and ROM boot is unverified.
- Real DSi camera capture, Slot-1 cartridge hardware and flashcart behavior are not tested.
- Complete original game mechanics/graphics/audio/dialogue and Black 2/White 2 Unova Link transfer are not implemented.
- No representation of 1:1 feature parity or an identical Nintendo 3DS conversion is appropriate yet.

### Camera-free DS / DS Lite compatibility (new)

- Runtime capability policy hides camera-only menus when DSi mode is unavailable.
- Camera initialization or transfer start failure falls back to stylus and D-pad without blocking search gameplay.
- `PLATFORM=ds` uses DS RAM layout and excludes camera code; `PLATFORM=dsi` retains optional DSi camera code.
- Save-root detection supports DSi `sd:/` and DS flashcart DLDI `fat:/`; no retail save writes.
- Host regression tests check DS/DSi menu mapping, camera policy, save mount choice and filesystem write probing.
- **No verified `.nds` boot or camera-hardware test yet.**

# Dream Radar DSi — current development status

Milestone: **23 original item labels, research inventory view, 30 original Burnet messages** (2026-10-30)

## Completed and tested in this environment

- All 23 original English item names extracted from user-provided `Item.msbt` and used for six item-stack types, full-storage replacement, results, and research exports. The drop tables are still approximations.
- Research Records now opens an explicit six-slot Pokémon / six-stack item inventory browser.
- A sixth lab option shows 30 original Professor Burnet dialogue messages, with an intro-replay action on the title screen.
- Added C regression suites for 23-type storage and dialogue text; the private save layout stays at version 3.

- Seven independent portable C test suites pass under GCC `-Wall -Wextra -Werror`.
- Main ARM9 UI C file passes a host-only syntax test against placeholder declarations.
- Uses the current official BlocksDS `rom_arm9` make rules and `dsi_arm9.specs` setting (not a verified ARM build).
- Recognizes one game at a time, from physical Slot-1 header or selected TWiLight Menu++ `.sav` or numbered `.sav1`–`.sav9` and matching ROM. Never writes a retail save.
- Detects changes to supported game ROM headers and sampled same-size save changes between scanning, selecting, and starting a search; also rechecks physical cartridge identity before starting research.
- Recovered backup save is preserved on next write when the primary save was corrupt.
- Invalid but checksum-valid story/upgrades/queue payloads fail validation.
- Secret extension unlocks are persisted into a reserved byte of the same version-3 private save format.
- Full Pokémon storage opens a cancelable six-slot replacement UI rather than blocking legendary searches. B/SELECT cancels without overwriting; replacement of a Pokémon or item stack requires two confirmations. One-time legendary / story flags change only after an accepted replacement.
- Item storage offers an optional replacement UI only when no matching stack has spare capacity and there is no empty item slot; item type mapping survives save/load with backward-compatible version-3 private save migration. Item-stack replacement discards the entire old stack.
- An archive-release signature is invalidated by any real storage mutation, including item type changes.
- More types of research remain available with a full Pokémon queue.
- UI can create numbered text-only archives without overwriting previous exports. A second explicit confirmation is required to clear the **local prototype queue**, never a B2/W2 save.
- English Burnet dialogue and converted original menu elements remain packaged.

## Not finished; no claim of feature parity

- No actual `.nds` is provided: BlocksDS + Wonderful Toolchain are not installed here; no console/emulator binary build or DSi boot proof.
- No verified real-camera operation, optical-flow accuracy, or tested physical Slot-1 cartridge reading.
- No Pokémon Black 2/White 2 Unova Link transfer; text export/queue clear is **not** a substitute.
- No complete original 3D model rendering, sound/music, full dialogue, item/encounter tables, cutscenes, and other original-game mechanics.
- Identical gyroscope control is impossible with the DSi's built-in hardware; the DSi lacks a gyroscope.
- TWiLight save pairing checks a ROM header, file size and sampled fingerprint; it does **not** validate the internal Pokémon game save structure.

## Testing and building

```sh
make test-host
make test-syntax
make check-sdk
make
```

`make check-sdk` currently fails as expected with `BlocksDS SDK not installed` in this container. On a computer configured with BlocksDS and Wonderful Toolchain, `make` is intended to produce `dream_radar_dsi.nds`, which must then be verified in DSi mode and on hardware. Copy retail `.sav` backups before any experimentation.
