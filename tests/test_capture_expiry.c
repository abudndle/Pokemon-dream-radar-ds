#include "game.h"
#include <assert.h>
#include <stdio.h>
int main(void) {
    game_fire(NULL); /* Invalid caller must not crash. */
    Game g;
    game_new(&g,29);
    g.screen=STATE_SPHERE;
    g.capture_timeout=0;
    g.capture_hp=239;
    g.sphere_x=g.aim_x;
    g.sphere_y=g.aim_y;
    uint32_t count=g.save.caught_count;
    game_fire(&g);
    assert(g.screen==STATE_SPHERE && g.capture_hp==239);
    assert(g.save.caught_count==count);
    game_tick(&g);
    assert(g.screen==STATE_RESULTS && g.session_caught==-1);
    game_fire(&g);
    assert(g.save.caught_count==count);
    puts("PASS: expired capture cannot be completed by a late shot");
    return 0;
}
