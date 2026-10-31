/* Crash-recoverable writes for OUR OWN save format; never open retail saves for writing. */
#include "save_backend.h"
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

static int path_append(char *dst,size_t cap,const char *a,const char *b) {
    const size_t len=strlen(a), sep=(len && a[len-1]=='/')?0:1;
    if (len+sep+strlen(b)+1>cap)return 0;
    memcpy(dst,a,len);
    size_t offset=len;
    if (sep)dst[offset++]='/';
    memcpy(dst+offset,b,strlen(b)+1);
    return 1;
}
static int mkdir_if_needed(const char *path) {
    if(mkdir(path,0777)==0)return 1;
    struct stat st;
    return stat(path,&st)==0 && S_ISDIR(st.st_mode);
}
static int create_parent(const char *path) {
    char folder[TW_MAX_PATH];const char *sep=strrchr(path,'/');
    if(!sep || (size_t)(sep-path)>=sizeof folder)return 0;
    memcpy(folder,path,(size_t)(sep-path));folder[sep-path]=0;
    return mkdir_if_needed(folder);
}
int save_backend_init(SaveBackend *backend,const char *root,const char *rom_path) {
    if(!backend || !root || !*root)return 0;
    memset(backend,0,sizeof *backend);
    if(!path_append(backend->legacy,sizeof backend->legacy,root,"DreamRadarDSi/save.dat"))return 0;
    /* Reject paths on other drives. No writes to NAND. */
    size_t root_len=strlen(root);
    /* A matching prefix is not enough: /sd/games2 is not within /sd/games. */
    if(rom_path && strncmp(rom_path,root,root_len)==0 &&
       (root[root_len-1]=='/' || rom_path[root_len]=='/') &&
       twilight_homebrew_save_path(rom_path,backend->active,sizeof backend->active) &&
       create_parent(backend->active)) {
        backend->using_twilight_path=1;
    } else {
        strcpy(backend->active,backend->legacy);
    }
    /* A missing legacy directory should not prevent launcher-adjacent saves. */
    create_parent(backend->legacy);
    return 1;
}
int save_backend_load(SaveBackend *backend,Game *g) {
    if(!backend || !g)return 0;
    backend->recovered_backup=0;
    backend->migrated_legacy=0;
    if(game_load(g,backend->active))return 1;
    char bak[TW_MAX_PATH];
    if(snprintf(bak,sizeof bak,"%s.bak",backend->active) < (int)sizeof bak && game_load(g,bak)) {
        backend->recovered_backup=1;
        g->requested_save=1; /* Repair the failed primary automatically. */
        return 1;
    }
    if(backend->using_twilight_path && game_load(g,backend->legacy)) {
        backend->migrated_legacy=1;
        g->requested_save=1; /* Safely move old progress into the active path. */
        return 1;
    }
    if(backend->using_twilight_path && snprintf(bak,sizeof bak,"%s.bak",backend->legacy) < (int)sizeof bak && game_load(g,bak)) {
        backend->migrated_legacy=1;
        g->requested_save=1; /* Safely move old progress into the active path. */
        return 1;
    }
    return 0;
}
int save_backend_write(SaveBackend *backend,Game *g) {
    if(!backend || !g || !backend->active[0])return 0;
    char temp[TW_MAX_PATH],bak[TW_MAX_PATH];
    size_t len=strlen(backend->active);
    if(len+sizeof(".tmp")>sizeof temp || len+sizeof(".bak")>sizeof bak)return 0;
    snprintf(temp,sizeof temp,"%s.tmp",backend->active);
    snprintf(bak,sizeof bak,"%s.bak",backend->active);
    if(!game_save(g,temp)) {remove(temp);return 0;}
    /* We only rotate the current save AFTER the replacement is complete. */
    struct stat st;
    /* Validate again at write time. The primary may have been corrupted after
       loading (card removal, incomplete external copy, etc.). Never rotate an
       invalid primary over a potentially good backup. */
    if(stat(backend->active,&st)==0) {
        Game current;
        game_new(&current,1);
        if(backend->recovered_backup || !game_load(&current,backend->active)) {
            if(remove(backend->active)!=0){remove(temp);return 0;}
        } else {
            /* Only a checksum- and semantics-valid primary may replace .bak. */
            remove(bak);
            if(rename(backend->active,bak)!=0){remove(temp);return 0;}
        }
    }
    if(rename(temp,backend->active)==0){backend->recovered_backup=0;return 1;}
    /* In recovery mode we deliberately leave the known-good .bak untouched. */
    if(!backend->recovered_backup && stat(bak,&st)==0)rename(bak,backend->active);
    remove(temp);
    return 0;
}
