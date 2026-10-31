#include "game.h"
#include <assert.h>
#include <stdio.h>

int main(void) {
    Game g;
    game_new(&g,123);
    game_begin_search(&g,EXT_BASIC);
    assert(g.screen==STATE_RADAR);
    g.active_clouds=2;
    g.cloud_hit=0;
    g.clouds[0].x=110;g.clouds[0].y=90;g.clouds[0].alive=1;g.clouds[0].kind=0;
    g.clouds[1].x=120;g.clouds[1].y=90;g.clouds[1].alive=1;g.clouds[1].kind=0;
    g.aim_x=120;g.aim_y=90;
    game_fire(&g);
    assert(g.clouds[0].alive==1);
    assert(g.clouds[1].alive==0);
    assert(g.cloud_hit==1 && g.screen==STATE_RADAR);
    g.aim_x=110;
    game_fire(&g);
    assert(g.cloud_hit==2 && g.screen==STATE_RESULTS);
    assert(g.save.searches==1);
    /* No ghost rewards after the completed search. */
    uint32_t orbs=g.save.orbs;
    game_fire(&g);
    assert(g.save.orbs==orbs && g.save.searches==1);
    puts("PASS: nearest overlapping cloud selected; search ends once");
    return 0;
}
