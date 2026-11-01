# Next milestone: original-asset and end-to-end parity gates (2026-11-01)

This milestone records verified blockers without claiming original-game fidelity.

## Current verified baseline
- 177/177 LZH8 CARC containers decode; 1,462 DARC entries inventoried.
- 875 BCLIM images, 417 BCLAN animations, 135 BCLYT layouts, 35 MSBT catalogs.
- BCLIM conversion, partial pane runtime, private sprite overrides and DS mesh/animation loaders exist.
- Prior Linux CI host tests, ARM build and ROM validation passed. Emulator navigation has been tested separately, but complete capture/save/camera paths are not verified.

## Priority acceptance gates
- [ ] Run a full deterministic cloud search -> shoot -> orb collection -> sphere -> results -> resume -> save -> reload path in melonDS, capturing screenshots and logs.
- [ ] Validate original title, main menu, ScanList, encounter and results pane placements using private BCLYT/BCLAN data; include stylus hitboxes and animation frames.
- [ ] Determine location and encoding of actual gameplay Pokémon rigs; ExeFS Home Menu banner CGFX is not sufficient.
- [ ] Convert and test original audio privately; record unsupported formats without silently substituting fabricated original sounds.
- [ ] Validate DS and DSi fallback paths, FAT storage and live camera on supported hardware.
- [ ] Compare encounter rates, colored orb chains, extensions, story and original reward tables with original gameplay evidence.
- [ ] Implement and test actual Black 2/White 2 transfer protocol before labeling archive export as Unova Link.

## Asset safety
Original decrypted NCCH, converted copyrighted sprites, model assets and audio must remain in private local storage. Only source code, tests, metadata, instructions and synthetic fixtures belong in this public repository.

## Definition of done for this milestone
A reproducible emulator test with evidence for a complete capture/resume/save cycle, or a documented failure with a minimized reproducer and automated regression test. No claim of completion until this gate passes.

## Fast completion plan: parallel workstreams and hard gates

Avoid creating a milestone for each small test or comment. Batch related implementation, source tests, ARM build, and emulator evidence into one PR review cycle. Keep the following independent workstreams moving in parallel where tooling allows:

| Workstream | Deliverable | Completion gate |
| --- | --- | --- |
| A. Gameplay loop | Radar cloud search, beam hits, Orb collection, sphere combat, rewards, resume | Host tests pass AND a real melonDS capture sequence is observed |
| B. UI fidelity | Private original BCLIM/BCLYT/BCLAN assets converted, correctly positioned and touch-tested | Side-by-side original/reference geometry and actual DS screens reviewed |
| C. Pokémon and audio | Private model/rig/animation/texture/audio extraction, conversion and memory-budget report | No missing original assets silently replaced; DS render and playback verified |
| D. Persistence and transfer | Save/restart, inventory and progression; separately Black 2/White 2 protocol | Restart verified on emulator; transfer only labeled complete after protocol proof |
| E. Hardware compatibility | DS controls and DSi camera motion aiming, FAT storage | DS emulator and real DSi hardware tests; clearly label hardware-only blockers |

### Execution order and speed rules

1. Run `python3 tools/audit_capture_milestone.py --run-host` and `make test-host test-syntax` before extending gameplay. Fix failures in the same implementation batch.
2. Build with BlocksDS and run `scripts/melonds_smoke.sh` on the actual ROM. Existing navigation screenshots **do not** prove capture. Add a deterministic emulator fixture or reliable input sequence and verify real cloud hits, rewards, save and restart before closing the capture gate. Screenshots are external QA evidence, never in-game capture shortcuts.
3. Convert original user-owned 3DS assets in private storage through existing tools; keep copyrighted binaries out of this public repository. Audit extraction gaps once per batch rather than repeating manual inventories.
4. Do not claim the entire retail game is ported merely because menus render. Mark each feature as original-data verified, gameplay-equivalent, adapted for DS, or unimplemented.
5. Close the milestone only with passing acceptance evidence; otherwise publish the failing command, reproducible input and the smallest actionable blocker.
