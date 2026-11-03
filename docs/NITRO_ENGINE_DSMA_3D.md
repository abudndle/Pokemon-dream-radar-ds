# Nitro Engine + DSMA 3D migration (experimental)

This branch **reuses** `source/game.c` and `source/game.h`. Do not reimplement the cloud, sphere, projectile, save or reward rules. The existing `dream_radar.nds` 2D/DSi build remains the reference until the 3D build is demonstrably stable.

## Libraries evaluated

- **Nitro Engine**, [AntonioND/nitro-engine](https://github.com/AntonioND/nitro-engine) (upstream development has moved to Codeberg): optional BlocksDS-installed hardware 3D renderer, camera, materials, model and animation objects. The new `source_3d/main.c` uses `NE_ModelLoadDSMFAT`, `NE_AnimationLoadFAT`, and `NE_ModelDraw`.
- **DSMA**, [AntonioND/dsma-library](https://github.com/AntonioND/dsma-library): skinning implementation used by Nitro Engine's DSM/DSA animated model pipeline. Do not separately link two skinning implementations.
- **[BlocksDS library catalog](https://blocksds.skylyrac.net/docs/libs/)**: `libnds`, NitroFS and existing `libfat` remain the base. External libraries reside under `BLOCKSDSEXT`.
- **[DS-Homebrew/libslim](https://github.com/DS-Homebrew/libslim)**: lightweight `libfat`-compatible `fat:/` (Slot-1) and `sd:/` (TWL) implementation. **Not enabled**: the existing save backend and NitroFS/DLDI paths already use libfat and changing the storage layer before end-to-end persistence checks risks regressions. May be tested as an alternative with the same save backend suite.
- **[BlocksDS uLibrary](https://codeberg.org/blocksds/ulibrary)**: not required for basic 3D meshes. Consider for an independently tested UI layer after the renderer and input are verified. Do not make two libraries control VRAM/display initialization concurrently.

## BlocksDS core libraries and tutorials (upstream SDK reference)

The [official BlocksDS core-library documentation](https://blocksds.skylyrac.net/docs/libs/core_libs/) is the authoritative starting point for APIs and examples used by both frontends. **Do not replace or duplicate the libnds hardware layer** when introducing Nitro Engine or DSMA:

| BlocksDS base component | Dream Radar integration | Implementation priority |
| --- | --- | --- |
| [libnds](https://blocksds.skylyrac.net/docs/libs/core_libs/#libnds) | ARM9 NDS/DSi hardware, touch and button input, timers, IRQs, video/VRAM and 3D display. Nitro Engine links against `-lnds9`; existing camera paths remain in the original launcher. | **Required**, already linked in `Makefile.3d`. Avoid two simultaneous owners of the top-screen video mode. |
| [Maxmod](https://blocksds.skylyrac.net/docs/libs/core_libs/#maxmod) | ARM7 sound and music for recovered original sound assets, subject to lawful extraction and memory profiling. | Deferred until the 3D renderer is stable; it is not a 3D rendering dependency. |
| [DSWiFi](https://blocksds.skylyrac.net/docs/libs/core_libs/#dswifi) | Possible DS/DSi networking transport in separate tested features. | Deferred; does **not** by itself implement original Black 2/White 2 Unova Link protocol. |
| [LibXM7](https://blocksds.skylyrac.net/docs/libs/core_libs/#libxm7) | Alternative ARM7 XM/MOD audio path. | Evaluate against Maxmod only if actual original music assets and constraints warrant it; don't link both by default. |
| [libteak](https://blocksds.skylyrac.net/docs/libs/core_libs/#libteak) | DSi/3DS Teak DSP access for optional platform-specific DSP tasks. | Not appropriate for basic 3D, capture input, or normal DS builds; DSi-specific and unnecessary for now. |
| [Grit](https://blocksds.skylyrac.net/docs/libs/core_libs/#grit) | Convert compatible 2D backgrounds, sprites, tiles and palettes for the bottom-screen HUD and overlays. | Retain existing conversion tooling and add Grit selectively, without inventing replacement 3DS artwork. |

Use the upstream tutorials during incremental migration: [3D graphics](https://blocksds.skylyrac.net/tutorial/intermediate/3d_graphics/), [advanced 3D techniques](https://blocksds.skylyrac.net/tutorial/advanced/advanced_3d/), [NitroFS](https://blocksds.skylyrac.net/tutorial/intermediate/nitrofs/), [FAT filesystems](https://blocksds.skylyrac.net/tutorial/intermediate/fat/), [user input](https://blocksds.skylyrac.net/tutorial/basic/input/), and [DMA](https://blocksds.skylyrac.net/tutorial/intermediate/dma/). These are *reference URLs*, not APIs inferred from their path names: verify tutorial pages before copying specific API calls.

**Makefile contract:** `LIBS := -lNE -lnds9 -lc` in `Makefile.3d` deliberately reuses the already-verified Nitro Engine + libnds linker integration. Additional core libraries will be added only with a demonstrated feature and corresponding ARM9/ARM7 linker dependencies, rather than linking every listed library preemptively. Keep external Nitro Engine under `BLOCKSDSEXT`, alongside its DSMA implementation.

## Asset fidelity and workflow

The converter accepts an **authorized** source mesh exported to MD5 (`.md5mesh`) and original MD5 animation tracks (`.md5anim`) from a **private** workspace. The stock Nitro Engine tool `tools/md5_to_dsma/md5_to_dsma.py` emits `.dsm` and `.dsa`. It does **not** decode arbitrary 3DS BCH/CGFX/model archives or recreate missing 3DS animation data. Extracted assets must be matched to originals and geometry/textures/bones optimized for DS hardware; no invented replicas.

Example on your local/private workspace, after installing Nitro Engine tools:

```sh
mkdir -p private-3d-assets/converted
python3 /path/to/nitro-engine/tools/md5_to_dsma/md5_to_dsma.py \
  --name pokemon_00 --output private-3d-assets/converted \
  --model /private/source/pokemon_00.md5mesh \
  --texture 128 128 --export-base-pose \
  --anims /private/source/walk.md5anim
```

Move the three files `pokemon_00.dsm`, `pokemon_00.dsa` or `pokemon_00_walk.dsa`, and converted `pokemon_00.img.bin` into `nitrofs/models/` **locally only**. Do not commit converted private assets. Converted texture must match `NE_A1RGB5` 128x128 expected by the experimental loader; change both the converter and loader for other dimensions.

## Build

Install Nitro Engine (and its DSMA implementation) against the same BlocksDS version and run:

```sh
make -f Makefile.3d
```

Expected artifact: `dream_radar_3d.nds`. This is **a separate technical 3D renderer bring-up**, not a finished faithful 3DS game or a replacement release. Its top screen uses DS 3D and its bottom uses a debug console, and it currently supports minimal input/capture-scene wiring. The original 2D 2-screen interface, DSi camera, save backend, persistent rewards and original art still need to be threaded through a 3D/2D compositor before the 3D executable can be promoted.

## Display/VRAM caveat

Existing `source/main.c` uses `MODE_5_2D` with a 16-bit bitmap in main background VRAM; Nitro Engine needs the hardware 3D display mode. Calling its `NE_Init3D` on top of the existing bitmap initialization would overwrite video/VRAM state. Keep these as mutually exclusive frontends and later migrate the top-screen layer to Nitro Engine with compatible 2D overlay, retaining the existing bottom UI and camera path.

## Acceptance still open

1. Verify the alternative build compiles against the installed Nitro Engine and ARM toolchain and boots in melonDS.
2. Convert one **real** authorized source Pokémon geometry/rig/animation and measure DS vertex, bone, texture and memory limits.
3. Verify original animations, depth, lighting, camera movement and reticle alignment in real screenshots.
4. Bring over complete bottom-screen UI, save, camera gating and all capture/reward behavior before replacing the software frontend.

Never commit original 3DS ROM archives, converted proprietary artwork, private SD saves, or asset-rich CI artifacts.
