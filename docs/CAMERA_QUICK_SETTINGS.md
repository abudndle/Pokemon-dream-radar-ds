# Hidden camera settings for Pokémon Dream Radar DS/DSi

The original 3DS title's four lower-screen choices remain Start, Send Research Data, Credits and Records. The DS-port-only camera/background utility is intentionally hidden: **no gear icon, title menu entry, or single-X shortcut** is displayed.

## Open and return

Hold **Select + X** together on a non-gameplay menu. Either button may be pressed first; the second must be newly pressed while the first is held. This works on Title, Research Lab, Development Shop, Extensions, Records, Storage, transfer queue, Options, Tips, and Album. It is disabled during active cloud search, Pokémon/item encounters, introduction/story dialogue and other gameplay.

Inside Camera Settings, press **B** or **Select + X** again to go back to the **same previous menu and its previous selected row**. The exit combination runs before the standalone Select reset action, so it cannot accidentally clear an imported background.

Use Up/Down, A or the touchscreen inside Camera Settings to choose:

1. **Camera ON/OFF:** DSi real camera toggle; on DS/DS Lite and standard DS-mode emulators the row reports CAMERA: NOT AVAILABLE.
2. **Import placeholder BMP:** reads one specific user-owned still image, disables the live camera and uses the image in radar/search encounters.

Press **Select alone** while inside Camera Settings to restore the bundled camera-free background without deleting your BMP.

## User-supplied background

Use a **256 × 192 uncompressed 24-bit Windows BMP** at one of:

```text
sd:/DreamRadarDSi/placeholder.bmp     (DSi with SD)
fat:/DreamRadarDSi/placeholder.bmp    (DS/DS Lite with DLDI flashcart)
```

Convert on Linux with:

```sh
magick input.png -resize '256x192^' -gravity center -extent 256x192 \
  -type TrueColor BMP3:placeholder.bmp
```

The menu never browses arbitrary paths. A missing, corrupt, oversized or truncated image cannot overwrite the previous valid image or preference. The selected user-owned BMP is reloaded from removable storage after reboot when available; it is never added to the public ROM.

## Fidelity and validation limits

This is a hidden DS-port utility, not a 3DS retail title option. The title artwork and original menu geometry are preserved as separate work under Milestone #47. The current title backgrounds are recreated from a user-provided 3DS reference screenshot; they are **not yet exact original Nintendo UI textures**. The extracted original title logo is already packaged. A DSi camera is not equivalent to the Nintendo 3DS physical gyroscope.

Host regressions check the Select+X chord and rejection of single-key/touch entry, menu restrictions, previous-menu selection return, safe BMP paths, atomic imports and save persistence. Emulator input delivery is tracked separately and is never claimed when screenshots show no actual navigation. Real DSi camera and SD import still require hardware testing.
