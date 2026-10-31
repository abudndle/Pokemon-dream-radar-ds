#include "game.h"
#include <assert.h>
#include <stdio.h>

int main(void) {
    Game g;
    game_new(&g, 123);
    g.save.total_orbs=400;
    g.save.story_phase=0;
    game_begin_search(&g, EXT_TORNADUS);
    assert(g.screen==STATE_RADAR);
    g.aim_x=g.clouds[0].x;
    g.aim_y=g.clouds[0].y;
    game_fire(&g);
    assert(g.screen==STATE_SPHERE);
    unsigned phase=g.save.story_phase;
    unsigned count=g.save.caught_count;
    g.capture_timeout=1;
    g.freeze_frames=10;
    g.slow_frames=10;
    game_tick(&g);
    assert(g.screen==STATE_RESULTS);
    assert(g.freeze_frames==0 && g.slow_frames==0);
    assert(g.session_caught==-1);
    assert(g.save.story_phase==phase);
    assert(g.save.caught_count==count);
    assert(game_extension_unlocked(&g,EXT_TORNADUS));

    game_new(&g, 456);
    g.save.story_phase=3;
    game_set_cart(&g, GAME_DIAMOND);
    assert(game_extension_unlocked(&g,EXT_DIALGA));
    game_begin_search(&g,EXT_DIALGA);
    assert(g.screen==STATE_RADAR);
    g.aim_x=g.clouds[0].x;
    g.aim_y=g.clouds[0].y;
    game_fire(&g);
    assert(g.screen==STATE_SPHERE);
    g.capture_timeout=1;
    g.freeze_frames=10;
    g.slow_frames=10;
    game_tick(&g);
    assert(g.screen==STATE_RESULTS);
    assert(g.freeze_frames==0 && g.slow_frames==0);
    assert(!(g.save.legends_caught&1));
    assert(game_extension_unlocked(&g,EXT_DIALGA));
    /* A completed Tornadus capture advances research exactly once. */
    game_new(&g,789);
    g.save.total_orbs=400;
    g.save.story_phase=0;
    game_begin_search(&g,EXT_TORNADUS);
    assert(g.screen==STATE_RADAR);
    g.aim_x=g.clouds[0].x;g.aim_y=g.clouds[0].y;
    game_fire(&g);
    assert(g.screen==STATE_SPHERE && g.session_species==15);
    g.capture_timeout=100;
    game_capture(&g);
    assert(g.screen==STATE_RESULTS);
    assert(g.save.story_phase==1 && g.session_caught==15);
    assert(g.save.pending_count==1 && g.save.pending[0]==15);
    assert(g.save.caught_count==1);

    /* Progress must wait for user acceptance when all storage is occupied. */
    game_new(&g,790);
    g.save.total_orbs=400;
    g.save.story_phase=0;
    game_begin_search(&g,EXT_TORNADUS);
    g.aim_x=g.clouds[0].x;g.aim_y=g.clouds[0].y;
    game_fire(&g);
    assert(g.screen==STATE_SPHERE && g.session_species==15);
    g.save.pending_count=MAX_CAUGHT;
    for(int i=0;i<MAX_CAUGHT;i++)g.save.pending[i]=(uint8_t)i;
    game_capture(&g);
    assert(g.screen==STATE_REPLACE && g.save.story_phase==0);
    assert(g.save.caught_count==0);
    assert(game_replace_pending(&g,3));
    assert(g.screen==STATE_RESULTS && g.save.story_phase==1);
    assert(g.save.pending[3]==15 && g.save.caught_count==1);
    /* Finish the three-story legendary chain through the real radar and
       capture state transitions, verifying each next unlock threshold. */
    game_new(&g,791);
    for(int phase=0;phase<3;phase++) {
        int extension=EXT_TORNADUS+phase;
        g.save.total_orbs=(phase==0)?400u:(phase==1)?1500u:3000u;
        assert(game_extension_unlocked(&g,extension));
        game_begin_search(&g,extension);
        assert(g.screen==STATE_RADAR);
        g.aim_x=g.clouds[0].x;g.aim_y=g.clouds[0].y;
        game_fire(&g);
        assert(g.screen==STATE_SPHERE);
        assert(g.session_type==0 && g.session_species==15+phase);
        game_capture(&g);
        assert(g.screen==STATE_RESULTS);
        assert(g.save.story_phase==(unsigned)(phase+1));
        assert(g.save.pending_count==(unsigned)(phase+1));
        assert(g.save.pending[phase]==15+phase);
        assert(g.save.caught_count==(unsigned)(phase+1));
        assert(!game_extension_unlocked(&g,extension));
    }
    assert(game_extension_unlocked(&g,EXT_SIM_TORNADUS));
    /* Cartridge-specific legendary research is single-use after capture. */
    game_set_cart(&g,GAME_DIAMOND);
    assert(game_extension_unlocked(&g,EXT_DIALGA));
    game_begin_search(&g,EXT_DIALGA);
    assert(g.screen==STATE_RADAR);
    g.aim_x=g.clouds[0].x;g.aim_y=g.clouds[0].y;
    game_fire(&g);
    assert(g.screen==STATE_SPHERE && g.session_species==18);
    game_capture(&g);
    assert(g.screen==STATE_RESULTS && g.session_caught==18);
    assert((g.save.legends_caught & 1u)!=0);
    assert(g.save.pending_count==4 && g.save.pending[3]==18);
    assert(!game_extension_unlocked(&g,EXT_DIALGA));
    /* A simulator must not capture a duplicate legendary or advance the
       story; it DOES award a research item from the Simulator's item pool. */
    g.save.orbs=1000;
    game_begin_search(&g,EXT_SIM_TORNADUS);
    assert(g.screen==STATE_RADAR);
    g.aim_x=g.clouds[0].x;g.aim_y=g.clouds[0].y;
    game_fire(&g);
    assert(g.screen==STATE_SPHERE && g.session_species==15);
    unsigned before_count=g.save.caught_count;
    unsigned before_pending=g.save.pending_count;
    unsigned before_phase=g.save.story_phase;
    int simulator_item=g.session_item;
    assert(simulator_item>=0 && simulator_item<RESEARCH_ITEM_TYPES);
    game_capture(&g);
    assert(g.screen==STATE_RESULTS && g.session_caught==-2);
    assert(g.save.caught_count==before_count);
    assert(g.save.pending_count==before_pending);
    assert(g.save.story_phase==before_phase);
    assert(g.save.pending_items[0]==1);
    assert(game_item_slot_kind(&g,0)==simulator_item);
    puts("PASS: legendary escape, captures, replacement and 3-stage story progression");
    return 0;
}
