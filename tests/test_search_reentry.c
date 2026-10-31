#include "game.h"
#include <assert.h>
#include <stdio.h>

int main(void) {
    game_begin_search(NULL, EXT_BASIC);
    Game g;
    game_new(&g,123);
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
    puts("PASS: searches cannot overwrite active gameplay or pending storage choices");
    return 0;
}
