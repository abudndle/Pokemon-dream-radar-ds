# Private original UI verification

The user-supplied decrypted NCCH with SHA-256
`1540315aff12de4d899e2d8608a5b6890634c6d58715c36996288a902ac44366`
was read without changing the uploaded image. Its 177 RomFS CARC archives
decode to 1,462 DARC members: 875 BCLIM images, 135 BCLYT layouts,
417 BCLAN UI animations, and 35 message files. The RomFS also has 20 BCSTM
streams and one BCSAR sound archive. Presence is not audio playback support.

The recovered collection remains **outside the checkout**. No NCCH, executable,
new original layout/animation binary, or full game archive is included in this
change. Existing packaged original art is unchanged.

The layout inventory can now require exact source matches for every public
snapshot entry:

```sh
python3 tools/map_original_ui_layouts.py /private/extracted/resources \
  /private/ui_layout_audit.json \
  --snapshot ui_mapping/original_pane_geometry.json
```

This command succeeded against all 135 private layouts and 417 animation clips.
All 22 existing snapshot layouts have exactly matching decoded pane hierarchies,
transforms and section counts. Missing, ambiguous or altered snapshot sources
fail the check; the report records the snapshot hash. The original private path
is machine-specific and is not a CI dependency.

This does not recover original C/C++ source code, make the remaining UI runtime
faithful, or turn BCLAN pane animation into Pokémon skeletal geometry. See
`FEATURE_PARITY.md` for the remaining implementation gaps.
