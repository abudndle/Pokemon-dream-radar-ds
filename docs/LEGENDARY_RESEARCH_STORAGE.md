# Milestone #23 — original-style separate legendary research storage

The retail Nintendo 3DS game has six ordinary Pokémon research slots and a
separate row for its eight obtainable legendary Pokémon. **At most six Pokémon
are sent in one batch; legendary Pokémon take priority.** The DS/DSi homebrew
now models this queue ordering without suggesting that a text archive is an
actual Pokémon Black 2 / White 2 transfer.

## Implemented DS behavior

- Six ordinary Pokémon remain in `save.pending[0..5]`; eight independent
  legendary species occupy a dedicated eight-cell lower-screen research row.
- Story legendaries Tornadus/Thundurus/Landorus and Gen-IV Dialga/Palkia/
  Giratina/Ho-Oh/Lugia can be captured even with all six ordinary slots full.
  Their story and one-time-capture unlock flags remain separate from stored
  research occupancy; a duplicate capture cannot create a second copy.
- The Transfer preview shows the special row. Left/right moves within the
  selected 6/6/8-cell row; up/down moves between rows. Touch uses shared
  render/input rectangles.
- Exporting a **private text archive** writes a six-Pokémon preview in
  legendary-first order, followed by the existing six item stacks. If more
  than six Pokémon are stored, only the current batch appears in the export.
  The archive explicitly states it is NOT Unova Link compatible.
- Only after exporting and explicitly confirming does the private queue
  remove those six (or fewer) Pokémon. Any ordinary or legendary Pokémon not
  in the batch remain for later archives; one-time story/capture flags are
  retained. Existing item stacks clear as part of the archived batch.

## Save layout and migration

The same checksummed `SAVE_VERSION=3` save structure is retained. Byte
`reserved[14]` holds the eight occupancy bits; `reserved[15]` stores the
`0xE9` format marker. Previously unused bytes remain unchanged. When
loading a valid old v3 homebrew save without the marker, any species 15..22
previously held in the normal six-slot queue are moved into the special
bitset, the ordinary queue is compacted, and a new private save is requested.
A malformed modern save with a legendary in the ordinary queue is rejected
rather than silently normalized.

This migration touches only Dream Radar homebrew data. It does not open or
write any retail Black 2/White 2 save.

## Verification

`make test-host test-syntax` includes
`tests/test_legendary_storage.c` (all eight legendary slots, six-Pokémon
priority batches, overflow retention, private save round-trip, old-v3
migration, duplicate-capture guard), original capture story regressions,
transfer touch geometry tests, and the existing archive safety suite. ARM
build and DeSmuME smoke tests are separate CI jobs. A successful emulator
boot does not prove actual DSi camera support or genuine retail transfers.

## Remaining original-game work

- Original screen animation and material fidelity for the entire transfer
  scene, rather than a partially adapted DS tray.
- Nintendo 3DS Link-compatible authentication, Pokémon personality/ability
  payloads, language, Dream Ball/OT data, badge-dependent levels, receive
  acknowledgement and one-time acceptance semantics. No genuine cross-game
  transfer is presently implemented or represented as complete.
- Continued original 3DS model, skeletal animation, sound, UI and gameplay
  data extraction in private, validated pipelines.
