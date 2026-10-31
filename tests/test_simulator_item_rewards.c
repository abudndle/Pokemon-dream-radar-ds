#include "game.h"
#include <assert.h>
#include <stdio.h>
#include <stdint.h>
static int in_pool(int ext,int id) {
    const int pools[3][6]={
        {4,17,15,16,7,20},
        {18,17,15,16,19,21},
        {22,17,15,16,20,21}
    };
    for(int i=0;i<6;i++)if(pools[ext-EXT_SIM_TORNADUS][i]==id)return 1;
    return 0;
}
static void trigger(Game *g,int ext) {
    game_begin_search(g,ext);
    assert(g->screen==STATE_RADAR);
    g->aim_x=g->clouds[0].x;g->aim_y=g->clouds[0].y;
    game_fire(g);
    assert(g->screen==STATE_SPHERE);
    assert(g->session_species==15+ext-EXT_SIM_TORNADUS);
    assert(g->session_type==0); /* Still display the Therian Pokemon */
    assert(in_pool(ext,g->session_item));
}
int main(void) {
    for(int ext=EXT_SIM_TORNADUS;ext<=EXT_SIM_LANDORUS;ext++) {
        for(uint32_t seed=1;seed<=192;seed++) {
            Game g;
            game_new(&g,seed);
            g.save.story_phase=3;
            g.save.orbs=10000;
            trigger(&g,ext);
            int prize=g.session_item;
            game_capture(&g);
            assert(g.screen==STATE_RESULTS);
            assert(g.session_caught==-2);
            assert(g.save.caught_count==0);
            assert(g.save.pending_count==0);
            assert(g.save.story_phase==3);
            assert(g.save.pending_items[0]==1);
            assert(game_item_slot_kind(&g,0)==prize);
        }
    }
    /* A full item store uses the same explicit replace-or-cancel UI, and
       does not silently discard Simulator prizes. */
    Game g;
    game_new(&g,17);
    g.save.story_phase=3;g.save.orbs=10000;
    trigger(&g,EXT_SIM_LANDORUS);
    int prize=g.session_item;
    for(int i=0;i<MAX_ITEMS;i++) {
        g.save.pending_items[i]=MAX_ITEM_STACK;
        g.save.reserved[2+i]=(uint8_t)(i+1);
    }
    game_capture(&g);
    assert(g.screen==STATE_REPLACE && g.replace_kind==REPLACE_ITEM);
    assert(g.replace_value==prize);
    assert(game_cancel_pending_replace(&g));
    assert(g.save.pending_items[0]==MAX_ITEM_STACK);
    assert(g.save.pending_count==0);
    /* Malformed simulator encounters must not mint either reward kind. */
    game_new(&g,17);
    g.screen=STATE_SPHERE;g.ext_selection=EXT_SIM_TORNADUS;
    g.session_type=0;g.session_species=24;g.session_item=4;
    g.capture_timeout=200;
    game_capture(&g);
    assert(g.screen==STATE_SPHERE && g.save.caught_count==0);
    assert(g.save.pending_count==0 && g.save.pending_items[0]==0);
    puts("PASS: all 3 simulator item pools, Therian encounter, storage and validation");
    return 0;
}
