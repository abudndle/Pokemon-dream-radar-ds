/* A real pink-cloud discovery, Orb pickup, save, clean reload and
 * continuation must award each collected Orb exactly once. This is a host
 * backend scenario; independent melonDS screenshot proof remains pending. */
#include "game.h"
#include "save_backend.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

static void restart(SaveBackend *backend,Game *g,unsigned seed) {
    game_new(g,seed);
    assert(save_backend_load(backend,g));
}

static int orbs(const Game *g) {
    return game_active_dream_orbs(g);
}

static void collect_one(Game *g) {
    int index=-1;
    for(int i=0;i<MAX_DREAM_ORBS;i++)
        if(g->dream_orbs[i].alive){index=i;break;}
    assert(index>=0);
    g->aim_x=g->dream_orbs[index].x;
    g->aim_y=g->dream_orbs[index].y;
    int before=orbs(g);
    game_fire(g);
    assert(orbs(g)==before-1);
}

int main(void) {
    char root[]="/tmp/dr_orb_clean_restart_XXXXXX";
    assert(mkdtemp(root));
    char rom[TW_MAX_PATH];
    assert(snprintf(rom,sizeof rom,"%s/DreamRadarDSi.nds",root)<(int)sizeof rom);
    SaveBackend backend;
    assert(save_backend_init(&backend,root,rom));
    Game g,loaded;
    game_new(&g,115);
    game_begin_search(&g,EXT_BASIC);
    assert(g.screen==STATE_RADAR);
    /* Restrict the cloud fixture without leaving hidden live targets
       outside active_clouds: the checkpoint validator correctly rejects
       those impossible sessions on a clean restart. */
    g.active_clouds=1;
    for(int i=1;i<MAX_CLOUDS;i++)g.clouds[i].alive=0;
    g.clouds[0].alive=1;
    g.clouds[0].kind=0;
    g.clouds[0].x=128;g.clouds[0].y=96;
    g.aim_x=128;g.aim_y=96;
    game_fire(&g);
    assert(g.screen==STATE_RADAR && g.cloud_hit==1);
    assert(orbs(&g)==3);
    assert(g.save.orbs==0 && g.save.total_orbs==0);
    assert(g.session_orbs==0 && g.save.searches==0);
    assert(save_backend_write(&backend,&g));

    /* A fresh Game in a new process can recover the same session from
       stable SaveData and its checksum-bound radar sidecar. */
    restart(&backend,&loaded,999);
    assert(loaded.screen==STATE_RADAR);
    assert(orbs(&loaded)==3);
    assert(loaded.save.orbs==0 && loaded.session_orbs==0);
    assert(loaded.save.searches==0);
    game_tick(&loaded);
    assert(orbs(&loaded)==3);
    collect_one(&loaded);
    assert(loaded.screen==STATE_RADAR);
    assert(loaded.save.orbs==1 && loaded.save.total_orbs==1);
    assert(loaded.session_orbs==1 && orbs(&loaded)==2);
    assert(save_backend_write(&backend,&loaded));

    /* After another restart the exact first reward stays credited
       while both remaining targets are still alive and collectible. */
    restart(&backend,&g,777);
    assert(g.screen==STATE_RADAR && orbs(&g)==2);
    assert(g.save.orbs==1 && g.save.total_orbs==1);
    assert(g.session_orbs==1 && g.save.searches==0);
    assert(g.session_color_counts[ORB_PINK]==1);
    collect_one(&g);
    assert(g.save.orbs==2 && orbs(&g)==1);
    collect_one(&g);
    assert(g.screen==STATE_RESULTS && orbs(&g)==0);
    assert(g.save.orbs==3 && g.save.total_orbs==3);
    assert(g.session_orbs==3 && g.save.searches==1);
    assert(g.save.caught_count==0 && g.save.pending_count==0);
    assert(save_backend_write(&backend,&g));

    restart(&backend,&loaded,123);
    assert(loaded.screen==STATE_RESULTS && orbs(&loaded)==0);
    assert(loaded.save.orbs==3 && loaded.save.total_orbs==3);
    assert(loaded.session_orbs==3 && loaded.save.searches==1);
    assert(loaded.session_color_counts[ORB_PINK]==3);
    /* A repeated boot must never replay an Orb pickup or search count. */
    restart(&backend,&g,234);
    assert(g.save.orbs==3 && g.save.total_orbs==3);
    assert(g.save.searches==1 && g.session_orbs==3);
    puts("PASS: cloud -> Orb pickup -> save/restart -> remaining Orbs -> restored exactly-once reward");
    return 0;
}
