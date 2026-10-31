/* Validate private save recovery: never overwrite a good .bak with a corrupt primary. */
#include "game.h"
#include "save_backend.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

static void suffix(char *dst, size_t cap, const char *s, const char *ext) {
    assert(snprintf(dst, cap, "%s%s", s, ext) < (int)cap);
}
static void damage(const char *path) {
    FILE *f=fopen(path,"r+b");assert(f);
    assert(fseek(f, 8, SEEK_SET)==0);
    assert(fputc(0xFE,f)!=EOF);assert(fclose(f)==0);
}
int main(void) {
    char root[]="/tmp/dr_recovery_XXXXXX";
    assert(mkdtemp(root));
    char rom[TW_MAX_PATH];
    assert(snprintf(rom,sizeof rom,"%s/DreamRadarDSi.nds",root) < (int)sizeof rom);
    SaveBackend backend;
    assert(save_backend_init(&backend,root,rom));
    /* Invalid persistence arguments must fail without dereferencing pointers. */
    Game invalid;game_new(&invalid,77);
    assert(!game_load(NULL,"/tmp/missing.drs"));
    assert(!game_load(&invalid,NULL));
    assert(!game_load(&invalid,""));
    assert(!game_save(NULL,"/tmp/missing.drs"));
    assert(!game_save(&invalid,NULL));
    assert(!game_save(&invalid,""));
    /* A failed open must not silently alter the in-memory save checksum. */
    Game denied;game_new(&denied,123);
    denied.save.checksum=0xAABBCCDDu;
    assert(!game_save(&denied,"/this/directory/does/not/exist/dream-radar.sav"));
    assert(denied.save.checksum==0xAABBCCDDu);
    /* Successful serialization writes a valid checksum to disk without
       mutating the live snapshot or its stale checksum. */
    char standalone[TW_MAX_PATH];
    assert(snprintf(standalone,sizeof standalone,"%s/direct.sav",root)<(int)sizeof standalone);
    Game direct;game_new(&direct,31);
    direct.save.orbs=77;
    direct.save.checksum=0xBEEFu;
    assert(game_save(&direct,standalone));
    assert(direct.save.checksum==0xBEEFu);
    Game loaded;game_new(&loaded,1);
    assert(game_load(&loaded,standalone) && loaded.save.orbs==77);
    Game g;game_new(&g,1);
    g.save.orbs=123;
    assert(save_backend_write(&backend,&g));
    g.save.orbs=222;
    assert(save_backend_write(&backend,&g));
    char bak[TW_MAX_PATH];suffix(bak,sizeof bak,backend.active,".bak");
    Game backup;game_new(&backup,1);
    assert(game_load(&backup,bak) && backup.save.orbs==123);
    damage(backend.active);
    Game recovered;game_new(&recovered,999);
    assert(save_backend_load(&backend,&recovered));
    assert(backend.recovered_backup && recovered.save.orbs==123);
    assert(recovered.requested_save); /* Autosave repair is requested. */
    recovered.save.orbs=333;
    assert(save_backend_write(&backend,&recovered));
    assert(!backend.recovered_backup);
    assert(game_load(&backup,bak) && backup.save.orbs==123);
    Game valid;game_new(&valid,42);
    assert(game_load(&valid,backend.active) && valid.save.orbs==333);
    /* A primary corrupted AFTER the previous successful load must never
       overwrite the good backup during the next write. */
    damage(backend.active);
    recovered.save.orbs=444;
    assert(save_backend_write(&backend,&recovered));
    assert(game_load(&backup,bak) && backup.save.orbs==123);
    assert(game_load(&valid,backend.active) && valid.save.orbs==444);
    /* Even internally consistent but invalid values cannot be loaded. */
    valid.save.story_phase=255;
    assert(game_save(&valid,backend.active));
    assert(!game_load(&valid,backend.active));
    /* Recovery remains possible after a second corrupted primary. */
    assert(save_backend_load(&backend,&valid) && backend.recovered_backup);
    assert(valid.save.orbs==123 && valid.requested_save);
    /* A full storage queue may still conduct orb / item searches. */
    Game full;game_new(&full,4);
    full.save.pending_count=MAX_CAUGHT;
    full.save.total_orbs=500;
    full.save.orbs=500;
    game_begin_search(&full,EXT_RETRIEVAL);
    assert(full.screen==STATE_RADAR);
    /* Older Dream Radar progress is copied to the current launch-relative
       save location, not mistaken for a retail Pokemon .sav. */
    char oldroot[]="/tmp/dr_legacy_XXXXXX";
    assert(mkdtemp(oldroot));
    SaveBackend migration;
    char oldrom[TW_MAX_PATH];
    assert(snprintf(oldrom,sizeof oldrom,"%s/DreamRadar.nds",oldroot)<(int)sizeof oldrom);
    assert(save_backend_init(&migration,oldroot,oldrom));
    assert(migration.using_twilight_path);
    Game original;game_new(&original,17);
    original.save.orbs=987;
    assert(game_save(&original,migration.legacy));
    Game loaded;game_new(&loaded,18);
    assert(save_backend_load(&migration,&loaded));
    assert(migration.migrated_legacy && loaded.requested_save);
    assert(loaded.save.orbs==987);
    assert(save_backend_write(&migration,&loaded));
    Game installed;game_new(&installed,0);
    assert(game_load(&installed,migration.active));
    assert(installed.save.orbs==987);
    FILE *f=fopen(migration.active,"ab");assert(f);
    assert(fputc('X',f)!=EOF);assert(fclose(f)==0);
    assert(!game_load(&installed,migration.active)); /* No trailing payload. */
    puts("PASS: backup auto-repair, late corruption, migration and strict save length");
    return 0;
}
