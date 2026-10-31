# Camera-free image and interface fidelity update

The camera-free fallback for the radar gameplay screen now uses the image supplied by the user, stored at `assets/no_camera_cloud_original.png`. The image is resized/cropped to DS native 256×192 and converted into `nitrofs/game_top.raw` (RGB555 A-bit) to match the BlocksDS frame loader. In-game reticle, Dream Clouds, and orb indicators are rendered on top of this background by the existing game code.

The uploaded cloud artwork only appears when camera initialization is unavailable, disabled, or DS/DS Lite camera-free build is used. When a DSi camera frame is successfully available, the live camera preview takes priority. The 3DS gyroscope cannot be recreated on DS/DSi hardware without additional equipment.

The project still uses extracted original title, radar, Burnet, item/shop and visor textures but its interface layout is only partially faithful: game menus, backgrounds, and HUD are not an exact pixel-level reconstruction of the 3DS original. Original UI archives also contain BCLYT layouts and BCLAN animations that are not yet fully ported. Game transfer and full gameplay are not implemented.

The visual mockup is included in the archive under `preview/corrected_original_assets_mockup.png`. It is not an emulator screenshot. The original 3DS and user-supplied textures were used directly; reconstructed DS navigation buttons and hex controls are still illustrative.
