# Original Pokémon Dream Radar → Nintendo DS/DSi feature coverage

**Status: not finished.** The decrypted 3DS NCCH contains **compiled** executable code and asset archives, not the original C/C++ source code. This port is a separately implemented homebrew adaptation; a passing test suite proves only the properties those tests exercise.

The source-of-truth checklist is [`feature_parity.json`](feature_parity.json), checked by `tests/test_feature_parity.py`. **Host-tested** means the present behavior is covered by unit tests, **not** that it exactly matches retail gameplay. The original's camera/gyroscope/stereoscopic output cannot simply be copied unchanged to DS hardware.

| Original feature | Current status | Remaining gap |
|---|---|---|
| Title, intro and research lab navigation | partial | Screens and D-pad/touch routing implemented; not frame-perfect. |
| Professor Burnet story and tutorials | partial | Dialogue and tips exist; exact original scene sequencing not independently verified. |
| Dream Cloud generation and shooting | partial | Clouds and collectible Orbs remain after an intermediate sphere encounter; A resumes the same scan, B abandons remaining targets. Original distribution and pacing are not fully matched. |
| Aim/beam input and capture | partial | Stylus/D-pad/A inputs work; original gyroscopic aiming is absent. |
| Dream Orb currency and purchases | host tested | Overflow-safe counters and shop pricing tested; exact color-dependent logic missing. |
| Pink/green/orange/blue Dream Orb cycle | partial | Four colors cycle per moving orb. Cloud hits spawn shootable 3–5-orb clusters; larger groups can split into short-lived chains (max 20 collected), and missed orbs expire. Original spawn rates/3D movement remain provisional. |
| Color-influenced next-search Pokémon encounter selection | partial | Color is counted on individual orb collection, dominant color persists between scans, and the 15 ordinary species are filtered by documented affinity. Exact weighted encounter rates remain unverified. |
| Timed sphere chase and beam capture | partial | Five species-class difficulty profiles vary target hitbox, motion/turn cadence, and attack behavior; encounter resumes are tested. The true original species parameters and capture animations remain unknown. |
| Original sphere projectile/penalty attacks | partial | Legendary spheres now fire three simultaneous independently targetable energy balls, while ordinary encounters use shorter staggered volleys. Overlapping balls now cause at most one timer penalty per frame, and beam defense selects the nearest ball; exact per-species retail patterns and animation data are still unverified. |
| Beam, Energy and Visoscope upgrades | host tested | Five levels and Dream Orb costs tested; original animation/effects not exact. |
| Vortex, Dragnet and Energy Recharge | host tested | Encounter-local effects and inventory enforcement tested; visuals not authentic. |
| All 17 research/simulator/secret Extension menu entries | partial | Extension enums, gates and prices implemented; original encounter tables pending. |
| Retrieval favors Pokémon; Dowsing favors items | host tested | Opposing bias implemented and tested; numerical odds are provisional. |
| Simulator α/β/γ award their special item pools | host tested | Six-item original pool identities, storage and cancellation tested; odds unverified. |
| Therian Tornadus, Thundurus and Landorus story | partial | Unlock phases and basic legendary capture work; effects/forms not fully reproduced. |
| Diamond/Pearl/Platinum/HeartGold/SoulSilver special bosses | partial | DS cart game-code detection and legendary Extension gating exist; full transfer behavior absent. |
| Beldum, Slowpoke, Hoothoot secret codes | partial | International button sequences accepted; regional variants and repeat-use parity need review. |
| All original obtainable Pokémon and encounter probabilities | partial | 26 named species supported, but spawn tables and form presentation are provisional. |
| All original item names and drops | partial | 23 extracted English names supported, but drop tables are not proven original. |
| Six Pokémon slots and six item stacks with replacement | host tested | Portable storage/replacement tested; original separate legendary priority remains missing. |
| Separate special legendary row and priority on transfer | host tested | Eight special legendary research slots now persist independently of six regular slots. Six-Pokémon text archive batches place legends first and retain overflow for later archives; v3 saves migrate without changing size. Actual Black 2/White 2 Unova Link remains unimplemented. |
| Durable homebrew save/restore and recovery | host tested | Private save version/checksum and recovery tests; never equate with retail save data. |
| Nintendo DS dual-screen and tactile/touch navigation | partial | Main controls and hitboxes exist; exact original touch layout is not proven. |
| DSi outer camera live preview and optional album | partial | DSi camera API and fallback present; real DSi gameplay boot testing still pending. |
| DS-only bottom-left camera settings and placeholder image import | host tested | Gear and X shortcut now open only on the title screen; no camera/placeholder rows in ordinary Options. Atomic fixed-path BMP selection, save restore and camera-free fallback have host tests; end-to-end emulator/DSi FAT import and camera tests pending. This is a user-requested new option, not original 3DS UI. |
| Original 3DS gyroscope aiming | hardware limited | DS/DSi has no built-in 3DS gyroscope; needs explicitly designed alternative. |
| Original stereoscopic 3DS rendering | hardware limited | Nintendo DS/DSi has no autostereoscopic 3D display; 2D adaptation only. |
| Original BCLIM graphics mapped to DS assets | partial | Conversion and SD override exist; wholesale original UI integration is incomplete. |
| Original BCLYT screen positions and pane hierarchy | investigation only | 135 original layouts inventoried; runtime compositor retargeting not integrated. |
| Original BCLAN animation keyframes and playback | investigation only | 417 CLAN files in the validated private 177-DARC set are 2D UI/pane animations, not Pokémon skeletons; clip timing identified, runtime pane-keyframe playback pending. |
| Original Pokémon 3D geometry and animations | partial | Converted DRM1/DRA1/DRB1/DRK1 and strict glTF retargeting exist. Original NCCH ExeFS contains 14 verified CGFX Home Menu banner assets and a separate 16-file logo DARC; these are not confirmed Pokémon encounter rigs. Native gameplay model/skeletal animation decoding remains unverified. |
| Original music, sound effects and timing | unimplemented | No verified original 3DS audio conversion and playback across scenes. |
| Real Black 2/White 2 Nintendo 3DS Link transfers | unimplemented | Only a safe text archive is exported; no retail transfer, save injection or handshake. |
| Unova Link receiving Pokémon/items into Black 2/White 2 | unimplemented | No compatible send/receive implementation or save-verified integration. |
| Original hidden-ability and badge-dependent levels | unimplemented | Without genuine Pokémon transfer payloads these properties are not delivered. |
| Original complete language selection and translated UI | partial | Extracted localized assets exist; complete in-game per-language switching is absent. |
| Boot, input, performance, save tests on DS/DSi and emulator | unverified | melonDS 1.1 DS-mode boot and six navigation headings verified locally. Stylus delivery, cloud shooting/full encounters, save reload, DSi camera/SD and hardware remain unverified. |

## Required acceptance gates before calling the port finished

1. Validate all original modes, encounter pools, orb colors, drop tables, upgrades, support effects, secrets, tutorial progression, and per-session rewards against the original gameplay—not merely that each function exists.
2. Integrate original user-provided UI graphics with accurate BCLYT layout transforms and BCLAN keyframe playback; verify touch targets and dual-screen presentation in a real emulator.
3. Integrate genuine model/animation assets where DS hardware permits, with explicit 2D fallbacks and memory/performance profiling. The DRM1 preview supports converted geometry, DRA1/DRB1/DRK1 motion and strict glTF-to-DRK1 retargeting. The 177 decoded RomFS DARC archives contain 2D/UI assets, while the separate ExeFS banner has 14 verified CGFX Home Menu graphic containers. Neither establishes original Pokémon gameplay rig/animation decode; native game model locations, multi-axis bone motion and material fidelity remain unresolved.
4. Test original music, effects, and localization across all reachable states.
5. Address original motion-controlled AR with an explicit DS/DSi alternative; document incompatible 3DS gyroscope and stereoscopic features rather than pretending they exist.
6. Implement and safely test authentic Black 2/White 2 transfer compatibility **before** representing private text-archive export as genuine Unova Link. Never modify a user's retail save to claim this feature works.
7. Complete emulator boot-through, capture/escape, full storage replacement, save persistence, DSi camera and DS-only fallback tests; then conduct a hardware smoke test.

## Sources used to define original behavior

- [The Pokémon Company's original game description](https://www.pokemon.com/us/pokemon-video-games/pokemon-dream-radar/)
- [Nintendo's official game description](https://www.nintendo.com/en-gb/Games/Nintendo-3DS-download-software/Pokemon-Dream-Radar-523679.html)
- [Bulbapedia gameplay and progression reference](https://bulbapedia.bulbagarden.net/wiki/Dream_Radar)
- [Smogon original Extension/item reward guide](https://www.smogon.com/ingame/guides/dream_radar)

The documented game mechanics are the parity target; DS RAM/display/input constraints may require equivalent behavior rather than literal 3DS binary/source-code reuse. Original proprietary files must stay private and must not be published in the repository.
