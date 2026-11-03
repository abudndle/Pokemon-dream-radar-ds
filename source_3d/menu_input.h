#ifndef DREAM_RADAR_3D_MENU_INPUT_H
#define DREAM_RADAR_3D_MENU_INPUT_H
#include "game.h"

/* Portable input adapter for the experimental hardware-3D frontend.
 * The original simulation owns progression, unlock checks, rewards and radar.
 * Keep button encoding separate from libnds for host testing. */
typedef struct {
    int confirm;
    int back;
    int up;
    int down;
} Dr3dMenuInput;

static inline void dr3d_menu_step(Game *g, Dr3dMenuInput input) {
    if (!g) return;
    switch (g->screen) {
    case STATE_TITLE:
        if (input.confirm)
            g->screen = g->save.intro_seen ? STATE_LAB : STATE_INTRO;
        break;
    case STATE_INTRO:
        if (input.confirm || input.back) {
            g->save.intro_seen = 1;
            g->requested_save = 1;
            g->screen = STATE_LAB;
        }
        break;
    case STATE_LAB:
        if (input.back) g->screen = STATE_TITLE;
        else if (input.confirm) {
            g->ext_selection = EXT_BASIC;
            g->screen = STATE_EXTENSIONS;
        }
        break;
    case STATE_EXTENSIONS: {
        if (input.back) { g->screen = STATE_LAB; break; }
        int direction = input.down ? 1 : input.up ? -1 : 0;
        if (direction) {
            int selected = g->ext_selection;
            if (selected < 0 || selected >= EXT_COUNT) selected = EXT_BASIC;
            for (int i = 0; i < EXT_COUNT; ++i) {
                selected = (selected + direction + EXT_COUNT) % EXT_COUNT;
                if (game_extension_unlocked(g, selected)) {
                    g->ext_selection = selected;
                    break;
                }
            }
        }
        if (input.confirm)
            game_begin_search(g, g->ext_selection);
        break;
    }
    case STATE_RESULTS:
        if (input.back) {
            game_finish_pending_radar(g);
            g->screen = STATE_LAB;
        } else if (input.confirm && !game_resume_radar(g))
            g->screen = STATE_LAB;
        break;
    default:
        break;
    }
}
#endif
