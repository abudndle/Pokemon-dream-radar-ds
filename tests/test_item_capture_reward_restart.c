/* Item reward persistence through real storm -> sphere gameplay and backend.
 * This is a host test, not an emulator gameplay demonstration. */
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
static int item_stack(const Game *g,int item) {
    int count=0;
    for(int i=0;i<MAX_ITEMS;i++)
        if(game_item_slot_kind(g,i)==item)count+=g->save.pending_items[i];
    return count;
}
static void begin_item(Game *g) {
    int found=0;
    for(unsigned seed=1;seed<=512 && !found;seed++) {
        game_new(g,seed);
        g->save.story_phase=1;
        g->save.cloud_count=2;
        g->save.orbs=1000;g->save.total_orbs=1000;
        game_begin_search(g,EXT_DOWSING);
        assert(g->screen==STATE_RADAR && g->active_clouds==2);
        g->clouds[0].alive=1;g->clouds[0].kind=1;
        g->clouds[0].x=70;g->clouds[0].y=90;
        g->clouds[1].alive=1;g->clouds[1].kind=0;
        g->clouds[1].x=180;g->clouds[1].y=90;
        g->aim_x=70;g->aim_y=90;
        game_fire(g);
        assert(g->screen==STATE_SPHERE);
        if(g->session_type==1 && g->session_item>=0 &&
           g->session_item<RESEARCH_ITEM_TYPES)found=1;
    }
    assert(found);
    assert(g->session_species==-1);
    assert(g->radar_resume_pending && g->clouds[1].alive);
    assert(g->save.searches==0 && g->save.orbs==900);
    for(int i=0;i<MAX_ITEMS;i++)assert(g->save.pending_items[i]==0);
}
int main(void) {
    char root[]="/tmp/dr_item_reward_restart_XXXXXX";
    assert(mkdtemp(root));
    char rom[TW_MAX_PATH];
    assert(snprintf(rom,sizeof rom,"%s/DreamRadarDSi.nds",root)<(int)sizeof rom);
    SaveBackend backend;
    assert(save_backend_init(&backend,root,rom));
    Game g,restored;
    begin_item(&g);
    int item=g.session_item;
    int x=g.sphere_x,y=g.sphere_y;
    int vx=g.sphere_vx,vy=g.sphere_vy;
    int timer=g.capture_timeout;
    assert(save_backend_write(&backend,&g));
    reboot(&backend,&restored,999);
    assert(restored.screen==STATE_SPHERE && restored.session_item==item);
    assert(restored.session_type==1 && restored.session_species==-1);
    assert(restored.sphere_x==x && restored.sphere_y==y);
    assert(restored.sphere_vx==vx && restored.sphere_vy==vy);
    assert(restored.capture_timeout==timer);
    assert(item_stack(&restored,item)==0 && restored.save.searches==0);
    reboot(&backend,&g,998);
    assert(g.screen==STATE_SPHERE && g.session_item==item);
    assert(item_stack(&g,item)==0 && g.save.orbs==900);
    /* Capturing the moving target must go through actual normal aiming. */
    g.projectile_enabled=0;
    int moved=0;
    for(int frame=0;frame<240 && g.screen==STATE_SPHERE;frame++) {
        int x0=g.sphere_x,y0=g.sphere_y;
        game_tick(&g);
        if(g.screen!=STATE_SPHERE)break;
        if(g.sphere_x!=x0 || g.sphere_y!=y0)moved=1;
        g.aim_x=g.sphere_x;g.aim_y=g.sphere_y;
        game_fire(&g);
    }
    assert(moved && g.screen==STATE_RESULTS);
    assert(g.session_caught==-2 && g.session_item==item);
    assert(item_stack(&g,item)==1);
    assert(g.save.caught_count==0 && g.save.pending_count==0);
    assert(g.save.searches==1 && g.save.orbs==900);
    assert(save_backend_write(&backend,&g));

    /* Repeated cold loads cannot turn a single collected item into two. */
    for(unsigned seed=100;seed<103;seed++) {
        reboot(&backend,&restored,seed);
        assert(restored.screen==STATE_RESULTS);
        assert(restored.session_item==item && restored.session_caught==-2);
        assert(item_stack(&restored,item)==1);
        assert(restored.save.searches==1 && restored.save.orbs==900);
        assert(restored.radar_resume_pending);
    }
    assert(game_resume_radar(&restored));
    assert(restored.screen==STATE_RADAR && restored.clouds[1].alive);
    assert(item_stack(&restored,item)==1 && restored.save.searches==1);
    assert(save_backend_write(&backend,&restored));
    reboot(&backend,&g,124);
    assert(g.screen==STATE_RADAR && g.clouds[1].alive);
    assert(item_stack(&g,item)==1 && g.save.searches==1);
    assert(game_leave_search(&g));
    assert(save_backend_write(&backend,&g));
    reboot(&backend,&restored,125);
    assert(item_stack(&restored,item)==1);
    assert(restored.save.searches==1 && restored.save.orbs==900);
    puts("PASS: actual item capture persists across live sphere and repeated clean backend restarts without duplicates");
    return 0;
}
