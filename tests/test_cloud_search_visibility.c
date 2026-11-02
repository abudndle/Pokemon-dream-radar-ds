#include "game.h"
#include <assert.h>
#include <stdio.h>

/* Gameplay contract: no encounter or orb can be fired from title/lab;
 * clouds must be discovered in a radar search before shooting yields rewards.
 * This is a portable rules test, not a claim of emulator visual parity. */
int main(void) {
    Game g;
    game_new(&g, 0x5A17u);
    assert(g.screen == STATE_TITLE);
    assert(game_active_dream_orbs(&g) == 0);
    unsigned int before_orbs = g.save.orbs;
    unsigned int before_caught = g.save.caught_count;
    g.aim_x = 128;
    g.aim_y = 85;
    game_fire(&g);
    assert(g.screen == STATE_TITLE);
    assert(g.save.orbs == before_orbs);
    assert(g.save.caught_count == before_caught);
    assert(game_active_dream_orbs(&g) == 0);

    g.screen = STATE_LAB;
    game_fire(&g);
    assert(g.screen == STATE_LAB);
    assert(game_active_dream_orbs(&g) == 0);
    assert(g.save.caught_count == before_caught);

    g.save.cloud_count = 0;
    g.screen = STATE_EXTENSIONS;
    game_begin_search(&g, EXT_BASIC);
    assert(g.screen == STATE_EXTENSIONS);
    assert(game_active_dream_orbs(&g) == 0);
    assert(g.active_clouds == 0);
    game_fire(&g);
    assert(g.screen == STATE_EXTENSIONS);
    assert(game_active_dream_orbs(&g) == 0);
    assert(g.save.caught_count == before_caught);
    puts("PASS: encounters and orbs remain hidden until radar cloud discovery");
    return 0;
}
