# Optional DRT1 texture sidecars (DS model-preview milestone)

The port can draw user-converted **DRM1** Pokémon meshes with small, opaque RGB555 textures. This is an initial CPU-rendered preview, **not** an original 3DS model/texture importer, faithful material renderer, depth buffer, or skeletal animation implementation. No Nintendo 3DS models or textures are distributed in the public repository.

## File placement

For an encounter with species index `00`, place the matching pair alongside each other:

- `sd:/DreamRadarDSi/Models/pokemon_00.drm` and `sd:/DreamRadarDSi/Models/pokemon_00.drt` in DSi mode, or `fat:/DreamRadarDSi/Models/...` on a DS flashcart when supported.
- Optionally `nitro:/pokemon_00.drm` and `nitro:/pokemon_00.drt` in a private NitroFS build.

The 26-index mapping is the same as the existing `pokemon_00.drm` through `pokemon_25.drm` model loader. The mesh is loaded first, then its corresponding sidecar. An invalid/missing texture leaves the solid-filled model preview available; an invalid/missing mesh falls back to original 2D artwork. Item encounters continue to use their existing 2D sprites. Assets from external storage are not committed to GitHub.

## DRT1 binary layout

All multi-byte fields are **little-endian**:

| Offset | Size | Description |
| --- | --- | --- |
| 0 | 4 bytes | ASCII `DRT1` |
| 4 | 1 byte | Width, 1–64 |
| 5 | 1 byte | Height, 1–64 |
| 6 | 2 bytes | Vertex count, must match the DRM1 mesh |
| 8 | 4 × vertex count | Consecutive `u16 u, u16 v` UV pairs, Q12 (0–4096 inclusive) |
| After UVs | 2 × width × height | Row-major opaque RGB555 pixel data (`0x8000` set for every texel) |

The file must match the computed length *exactly*. UV zero is the upper/left edge of the texture, 4096 is the lower/right edge; nearest-neighbor sampling is used. Invalid or truncated files are rejected without overwriting the previously accepted texture.

## Packing user-owned converted data

Prepare an existing DRM1 mesh, a JSON array of `[u,v]` Q12 vertex pairs in exactly the mesh vertex order, and raw **little-endian opaque RGB555** texture bytes. Then run:

```sh
python3 tools/pack_drt1.py \
  --mesh pokemon_00.drm \
  --uv-json pokemon_00_uv.json \
  --pixels-rgb555 pokemon_00_rgb555.raw \
  --width 32 --height 32 \
  --output pokemon_00.drt
```

For example, for a three-vertex triangle UV JSON can be `[[0,0],[4096,0],[0,4096]]`. Do not upload private original game assets to public GitHub.

## Current limitations

- Small opaque textures only (maximum 64×64, no alpha transparency).
- Affine UV mapping, painter-order triangles, no Z-buffer or lighting; triangles can overdraw one another incorrectly.
- No original 3DS material/shader/skeletal animation decode; only exported DRM1 meshes with hand-provided or externally converted UV data.
- CPU rendering may be expensive for dense meshes. Model complexity needs further optimization for DS hardware.
- The original item icons remain sprites, not 3D item meshes.

Validation: `make test-host test-syntax` and the BlocksDS ARM build in CI. An actual emulator/hardware visual check remains necessary.
