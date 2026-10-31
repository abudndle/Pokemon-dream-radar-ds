# Shared shop layout milestone

The Development Lab shop selection geometry is now shared by drawing and touch input through `dr_shop_row_top()` and `dr_shop_hit()` in `source/reference_layout.c`. This corrects the previous mismatched 24-pixel painted rows versus 29-pixel touch calculation. Touching the 6th shop row no longer gets misidentified, and touching the footer no longer purchases an item. Host regression tests cover all six rows and out-of-range taps.

**Fidelity boundary:** These are harmonized existing DS adaptation coordinates, **not** a recovered .bclyt transform or validated .bclan animation. All remaining original-game UI and gameplay work is incomplete, as is actual Black 2/White 2 transfer integration. No bootable .nds is confirmed.
