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
    puts("PASS: escaped legendaries preserve one-time unlock and progression");
    return 0;
}
