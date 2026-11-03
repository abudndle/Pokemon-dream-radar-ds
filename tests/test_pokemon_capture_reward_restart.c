/* Gameplay-to-save acceptance using real capture input and checkpoint files.
 * This is a portable host test, not evidence of a melonDS GUI playthrough. */
#include "game.h"
#include "save_backend.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

static void reboot(SaveBackend *backend,Game *g,unsigned seed) {
    game_new(g,seed);
    assert(save_backend_load(backend,g));
}
static void find_pokemon(Game *g) {
    int found=0;
    for(unsigned seed=1;seed<=512 && !found;seed++) {
        game_new(g,seed);
        g->save.story_phase=1;
        g->save.cloud_count=2;
        g->save.orbs=1000;
        g->save.total_orbs=1000;
        game_begin_search(g,EXT_DOWSING);
        assert(g->screen==STATE_RADAR && g->active_clouds==2);
        g->clouds[0].alive=1;g->clouds[0].kind=1;
        g->clouds[0].x=70;g->clouds[0].y=90;
        g->clouds[1].alive=1;g->clouds[1].kind=0;
        g->clouds[1].x=180;g->clouds[1].y=90;
        g->aim_x=70;g->aim_y=90;
        game_fire(g);
        assert(g->screen==STATE_SPHERE);
        if(g->session_type==0 && g->session_species>=0 &&
           g->session_species<LEGEND_SPECIES_START)found=1;
    }
    assert(found);
    assert(g->radar_resume_pending && g->clouds[1].alive);
    assert(g->save.pending_count==0 && g->save.caught_count==0);
    assert(g->save.searches==0 && g->save.orbs==900);
}
int main(void) {
    char root[]="/tmp/dr_pokemon_reward_restart_XXXXXX";
    assert(mkdtemp(root));
    char rom[TW_MAX_PATH];
    assert(snprintf(rom,sizeof rom,"%s/DreamRadarDSi.nds",root)<(int)sizeof rom);
    SaveBackend backend;
    assert(save_backend_init(&backend,root,rom));
    Game g,restored;
    find_pokemon(&g);
    int species=g.session_species;
    int x=g.sphere_x,y=g.sphere_y;
    int vx=g.sphere_vx,vy=g.sphere_vy;
    int timer=g.capture_timeout;
    /* Persist a naturally generated, unresolved Pokémon encounter. */
    assert(save_backend_write(&backend,&g));
    reboot(&backend,&restored,999);
    assert(restored.screen==STATE_SPHERE);
    assert(restored.session_type==0 && restored.session_species==species);
    assert(restored.sphere_x==x && restored.sphere_y==y);
    assert(restored.sphere_vx==vx && restored.sphere_vy==vy);
    assert(restored.capture_timeout==timer);
    assert(restored.save.pending_count==0 && restored.save.caught_count==0);
    reboot(&backend,&g,998);
    assert(g.screen==STATE_SPHERE && g.session_species==species);
    assert(g.capture_timeout==timer && g.save.orbs==900);
    assert(g.save.pending_count==0 && g.save.searches==0);

    /* Finish the restored moving-target encounter by ordinary ticks/shots;
     * no direct game_capture or fabricated reward values are permitted. */
    g.projectile_enabled=0;
    int moved=0;
    for(int frame=0;frame<240 && g.screen==STATE_SPHERE;frame++) {
        int old_x=g.sphere_x,old_y=g.sphere_y;
        game_tick(&g);
        if(g.screen!=STATE_SPHERE)break;
        if(old_x!=g.sphere_x || old_y!=g.sphere_y)moved=1;
        g.aim_x=g.sphere_x;g.aim_y=g.sphere_y;
        game_fire(&g);
    }
    assert(moved && g.screen==STATE_RESULTS);
    assert(g.session_caught==species);
    assert(g.save.pending_count==1 && g.save.pending[0]==species);
    assert(g.save.caught_count==1 && g.save.searches==1);
    assert(g.save.orbs==900 && g.radar_resume_pending);
    assert(save_backend_write(&backend,&g));

    /* Results page and actual Pokémon reward must survive TWO clean reloads.
     * A Results screen alone must never count as sufficient evidence. */
    for(unsigned seed=100;seed<102;seed++) {
        reboot(&backend,&restored,seed);
        assert(restored.screen==STATE_RESULTS);
        assert(restored.session_caught==species);
        assert(restored.save.pending_count==1);
        assert(restored.save.pending[0]==species);
        assert(restored.save.caught_count==1);
        assert(restored.save.searches==1);
        assert(restored.save.orbs==900);
        assert(restored.radar_resume_pending);
    }
    assert(game_resume_radar(&restored));
    assert(restored.screen==STATE_RADAR && restored.clouds[1].alive);
    assert(restored.save.pending_count==1 && restored.save.pending[0]==species);
    assert(restored.save.caught_count==1 && restored.save.searches==1);
    assert(save_backend_write(&backend,&restored));
    reboot(&backend,&g,123);
    assert(g.screen==STATE_RADAR && g.clouds[1].alive);
    assert(g.save.pending_count==1 && g.save.pending[0]==species);
    assert(g.save.caught_count==1 && g.save.searches==1);
    assert(game_leave_search(&g));
    assert(save_backend_write(&backend,&g));
    reboot(&backend,&restored,124);
    assert(restored.save.pending_count==1 && restored.save.pending[0]==species);
    assert(restored.save.caught_count==1 && restored.save.searches==1);
    puts("PASS: actual Pokémon cloud/beam capture survives repeated backend restarts and resumed radar without duplicate rewards");
    return 0;
}
