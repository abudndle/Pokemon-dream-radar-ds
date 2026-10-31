# Pokémon Dream Radar DS/DSi — port completion status

This is an **unfinished homebrew port**, not a fully verified replacement for the Nintendo 3DS game.

## Working automated checks
- One `dream_radar.nds` compiled with BlocksDS DSi-enhanced specs and runtime `isDSiMode()` branching.
- Host-side gameplay and platform tests.
- Nintendo DS ROM container/header checks.
- Bundled NitroFS assets have expected file sizes.

**These checks do not demonstrate successful boot, camera operation, accurate visuals, or complete gameplay on an emulator or real console.**

## Original assets currently represented in repository
- Original UI images converted to sprites (including English title logo, visor, orb, Professor Burnet, some equipment icons).
- Original source screenshots under `reference/`, some used to create DS-resolution preview/background images.
- A DS camera-free fallback image for cloud search.
- Title pane geometry extracted from `MnIf_S_TitleList.bclyt`, with **provisional** vertical positioning.

## Still missing or unverified
- All original 3DS `.bclyt` screen hierarchies, transforms, material bindings and layered UI behavior faithfully retargeted for 256×192 DS screens.
- `.bclan` transition, selection, HUD and dialogue animations decoded and reproduced.
- Complete original fonts, glyph metrics, text layout, color/material effects and localization.
- Original artwork for every screen and all required animated states, rather than generated placeholder gradients/panels.
- Original gameplay encounter and drop tables, timing, balancing and complete progression behavior.
- All original transfer semantics and interoperability with retail Pokémon Black 2 / White 2 (currently **not implemented**; a text research archive is not a retail transfer).
- Hardware/emulator boot and interactive verification across DS, DS Lite, DSi, plus DSi camera capture and photo album.
- Pixel/animation comparisons against original reference frames.

## Platform contract
- **One ROM**, automatically chooses DSi-enhanced features when launched in actual DSi mode.
- DS / DS Lite must retain the camera-free virtual cloud hunting and capture views.
- DSi mode enables the live-camera path; if camera isn't enabled/available, fallback remains playable.
- Do not overwrite commercial Pokémon save files without a separately implemented, tested and explicitly authorized export path.

## Milestone acceptance gates
1. Extract/verify each original source screen, its associated textures and animation resources.
2. Map layout states and touch hitboxes to DS coordinates; add assertions and screenshot comparisons.
3. Implement complete gameplay, dialogue, models/graphics representation and progression; test state transitions.
4. Verify unified ROM boots and plays in melonDS DS and DSi profiles and, where possible, original hardware.
5. Validate DSi camera, SD photo album, persistence, and fallback.
6. Test transfer interoperability before representing it as supported.

Do not mark the project or graphics overhaul complete until these gates have evidence.
