## Optional original encounter mesh rendering milestone

During a Pokémon capture encounter, the game now tries to load a converted `nitro:/pokemon_XX.drm` mesh, where `XX` is the zero-padded encounter species index (00–25). It decodes the bounded `DRM1` data and draws a CPU-side cyan wireframe into the top screen. If the mesh is missing or invalid, the **original extracted 2D Pokémon art remains the fallback**; item encounters retain their 2D artwork. A single species mesh is cached instead of rereading the file each frame. The same shared encounter rendering path is used for camera and non-camera modes.

Converted models must be explicitly added to `nitrofs/` by the builder from lawfully held original game exports; none are included here. This is **optional untextured wireframe rendering**, not a finished original-model reconstruction, skeletal animation playback, a hardware 3D path, or a verified ROM build.

## Software mesh wireframe milestone

`dr_mesh_wireframe()` draws decoded `DRM1` triangle edges into a caller-owned, 16-bit RGB555 pixel buffer with viewport checks. Its portable Bresenham routine clips out-of-range pixels, and host regression tests exercise a sample triangle. This is a **CPU-side wireframe renderer** only: encounter integration, hidden-surface handling, textured polygons, original animation playback, and a verified DS ROM build remain unfinished. No original model binaries are included.

## Q12 mesh projection milestone

The portable `dr_mesh_project_vertex()` function now converts decoded signed-Q12 XYZ mesh coordinates into orthographic DS screen coordinates, using caller-supplied screen center and scale. It validates parameters and uses 64-bit multiplication before division. `tests/test_dr_mesh.c` covers known vertex locations and invalid arguments; the existing `make test-host` target includes this suite. This is **CPU-side projection only**: there is not yet a triangle rasterizer or hardware 3D renderer, and no verified original Pokémon model files are currently packaged.

## DRM1 mesh decoder milestone

The project now includes `source/dr_mesh.c` and `source/dr_mesh.h`, a bounded C decoder for the `DRM1` intermediate mesh files written by `tools/convert_extracted_obj.py`. Its format is an 8-byte header (`DRM1`, 16-bit vertex count, 16-bit triangle count), then packed signed Q12 XYZ vertices and unsigned 16-bit triangle indices (six bytes each). The decoder rejects truncated/appended payloads, invalid indices, repeated vertices and zero-area geometry. Run `make test-host` to compile its host regression test.

**Scope:** This is a portable CPU-side intermediate mesh decoder, not the DS GPU renderer. No genuine original Pokémon geometry has yet been bundled or rendered; textures, materials, camera transforms, skeletal animation and verified 3DS asset provenance remain open work.

## Original exported geometry conversion — Q12 mesh milestone

A new bounded converter is available at `tools/convert_extracted_obj.py`. If you export a **genuine original model** to Wavefront OBJ using an appropriate private 3DS extraction tool, run `python3 tools/convert_extracted_obj.py /private/original_export.obj build/model.drm`. It produces a compact `DRM1` file with signed 16-bit Q12 vertices and triangle indices, plus a JSON metadata sidecar. This is a **source-geometry intermediate format**, not yet a DS GPU renderer or proof of authenticity. It supports simple vertex positions and triangulates polygon faces, with a configurable 2048-triangle default budget; it does not yet convert normals, textures, materials, rigging, or animations. The exported original geometry is not bundled in this repository. Run `python3 tests/test_extracted_obj_converter.py` for portable conversion checks.

## Original 3D model source inventory (pre-conversion milestone)

Run `python3 tools/inventory_original_models.py /path/to/your/private/extracted/models build/original_model_inventory.json` to inventory locally owned/extracted model candidates. The command records relative filenames, file sizes, SHA-256 hashes, and extensions without copying any original model bytes into the repository. It distinguishes **candidate files** from **converted or DS-verified models** (both remain zero until an actual conversion/rendering pipeline is implemented). The script accepts candidate extensions `.bcmdl`, `.bcres`, `.bch`, `.cmb`, and `.cgfx` but extension alone is not evidence of a valid model. The original models are not currently bundled in this repository. Run `python3 tests/test_original_model_inventory.py` or `make test-host` to check the inventory logic. To detect changed, newly added, or removed original model source candidates, run `python3 tools/inventory_original_models.py /path/to/your/private/extracted/models build/model_inventory_new.json --compare build/original_model_inventory.json`. The comparison checks file hashes and sizes without exposing source binary contents or claiming models are converted.

## Original asset encounter renderer — current milestone

The in-game capture encounter now selects the **bundled original 3DS-extracted Pokémon thumbnails (26 species)** or **research-item artwork (23 items)** instead of always drawing the generic orb. Its target remains aligned with the game's sphere coordinates in both DSi camera and camera-free rendering. If an image cannot load, the orb remains a fallback. Asset order is taken from the packaged `nitrofs/pokemon_00.spr` … `pokemon_25.spr` and `item_00.spr` … `item_22.spr` names.

**These are original extracted 2D assets, not original 3D model geometry.** The repository does not yet contain a verified converted BCMDL/model and animation pipeline. Original 3D models, their skeletal animations and DS-friendly rendering are still pending. The source change also awaits a successful BlocksDS compile and emulator/hardware verification.

## DSi custom camera-free background (source milestone)

On a DSi running the enhanced build, open **Options → Camera: OFF** to disable the live camera, then choose **Custom Camera-Free Image**. Copy a **256 × 192, uncompressed 24-bit BMP** file to the SD card at `sd:/DreamRadarDSi/Photos/photo_000.bmp` (or use numbered files `photo_001.bmp` through `photo_999.bmp`). The port reuses the existing photo album's strict BMP decoder; arbitrary JPG, PNG, dimensions, and filenames are not supported.

In the image picker, **Left/Right** previews available numbered photos, **A** activates the displayed photo, **X** toggles the DSi camera on/off, **Select** resets to the included background, and **B** returns to settings without applying a new preview. When the camera is ON and producing frames, the live view takes priority over the selected background. The selected numbered slot is stored in the homebrew save and reloaded on restart when the file is still present. The image is only used for the top-screen background when the live DSi camera feed isn't being used; capture overlays and controls remain in-game. Photos don't modify retail saves.

**Status:** This is a source-level feature committed to GitHub, awaiting full BlocksDS build and real-DSi testing.

this is ai project dont look into this page please i was originally trying to keep it private but i cant do that 
anynore so dont mind the notes and messages you read in the code
im just playing with ai for fun
**LATEST — Screenshot cloud radar / camera search / transfer tray milestone:** See `SCREENSHOT_SEARCH_TRANSFER_MILESTONE.md`, `preview/cloud_search_transfer_triptych.png`, and `nitrofs/` for actual source UI and original extracted Pokémon/item sprites. Transfer to retail games is **not** implemented.

**NEW — Reference-screen fidelity update:** The title-screen menu now matches
Start / Send Research Data / Credits / Records; the Development Lab shows
real levels (1–5), upgrade bars and support item amounts on the top screen;
the in-game touch HUD uses the supplied original three-hexagon screenshot;
and the normal cloud cap has been corrected to 10–30. See
`REFERENCE_SCREEN_MILESTONE.md` and `preview/original_reference_layout_triptych.png`.
This is a source prototype, not a finished ROM or verified DSi emulator run.

**Current camera-free artwork update:** The radar screen now shows the user-supplied cloud image when no camera is available. See `CORRECTED_MOCKUP.md` and the new visual previews under `preview/`. This is still an unfinished source prototype.

# Pokémon Dream Radar DS/DSi — BlocksDS (source prototype)

**Milestone: boot-path hardening, dual-target build automation and safe save recovery (October 30, 2026).** This is **not a finished game**. It includes original art and text converted from the supplied 3DS files and many working prototype systems, but it has not yet been compiled into a tested `.nds` file. Black 2/White 2 transfer, accurate 3D animations/audio and full feature parity remain incomplete.

## What's new in this milestone

- **Boot preparation:** call `fatInitDefault()` before `nitroFSInit(NULL)`. DS homebrew launched by SD-based menus may need the launcher filesystem mounted before NitroFS can read assets from the `.nds` file. Explicitly include `<filesystem.h>` for the BlocksDS API.
- **DS and DSi build script:** `sh scripts/build_both.sh` runs host tests and builds `dream_radar_ds.nds` (no camera code) and `dream_radar_dsi.nds` (camera optional). It checks file format and the ARM / NitroFS sections. Requires a real BlocksDS installation.
- **GitHub Actions workflow:** `.github/workflows/blocksds.yml` can run the official `skylyrac/blocksds:slim-latest` container on a GitHub-hosted runner. **The workflow has been created but NOT run in this environment.**
- **Recovery:** a verified `.bak` now requests automatic restoration of the primary save; migration of an older private Dream Radar save requests a write to the current path. If the primary has become corrupt since loading, a subsequent write does not rotate it over the last known-good backup.
- **Validation:** rejects private save files with trailing payload bytes. Host tests also check NDS header plausibility and all 5 background + 11 sprite asset sizes.

## To compile and test both versions

With BlocksDS + Wonderful Toolchain installed:

```sh
make test-host test-syntax     # portable checks, works without SDK
make PLATFORM=ds check-sdk   # show missing SDK components if necessary
sh scripts/build_both.sh     # build both NDS binaries with SDK
```

Alternatively, on a desktop with Docker installed and internet access:

```sh
docker run --rm -v "$PWD:/workspace" -w /workspace \
  skylyrac/blocksds:slim-latest sh scripts/build_both.sh
```

Do not treat the validation script as a substitute for testing in melonDS DSi mode, on a real DSi, and on DS/DS Lite with a compatible flashcart. A valid `.nds` header alone does not prove runtime behavior.

## Camera and data rules

- **DS / DS Lite:** camera-independent gameplay and no camera menus. Filesystem writes require compatible DLDI/flashcart storage; these consoles do not have DSi internal SD access.
- **DSi:** camera is optional. If disabled, absent or initialization fails, aim with stylus and D-pad. Experimental camera tracking cannot reproduce a missing gyroscope.
- **Pokémon game recognition:** only one active game at a time, via inserted Slot-1 header (where hardware access allows) or one TWiLight `.nds` and `.sav[1..9]` pair; retail save files are read-only.
- **Storage full:** replace a chosen Pokémon/item slot with a second confirmation or cancel. Legendary once-only flags set only on accepted capture.
- **Unova Link:** text research exports are not Black 2/White 2 transfers. No retail write or authentic transfer is claimed.

---

# Camera-optional Nintendo DS / DSi milestone

**The camera is optional.** DS/DS Lite users can play the prototype without a camera using the touchscreen stylus and D-pad. DSi users can turn the camera off, or continue playing if camera initialization or preview-start fails. DS/DS Lite menus hide Camera, Optical Aim and Photo Album. A camera failure does not lock the search game loop, capture, upgrades, dialogue, or storage. (This is an implemented **source-level fallback**, still awaiting hardware tests.)

**Two build configurations:**

- `make PLATFORM=ds` — DS/DS Lite binary `dream_radar_ds.nds`, DS ARM9 memory layout, camera hardware code excluded. DS/DS Lite homebrew requires a compatible flashcart/DLDI storage device for saving data; the program looks under `fat:/DreamRadarDSi/`. It can also run as a camera-free option on a DSi.
- `make PLATFORM=dsi` or `make` — DSi binary `dream_radar_dsi.nds`, DSi ARM9 layout with *optional* camera, photo album and `sd:/DreamRadarDSi/` storage. If SD isn't writable and a DLDI drive is, it falls back to `fat:/`.

In both builds, retail Pokémon `.sav` files are **read only**. The game only selects **one** game/SD ROM-save pair as active. On a DS/DS Lite, inserted retail game card detection is not supported by this app while launched from a Slot-1 flashcart; choose a single TWiLight/flashcart ROM-save pair instead. Flashcart save scanning depends on ROM and save paths being visible to the homebrew. If no writable storage exists, gameplay can proceed but progress cannot be saved.

**Tests:** `make test-host test-syntax` (nine host test suites; syntax checks both normal and `DR_DS_ONLY` variants). The ARM cross-toolchain is unavailable in this environment, so no bootable `.nds` has been verified; none of these tests proves real DS/DSi hardware compatibility. Reusing original game graphics is ongoing and Black 2/White 2 transfer is not implemented.

---

# Pokémon Dream Radar DSi — BlocksDS source prototype

**Status:** Work in progress (original 23-item catalog + 30 additional Burnet dialogues milestone). Source and converted original art are included; a bootable `.nds` is **not** included because the BlocksDS ARM toolchain and hardware/emulator verification are unavailable in this environment. This is not a complete or identical port of the Nintendo 3DS game.

This is a Nintendo DSi homebrew prototype developed from the *user-provided decrypted Pokémon Dream Radar NCCH/CIA* and playable game-rule code. It uses selected extracted sprites and English text, drawn at DS screen resolution. The camera code is experimental; the DSi has no internal gyroscope. Stylus/D-pad aiming is the fallback.

## One active Pokémon game — enforced

Only **one** source can be active at any given time:

- **Physical Slot-1 cartridge**: On the DSi, choose **Options → Read Inserted DS Game** (or **Y** in the lab). Reads the game-code header only. There is physically only one Slot-1 slot.
- **One TWiLight Menu++ SD ROM/save pair**: Choose **Options → Select One SD Game**. Select a matching `.nds` and its `.sav` / `.sav1`–`.sav9` entry, then press **A**. The scanner validates that the ROM and selected save have not changed. This replaces any previously selected cartridge or SD save. The browser may list multiple entries but **never activates more than one**.
- **Clear**: On the SD game screen, press **SELECT** to clear the active game. **Y** selects the currently inserted physical cartridge instead.

Choosing a new game **replaces** the previous game identity and legendary availability; it never combines unlocks from multiple games. Any legendary captured is still marked obtained **once per Dream Radar save**, independent of source changes.

### SD save locations

The read-only SD browser scans these folders on the SD root and the homebrew's launcher directory:

- `sd:/roms/nds/` (usual location)
- `sd:/roms/`, `sd:/games/`, `sd:/nds/`, `sd:/`

For a matching game ROM, it looks for `GameName.sav` in:

- `saves/` beside the `.nds` file (TWiLight Menu++ default)
- the same directory as the ROM
- `sd:/_nds/TWiLightMenu/saves/` (central save location)

The browser checks the **ROM's game-code header**, whether the matching `.sav` / numbered save is a plausible size, and three read-only file samples to detect some same-size file replacements. The selected source is checked again before each new search, so changed or removed SD save pairs cannot keep an old active identity. A physical cartridge game-code change is also checked before starting a search. This sample fingerprint is NOT full game-save validation. It **does not verify full Pokémon save integrity**, authenticate ownership, emulate Slot-1, or write to that file. A ROM alone without its matching SD save does not activate. Selecting an SD file is **not** physically inserting a cartridge and cannot provide genuine cartridge hardware behavior.

**Own progress:** when launched with a usable `argv[0]` from the SD card, the homebrew saves to a separate `saves/DreamRadarDSi.dreamradar.sav` file, using a temporary file plus backup rotation. When the primary is corrupt but `.bak` is good, the next save preserves the good backup rather than rotating the corrupt primary over it. When the launcher doesn't supply a path, it falls back to `sd:/DreamRadarDSi/save.dat`. It can read a legacy `save.dat` if the new file isn't present. Homebrew progress saves are a private format, not retail Black 2/White 2 saves.

### DS Pokémon game IDs

| Active game | Special extension after Landorus | One-time encounter |
|---|---|---|
| Diamond | Temporal | Dialga |
| Pearl | Spatial | Palkia |
| Platinum | Renegade | Giratina |
| HeartGold | Rainbow | Ho-Oh |
| SoulSilver | Diving | Lugia |
| Black, White | Recognized | None of these five |
| Black 2, White 2 | Recognized / transfer destination | Unova Link transfer not yet implemented |

The original game transfer uses a specific 3DS-to-Black 2/White 2 exchange. This prototype has **text-only export**, not a working retail cartridge or TWiLight save transfer. No retail files are modified.

## Features represented in the prototype

- Two DS screens, converted original title/menu/reticle/cloud/portrait/equipment graphics
- Intro dialogue excerpted from original English message files; post-capture Professor Burnet conversations for the Tornadus, Thundurus and Landorus milestones, shown once each (original message data adapted for the smaller screens)
- Playable search, Dream Orb collection, beam/capture encounter loop, and result screen
- Upgrade/shop and research records, strict save validation, checksum, backup and migration handling; recovered backups are protected on the next write
- Eureka progression, five special cartridge-related legends with single-capture flags; storage-full handling prevents marking an unstored legendary as captured
- Experimental live outer-DSi-camera feed, optical-flow aiming option, SD `.bmp` photo capture with no silent photo overwrites; completed camera frames are double-buffered
- One-active-game selection and read-only TWiLight SD save browser, including numbered save slots 1–9 and stale-selection checks for both ROM code and sampled same-size save-file changes
- Render backgrounds cached in RAM to avoid repeatedly reading NitroFS on every frame
- Six Pokémon pending slots and six item-stack slots (up to 255 per stack, from 23 original named item types), with **optional, two-step confirmed slot replacement** if no space remains. Choose a slot with the D-pad/touch and press A twice to overwrite, or press B/SELECT to keep stored data. One-time Pokémon captures are counted only after a slot is successfully assigned.
- Item-stack type metadata lives in previously unused private version-3 save bytes; existing version-3 homebrew saves migrate when loaded. The `.sav` file layout/size stays unchanged. Item slots cannot be transferred to retail saves.
- Secret research extension unlock flags persist across homebrew saves (older version-3 saves remain supported)
- Text-only research exports receive unique filenames (`sd:/DreamRadarDSi/research_0001.txt`, etc.), with an **explicit two-step optional demo-queue clear** after successful export; it does not unlock/transfer any Pokémon in a retail save

**Not finished:** full original menus/dialogue and cutscenes, original 3D models/animations, complete encounter/item tables, 3DS-equivalent motion tracking, sound/music playback, validated Black 2/White 2 transfer, on-hardware stability, and `.nds` build verification. This SDK is not installed in the current build environment, so **no bootable `.nds` is claimed here**. The DSi has no integrated gyroscope; optional optical motion is only a coarse experimental fallback. These are real limitations, not hidden features.

## Build on a computer with BlocksDS

Install the BlocksDS SDK and Wonderful Toolchain and set `BLOCKSDS` / `WONDERFUL_TOOLCHAIN` to their installation paths, then run:

```sh
make check-sdk    # confirms the required BlocksDS DSi SDK paths exist
make dialogue     # regenerates stage-specific dialogue from the included TSV
make             # attempts to produce dream_radar_dsi.nds with the SDK
```

To run portable host logic and C syntax tests without BlocksDS:

```sh
make test-host
make test-syntax
```

`test-syntax` uses **minimal host declarations**, NOT real libnds headers. Seven portable host test programs now validate gameplay, TWiLight file recognition, backup recovery, local archives, and cancelable storage replacement. Passing it does not verify a console build. A proper BlocksDS build and DSi hardware test are still required. The supplied Makefile uses the **maintained BlocksDS ARM9 template** and overrides `SPECS` to `dsi_arm9.specs` for DSi homebrew. This template change has not yet been cross-compiled in this environment.

Installing BlocksDS on Windows: https://blocksds.skylyrac.net/docs/setup/windows/
Linux: https://blocksds.skylyrac.net/docs/setup/linux/

The preconverted NitroFS data is already included. `make assets` additionally requires the **decrypted original RomFS** in the parent folder plus Python/Pillow; it is **not** needed for a normal build from this ZIP. Original 3DS NCCH/CIA files are **not bundled**.

For DSi SD storage and camera, the program must be launched in **DSi mode** with SD access. The DS/DS Lite lacks the DSi cameras and SD-card hardware. Preserve a backup of your real retail saves before doing any external experiments.

## Controls

- **A / touchscreen:** select, shoot in search mode
- **D-pad:** move selection / aim
- **When full storage opens the replacement list:** D-pad up/down or touch selects one of six occupied Pokémon or item-stack slots; press A (or tap the selected slot) **twice** to confirm overwrite, **B/SELECT** to cancel and retain everything. Replacing an item stack discards its entire previous stack. Replaced one-time legendaries are not re-obtainable within the same Dream Radar save.
- **B:** return / finish search
- **X:** take camera snapshot while researching; rescan SD games in browser
- **Y:** recognize single physically inserted DS cart from lab/SD browser
- **SELECT** in SD browser: clear active game
- **A** on Research Export screen: export **one new numbered text archive**, not a Black 2/White 2 transfer
- **SELECT**, then **START** on Research Export screen: after a successful archive, explicitly clear only the local prototype pending queue so play can continue; the archived text is not a transferable Pokémon

### Tested here

The included host tests cover game-code identification, story unlocks, one-time legendary flags, full-storage protection, switching among Slot-1 and SD sources, numbered TWiLight save slots, stale save identity checks, safe save paths, private save read/write, and no retail save mutation. The host syntax smoke test also checks `main.c` parses against small placeholder API definitions. None of these tests prove that the handheld build boots or that live camera / Slot-1 access works on DSi hardware.

### Item catalog and Professor Burnet dialogue update

The six item-stack storage slots can now hold any of **23 item types named in the original Dream Radar English `Item.msbt`**. These are original labels with *prototype* drop rules (not a reproduction of the original drop tables). Names appear on capture results, replacement choices, research inventory, and exports. In **Research Records**, press **A** or **X** to view the two storage tabs; **L/R/A** switches between Pokémon and item lists.

The Research Lab contains **Talk to Burnet**, which cycles through **30 original English Burnet messages** decoded from the supplied `Event.msbt` data. Press **A/touch** to advance and **B** to close. You can also replay the intro excerpt with the title-screen Burnet button or **X**. Story milestone dialogue remains available.

To regenerate these textual assets from the packaged English message TSV, run `make item-catalog burnet-tips` (pre-generated headers are included for normal builds). This is a source-only milestone and not a verified `.nds`. See `MILESTONE_2026-10-30_ORIGINAL_ITEMS_DIALOGUE.md`.
