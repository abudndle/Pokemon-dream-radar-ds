# Milestone #12 — Optional DRA1 vertex animation sidecars

DRA1 lets the DS/DSi Dream Radar demake animate **user-converted DRM1 Pokémon models** using a compact sequence of per-vertex keyframe offsets. There is no Nintendo proprietary animation bundled here, and this is **not a decoder for the original 3DS skeletal animation format**.

## Runtime and storage

Store a DRA1 sidecar alongside the matching mesh:

- `sd:/DreamRadarDSi/Models/pokemon_00.drm`, optional `pokemon_00.drt`, and optional `pokemon_00.dra` on a DSi with SD access.
- For a DS flashcart, use the equivalent `fat:/DreamRadarDSi/Models/` path.
- For private NitroFS builds, the optional model and companions are `nitro:/pokemon_00.drm`, `nitro:/pokemon_00.drt`, and `nitro:/pokemon_00.dra`.

Indices run from `00` to `25`. A sidecar is only loaded after a valid mesh from the same storage source. When DRK1, DRB1 and DRA1 are all available, **DRK1 weighted hierarchy takes priority**, then DRB1 rigid parts, then DRA1 vertex offsets (see [DRK1_SKINNING.md](DRK1_SKINNING.md)). A missing or invalid DRA1 file leaves the original model's rigid rotation intact; missing textures keep the flat-color fallback, and missing meshes keep 2D Pokémon artwork. **Items remain 2D sprites.**

Animation time starts when the cached species changes. Each keyframe lasts a configurable number of gameplay ticks. Linear interpolation blends to the next frame and loops continuously, including from last to first. The system never allocates RAM per rendered frame; it writes into one reused scratch mesh and passes that geometry to both textured and flat-shaded renderers.

## Binary DRA1 format

All multibyte fields are little-endian. The file must match its declared size **exactly**.

| Offset | Size | Meaning |
| --- | --- | --- |
| 0 | 4 | ASCII `DRA1` |
| 4 | 2 | DRM1 vertex count, 3–2048 and exactly equal to the loaded mesh |
| 6 | 1 | Number of keyframes, 2–8 |
| 7 | 1 | Gameplay ticks per keyframe, 1–60 |
| 8 | 3 × vertex count × keyframe count | Signed 8-bit XYZ vertex offsets, keyframe-major and then vertex-major |

Deltas are in **1/256 of one DRM1 model unit**, i.e. a signed byte is multiplied by 16 in Q12 coordinates. Each `[dx,dy,dz]` is **additive** to the original neutral mesh vertex, not to the prior animation frame. The resulting Q12 coordinates are clamped to signed 16-bit limits. There is no frame-by-frame accumulation drift.

**Maximum animation payload:** 49,152 bytes, plus an 8-byte header, for an eight-keyframe 2,048-vertex mesh. The decoder also allocates a reusable animated vertex buffer of 12,288 bytes at this limit. Simpler rigs are proportionally smaller. The unchanged triangle list and UV mapping are borrowed from the original mesh.

## Convert user-owned motion

With an existing private DRM1 mesh, to generate a simple four-pose demonstration idle bob:

```sh
python3 tools/pack_dra1.py --mesh pokemon_00.drm \
  --idle-bob --ticks 8 --output pokemon_00.dra
```

This generates offsets of `0, +64, 0, -64` along Y (in signed delta units) and repeats them for every model vertex. It is an original *placeholder idle motion*, **not the original game's animation**.

To supply custom vertex poses, create a UTF-8 JSON array of keyframes. Every keyframe contains one `[dx,dy,dz]` signed-byte triple per vertex, in the same order as the DRM1 vertex stream. For example, for a three-vertex model:

```json
[
  [[0,0,0],[0,0,0],[0,0,0]],
  [[0,64,0],[0,64,0],[0,64,0]]
]
```

Then pack it:

```sh
python3 tools/pack_dra1.py --mesh pokemon_00.drm \
  --keyframes-json my_idle.json --ticks 8 --output pokemon_00.dra
```

Keep copyrighted extracted 3DS assets and derived private animation streams **out of the public GitHub repository**.

## Limits and verification

This is additive vertex-keyframe motion, **not skinning, inverse kinematics, material animation, original 3DS skeletal playback, or true 3DS camera tracking**. Animation keyframes support up to 2,048 vertices and eight poses; meshes without DRA1 remain supported. Rendering still uses a CPU triangle rasterizer and two independent static depth buffers, so emulator and actual DS performance testing is necessary.

Host regression tests cover strict DRA1 decoding and exact file sizes, mismatch/overflow rejection, interpolation, deterministic looping, coordinate clamping, safe replacement, preservation of original vertices, and both existing renderer paths. The CI ARM build verifies successful compilation, not exact visual fidelity.
