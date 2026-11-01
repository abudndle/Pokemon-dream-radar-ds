# Title-screen-only camera settings and placeholder-image import (DS/DSi)

This is an **additional DS-port setting**, deliberately separated from the original Pokémon Dream Radar menus. It does not replace the old Options page, photo album, or any original-game resource. The icon appears **only on the title screen**, at the **bottom-left corner of the lower touch screen** (small gear, x=3–36, y=168–191). No gear or camera-settings entry is displayed during gameplay, Professor Burnet's introduction, or in the Options list.

Tap it to open a focused menu with **only two actions**:

1. **Camera: ON/OFF** — toggles the real DSi camera. On DS/DS Lite and a standard DS emulator, this row displays **CAMERA: NOT AVAILABLE**. Gameplay remains camera-free, and the setting cannot enable an unsupported camera.
2. **Import placeholder BMP** — reads a single user-provided image from removable storage. Import automatically turns off the live camera so the image is visible as the camera-free radar/capture background.

On the **title screen only**, tap the gear or press **X** (the emulator keyboard fallback) to open the menu. Press **Up/Down** to select a row, **A** to activate, **B** to return to the title with its previous selection, or touch a row directly. **Select** inside the camera menu resets the background to the bundled default without deleting files. Select/X/Start no longer open this menu from the intro or gameplay. The import/toggle selection still applies when a later research session starts.

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

The Linux host suite includes `tests/test_camera_quick.c` for title-only input gating, hitboxes, safe paths, BMP decoding, and invalid-file protection, plus `tests/test_camera_quick_ui.py` to verify title-only routing and camera/BMP persistence. The Linux emulator smoke workflow attempts title X or a real gear tap, checks title return only if the menu actually opens, and logs input delivery as **unverified** when those events cannot be confirmed; it also checks a title-to-intro Start transition and observes whether intro X leaves the frame unchanged. A real DSi camera and writable FAT BMP import remain separate end-to-end tests.

## Transactional BMP selection (milestone #21)

The import and save selection now share a portable, host-tested transaction in `source/dr_background.c`. A missing, truncated, malformed or oversized BMP leaves the existing display pixels, saved background marker, camera toggle and current gameplay session unchanged. A successful import marks the file in the homebrew save, disables the DSi camera, and uses the same BMP for the camera-free radar and sphere backgrounds. Restoring the marker on reboot reads the file again without dirtying the save. If the file is unavailable on reboot, the bundled background remains the fallback; the saved preference is retained for when storage returns. Reset clears the selection without deleting the user's file.

`tests/test_background_import.c` covers success, rollback, restore, reset and preservation of the active capture timeout. An actual end-to-end DSi/DeSmuME FAT import remains a separate hardware or emulator test; portable host tests do not prove SD mounting.

## Milestone #22 — title-only camera access

The camera settings gear and X shortcut exist exclusively on the title screen. The DS/DSi Options menu no longer offers camera or custom-photo entries; optical aim and DS cartridge/SD game pairing remain. Existing selected images and saves are still restored by the original background loader on launch. Camera toggling and BMP imports are unchanged once the title-only menu is open. Portable tests cover rejection from other states; real emulator smoke validation attempts title entry/return and intro rejection without claiming success for unregistered SDL input.
