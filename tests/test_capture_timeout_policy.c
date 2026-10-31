#include "game.h"
#include <assert.h>
#include <stdio.h>

static void begin_capture(Game *g,int ext) {
    game_begin_search(g,ext);
    assert(g->screen==STATE_RADAR);
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
    puts("PASS: introductory timer only on first basic encounter");
    return 0;
}
