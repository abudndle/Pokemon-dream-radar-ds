# Dream Radar DSi — ROM-localized item catalog & Burnet dialogues

**Development milestone:** expanded the existing BlocksDS source prototype using data from the user's decrypted 3DS NCCH/CIA. This is **not** a complete Nintendo DSi release or verified `.nds`.

## Changes in this build

1. **All 23 original item *names*** from English `Item.msbt` (`ITEM_00`–`ITEM_22`) have been extracted into a generated C table. The six pending item **stack** slots can store any of those 23 types. Capture results, full-storage replacement, and text archives show the original names (such as *Rare Candy* and *Eviolite*) instead of `Research Item 6`.
2. **Full-storage prompts remain optional.** Six Pokémon and six item-stack slots are retained. Nothing is overwritten without a confirmation. Retail Black 2/White 2 `.sav` files are still never modified.
3. **Research Records → Stored Research** now presents two browsing tabs (Pokémon and Items) on the DSi touchscreen. Press **A/X** in Research Records to enter, **L/R/A** to switch tab, and **B** to return.
4. **Professor Burnet talk screen**: the Research Lab menu has a sixth entry, **Talk to Burnet**. This cycles through 30 original short messages from the user's English `Event.msbt` (ASCII/whitespace-normalized for the small DS font). Press **A** or tap for the next message, **B** to return. The Burnet button on the title screen replays the original intro excerpt.
5. **Existing version-3 Dream Radar homebrew saves remain compatible.** Item type values are now validated against 23 types while keeping the private save structure and six-slot capacity unchanged. The original backup recovery logic is unchanged.
6. **Host regressions:** two new test programs verify 23 names, high-ID stack persistence, replacement/cancel, invalid metadata rejection, archive naming, and the new Burnet message table.

## Important limitations

The 23 item **labels** are original; actual random item drops still use **prototype probabilities**, not reverse-engineered original item tables. The 30 added dialogues are not the entire 3DS dialogue/cutscene system. Original sound/3D and Black 2/White 2 Unova Link transfers remain unfinished. DSi lacks the 3DS gyroscope, and camera/optical motion behavior is experimental.

A cross-compiled DSi `.nds` is **not** included. BlocksDS + Wonderful Toolchain are absent in the current environment, so testing is on host GCC plus a main-file syntax smoke test, **not** melonDS or DSi hardware.

## Build and verify

```bash
make item-catalog     # Rebuild 23 English item labels from supplied TSV
make burnet-tips      # Rebuild original Burnet conversation text from supplied TSV
make test-host        # Seven host-side C regression suites
make test-syntax      # Main ARM9 code syntax smoke test with stub host headers
make check-sdk        # Check BlocksDS and Wonderful Toolchain installation
make                  # Build .nds when BlocksDS/ARM toolchain is installed
```

The original decrypted `.cia` and `.ncch` are **not** included in this source ZIP. Preconverted 3DS-derived sprites/bitmaps and the extracted reference English text are included, so building from the provided project does not require the original files again.
