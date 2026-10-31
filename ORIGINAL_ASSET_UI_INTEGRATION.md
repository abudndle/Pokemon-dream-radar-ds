# Original-asset UI integration — October 30, 2026

This build keeps the original Dream Radar graphics converted from the owner's ROM rather than producing new replacement illustrations. Current original-derived NitroFS backgrounds include `title_original_top.raw`, `title_menu_bottom.raw`, `development_top.raw`, `radar_overview.raw`, `game_bottom.raw`, `transfer_top.raw`, and `transfer_bottom.raw`; matching original-derived sprites are under `nitrofs/*.spr`.

## Screen controls / data bindings
- Title bottom: the four menu buttons use `dr_title_panes` (generated ROM-derived pane geometry). Touch and selection outlines share these rectangles.
- Start -> Research Lab: visible buttons respond to stylus selection and D-pad/A. Photo Album remains hidden on camera-free DS configurations.
- Extensions: original-derived backgrounds are preserved. The list now filters out Dialga, Palkia, Giratina, Ho-Oh, and Lugia unless a matching active Slot-1 cartridge or selected, validated ROM has been identified, and story/one-time unlock requirements are satisfied. Only one source is active at a time.
- SD ROM selection: a recognized ROM may be selected read-only even when no `.sav` exists; ROM and optional save are checked again before starting an extension.
- Cloud Search: D-pad moves the aiming reticle, A fires; original bottom assets remain, no synthetic joystick. Support-item touch controls remain available in encounter state.
- Development Lab and transfer: extracted bitmaps/icons retained; touch hitboxes use shared geometry helpers where implemented.

## Known limits
This is not yet a pixel-exact port of the full 3DS BC* layout/animation engine. The DS viewport is smaller, several panels still use adaptation coordinates, and live Black 2/White 2 transfers are not implemented. Host tests and C syntax checks cannot prove emulator or hardware compatibility. The original graphics are redistributed only as part of this owner-supplied ROM-based project.
