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
    assert(g.screen==STATE_RADAR && game_active_dream_orbs(&g)>=3);
    assert(g.save.orbs==UINT32_MAX-1);
    /* Fire at the actual orb positions, not the spent cloud. */
    for(int pass=0;pass<MAX_DREAM_ORBS;pass++) {
        int found=-1;
        for(int i=0;i<MAX_DREAM_ORBS;i++)
            if(g.dream_orbs[i].alive){found=i;break;}
        if(found<0)break;
        g.aim_x=g.dream_orbs[found].x;
        g.aim_y=g.dream_orbs[found].y;
        game_fire(&g);
    }
    assert(g.save.orbs==UINT32_MAX);
    assert(g.save.total_orbs==UINT32_MAX);
    assert(g.session_orbs==INT_MAX);
    assert(g.screen==STATE_RESULTS);
    assert(g.save.searches==1);
    assert(g.requested_save);
    puts("PASS: orb reward counters saturate rather than wrap");
    return 0;
}
