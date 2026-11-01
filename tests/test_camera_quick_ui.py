#!/usr/bin/env python3
"""Verify hidden camera chord and previous-menu return without artwork changes."""
from pathlib import Path
import re

root=Path(__file__).resolve().parents[1]
main=(root/'source/main.c').read_text()
game=(root/'source/game.h').read_text()
platform=(root/'source/platform_compat.c').read_text()
background=(root/'source/dr_background.c').read_text()
header=(root/'source/platform_compat.h').read_text()

assert 'STATE_CAMERA_QUICK } GameScreen;' in game
assert 'case STATE_CAMERA_QUICK:' in main
assert 'camera_combo_menu_allowed(GameScreen screen)' in main
assert 'dr_camera_quick_open(camera_combo_menu_allowed(game.screen),' in main
assert 'keys,down,KEY_SELECT,KEY_X))' in main
assert 'dr_camera_quick_open(1,keys,down,KEY_SELECT,KEY_X)' in main
assert 'switch_screen(STATE_CAMERA_QUICK);' in main
assert 'camera_quick_return=game.screen;' in main
assert 'camera_quick_return_selection=game.selection;' in main
assert 'switch_screen(camera_quick_return);' in main
assert 'game.selection=camera_quick_return_selection;' in main
assert 'if((down&KEY_B) ||' in main
assert 'case STATE_TITLE:' in main and 'case STATE_LAB:' in main
assert 'case STATE_SETTINGS:' in main and 'case STATE_EXTENSIONS:' in main
# Hidden and unadvertised: no gear, title touch hot corner or single X trigger.
assert 'render_camera_quick_icon' not in main
assert 'camera_quick_icon_visible' not in main
assert 'dr_camera_quick_icon_hit' not in platform
assert 'dr_camera_quick_icon_hit' not in header
assert 'int dr_camera_quick_open(int menu_allowed,int held,int down,' in platform
assert 'return menu_allowed && (held&combo)==combo && (down&combo)!=0;' in platform
assert 'dr_camera_intro_start_shortcut' not in main
assert 'dr_camera_intro_start_shortcut' not in platform

# Gameplay and intro screens excluded. The chord is a menu control only.
routing=main.split('static int camera_combo_menu_allowed(GameScreen screen)',1)[1].split('static int title_live_rects',1)[0]
for screen in ['STATE_RADAR','STATE_SPHERE','STATE_INTRO','STATE_DIALOGUE','STATE_CAMERA_QUICK']:
    assert ('case '+screen+':') not in routing
assert 'if(down&KEY_SELECT)' in main  # Select still resets BMP inside camera menu
assert 'if(game.screen==STATE_CAMERA_QUICK)' in main
assert 'dr_camera_quick_row_hit(touch->px,touch->py)' in main
assert 'dr_camera_retry_latch' in main
assert 'game.save.camera_enabled=!game.save.camera_enabled;' in main

# Original game menus unchanged; camera settings is never an original title button.
assert 'const char *opts[]={"Start","Send Research Data","Credits","Records"};' in main
assert 'case STATE_SETTINGS:' in main
assert 'case STATE_PLACEHOLDER:' in main
assert 'case STATE_ALBUM:' in main
assert 'for(int i=0;i<dr_settings_count(running_dsi);i++)' in main
assert 'int dr_settings_count(int dsi_mode){return dsi_mode?3:2;}' in platform
assert 'if(action==DR_SETTING_CAMERA)' not in main

# Actual camera-free source remains available on DS fallback and DSi.
assert 'if(running_dsi)' in main
assert 'if(load_imported_placeholder())' in main
assert 'dr_background_import(storage_root,custom_background,PIXELS,' in main
assert 'dr_photo_read(path,pixels,count)' in background
assert 'dr_placeholder_path(path,sizeof path,root)' in background
assert 'DR_BACKGROUND_IMPORT_MARKER 0xB7' in (root/'source/dr_background.h').read_text()
assert 'if(game.save.reserved[11]==DR_BACKGROUND_IMPORT_MARKER)' in main
assert 'dr_background_restore(storage_root,custom_background,PIXELS,' in main
assert 'dr_background_reset(&game,&custom_background_loaded,' in main
assert 'CUSTOM_BG_MARKER 0xB6' in main
assert 'if(was_search && !is_search)camera_off();' in main
assert 'if(!was_search && is_search)camera_on();' in main
assert 'if(custom_background_loaded && (!running_dsi || !game.camera_active || !game.camera_ok))' in main
assert 'render_ds_search_sandbox(1);' in main
assert 'render_ds_search_sandbox(0);' in main
assert 'memcpy(top,custom_background,sizeof top);' in main
assert 'if(y>=40 && y<68)return 0;' in platform
assert 'if(y>=86 && y<114)return 1;' in platform
print('PASS: hidden Select+X camera menu from menus, previous-menu return and BMP persistence')
