#include "game.h"
#include <assert.h>
#include <stdio.h>
#include <stdint.h>

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
    assert(g.cloud_hit==2 && g.screen==STATE_RADAR);
    assert(game_active_dream_orbs(&g)>0);
    /* Uncollected Orbs expire; a scan ends only after its contents expire. */
    for(int tick=0;tick<300 && g.screen==STATE_RADAR;tick++)game_tick(&g);
    assert(g.screen==STATE_RESULTS);
    assert(g.save.searches==1);
    game_new(&g,44);
    game_begin_search(&g,EXT_BASIC);
    g.save.searches=UINT32_MAX;
    g.active_clouds=1;
    g.cloud_hit=0;
    g.clouds[0].alive=1;g.clouds[0].kind=0;
    g.clouds[0].x=128;g.clouds[0].y=90;
    g.aim_x=128;g.aim_y=90;
    game_fire(&g);
    assert(g.save.searches==UINT32_MAX && g.screen==STATE_RADAR);
    for(int tick=0;tick<300 && g.screen==STATE_RADAR;tick++)game_tick(&g);
    assert(g.save.searches==UINT32_MAX && g.screen==STATE_RESULTS);
    /* A corrupt nearly-overflowed hit counter must saturate safely. */
    game_new(&g,321);
    game_begin_search(&g,EXT_BASIC);
    g.active_clouds=1;
    g.cloud_hit=2147483647;
    g.clouds[0].alive=1;g.clouds[0].kind=0;
    g.clouds[0].x=128;g.clouds[0].y=90;
    g.aim_x=128;g.aim_y=90;
    game_fire(&g);
    assert(g.cloud_hit==2147483647 && g.screen==STATE_RADAR);
    for(int tick=0;tick<300 && g.screen==STATE_RADAR;tick++)game_tick(&g);
    assert(g.screen==STATE_RESULTS);
    /* No ghost rewards after the completed search. */
    uint32_t orbs=g.save.orbs;
    game_fire(&g);
    assert(g.save.orbs==orbs && g.save.searches==1);
    /* Initial cloud placement should avoid visually stacked targets in
       ordinary searches while keeping all positions inside the play area. */
    game_new(&g,123);
    g.save.cloud_count=10;
    game_begin_search(&g,EXT_BASIC);
    assert(g.active_clouds==10);
    for(int i=0;i<g.active_clouds;i++) {
        assert(g.clouds[i].x>=24 && g.clouds[i].x<=230);
        assert(g.clouds[i].y>=24 && g.clouds[i].y<=152);
        for(int j=0;j<i;j++) {
            int dx=g.clouds[i].x-g.clouds[j].x;
            int dy=g.clouds[i].y-g.clouds[j].y;
            assert(dx*dx+dy*dy>=20*20);
        }
    }
    for(int i=g.active_clouds;i<MAX_CLOUDS;i++)
        assert(!g.clouds[i].alive && g.clouds[i].x==0 && g.clouds[i].y==0 && g.clouds[i].kind==0);
    /* Out-of-range cloud coordinates must not produce a false target hit. */
    game_new(&g,99);
    game_begin_search(&g,EXT_BASIC);
    g.active_clouds=1;
    g.clouds[0].alive=1;
    g.clouds[0].kind=0;
    g.clouds[0].x=2147483647;
    g.clouds[0].y=-2147483647;
    g.aim_x=128;
    g.aim_y=90;
    game_fire(&g);
    assert(g.clouds[0].alive && g.cloud_hit==0);
    /* Both axes may contain extreme signed values in corrupt state.
       Such clouds must be ignored rather than squared and selected. */
    g.clouds[0].x=-2147483647;
    g.clouds[0].y=2147483647;
    game_fire(&g);
    assert(g.clouds[0].alive && g.cloud_hit==0);
    puts("PASS: nearest overlapping cloud selected; search ends once");
    return 0;
}
