#include "game.h"
#include <assert.h>
#include <stdio.h>

static void begin_capture(Game *g,int ext) {
    game_begin_search(g,ext);
    assert(g->screen==STATE_RADAR);
    /* Isolate one pink target and make the Basic Extension's random
       encounter roll deterministic; this test is about the timer. */
    g->active_clouds=1;
    g->clouds[0].kind=1;
    g->save.random_seed=1;
    g->aim_x=g->clouds[0].x;
    g->aim_y=g->clouds[0].y;
    game_fire(g);
    assert(g->screen==STATE_SPHERE);
}
int main(void) {
    Game g;
    game_new(&g,1024);
    g.save.cloud_count=1;
    begin_capture(&g,EXT_BASIC);
    assert(g.capture_timeout==9999*60);
    game_new(&g,1024);
    g.save.story_phase=0;
    g.save.searches=1;
    g.save.cloud_count=1;
    begin_capture(&g,EXT_BASIC);
    assert(g.capture_timeout==(90+g.save.upgrades[1]*30)*60);
    game_new(&g,1024);
    g.save.story_phase=0;
    g.save.searches=0;
    g.save.total_orbs=400;
    begin_capture(&g,EXT_TORNADUS);
    assert(g.capture_timeout==(90+g.save.upgrades[1]*30)*60);
    game_new(&g,123);
    g.screen=STATE_SPHERE;
    g.capture_timeout=60;
    g.sphere_x=g.aim_x;
    g.sphere_y=g.aim_y;
    g.capture_hp=2147483647;
    g.session_type=0;
    g.session_species=0;
    game_fire(&g);
    assert(g.screen==STATE_RESULTS && g.capture_hp==240);
    game_new(&g,123);
    g.screen=STATE_SPHERE;
    g.capture_timeout=60;
    g.sphere_x=g.aim_x;
    g.sphere_y=g.aim_y;
    g.save.upgrades[0]=0;
    game_fire(&g);
    assert(g.screen==STATE_SPHERE && g.capture_hp==0);
    puts("PASS: introductory timer only on first basic encounter");
    return 0;
}
