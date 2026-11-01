# Camera settings icon and placeholder-image import (DS/DSi)

This is an **additional DS-port setting**, deliberately separated from the original Pokémon Dream Radar menus. It does not replace the old Options page, photo album, or any original-game resource. The icon appears at the **bottom-left corner of the lower touch screen** (small gear, x=3–36, y=168–191) on normal gameplay/menu screens.

Tap it to open a focused menu with **only two actions**:

1. **Camera: ON/OFF** — toggles the real DSi camera. On DS/DS Lite and a standard DS emulator, this row displays **CAMERA: NOT AVAILABLE**. Gameplay remains camera-free, and the setting cannot enable an unsupported camera.
2. **Import placeholder BMP** — reads a single user-provided image from removable storage. Import automatically turns off the live camera so the image is visible as the camera-free radar/capture background.

You can also press **Select** on normal gameplay screens, **X on the title/intro screens**, or **Start during Professor Burnet's intro** to open the same camera menu; these shortcuts are useful when an emulator does not forward stylus events. Press **Up/Down** to select a row, **A** to activate, **B** to return to the exact previous game screen and selection, or touch a row directly. **Select** resets the background to the bundled default (without deleting files). In radar/sphere, opening the quick menu temporarily stops the camera and pauses encounter input; returning resumes the previous session.

## Prepare and import an image

Copy a **256 × 192-pixel, uncompressed, 24-bit Windows BMP** to this exact filename on your accessible storage:

```text
sd:/DreamRadarDSi/placeholder.bmp    (DSi with SD)
fat:/DreamRadarDSi/placeholder.bmp   (DS/DS Lite with DLDI flashcart)
```

There is no arbitrary filesystem picker in the game. On emulator, attach writable FAT storage if you want to import a local file; the ROM's bundled files are not writable. The BMP file is *not* committed to GitHub or inserted into the ROM.

To convert your own JPG/PNG on a Linux PC with ImageMagick, run:

```sh
magick input.png -resize '256x192^' -gravity center -extent 256x192 \
  -type TrueColor BMP3:placeholder.bmp
```

Some distributions use `convert` instead of `magick`. Verify `identify placeholder.bmp` shows **256x192 24-bit BMP**. Place the result in `DreamRadarDSi/placeholder.bmp` on the mounted FAT/SD root, then launch the ROM.

Open the bottom-left gear, select **IMPORT PLACEHOLDER BMP**, and press A. A success notification confirms import; the top screen previews the imported image. With the DSi camera off, the same picture is used behind Dream Clouds and Pokémon/item capture encounters. On DS without a camera, this image is your camera-free view.

The image selection persists in the existing homebrew save's previously reserved background-selection marker, without changing the save format. The next launch reloads the fixed BMP from storage when the file remains valid. If the BMP is absent, damaged, the wrong size, or has appended data, the old image is not overwritten; the game retains its bundled background fallback.

**Limits:** The icon is a new DS-specific addition, not an original 3DS UI element. The image is a still camera replacement, **not** a simulated live camera, a filesystem browser, automatic AR tracking, or a reconstruction of the original 3DS motion sensor. The emulator smoke test can verify its appearance after boot, but actual use of the imported image requires the correct mounted writable storage.

## Verification

The Linux host suite includes `tests/test_camera_quick.c` for hitboxes, safe paths, BMP decoding, and invalid-file protection, plus `tests/test_camera_quick_ui.py` to verify camera toggle, session restoration, and menu integration. The Nintendo DS ARM build validates the executable. A real emulator screenshot and gameplay test remain separate acceptance steps.
