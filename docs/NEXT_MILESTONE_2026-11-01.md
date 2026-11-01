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
