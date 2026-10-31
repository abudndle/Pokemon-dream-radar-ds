#include "game.h"
#include <assert.h>
#include <stdio.h>

int main(void) {
    game_begin_search(NULL, EXT_BASIC);
    Game g;
    game_new(&g,123);
    assert(g.session_caught==-1 && g.session_item==-1 && g.session_species==-1);
    assert(g.session_type==0 && g.capture_hp==0);
    game_begin_search(&g,EXT_BASIC);
    assert(g.screen==STATE_RADAR);
    unsigned count=g.save.cloud_count;
    unsigned seed=g.save.random_seed;
    int first_x=g.clouds[0].x,first_y=g.clouds[0].y;
    game_begin_search(&g,EXT_BASIC);
    assert(g.screen==STATE_RADAR && g.save.cloud_count==count);
    assert(g.save.random_seed==seed);
    assert(g.clouds[0].x==first_x && g.clouds[0].y==first_y);
    g.screen=STATE_SPHERE;
    g.capture_timeout=200;
    game_begin_search(&g,EXT_BASIC);
    assert(g.screen==STATE_SPHERE && g.capture_timeout==200);
    g.screen=STATE_REPLACE;
    g.replace_kind=REPLACE_POKEMON;
    game_begin_search(&g,EXT_BASIC);
    assert(g.screen==STATE_REPLACE && g.replace_kind==REPLACE_POKEMON);
    assert(!game_leave_search(NULL));
    assert(!game_leave_search(&g)); /* Replacement choice must remain intact. */
    assert(g.screen==STATE_REPLACE);
    g.screen=STATE_RADAR;
    g.save.searches=UINT32_MAX;
    g.requested_save=0;
    assert(game_leave_search(&g));
    assert(g.screen==STATE_RESULTS && g.save.searches==UINT32_MAX);
    assert(g.requested_save);
    assert(!game_leave_search(&g)); /* Repeated Back must not double-count. */
    g.screen=STATE_SPHERE;
    g.capture_timeout=20;g.freeze_frames=4;g.slow_frames=6;
    g.session_caught=5;g.session_item=9;g.session_species=18;g.session_type=1;
    g.capture_hp=200;
    g.save.searches=12;
    assert(game_leave_search(&g));
    assert(g.save.searches==13 && g.capture_timeout==0);
    assert(g.freeze_frames==0 && g.slow_frames==0);
    assert(g.session_caught==-1 && g.session_item==-1 && g.session_species==-1 && g.session_type==0);
    assert(g.capture_hp==0);
    /* Expired captures must also discard unearned encounter metadata. */
    g.screen=STATE_SPHERE;
    g.capture_timeout=1;
    g.session_caught=20;g.session_item=4;g.session_species=20;g.session_type=1;
    g.capture_hp=150;
    unsigned before_expiry=g.save.searches;
    game_tick(&g);
    assert(g.screen==STATE_RESULTS && g.capture_timeout==0);
    assert(g.save.searches==before_expiry+1);
    assert(g.session_caught==-1 && g.session_item==-1 && g.session_species==-1);
    assert(g.session_type==0 && g.capture_hp==0);
    assert(!game_leave_search(&g));
    /* After returning to the menu, a new search must start with no
       species assigned until an actual sphere encounter begins. */
    g.save.cloud_count=5;
    g.session_species=22;
    g.capture_timeout=999;
    g.session_item=8;
    g.session_caught=14;
    game_begin_search(&g,EXT_BASIC);
    assert(g.screen==STATE_RADAR);
    assert(g.capture_timeout==0 && g.capture_hp==0);
    assert(g.session_species==-1 && g.session_item==-1 && g.session_caught==-1);
    puts("PASS: searches cannot overwrite active gameplay or pending storage choices");
    return 0;
}
