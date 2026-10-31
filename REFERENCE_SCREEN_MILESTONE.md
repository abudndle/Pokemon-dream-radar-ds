# Screenshot-matched menus and gameplay HUD — October 30, 2026

This BlocksDS source update is based on the three screenshots supplied by the user.
The reference graphics are in `reference/`, and the resulting native-resolution
screens are in `preview/`. Source previews are **not emulator captures** and
should not be used as proof of a working `.nds` binary.

## Main menu

- Top screen: clean dark-blue title panel with **original extracted English
  Dream Radar logo** (`titlelogo00.bclim`, converted into `logo.spr`).
- Bottom screen: four original 3DS entry labels in the right sequence:
  **Start**, **Send Research Data**, **Credits**, **Records**.
- A live Dream Cloud meter replaces the old fake main menu buttons.
- Start leads to Professor Burnet's intro (if new save) and then the existing
  Research Lab hub with gameplay, Development Lab and additional prototype menus.
- Touch and D-pad/A selection share the same four menu hitboxes.

## Development Lab

- Top: three full-width equipment rows using the actual 3DS equipment drawings
  `ShopImage00/01/02.bclim` as a background. The original upgrade icons are
  overlaid alongside live level bars and **Level MAX** state. Selection changes
  the top dialogue box. The support-item icons `IconBom00/01/02.bclim` and
  owned quantities are also displayed in the top screen.
- Bottom: a selectable list of three permanent upgrades followed by three
  purchases; buying reflects real save state on both screens.
- Original upgrade rules for Beam / Energy Pack / Visoscope:

| Level | Upgrade cost | Energy seconds | Visoscope max clouds |
| --- | ---: | ---: | ---: |
| 1 | Included | 120 | 10 |
| 2 | 100 | 150 | 15 |
| 3 | 500 | 180 | 20 |
| 4 | 1000 | 210 | 25 |
| 5 (MAX) | 1500 | 240 | 30 |

The very first search may start with only five Dream Clouds (a special case).
The prototype had previously used the first-search value as its full Level 1
capacity; that has been corrected. Each equipment upgrade is paid separately.

Six Pokémon and six **types** of research items may wait in storage. They are
separate from the three consumable Support Items. The current homebrew save
format still limits Support Item purchases to **nine each** and research stack
quantity to 255; those caps are **prototype limits, not verified as the exact
original 3DS limits**. Storage replacement remains optional and safe.

## Gameplay and no-camera fallback

- Bottom screen uses the **original gameplay touchscreen screenshot supplied by
  the user** cropped to its 4:3 touch area. The blue / green / orange hexagons
  are now active touch targets in a capture encounter, with counts drawn from
  the real saved Support Item quantities. Cloud count and Dream Orb count
  overwrite the static screenshot numbers. `B` exits search.
- While the original photo layout has no analogue sticks, the D-pad and A
  remain playable. The upper touchscreen strip also allows stylus aiming and
  firing. Experimental DSi camera support remains separate.
- Top camera-free view uses the user's cloud graphic; no camera is required on
  DS/DS Lite, and the DSi falls back when a camera is disabled or fails.
- The real 3DS game supports gyro-based looking around; a stock DS/DSi does not
  have a gyro. The optical tracking workaround is not equivalent or verified.

## Exact original assets used

- `LocalizeTex/Tex_Title_En.carc / titlelogo00.bclim`
- `Ui/MnIf_U_Shop.carc / ShopImage00..02.bclim`
- `Ui/MnIf_S_ShopList.carc / IconBom00..02.bclim`
- Game HUD: the user's uploaded original Dream Radar gameplay screenshot
- Camera-free background: the user's previously uploaded cloud image.

The layout is now **much closer** to the supplied screenshots, but it has not
been reconstructed directly from all original `.bclyt` layout metadata or
`.bclan` animation tracks. Some UI elements are recreated or screenshot-based.
This is not a pixel-perfect 3DS port.

## Verification

Run `make test-host test-syntax` (ten independent host test suites plus asset
sanity and C syntax validation for both DS and DSi). Neither BlocksDS ARM
cross-compilation nor melonDS/physical console boot was available in this
session. Black 2/White 2 Unova Link transfers remain unimplemented.
