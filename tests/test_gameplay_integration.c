#include "game.h"
#include <assert.h>
#include <stdio.h>
/* One real gameplay sequence: scan -> cloud hit -> timed sphere ->
   support activation -> capture -> queued item reward -> results. */
int main(void) {
    Game g;
    game_new(&g, 12345);
    g.screen=STATE_RADAR;
    g.ext_selection=EXT_RETRIEVAL;
    g.active_clouds=1;
    g.cloud_hit=0;
    g.clouds[0].alive=1;
    g.clouds[0].kind=1;
    g.clouds[0].x=120;
    g.clouds[0].y=80;
    g.aim_x=120;
    g.aim_y=80;
    g.save.goods[0]=1;
    g.save.upgrades[0]=5;
    uint32_t searches=g.save.searches;
    game_fire(&g);
    assert(g.screen==STATE_SPHERE);
    assert(g.session_type==1);
    assert(g.session_species==-1);
    assert(g.session_item>=0 && g.session_item<RESEARCH_ITEM_TYPES);
    assert(g.cloud_hit==1);
    assert(game_use_support(&g,0)==1);
    assert(g.save.goods[0]==0);
    assert(g.freeze_frames==300);
    g.aim_x=g.sphere_x;
    g.aim_y=g.sphere_y;
    for(int i=0;i<10 && g.screen==STATE_SPHERE;i++)
        game_fire(&g);
    assert(g.screen==STATE_RESULTS);
    assert(g.session_caught==-2);
    assert(g.save.searches==searches+1);
    assert(g.freeze_frames==0);
    assert(g.save.pending_items[0]==1);
    assert(game_item_slot_kind(&g,0)==g.session_item);
    assert(game_use_support(&g,0)==0);
    assert(g.requested_save==1);
    puts("PASS: radar-to-item capture integrates aim, support, reward and results");
    return 0;
}
