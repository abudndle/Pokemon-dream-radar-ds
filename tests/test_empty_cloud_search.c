#include "game.h"
#include <assert.h>
#include <stdio.h>

int main(void) {
    Game g; game_new(&g, 123);
    g.save.story_phase=3;
    g.save.total_orbs=4000;
    g.save.orbs=800;
    g.save.cloud_count=0;
    for (int ext=EXT_BASIC; ext<=EXT_DOWSING; ext++) {
        if (ext!=EXT_BASIC && ext!=EXT_RETRIEVAL && ext!=EXT_DOWSING) continue;
        g.screen=STATE_EXTENSIONS;
        g.requested_save=0;
        uint32_t before=g.save.orbs;
        game_begin_search(&g,ext);
        assert(g.screen==STATE_EXTENSIONS);
        assert(g.save.orbs==before);
        assert(g.save.cloud_count==0);
        assert(g.requested_save==0);
    }
    /* A new cloud enables a paid search and charges exactly once. */
    g.save.cloud_count=1;
    game_begin_search(&g,EXT_DOWSING);
    assert(g.screen==STATE_RADAR);
    assert(g.active_clouds==1);
    assert(g.save.orbs==700);
    assert(g.save.cloud_count==0);
    puts("PASS: empty cloud searches do not charge or enter an unwinnable radar");
    return 0;
}
