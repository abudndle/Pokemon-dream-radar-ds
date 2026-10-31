#include "game.h"
#include <assert.h>
#include <limits.h>
#include <stdio.h>
#include <string.h>
static void test_effect_reuse(void) {
    for(int slot=0;slot<2;slot++) {
        Game g;game_new(&g,42);
        g.screen=STATE_SPHERE;g.capture_timeout=1000;
        g.sphere_x=100;g.sphere_y=100;
        g.save.goods[slot]=2;
        assert(game_support_status(&g,slot)==SUPPORT_READY);
        assert(game_use_support(&g,slot));
        for(int remaining=299;remaining>=1;remaining--) {
            game_tick(&g);
            SaveData before=g.save;
            g.requested_save=0;
            assert(game_support_status(&g,slot)==SUPPORT_ACTIVE);
            assert(!game_use_support(&g,slot));
            assert(!memcmp(&before,&g.save,sizeof before));
            assert(!g.requested_save);
            assert((slot==0?g.freeze_frames:g.slow_frames)==remaining);
        }
        game_tick(&g);
        assert(game_support_status(&g,slot)==SUPPORT_READY);
        assert(game_use_support(&g,slot));
        assert(g.save.goods[slot]==0 && g.requested_save);
        assert(game_support_status(&g,slot)==SUPPORT_ACTIVE);
        for(int i=0;i<300;i++)game_tick(&g);
        assert(game_support_status(&g,slot)==SUPPORT_EMPTY);
        g.requested_save=0;
        assert(!game_use_support(&g,slot) && !g.requested_save);
        assert(strstr(g.message,"Restock") && g.messages>0);
    }
    assert(game_support_status(NULL,0)==SUPPORT_UNAVAILABLE);
}
int main(void) {
    test_effect_reuse();
    Game g; game_new(&g, 42);
    g.save.goods[0]=1; g.save.goods[1]=1; g.save.goods[2]=1;
    assert(!game_use_support(&g,0));
    assert(g.save.goods[0]==1 && !g.requested_save);
    g.screen=STATE_SPHERE;
    g.capture_timeout=120*60;
    g.save.goods[0]=255;
    assert(!game_use_support(&g,0));
    assert(g.save.goods[0]==255 && g.freeze_frames==0 && !g.requested_save);
    g.save.goods[0]=1;
    assert(!game_use_support(&g,-1));
    assert(!game_use_support(&g,3));
    assert(game_use_support(&g,0));
    assert(g.freeze_frames==300 && g.save.goods[0]==0 && g.requested_save);
    g.save.goods[0]=1;g.requested_save=0;
    assert(!game_use_support(&g,0));
    assert(g.save.goods[0]==1 && g.freeze_frames==300 && !g.requested_save);
    g.save.goods[0]=0;
    g.requested_save=0;
    assert(!game_use_support(&g,0) && !g.requested_save);
    assert(game_use_support(&g,1) && g.slow_frames==300);
    g.save.goods[1]=1; g.requested_save=0;
    assert(!game_use_support(&g,1));
    assert(g.save.goods[1]==1 && g.slow_frames==300 && !g.requested_save);
    g.save.goods[1]=0;
    g.save.goods[0]=1;g.save.goods[1]=1;
    g.capture_timeout=0; g.requested_save=0;
    assert(!game_use_support(&g,0));
    assert(!game_use_support(&g,1));
    assert(g.save.goods[0]==1 && g.save.goods[1]==1 && !g.requested_save);
    g.save.goods[0]=0;g.save.goods[1]=0;
    assert(!game_use_support(&g,2));
    assert(g.save.goods[2]==1 && g.capture_timeout==0 && !g.requested_save);
    g.capture_timeout=-1;
    assert(!game_use_support(&g,2));
    assert(g.save.goods[2]==1 && g.capture_timeout==-1 && !g.requested_save);
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
    /* Captures must occur during an active, unexpired encounter. */
    g.capture_timeout=100;
    g.freeze_frames=240;
    g.slow_frames=120;
    game_capture(&g);
    assert(g.screen==STATE_RESULTS);
    assert(g.freeze_frames==0 && g.slow_frames==0);
    puts("PASS: support activation, item consumption, timer extension, saturation, and no-op behavior");
    return 0;
}
