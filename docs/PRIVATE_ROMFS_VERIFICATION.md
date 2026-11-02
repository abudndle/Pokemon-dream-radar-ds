# Original Dream Radar RomFS intake milestone

This milestone recovers a **metadata-only** baseline from an earlier audit of the
user-supplied decrypted game image. The baseline has **208 virtual files in 15
directories**: 177 CARC archives, 10 SHBIN shaders, 20 BCSTM audio streams,
and one BCSAR sound archive. It is a **list of names and byte lengths only**;
the actual Nintendo asset data is not in this repository.

## Private source verification

Keep an authorized decrypted Pokémon Dream Radar NCCH in a private workspace
**outside this public Git working tree**. The verifier reads it without
extracting any copyrighted resource bytes:

```sh
# CI-safe: checks only the baseline manifest, not the original game.
python3 tools/verify_private_romfs.py

# Local/private workstation: validates all 208 source filenames and sizes,
# computes a streaming source SHA-256, and writes a PRIVATE report.
python3 tools/verify_private_romfs.py \
  /private/dream-radar/source.ncch \
  --report /private/dream-radar/romfs-verified.json
```

A comparison reports missing, unexpected and different-size virtual files.
It fails if there is any difference. It refuses to read a game image from,
or write a report into, the public repository; report creation is atomic with
owner-only permissions. Only private input and reports should ever contain
source-image hashes. Neither original content nor source-image paths are
printed by the verifier or submitted to CI.

Run `make test-host` for the synthetic fixture/parity checks. The public CI
**does not contain the source NCCH**, so a passing CI test proves only that
the manifest and comparison utility work. It does not prove the original
ROM was re-verified in this run.

## Private-source verification evidence (2026-11-01)

The previously supplied **24,944,640-byte decrypted NCCH** was recovered
from the owner's file library into a private workspace and independently
inspected without copying its contents into GitHub. The verified RomFS has
**208 files / 15 directories** and matches all 208 paths and exact sizes in
the metadata-only manifest (**0 missing, 0 unexpected, 0 changed sizes**).

Two existing private extraction archives also passed ZIP integrity checks:

- 177 DARC archives, all with valid `darc` signatures; all 177 virtual
  archive names correspond exactly to original RomFS CARC names
- 1,462 UI members: 875 BCLIM textures, 417 BCLAN animations, 135 BCLYT
  layouts and 35 MSBT text resources

This establishes **resource inventory and archive integrity**, not complete
rendering or original game parity. Private NCCH bytes, extracted binaries,
the full source SHA-256 and detailed private report were kept outside GitHub.
CI uses synthetic test inputs and **does not read these private sources**.

## What is still needed before original 3DS parity

- Securely stage and convert the verified private NCCH and 1,462 UI assets
  for the DS renderer; **the manifest cannot reconstruct source bytes**.
- Recover authentic CARC/DARC textures, UI, layouts, BCLAN animation data,
  models where independently confirmed, audio, and related metadata into
  private asset-conversion workspaces.
- Match decoded resources to runtime scenes and DS constraints, and validate
  conversions and rendered screen/animation parity on emulator and hardware.
- Independently verify live DSi camera behavior and genuine retail transfer
  interoperability. A private research export is not Unova Link.

The previously audited ExeFS banner CGFX models are **Home Menu banner
graphics**, not confirmed playable Pokémon encounter models. Do not promote
those to gameplay source assets without verifying their provenance.

See `docs/ORIGINAL_NCCH_EXEFS_DISCOVERY.md`,
`docs/ORIGINAL_DARC_MODEL_SEARCH.md` and `PORT_COMPLETION_STATUS.md`
for existing investigation and remaining feature gaps.
