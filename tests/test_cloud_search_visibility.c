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
    /* Off-screen shots cannot discover clouds, reveal an encounter or
       create currency. The actual target must be fired upon separately. */
    g.aim_x = -1;
    g.aim_y = -1;
    game_fire(&g);
    assert(g.screen == STATE_RADAR && g.clouds[target].alive);
    assert(g.save.orbs == 0 && g.save.caught_count == 0);
    assert(g.session_species == -1 && g.session_item == -1);
    assert(game_active_dream_orbs(&g) == 0);
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
    /* A pink cloud shot reveals loose Orbs but does not award currency.
       Collecting one of the actual Orbs is a second independent shot. */
    game_new(&g, 0x5A17u);
    game_begin_search(&g, EXT_BASIC);
    assert(g.screen == STATE_RADAR);
    g.active_clouds = 1;
    g.clouds[0].alive = 1;
    g.clouds[0].kind = 0;
    g.clouds[0].x = 128;
    g.clouds[0].y = 96;
    g.aim_x = 128;
    g.aim_y = 96;
    unsigned int currency_before = g.save.orbs;
    game_fire(&g);
    assert(g.screen == STATE_RADAR);
    assert(!g.clouds[0].alive && g.cloud_hit == 1);
    assert(game_active_dream_orbs(&g) >= 3);
    assert(g.save.orbs == currency_before && g.session_orbs == 0);
    assert(g.session_species == -1 && g.session_item == -1);
    int orb = -1;
    for(int i = 0; i < MAX_DREAM_ORBS; ++i)
        if(g.dream_orbs[i].alive) { orb = i; break; }
    assert(orb >= 0);
    g.aim_x = g.dream_orbs[orb].x;
    g.aim_y = g.dream_orbs[orb].y;
    int orb_count_before = game_active_dream_orbs(&g);
    game_fire(&g);
    assert(game_active_dream_orbs(&g) == orb_count_before - 1);
    assert(g.session_orbs == 1 && g.save.orbs == currency_before + 1);
    assert(g.save.caught_count == 0 && g.session_species == -1);
    /* Uncollected Dream Orbs expire on the radar clock. With no remaining
       clouds, expiry ends the search without awarding uncollected currency. */
    game_new(&g, 0x5A17u);
    game_begin_search(&g, EXT_BASIC);
    assert(g.screen == STATE_RADAR);
    g.active_clouds = 1;
    g.clouds[0].alive = 1;
    g.clouds[0].kind = 0;
    g.clouds[0].x = 128;
    g.clouds[0].y = 96;
    g.aim_x = 128;
    g.aim_y = 96;
    game_fire(&g);
    assert(g.screen == STATE_RADAR && game_active_dream_orbs(&g) > 0);
    unsigned int uncollected_currency = g.save.orbs;
    for(int i = 0; i < MAX_DREAM_ORBS; ++i)
        if(g.dream_orbs[i].alive) g.dream_orbs[i].ttl = 1;
    game_tick(&g);
    assert(game_active_dream_orbs(&g) == 0);
    assert(g.screen == STATE_RESULTS);
    assert(g.save.orbs == uncollected_currency);
    assert(g.session_orbs == 0);
    assert(g.save.searches == 1);
    /* A spawned Dream Orb directly over an untouched cloud must be collected
       first. A single shot cannot both award currency and discover a cloud. */
    game_new(&g, 0x6A19u);
    game_begin_search(&g, EXT_BASIC);
    assert(g.screen == STATE_RADAR && g.active_clouds >= 2);
    g.active_clouds = 2;
    g.clouds[0].alive = 1;
    g.clouds[0].kind = 0;
    g.clouds[0].x = 128;
    g.clouds[0].y = 96;
    g.clouds[1].alive = 1;
    g.clouds[1].kind = 0;
    g.clouds[1].x = 180;
    g.clouds[1].y = 96;
    g.aim_x = 128;
    g.aim_y = 96;
    game_fire(&g);
    assert(!g.clouds[0].alive && g.clouds[1].alive);
    assert(game_active_dream_orbs(&g) > 0);
    int overlap_orb = -1;
    for(int i = 0; i < MAX_DREAM_ORBS; ++i)
        if(g.dream_orbs[i].alive) { overlap_orb = i; break; }
    assert(overlap_orb >= 0);
    /* Move the remaining live cloud under the collectible orb. */
    g.clouds[1].x = g.dream_orbs[overlap_orb].x;
    g.clouds[1].y = g.dream_orbs[overlap_orb].y;
    g.aim_x = g.clouds[1].x;
    g.aim_y = g.clouds[1].y;
    int remaining_orbs = game_active_dream_orbs(&g);
    int previous_hits = g.cloud_hit;
    int previous_rewards = g.session_orbs;
    game_fire(&g);
    assert(g.clouds[1].alive && g.cloud_hit == previous_hits);
    assert(game_active_dream_orbs(&g) == remaining_orbs - 1);
    assert(g.session_orbs == previous_rewards + 1);
    assert(g.screen == STATE_RADAR && g.session_species == -1);
    /* Overlapping cloud hitboxes must resolve to the nearest live cloud,
       rather than whichever happens to occupy the first array slot. */
    game_new(&g, 0x7B23u);
    game_begin_search(&g, EXT_BASIC);
    assert(g.screen == STATE_RADAR && g.active_clouds >= 2);
    g.active_clouds = 2;
    g.clouds[0].alive = 1;
    g.clouds[0].kind = 0;
    g.clouds[0].x = 110;
    g.clouds[0].y = 96;
    g.clouds[1].alive = 1;
    g.clouds[1].kind = 0;
    g.clouds[1].x = 120;
    g.clouds[1].y = 96;
    g.aim_x = 119;
    g.aim_y = 96;
    game_fire(&g);
    assert(g.clouds[0].alive && !g.clouds[1].alive);
    assert(g.cloud_hit == 1);
    assert(game_active_dream_orbs(&g) >= 3);
    assert(g.session_species == -1 && g.session_item == -1);
    assert(g.save.orbs == 0);
    /* End-to-end host gameplay acceptance: find a storm-cloud seed whose
       ordinary Basic search opens a real encounter, then follow the moving
       target using game_tick/game_fire until capture is awarded. This must
       never shortcut by directly calling game_capture(). */
    int found_sphere = 0;
    for(unsigned seed = 1; seed <= 256 && !found_sphere; ++seed) {
        game_new(&g, seed);
        game_begin_search(&g, EXT_BASIC);
        assert(g.screen == STATE_RADAR);
        g.active_clouds = 1;
        g.clouds[0].alive = 1;
        g.clouds[0].kind = 1;
        g.clouds[0].x = 128;
        g.clouds[0].y = 96;
        g.aim_x = 128;
        g.aim_y = 96;
        assert(g.session_species == -1 && g.session_item == -1);
        game_fire(&g);
        if(g.screen != STATE_SPHERE)continue;
        found_sphere = 1;
        assert(g.cloud_hit == 1 && !g.clouds[0].alive);
        assert(g.capture_timeout > 0 && g.save.caught_count == 0);
        assert(g.save.pending_count == 0 && g.save.orbs == 0);
        /* Invalid camera/touch aim must not damage a capture target or
           consume a projectile while the separate sphere screen is live. */
        int hp_before_invalid = g.capture_hp;
        int timeout_before_invalid = g.capture_timeout;
        int sphere_x_before_invalid = g.sphere_x;
        int sphere_y_before_invalid = g.sphere_y;
        /* Keep a live hostile projectile: invalid coordinates must not
           accidentally shoot it down or steal a legitimate capture shot. */
        g.projectile_enabled = 1;
        g.projectile_active = 1;
        g.projectile_x = 100;
        g.projectile_y = 90;
        g.projectile_vx = 1;
        g.projectile_vy = 0;
        g.projectile_lifetime = 60;
        const int invalid_coords[][2] = {
            {-1, 96}, {128, -1}, {256, 96}, {128, 192},
            {-2147483647-1, 0}, {2147483647, 2147483647}
        };
        for(unsigned invalid = 0;
            invalid < sizeof invalid_coords / sizeof invalid_coords[0];
            ++invalid) {
            g.aim_x = invalid_coords[invalid][0];
            g.aim_y = invalid_coords[invalid][1];
            game_fire(&g);
            assert(g.projectile_active && g.projectile_lifetime == 60);
            assert(g.projectile_x == 100 && g.projectile_y == 90);
        }
        assert(g.screen == STATE_SPHERE);
        assert(g.capture_hp == hp_before_invalid);
        assert(g.capture_timeout == timeout_before_invalid);
        assert(g.sphere_x == sphere_x_before_invalid);
        assert(g.sphere_y == sphere_y_before_invalid);
        int found_movement = 0;
        g.projectile_active = 0;
        g.projectile_enabled = 0; /* Isolate the target and capture meter. */
        for(int frame = 0; frame < 150 && g.screen == STATE_SPHERE; ++frame) {
            int old_x = g.sphere_x, old_y = g.sphere_y;
            game_tick(&g);
            if(g.screen != STATE_SPHERE)break;
            if(g.sphere_x != old_x || g.sphere_y != old_y)found_movement = 1;
            g.aim_x = g.sphere_x;
            g.aim_y = g.sphere_y;
            game_fire(&g);
        }
        assert(found_movement);
        assert(g.screen == STATE_RESULTS);
        assert(g.save.searches == 1);
        if(g.session_caught >= 0) {
            assert(g.save.pending_count == 1);
            assert(g.save.pending[0] == g.session_caught);
            assert(g.save.caught_count == 1);
        } else {
            assert(g.session_item >= 0);
            assert(g.save.pending_items[g.session_item] > 0);
        }
    }
    assert(found_sphere); /* A storm can open the dedicated shooting scene. */
    puts("PASS: cloud discovery, real moving-sphere capture and separate Orb currency");
    return 0;
}
