# Shared shop layout milestone

## Shared purchase feedback follow-up

The Development Lab now quotes purchases through the same read-only gameplay
policy used by `game_buy()`. The selected row shows `BUY <price>`, `NEED <missing
orbs>`, `MAX`, `FULL`, or `INVALID`; full support stacks also show `FULL` in their
row. The footer only advertises A to buy when the purchase is affordable and has
capacity. Rendering does not deduct orbs, change inventory, or request a save.

Prices, upgrade levels, support capacity, touch geometry, and immediate A/touch
purchases retain their existing behavior. Regression coverage checks all three
equipment types at levels 1–5, every support quantity from 0–9, exact affordability
boundaries, invalid state, and mutation-free quotes. Original assets are unchanged.

Validation: `make test-host test-syntax`, the original UI source audit, the pinned
BlocksDS unified ROM build, and `scripts/check_nds.py dream_radar.nds` passed.
This follow-up produced a 1,530,880-byte ROM. Emulator/hardware boot and visual
behavior remain unverified; this is not an original-game fidelity claim.

The Development Lab shop selection geometry is now shared by drawing and touch input through `dr_shop_row_top()` and `dr_shop_hit()` in `source/reference_layout.c`. This corrects the previous mismatched 24-pixel painted rows versus 29-pixel touch calculation. Touching the 6th shop row no longer gets misidentified, and touching the footer no longer purchases an item. Host regression tests cover all six rows and out-of-range taps.

**Fidelity boundary:** These are harmonized existing DS adaptation coordinates, **not** a recovered .bclyt transform or validated .bclan animation. All remaining original-game UI and gameplay work is incomplete, as is actual Black 2/White 2 transfer integration. No bootable .nds is confirmed.
