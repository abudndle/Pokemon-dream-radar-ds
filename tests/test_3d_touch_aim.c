#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "game.h"
#include "../source_3d/aim_input.h"

int main(void) {
    Game game;
    memset(&game, 0, sizeof(game));
    game.aim_x = 120;
    game.aim_y = 90;
    game.screen = STATE_TITLE;
    assert(!dr3d_apply_touch_aim(&game, 1, 30, 40));
    assert(game.aim_x == 120 && game.aim_y == 90);
    game.screen = STATE_RADAR;
    assert(!dr3d_apply_touch_aim(&game, 0, 30, 40));
    assert(game.aim_x == 120 && game.aim_y == 90);
    assert(dr3d_apply_touch_aim(&game, 1, 30, 40));
    assert(game.aim_x == 30 && game.aim_y == 40);
    assert(dr3d_apply_touch_aim(&game, 1, -10, 300));
    assert(game.aim_x == 0 && game.aim_y == 191);
    game.screen = STATE_SPHERE;
    assert(dr3d_apply_touch_aim(&game, 1, 999, -5));
    assert(game.aim_x == 255 && game.aim_y == 0);
    game.screen = STATE_RESULTS;
    assert(!dr3d_apply_touch_aim(&game, 1, 10, 10));
    assert(game.aim_x == 255 && game.aim_y == 0);
    assert(!dr3d_apply_touch_aim(NULL, 1, 5, 5));
    puts("PASS: DS touchscreen aim is bounded and radar/capture-only");
    return 0;
}
