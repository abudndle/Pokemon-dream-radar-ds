# Original asset pipeline and provenance

## Goal

Use the authentic Pokémon Dream Radar resources as the source of truth for visuals, audio, layout, animation, data, and behavior. DS-resolution adaptations and optimized formats are acceptable implementation transformations; generic placeholders are not completion evidence.

## Public repository policy

The public repository may contain:
- Original-source-independent conversion and validation tools.
- Asset mapping tables and provenance notes that do not reproduce copyrighted content.
- SHA-256 manifests only when their filenames and hashes do not expose restricted data or user secrets.
- Homebrew-authored code, test fixtures, and clearly identified generated placeholders.
- User-created reference screenshots where the user has the right to publish them.

Never upload retail ROMs, decrypted NCCH/CCI/CIA files, proprietary DARC/CARC archives, extracted textures/models/audio, or copyrighted assets to public GitHub or public CI artifacts. Keep such inputs in a private workspace.

## Reproducible private workflow

1. Place legally obtained, authorized source files in the ignored private asset workspace documented by the local extraction scripts.
2. Run the repository's asset inventory, extraction, conversion, and verification tools locally.
3. Compare converted assets against source dimensions, palette, alpha, animation frame order, and resource identifiers.
4. Record mapping and validation outcomes without publishing protected asset bytes.
5. Build the DS/DSi ROM locally and test with melonDS and real hardware where applicable.
6. Keep private source archives and derived proprietary files out of Git commits, PR patches, release bundles, and public Actions artifacts.

## Fidelity tracking

For each original screen or resource family, track source identifier, extraction status, conversion status, DS adaptation, runtime integration, and screenshot/animation comparison. Mark an item complete only after its in-game use has been verified. A file being present in NitroFS or a converter passing unit tests does not establish original-game parity.

## Known limitation

The repository's `PORT_COMPLETION_STATUS.md` remains the authoritative list of outstanding original-game parity and hardware validation gaps. This guide documents safe handling; it does not assert that missing original resources have been recovered or integrated.
