#include "game.h"
#include <assert.h>
#include <stdint.h>
#include <limits.h>
#include <stdio.h>

int main(void) {
    Game g;
    game_new(&g,123);
    g.screen=STATE_RADAR;
    g.active_clouds=1;
    g.clouds[0].alive=1;
    g.clouds[0].kind=0;
    g.clouds[0].x=128;
    g.clouds[0].y=96;
    g.aim_x=128;
    g.aim_y=96;
    g.save.orbs=UINT32_MAX-1;
    g.save.total_orbs=UINT32_MAX-2;
    g.session_orbs=INT_MAX-3;
    game_fire(&g);
    assert(g.save.orbs==UINT32_MAX);
    assert(g.save.total_orbs==UINT32_MAX);
    assert(g.session_orbs==INT_MAX);
    assert(g.screen==STATE_RESULTS);
    assert(g.save.searches==1);
    assert(g.requested_save);
    puts("PASS: orb reward counters saturate rather than wrap");
    return 0;
}
