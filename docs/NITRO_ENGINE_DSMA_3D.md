# Nitro Engine + DSMA 3D migration (experimental)

This branch **reuses** `source/game.c` and `source/game.h`. Do not reimplement the cloud, sphere, projectile, save or reward rules. The existing `dream_radar.nds` 2D/DSi build remains the reference until the 3D build is demonstrably stable.

## Libraries evaluated

- **Nitro Engine**, [AntonioND/nitro-engine](https://github.com/AntonioND/nitro-engine) (upstream development has moved to Codeberg): optional BlocksDS-installed hardware 3D renderer, camera, materials, model and animation objects. The new `source_3d/main.c` uses `NE_ModelLoadDSMFAT`, `NE_AnimationLoadFAT`, and `NE_ModelDraw`.
- **DSMA**, [AntonioND/dsma-library](https://github.com/AntonioND/dsma-library): skinning implementation used by Nitro Engine's DSM/DSA animated model pipeline. Do not separately link two skinning implementations.
- **[BlocksDS library catalog](https://blocksds.skylyrac.net/docs/libs/)**: `libnds`, NitroFS and existing `libfat` remain the base. External libraries reside under `BLOCKSDSEXT`.
- **[DS-Homebrew/libslim](https://github.com/DS-Homebrew/libslim)**: lightweight `libfat`-compatible `fat:/` (Slot-1) and `sd:/` (TWL) implementation. **Not enabled**: the existing save backend and NitroFS/DLDI paths already use libfat and changing the storage layer before end-to-end persistence checks risks regressions. May be tested as an alternative with the same save backend suite.
- **[BlocksDS uLibrary](https://codeberg.org/blocksds/ulibrary)**: not required for basic 3D meshes. Consider for an independently tested UI layer after the renderer and input are verified. Do not make two libraries control VRAM/display initialization concurrently.

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
