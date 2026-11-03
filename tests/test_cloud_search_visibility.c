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
    /* A real radar outing starts with hidden encounter metadata. Only an
     * actual cloud hit can create the separate capture screen or loose orbs. */
    game_new(&g, 0x5A17u);
    game_begin_search(&g, EXT_BASIC);
    assert(g.screen == STATE_RADAR);
    assert(g.active_clouds > 0);
    assert(g.session_species == -1);
    assert(g.session_item == -1);
    assert(g.session_caught == -1);
    assert(game_active_dream_orbs(&g) == 0);
    int target = -1;
    for (int i = 0; i < g.active_clouds; ++i)
        if (g.clouds[i].alive) { target = i; break; }
    assert(target >= 0);
    g.aim_x = g.clouds[target].x;
    g.aim_y = g.clouds[target].y;
    int clouds_before = 0;
    for (int i = 0; i < g.active_clouds; ++i)
        clouds_before += g.clouds[i].alive != 0;
    game_fire(&g);
    int clouds_after = 0;
    for (int i = 0; i < g.active_clouds; ++i)
        clouds_after += g.clouds[i].alive != 0;
    assert(clouds_after == clouds_before - 1);
    assert(g.screen == STATE_RADAR || g.screen == STATE_SPHERE);
    if (g.screen == STATE_SPHERE) {
        assert(g.capture_timeout > 0);
        assert(g.session_type == 0 || g.session_type == 1);
        if (g.session_type == 0) assert(g.session_species >= 0);
        else assert(g.session_species == -1 && g.session_item >= 0);
    } else {
        assert(game_active_dream_orbs(&g) > 0);
        assert(g.session_species == -1);
    }
    puts("PASS: encounters and orbs remain hidden until radar cloud discovery");
    return 0;
}
