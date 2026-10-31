#include "game.h"
#include <assert.h>
#include <stdio.h>

static void trigger(Game *g,int ext) {
    game_begin_search(g,ext);
    assert(g->screen==STATE_RADAR);
    g->aim_x=g->clouds[0].x;
    g->aim_y=g->clouds[0].y;
    game_fire(g);
    assert(g->screen==STATE_SPHERE);
}
int main(void) {
    Game g;
    for(unsigned seed=1;seed<=128;seed++) {
        game_new(&g,seed);
        g.save.total_orbs=4000;
        g.save.orbs=4000;
        g.save.story_phase=3;
        game_set_cart(&g,GAME_DIAMOND);
        trigger(&g,EXT_DIALGA);
        assert(g.session_type==0 && g.session_species==18 && g.session_item==-1);
        /* A new sphere encounter starts with no active support effects. */
        assert(g.freeze_frames==0 && g.slow_frames==0);
        game_new(&g,seed);
        g.save.story_phase=3;
        g.save.orbs=4000;
        trigger(&g,EXT_SIM_TORNADUS);
        assert(g.session_type==0 && g.session_species==15 && g.session_item==-1);
        game_new(&g,seed);
        g.save.total_orbs=4000;
        g.save.orbs=4000;
        g.save.story_phase=1;
        trigger(&g,EXT_RETRIEVAL);
        assert(g.session_type==1 && g.session_species==-1 && g.session_item>=0);
        game_new(&g,seed);
        g.save.total_orbs=4000;
        g.save.orbs=4000;
        g.save.story_phase=1; /* Dowsing unlocks after the first Eureka stage. */
        trigger(&g,EXT_DOWSING);
        assert(g.session_type==1 && g.session_species==-1);
    }
    /* Ordinary cloud searches must support both reward kinds, with exactly
       one payload populated for each result. */
    int pokemon_results=0,item_results=0;
    for(unsigned seed=1;seed<=256;seed++) {
        game_new(&g,seed);
        g.save.story_phase=1;
        game_begin_search(&g,EXT_BASIC);
        assert(g.screen==STATE_RADAR);
        g.active_clouds=1;
        g.clouds[0].alive=1;
        g.clouds[0].kind=1;
        g.aim_x=g.clouds[0].x;g.aim_y=g.clouds[0].y;
        /* Basic pink clouds have a one-in-three encounter roll; try with
           fresh deterministic seeds until an encounter is actually begun. */
        game_fire(&g);
        if(g.screen!=STATE_SPHERE)continue;
        if(g.session_type==1) {
            item_results++;
            assert(g.session_species==-1 && g.session_item>=0);
        } else {
            pokemon_results++;
            assert(g.session_species>=0 && g.session_item==-1);
        }
    }
    assert(pokemon_results>0 && item_results>0);
    puts("PASS: legendary, simulation, and dowsing encounter type policy");
    return 0;
}
