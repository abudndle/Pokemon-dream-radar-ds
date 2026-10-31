# Full-storage review and confirmation milestone

Full Pokémon and item storage now share tested replacement decisions between
gameplay and UI input. The first A press or row tap arms the selected slot. A
second confirmation commits once; selecting another slot disarms the previous
choice. B/SELECT retains all stored Pokémon and item stacks, including after
arming. Invalid selections or proposed rewards cannot be confirmed. The existing
low-level `game_replace_pending()` commit API is retained for callers that already
made a decision; interactive input uses the two-step decision API.

The top screen previews both the new reward and the old selected Pokémon or item
stack (including quantity). The six painted rows and their touch targets now use
shared geometry: margins, three-pixel gaps, and footer text are not replacement
rows. Existing D-pad navigation, two-step tap/A confirmation, cancellation, save
format, and one-time capture rules are retained. Original art is unchanged.

Host coverage exercises every screen pixel against row boundaries, selection
changes between confirmations, same-row second taps, preview labels, cancellation,
invalid runtime state, exactly one reward, and capture-timer pausing during a
decision. The play-time counter continues normally. Existing storage, legendary,
save, and archive regression tests remain part of the full host suite.

The transfer-detail text buffer also accommodates the compiler's maximum formatted
length without changing the rendered label, resolving its truncation warning.

Validation passed: `make test-host test-syntax`, original UI source audit, unified
ROM compilation using CI's digest-pinned BlocksDS image, and
`python3 scripts/check_nds.py dream_radar.nds` (1,530,880 bytes). The build retains
existing unused-symbol warnings; the transfer-label truncation warning is gone.

This is a DS usability and safety milestone, not recovered 3DS layout/animation
fidelity. Emulator and hardware interaction remain unverified.
