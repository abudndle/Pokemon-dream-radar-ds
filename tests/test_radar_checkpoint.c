/* Host-only regression for crash-safe radar resume sidecars. */
#include "game.h"
#include "save_backend.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

static void reload(SaveBackend *backend,Game *g) {
    game_new(g,999);
    assert(save_backend_load(backend,g));
}
int main(void) {
    char root[]="/tmp/dr_radar_checkpoint_XXXXXX";
    assert(mkdtemp(root));
    char rom[TW_MAX_PATH];
    assert(snprintf(rom,sizeof rom,"%s/DreamRadarDSi.nds",root)<(int)sizeof rom);
    SaveBackend backend;
    assert(save_backend_init(&backend,root,rom));
    char sidecar[TW_MAX_PATH];
    assert(snprintf(sidecar,sizeof sidecar,"%s.radar",backend.active)<(int)sizeof sidecar);

    Game g,loaded;
    game_new(&g,73);
    g.save.orbs=1000;
    g.save.total_orbs=1000;
    g.save.story_phase=1;
    g.save.cloud_count=2;
    game_begin_search(&g,EXT_DOWSING);
    assert(g.screen==STATE_RADAR && g.active_clouds==2);
    assert(g.save.orbs==900);
    g.clouds[0].alive=1;g.clouds[0].kind=1;
    g.clouds[0].x=65;g.clouds[0].y=85;
    g.clouds[1].alive=1;g.clouds[1].kind=1;
    g.clouds[1].x=155;g.clouds[1].y=85;
    assert(save_backend_write(&backend,&g));
    struct stat st;
    assert(stat(sidecar,&st)==0 && st.st_size>(off_t)sizeof(SaveData));
    reload(&backend,&loaded);
    assert(loaded.screen==STATE_RADAR && loaded.active_clouds==2);
    assert(loaded.clouds[0].x==65 && loaded.clouds[1].x==155);
    assert(loaded.save.orbs==900 && loaded.save.searches==0);
    assert(loaded.cart_source==CART_SOURCE_NONE && !loaded.camera_active);

    loaded.aim_x=65;loaded.aim_y=85;
    game_fire(&loaded);
    assert(loaded.screen==STATE_SPHERE && loaded.radar_resume_pending);
    loaded.capture_hp=77;
    assert(save_backend_write(&backend,&loaded));
    reload(&backend,&g);
    assert(g.screen==STATE_SPHERE && g.capture_hp==77);
    assert(g.radar_resume_pending && g.clouds[1].alive);
    g.capture_timeout=120;
    game_capture(&g);
    assert(g.screen==STATE_RESULTS && g.save.searches==1);
    assert(save_backend_write(&backend,&g));
    reload(&backend,&loaded);
    assert(loaded.screen==STATE_RESULTS && loaded.radar_resume_pending);
    assert(loaded.save.orbs==900 && loaded.save.searches==1);
    assert(game_resume_radar(&loaded));
    assert(loaded.screen==STATE_RADAR && loaded.clouds[1].alive);
    assert(loaded.save.searches==1 && loaded.save.orbs==900);

    /* A stable menu save retires the transient session. */
    loaded.screen=STATE_LAB;
    assert(save_backend_write(&backend,&loaded));
    assert(stat(sidecar,&st)!=0);
    reload(&backend,&g);
    assert(g.screen==STATE_LAB && g.save.searches==1);

    /* Corrupted sidecars are ignored, but valid v3 progress still loads. */
    g.save.cloud_count=1;
    game_begin_search(&g,EXT_BASIC);
    assert(g.screen==STATE_RADAR);
    assert(save_backend_write(&backend,&g));
    FILE *f=fopen(sidecar,"r+b");
    assert(f && fputc('X',f)!=EOF && fclose(f)==0);
    reload(&backend,&loaded);
    assert(loaded.screen==STATE_EXTENSIONS);
    assert(loaded.save.orbs==g.save.orbs);
    assert(loaded.requested_save);

    /* A sidecar for a different save cannot revive old entities. */
    assert(save_backend_write(&backend,&g)); /* Replace corrupted sidecar. */
    Game newer=g;
    newer.screen=STATE_SHOP;
    newer.save.orbs+=17;
    assert(game_save(&newer,backend.active));
    reload(&backend,&loaded);
    assert(loaded.screen==STATE_SHOP && loaded.save.orbs==newer.save.orbs);
    puts("PASS: radar/sphere/results resume, exactly-once charges, corrupt and stale sidecar fallback");
    return 0;
}
