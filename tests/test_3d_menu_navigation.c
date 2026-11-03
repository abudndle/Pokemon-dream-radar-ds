#include <assert.h>
#include <stdio.h>
#include "game.h"
#include "../source_3d/menu_input.h"

int main(void) {
    Game g;
    game_new(&g, 123);
    const Dr3dMenuInput confirm = {1, 0, 0, 0};
    const Dr3dMenuInput back = {0, 1, 0, 0};
    const Dr3dMenuInput down = {0, 0, 0, 1};
    const Dr3dMenuInput up = {0, 0, 1, 0};
    assert(g.screen == STATE_TITLE);
    dr3d_menu_step(&g, confirm);
    assert(g.screen == STATE_INTRO);
    dr3d_menu_step(&g, confirm);
    assert(g.screen == STATE_LAB && g.save.intro_seen);
    assert(g.requested_save);
    dr3d_menu_step(&g, confirm);
    assert(g.screen == STATE_EXTENSIONS && g.ext_selection == EXT_BASIC);
    dr3d_menu_step(&g, down);
    assert(g.ext_selection >= 0 && g.ext_selection < EXT_COUNT);
    assert(game_extension_unlocked(&g, g.ext_selection));
    dr3d_menu_step(&g, up);
    assert(g.ext_selection == EXT_BASIC);
    dr3d_menu_step(&g, confirm);
    assert(g.screen == STATE_RADAR);
    assert(g.ext_selection == EXT_BASIC);
    assert(g.active_clouds > 0);
    int previous_clouds = g.active_clouds;
    dr3d_menu_step(&g, confirm);
    assert(g.screen == STATE_RADAR && g.active_clouds == previous_clouds);
    assert(game_leave_search(&g));
    g.screen = STATE_LAB;
    dr3d_menu_step(&g, back);
    assert(g.screen == STATE_TITLE);
    dr3d_menu_step(&g, confirm);
    assert(g.screen == STATE_LAB);
    g.screen = STATE_EXTENSIONS;
    g.ext_selection = -5;
    dr3d_menu_step(&g, down);
    assert(g.ext_selection >= 0 && g.ext_selection < EXT_COUNT);
    assert(game_extension_unlocked(&g, g.ext_selection));
    dr3d_menu_step(&g, back);
    assert(g.screen == STATE_LAB);
    dr3d_menu_step(NULL, confirm);
    puts("PASS: alternate DSMA frontend menu uses game unlocks and original radar state");
    return 0;
}
