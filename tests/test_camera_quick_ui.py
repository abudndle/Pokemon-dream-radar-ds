#!/usr/bin/env python3
"""Camera quick-settings integration regression checks.

Focus on the touch UI, camera lifecycle, and persistent image source:
the extra bottom-left icon must never change the existing menu structure.
"""
from pathlib import Path
import re

root=Path(__file__).resolve().parents[1]
main=(root/'source/main.c').read_text()
game=(root/'source/game.h').read_text()
platform=(root/'source/platform_compat.c').read_text()

assert 'STATE_CAMERA_QUICK } GameScreen;' in game
assert 'case STATE_CAMERA_QUICK:' in main
assert 'render_camera_quick_icon' in main
assert 'if(camera_quick_icon_visible())render_camera_quick_icon();' in main
assert 'dr_camera_quick_icon_hit(touch->px,touch->py)' in main
assert 'dr_camera_quick_row_hit(touch->px,touch->py)' in main
assert 'camera_quick_return=game.screen;' in main
assert 'camera_quick_return_selection=game.selection;' in main
assert 'switch_screen(STATE_CAMERA_QUICK);' in main
assert 'switch_screen(camera_quick_return);' in main
assert 'game.selection=camera_quick_return_selection;' in main
assert 'if(down&KEY_B)' in main
assert 'if(down&KEY_SELECT)' in main
assert 'if(running_dsi)' in main
assert 'dr_camera_retry_latch' in main
assert 'game.save.camera_enabled=!game.save.camera_enabled;' in main
assert 'game.save.camera_enabled=0;' in main
assert 'if(load_imported_placeholder())' in main
assert 'select_imported_placeholder();' in main
assert 'dr_photo_read(filename,custom_background,PIXELS)' in main
assert 'dr_placeholder_path(filename,sizeof filename,storage_root)' in main
assert 'IMPORTED_BG_MARKER 0xB7' in main
assert 'if(game.save.reserved[11]==IMPORTED_BG_MARKER)' in main
assert 'load_imported_placeholder();' in main
assert 'game.requested_save=1;' in main
assert 'CUSTOM_BG_MARKER 0xB6' in main
assert 'STATE_RADAR' in main and 'STATE_SPHERE' in main
assert 'if(was_search && !is_search)camera_off();' in main
assert 'if(!was_search && is_search)camera_on();' in main
assert re.search(r'const int cx=20,cy=180;',main)
assert 'rect(bottom,3,168,34,24,0x8421);' in main
assert 'border(bottom,3,168,34,24,WHITE);' in main
assert 'for(int row=0;row<2;row++)' in main
assert 'IMPORT PLACEHOLDER BMP' in main
assert '256x192 / 24-BIT BMP ONLY' in main
assert '/DreamRadarDSi/placeholder.bmp' in main
assert 'CAMERA: NOT AVAILABLE' in main
assert 'CAMERA BACKGROUND PREVIEW' in main

# Camera-free imported image is active in both radar and sphere renderers.
assert 'if(custom_background_loaded && (!running_dsi || !game.camera_active || !game.camera_ok))' in main
assert 'render_ds_search_sandbox(1);' in main
assert 'render_ds_search_sandbox(0);' in main
assert 'memcpy(top,custom_background,sizeof top);' in main

# The legacy options page, album and model manifest remain intact.
assert 'case STATE_SETTINGS:' in main
assert 'case STATE_PLACEHOLDER:' in main
assert 'case STATE_ALBUM:' in main
assert 'for(int i=0;i<dr_settings_count(running_dsi);i++)' in main

# The filename and hitbox helpers are uniform between DS/DSi builds.
assert 'DreamRadarDSi/placeholder.bmp' in platform
assert 'return x>=3 && x<37 && y>=168 && y<192;' in platform
assert 'if(y>=40 && y<68)return 0;' in platform
assert 'if(y>=86 && y<114)return 1;' in platform
assert 'DR_SETTING_PLACEHOLDER' in (root/'source/platform_compat.h').read_text()
print('PASS: bottom-left camera settings icon, two-action menu, save persistence, DS fallback')
