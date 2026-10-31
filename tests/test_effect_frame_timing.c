#include "game.h"
#include <assert.h>
#include <stdio.h>

static void setup(Game *g) {
    game_new(g, 1234);
    g->screen = STATE_SPHERE;
    g->sphere_x = 100;
    g->sphere_y = 100;
    g->sphere_vx = 1;
    g->sphere_vy = 1;
    g->capture_timeout = 10000;
}

int main(void) {
    Game g;
    setup(&g);
    g.save.goods[0] = 1;
    assert(game_use_support(&g, 0));
    assert(g.freeze_frames == 300);
    for (int i=0; i<300; ++i) {
        game_tick(&g);
        assert(g.sphere_x == 100 && g.sphere_y == 100);
    }
    assert(g.freeze_frames == 0);
    game_tick(&g);
    assert(g.sphere_x == 101 && g.sphere_y == 101);
    setup(&g);
    g.save.goods[1] = 1;
    assert(game_use_support(&g, 1));
    int moves = 0, previous_x = g.sphere_x;
    for (int i=0; i<300; ++i) {
        game_tick(&g);
        if (g.sphere_x != previous_x) ++moves;
        previous_x = g.sphere_x;
    }
    /* 300 slowed frames move exactly once per three frames. */
    assert(moves == 100);
    assert(g.slow_frames == 0);
    puts("PASS: freeze lasts 300 full frames; slow lasts 300 full frames");
    return 0;
}
