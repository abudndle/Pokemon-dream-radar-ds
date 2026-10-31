# Milestone #13 — DRB1 independent rigid body-part animation

The DS/DSi Pokémon Dream Radar homebrew port can optionally animate distinct groups of **user-converted DRM1 model vertices**, each with its own Q12 pivot, translation, and yaw. This allows independently moving heads, wings, tails or limbs **when the user supplies a correct vertex-to-part mapping**.

**Important:** DRB1 is an intermediate *rigid part* format for converted models, not original 3DS skeletal animation, skinning, bone-weighted deformations, or automatic extraction of original 3DS animation data. This milestone does not introduce proprietary game assets into the public repository.

## Placement and priority

For species index `00` (through `25`), keep files from the same private model source together:

- SD or supported DS flashcart: `sd:/DreamRadarDSi/Models/pokemon_00.drm` (or `fat:/...`) plus optional `pokemon_00.drt`, `pokemon_00.dra`, `pokemon_00.drb`.
- Private NitroFS build: `nitro:/pokemon_00.drm` plus optional `pokemon_00.drt`, `pokemon_00.dra`, `pokemon_00.drb`.

Runtime chooses **valid DRK1 weighted hierarchy first**, then valid DRB1 rigid parts, then valid DRA1 if those are unavailable, then unmodified DRM1 geometry (see [DRK1_SKINNING.md](DRK1_SKINNING.md)). A missing/invalid mesh keeps the original 2D Pokémon art fallback, and items stay 2D sprites. Both the flat-shaded and DRT1 textured renderers accept animated geometry without changing vertex IDs, triangles or UV indices.

Changing the loaded species releases animation and mesh scratch buffers. Each animation loops and interpolates deterministically in integer arithmetic, with no per-frame allocation.

## Binary DRB1 stream

Fields are little-endian. The complete file length must be `10 + 6*groups + vertices + 4*groups*frames` bytes, with **no trailing bytes**.

| Offset | Size | Description |
| --- | --- | --- |
| 0 | 4 | ASCII `DRB1` |
| 4 | 2 | DRM1 vertex count, 3–2048, must match the loaded DRM1 mesh |
| 6 | 1 | Rigid part count, 1–16 |
| 7 | 1 | Keyframe count, 2–8 |
| 8 | 1 | Ticks per keyframe, 1–60 |
| 9 | 1 | Reserved, must equal 0 |
| 10 | `6 * groups` | Pivots: one signed Q12 int16 `x,y,z` triple per group |
| After pivots | `vertices` | One unsigned group index per base vertex (must be smaller than `groups`) |
| After group IDs | `4 * frames * groups` | Frame-major, then group-major: signed int8 `[tx,ty,tz,yaw]` per part |

Translation is additive to the neutral vertices, with each integer step representing **1/256 of a model unit** (Q12 offset = byte × 16). Yaw is an int8 angle with 256 steps per full revolution (e.g. +64 = +90 degrees). Rotation is around each group's Q12 pivot. Frame interpolation takes the shortest circular yaw route between adjacent poses, smoothly closing the loop from the last keyframe to the first.

Q12 output coordinates are clamped to signed 16-bit limits. Every vertex belongs to exactly one rigid part; **there is no multi-weight skinning, hierarchy/parenting, inverse kinematics, or independently animated materials**. Parts can therefore separate at joints; accurate meshes and group assignments are required for good results.

The maximum DRB1 file is **2,666 bytes** (2,048 vertices, 16 parts, 8 poses). Runtime additionally keeps one 2,048-vertex scratch mesh (12 KiB) and the compact group mapping and pivot data. It does not allocate memory each frame.

## Create a sidecar from your own converted models

Prepare a `parts.json` file containing:
- `pivots`: group origin coordinates (signed Q12).
- `owners`: one part index for every vertex of the DRM1 mesh, in original vertex order.
- `frames`: an array of poses; every frame has one `[tx,ty,tz,yaw]` per group.

Example for a *hypothetical* six-vertex mesh split between two parts:

```json
{
  "pivots": [[0,0,0],[4096,0,0]],
  "owners": [0,0,0,1,1,1],
  "frames": [
    [[0,0,0,0],[0,0,0,0]],
    [[0,64,0,0],[32,0,0,64]]
  ]
}
```

Generate the exact binary sidecar:

```sh
python3 tools/pack_drb1.py --mesh pokemon_00.drm \
  --parts-json parts.json --ticks 4 --output pokemon_00.drb
```

Or generate a **placeholder** four-pose wag for part index 1 (all other parts remain neutral). You must still author the pivots and owners in `parts.json`; its frames are ignored in this mode:

```sh
python3 tools/pack_drb1.py --mesh pokemon_00.drm \
  --parts-json parts.json --demo-wag --ticks 8 --output pokemon_00.drb
```

The demo motion is **not sourced from the 3DS game**. Keep your proprietary source materials and extracted Nintendo files outside the public GitHub repo.

## Acceptance tests and remaining work

CI host tests verify exact binary framing, group limits, invalid group rejection, signed translations, pivot-relative rotation, yaw interpolation and wrap, independent movement, looping, saturation, safe file replacement, and compatibility with both existing renderers. Host tests and ARM compilation do not establish actual hardware performance or visual accuracy.

Further work includes authentic joint mapping from user-provided decrypted 3DS data, real bone weights and parenting, additional rotations beyond yaw, actual 3DS skeletal keyframes, performance optimization, emulator boots, device smoke tests, and complete game-feature parity.
