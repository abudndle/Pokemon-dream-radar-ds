/* Crash-recoverable writes for OUR OWN save format; never open retail saves for writing. */
#include "save_backend.h"
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>
#include <errno.h>


/* Optional versioned radar-session sidecar. The stable v3 SaveData file
 * remains unchanged, so older builds can still load progress. No pointers
 * occur in Game; the size/version guards reject incompatible builds. */
#define RADAR_CHECKPOINT_MAGIC 0x52534350u
#define RADAR_CHECKPOINT_VERSION 1u
typedef struct {
    uint32_t magic, version, game_size, save_checksum, checksum;
    Game session;
} RadarCheckpoint;

static int radar_checkpoint_screen(GameScreen screen) {
    return screen==STATE_RADAR || screen==STATE_SPHERE ||
           screen==STATE_RESULTS || screen==STATE_REPLACE;
}
static uint32_t radar_checkpoint_checksum(const RadarCheckpoint *r) {
    const unsigned char *bytes=(const unsigned char *)r;
    uint32_t hash=2166136261u;
    for(size_t i=0;i<sizeof *r;i++) {
        if(i>=offsetof(RadarCheckpoint,checksum) &&
           i<offsetof(RadarCheckpoint,checksum)+sizeof r->checksum)continue;
        hash=(hash^bytes[i])*16777619u;
    }
    return hash;
}
static SaveData checkpoint_save_image(const Game *g) {
    SaveData s=g->save;
    s.reserved[16]=SAVE_UI_CHECKPOINT_MARKER;
    s.reserved[17]=(uint8_t)g->screen;
    s.reserved[18]=(uint8_t)((g->ext_selection>=0 && g->ext_selection<EXT_COUNT)
                              ? g->ext_selection:0);
    s.reserved[19]=(uint8_t)((g->page>=0 && g->page<16)?g->page:0);
    s.checksum=game_checksum(&s);
    return s;
}
static int radar_checkpoint_path(char *dst,size_t cap,const char *save_path,
                                 const char *suffix) {
    int n=snprintf(dst,cap,"%s%s",save_path,suffix);
    return n>=0 && (size_t)n<cap;
}
static int radar_checkpoint_write(const char *save_path,const Game *g) {
    char sidecar[TW_MAX_PATH],temp[TW_MAX_PATH];
    if(!radar_checkpoint_path(sidecar,sizeof sidecar,save_path,".radar") ||
       !radar_checkpoint_path(temp,sizeof temp,save_path,".radar.tmp"))return 0;
    if(!radar_checkpoint_screen(g->screen)) {
        /* Never resume a stale encounter after saving a stable menu. */
        if(remove(sidecar)!=0 && errno!=ENOENT)return 0;
        return 1;
    }
    RadarCheckpoint r;
    memset(&r,0,sizeof r);
    r.magic=RADAR_CHECKPOINT_MAGIC;
    r.version=RADAR_CHECKPOINT_VERSION;
    r.game_size=(uint32_t)sizeof(Game);
    r.session=*g;
    SaveData image=checkpoint_save_image(g);
    r.save_checksum=image.checksum;
    r.checksum=radar_checkpoint_checksum(&r);
    FILE *f=fopen(temp,"wb");
    if(!f)return 0;
    int ok=fwrite(&r,1,sizeof r,f)==sizeof r;
    if(fclose(f)!=0)ok=0;
    if(!ok){remove(temp);return 0;}
    /* FAT rename cannot necessarily replace an existing target. A stale
     * sidecar is harmless: it is tied to the exact main-save checksum. */
    if(remove(sidecar)!=0 && errno!=ENOENT){remove(temp);return 0;}
    if(rename(temp,sidecar)!=0){remove(temp);return 0;}
    return 1;
}
static int radar_checkpoint_restore(const char *save_path,Game *g) {
    char path[TW_MAX_PATH];
    if(!radar_checkpoint_path(path,sizeof path,save_path,".radar"))return 0;
    FILE *f=fopen(path,"rb");
    if(!f)return 0;
    RadarCheckpoint r;
    int ok=fread(&r,1,sizeof r,f)==sizeof r;
    if(ok && fgetc(f)!=EOF)ok=0;
    if(fclose(f)!=0)ok=0;
    if(!ok || r.magic!=RADAR_CHECKPOINT_MAGIC ||
       r.version!=RADAR_CHECKPOINT_VERSION ||
       r.game_size!=sizeof(Game) ||
       r.checksum!=radar_checkpoint_checksum(&r) ||
       !radar_checkpoint_screen(r.session.screen) ||
       r.save_checksum!=g->save.checksum)return 0;
    /* Verify all progress bytes, not merely a hash provided by the sidecar.
     * Never let a transient session replace authoritative saved rewards. */
    SaveData image=checkpoint_save_image(&r.session);
    if(memcmp(&image,&g->save,sizeof image)!=0 ||
       r.session.ext_selection<0 || r.session.ext_selection>=EXT_COUNT ||
       r.session.active_clouds<0 || r.session.active_clouds>MAX_CLOUDS ||
       r.session.aim_x<0 || r.session.aim_x>255 ||
       r.session.aim_y<0 || r.session.aim_y>191 ||
       r.session.radar_resume_pending<0 || r.session.radar_resume_pending>1 ||
       r.session.search_counted<0 || r.session.search_counted>1 ||
       r.session.replace_kind<REPLACE_NONE ||
       r.session.replace_kind>REPLACE_ITEM ||
       r.session.session_type<0 || r.session.session_type>1 ||
       r.session.session_species<-1 || r.session.session_species>25 ||
       r.session.session_item<-1 ||
       r.session.session_item>=RESEARCH_ITEM_TYPES ||
       r.session.capture_hp<0 || r.session.capture_hp>240 ||
       /* The orb-chain counters are bounded by the gameplay spawner.
        * Accepting impossible values could revive a broken or endlessly
        * rewarding chain from an otherwise checksummed sidecar. */
       r.session.search_orb_color>=ORB_COLOR_COUNT ||
       r.session.orb_chain_valid>1 ||
       r.session.orb_chain_stage>5 ||
       r.session.orb_group_target>5 ||
       /* Group collection can exceed the most recently spawned group's
        * target when orbs from overlapping clouds remain active. */
       r.session.orb_total_collected>DREAM_ORB_CHAIN_LIMIT)return 0;
    /* A full-storage prompt must have an actionable, bounded replacement.
     * Without these checks a checksummed but inconsistent sidecar can
     * restore a screen from which the player cannot complete the reward. */
    if(r.session.screen==STATE_REPLACE) {
        if(r.session.replace_selected<0 ||
           r.session.replace_selected>=MAX_CAUGHT ||
           r.session.replace_confirm<0 || r.session.replace_confirm>1)
            return 0;
        if(r.session.replace_kind==REPLACE_POKEMON) {
            if(r.session.save.pending_count!=MAX_CAUGHT ||
               r.session.replace_value<0 ||
               r.session.replace_value>25 ||
               (r.session.replace_value>=LEGEND_SPECIES_START &&
                r.session.replace_value<=LEGEND_SPECIES_END))return 0;
        } else if(r.session.replace_kind==REPLACE_ITEM) {
            if(r.session.replace_value<0 ||
               r.session.replace_value>=RESEARCH_ITEM_TYPES)return 0;
            for(int i=0;i<MAX_ITEMS;i++)
                if(!r.session.save.pending_items[i])return 0;
        } else return 0;
    }
    if(r.session.screen==STATE_SPHERE &&
       (r.session.capture_timeout<=0 ||
        r.session.sphere_x<0 || r.session.sphere_x>255 ||
        r.session.sphere_y<0 || r.session.sphere_y>191))return 0;
    for(int i=0;i<MAX_CLOUDS;i++) {
        const Cloud *cloud=&r.session.clouds[i];
        if(cloud->alive!=0 && cloud->alive!=1)return 0;
        /* A cloud outside the active search range must not reappear as
         * an invisible target that can never be cleared by radar logic. */
        if(cloud->alive && (i>=r.session.active_clouds ||
                            cloud->x<0 || cloud->x>255 ||
                            cloud->y<0 || cloud->y>191 ||
                            cloud->kind<0 || cloud->kind>1))return 0;
    }
    for(int i=0;i<MAX_DREAM_ORBS;i++) {
        const DreamOrb *orb=&r.session.dream_orbs[i];
        if(orb->alive>1)return 0;
        /* Spawned Orbs move by exactly one pixel per axis, have at most
         * 210 frames of life and use one of five color phases. Rejecting
         * impossible velocities also prevents signed overflow in the next
         * game_tick() position update after loading a damaged checkpoint. */
        if(orb->alive && (orb->ttl<=0 || orb->ttl>210 ||
                          orb->x<0 || orb->x>255 ||
                          orb->y<0 || orb->y>191 ||
                          (orb->vx!=-1 && orb->vx!=1) ||
                          (orb->vy!=-1 && orb->vy!=1) ||
                          orb->color_phase>4))return 0;
    }
    SaveData progress=g->save;
    *g=r.session;
    g->save=progress;
    /* Hardware and cartridge detection must be performed again on boot. */
    g->camera_ok=0;g->camera_active=0;g->camera_tracking=0;g->camera_error=0;
    g->cart=GAME_UNKNOWN;g->cart_source=CART_SOURCE_NONE;
    g->cart_read_attempted=0;
    g->pending_export_signature=0;g->archive_confirm=0;
    g->messages=0;g->message[0]=0;g->requested_save=0;
    return 1;
}

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
    if(game_load(g,backend->active)){
        radar_checkpoint_restore(backend->active,g);
        return 1;
    }
    char bak[TW_MAX_PATH];
    if(snprintf(bak,sizeof bak,"%s.bak",backend->active) < (int)sizeof bak && game_load(g,bak)) {
        /* The previous valid primary and its sidecar are backed up as a
         * pair. Restore the interrupted search when both match; an absent
         * or damaged sidecar safely falls back to the saved menu. */
        radar_checkpoint_restore(bak,g);
        backend->recovered_backup=1;
        g->requested_save=1; /* Repair the failed primary automatically. */
        return 1;
    }
    if(backend->using_twilight_path && game_load(g,backend->legacy)) {
        /* A legacy save can have an active radar session too. Carry its
         * matching checkpoint into the new launcher-adjacent location. */
        radar_checkpoint_restore(backend->legacy,g);
        backend->migrated_legacy=1;
        g->requested_save=1; /* Safely move old progress into the active path. */
        return 1;
    }
    if(backend->using_twilight_path && snprintf(bak,sizeof bak,"%s.bak",backend->legacy) < (int)sizeof bak && game_load(g,bak)) {
        /* Match the backup's own checkpoint, never the damaged primary's. */
        radar_checkpoint_restore(bak,g);
        backend->migrated_legacy=1;
        g->requested_save=1; /* Safely move old progress into the active path. */
        return 1;
    }
    return 0;
}
int save_backend_write(SaveBackend *backend,Game *g) {
    if(!backend || !g || !backend->active[0])return 0;
    char temp[TW_MAX_PATH],bak[TW_MAX_PATH];
    char sidecar[TW_MAX_PATH],bak_sidecar[TW_MAX_PATH];
    size_t len=strlen(backend->active);
    if(len+sizeof(".tmp")>sizeof temp || len+sizeof(".bak")>sizeof bak ||
       len+sizeof(".radar")>sizeof sidecar ||
       len+sizeof(".bak.radar")>sizeof bak_sidecar)return 0;
    snprintf(temp,sizeof temp,"%s.tmp",backend->active);
    snprintf(bak,sizeof bak,"%s.bak",backend->active);
    snprintf(sidecar,sizeof sidecar,"%s.radar",backend->active);
    snprintf(bak_sidecar,sizeof bak_sidecar,"%s.bak.radar",backend->active);
    int rotated_primary=0;
    if(!game_save(g,temp)) {remove(temp);return 0;}
    /* We only rotate the current save AFTER the replacement is complete. */
    struct stat st;
    /* Validate again at write time. The primary may have been corrupted after
       loading (card removal, incomplete external copy, etc.). Never rotate an
       invalid primary over a potentially good backup. */
    if(stat(backend->active,&st)!=0) {
        /* Only a missing primary is safe to treat as first-run storage.
           Permission or device errors must never be mistaken for absence. */
        if(errno!=ENOENT){remove(temp);return 0;}
    } else {
        Game current;
        game_new(&current,1);
        if(backend->recovered_backup || !game_load(&current,backend->active)) {
            if(remove(backend->active)!=0){remove(temp);return 0;}
        } else {
            /* Only a checksum- and semantics-valid primary may replace .bak. */
            remove(bak);
            if(rename(backend->active,bak)!=0){remove(temp);return 0;}
            rotated_primary=1;
            /* The old radar session belongs to the old primary. Move it
             * alongside .bak before the new main save can replace it.
             * If no sidecar exists, discard the previous backup's sidecar.
             * Failure to preserve an optional session must not invalidate
             * the fully recoverable stable .bak progress. */
            remove(bak_sidecar);
            if(rename(sidecar,bak_sidecar)!=0 && errno!=ENOENT)
                remove(sidecar);
        }
    }
    if(rename(temp,backend->active)==0){
        backend->recovered_backup=0;
        return radar_checkpoint_write(backend->active,g);
    }
    /* In recovery mode we deliberately leave the known-good .bak untouched. */
    if(!backend->recovered_backup && stat(bak,&st)==0) {
        if(rename(bak,backend->active)==0 && rotated_primary) {
            /* Roll back the matching session if installing the new main
             * save failed; otherwise the old session would be stranded. */
            rename(bak_sidecar,sidecar);
        }
    }
    remove(temp);
    return 0;
}
