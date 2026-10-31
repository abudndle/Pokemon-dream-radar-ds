#include "game.h"
#include <assert.h>
#include <limits.h>
#include <stdio.h>
int main(void) {
    Game g; game_new(&g, 42);
    g.save.goods[0]=1; g.save.goods[1]=1; g.save.goods[2]=1;
    assert(!game_use_support(&g,0));
    assert(g.save.goods[0]==1 && !g.requested_save);
    g.screen=STATE_SPHERE;
    g.save.goods[0]=255;
    assert(!game_use_support(&g,0));
    assert(g.save.goods[0]==255 && g.freeze_frames==0 && !g.requested_save);
    g.save.goods[0]=1;
    assert(!game_use_support(&g,-1));
    assert(!game_use_support(&g,3));
    assert(game_use_support(&g,0));
    assert(g.freeze_frames==300 && g.save.goods[0]==0 && g.requested_save);
    g.requested_save=0;
    assert(!game_use_support(&g,0) && !g.requested_save);
    assert(game_use_support(&g,1) && g.slow_frames==300);
    g.capture_timeout=120*60;
    assert(game_use_support(&g,2) && g.capture_timeout==145*60);
    g.save.goods[2]=1; g.capture_timeout=INT_MAX-10;
    assert(game_use_support(&g,2) && g.capture_timeout==INT_MAX);
    g.save.goods[2]=1; g.requested_save=0;
    assert(!game_use_support(&g,2));
    assert(g.save.goods[2]==1 && g.capture_timeout==INT_MAX && !g.requested_save);
    /* A completed capture clears encounter-local effects. */
    game_new(&g,71);
    g.screen=STATE_SPHERE;
    g.ext_selection=EXT_BASIC;
    g.session_type=0;
    g.session_species=0;
    g.freeze_frames=240;
    g.slow_frames=120;
    game_capture(&g);
    assert(g.screen==STATE_RESULTS);
    assert(g.freeze_frames==0 && g.slow_frames==0);
    puts("PASS: support activation, item consumption, timer extension, saturation, and no-op behavior");
    return 0;
}
