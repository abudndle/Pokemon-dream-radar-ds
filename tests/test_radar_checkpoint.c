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

    /* Rotating the primary save must rotate its *matching* radar session.
     * A corrupt new primary should recover the previous in-flight search,
     * not an unrelated or newer sidecar. The backup session is distinct
     * even when the stable SaveData checksum has not changed. */
    char backup_sidecar[TW_MAX_PATH];
    assert(snprintf(backup_sidecar,sizeof backup_sidecar,
                    "%s.bak.radar",backend.active)<(int)sizeof backup_sidecar);
    loaded.aim_x=101;
    assert(save_backend_write(&backend,&loaded));
    assert(stat(backup_sidecar,&st)==0 && st.st_size>(off_t)sizeof(SaveData));
    FILE *broken=fopen(backend.active,"r+b");
    assert(broken && fputc('X',broken)!=EOF && fclose(broken)==0);
    reload(&backend,&loaded);
    assert(backend.recovered_backup && loaded.requested_save);
    assert(loaded.screen==STATE_RADAR && loaded.aim_x==128);
    assert(loaded.active_clouds==2 && loaded.clouds[1].x==155);
    assert(loaded.save.orbs==900 && loaded.save.searches==0);
    assert(save_backend_write(&backend,&loaded));
    assert(!backend.recovered_backup);
    reload(&backend,&loaded);
    assert(loaded.screen==STATE_RADAR && loaded.aim_x==128);
    assert(loaded.save.orbs==900 && loaded.save.searches==0);

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

    /* Checksum-valid but impossible orb-chain state must never resume.
     * Each invalid sidecar is written through the normal persistence path
     * so these cases exercise semantic validation, not checksum failure. */
    for(int invalid=0;invalid<5;invalid++) {
        Game malformed=g;
        switch(invalid) {
            case 0: malformed.search_orb_color=ORB_COLOR_COUNT;break;
            case 1: malformed.orb_chain_valid=2;break;
            case 2: malformed.orb_chain_stage=6;break;
            case 3: malformed.orb_group_target=6;break;
            case 4: malformed.orb_total_collected=DREAM_ORB_CHAIN_LIMIT+1;break;
        }
        assert(save_backend_write(&backend,&malformed));
        reload(&backend,&loaded);
        assert(loaded.screen==STATE_EXTENSIONS);
        assert(loaded.save.orbs==g.save.orbs);
    }
    /* A corrupted-but-checksummed session must not resurrect impossible
     * Orb rewards or cloud hits. A tally mismatch can otherwise silently
     * change the dominant color after resuming the hunt. */
    for(int invalid=0;invalid<7;invalid++) {
        Game malformed=g;
        switch(invalid) {
            case 0: malformed.session_orbs=-1;break;
            case 1: malformed.session_orbs=MAX_CLOUDS*DREAM_ORB_CHAIN_LIMIT+1;break;
            case 2: malformed.cloud_hit=-1;break;
            case 3: malformed.cloud_hit=malformed.active_clouds+1;break;
            case 4: malformed.session_color_counts[0]=1;break;
            case 5: malformed.session_orbs=1;break;
            case 6:
                malformed.session_orbs=1;
                malformed.session_color_counts[0]=2;
                break;
        }
        assert(save_backend_write(&backend,&malformed));
        reload(&backend,&loaded);
        assert(loaded.screen==STATE_EXTENSIONS);
        assert(loaded.save.orbs==g.save.orbs);
    }
    /* A genuine matching per-color tally remains resumable and the
     * recovered search must not award or deduct an Orb on reload. */
    Game valid_tally=g;
    valid_tally.session_orbs=2;
    valid_tally.session_color_counts[ORB_PINK]=1;
    valid_tally.session_color_counts[ORB_GREEN]=1;
    valid_tally.cloud_hit=valid_tally.active_clouds;
    assert(save_backend_write(&backend,&valid_tally));
    reload(&backend,&loaded);
    assert(loaded.screen==STATE_RADAR);
    assert(loaded.session_orbs==2 && loaded.cloud_hit==valid_tally.active_clouds);
    assert(loaded.session_color_counts[ORB_PINK]==1);
    assert(loaded.session_color_counts[ORB_GREEN]==1);
    assert(loaded.save.orbs==g.save.orbs);

    /* A valid boundary state is still resumable. */
    Game valid_chain=g;
    valid_chain.search_orb_color=ORB_PINK;
    valid_chain.orb_chain_valid=1;
    valid_chain.orb_chain_stage=5;
    valid_chain.orb_group_target=5;
    /* Overlapping cloud groups may leave more collected than the last
     * group's target; that is a valid state and must remain resumable. */
    valid_chain.orb_group_collected=6;
    valid_chain.orb_total_collected=DREAM_ORB_CHAIN_LIMIT;
    assert(save_backend_write(&backend,&valid_chain));
    reload(&backend,&loaded);
    assert(loaded.screen==STATE_RADAR);
    assert(loaded.orb_total_collected==DREAM_ORB_CHAIN_LIMIT);

    /* A checksummed sidecar must not restore physically impossible entities.
     * In particular, a huge Orb velocity could overflow signed arithmetic
     * on the first radar tick after loading. The stable save remains usable. */
    for(int invalid=0;invalid<7;invalid++) {
        Game malformed=g;
        DreamOrb *orb=&malformed.dream_orbs[0];
        orb->alive=1;orb->x=120;orb->y=80;
        orb->vx=-1;orb->vy=1;orb->ttl=210;orb->color_phase=4;
        switch(invalid) {
            case 0: orb->vx=2;break;
            case 1: orb->vy=2147483647;break;
            case 2: orb->ttl=211;break;
            case 3: orb->color_phase=5;break;
            case 4: malformed.clouds[0].kind=2;break;
            case 5: orb->vx=0;break;
            case 6: malformed.active_clouds=0;break;
        }
        assert(save_backend_write(&backend,&malformed));
        reload(&backend,&loaded);
        assert(loaded.screen==STATE_EXTENSIONS);
        assert(loaded.save.orbs==g.save.orbs);
    }
    Game valid_orb=g;
    valid_orb.dream_orbs[0].alive=1;
    valid_orb.dream_orbs[0].x=120;
    valid_orb.dream_orbs[0].y=80;
    valid_orb.dream_orbs[0].vx=-1;
    valid_orb.dream_orbs[0].vy=1;
    valid_orb.dream_orbs[0].ttl=210;
    valid_orb.dream_orbs[0].color_phase=4;
    assert(save_backend_write(&backend,&valid_orb));
    reload(&backend,&loaded);
    assert(loaded.screen==STATE_RADAR);
    assert(loaded.dream_orbs[0].alive && loaded.dream_orbs[0].ttl==210);
    game_tick(&loaded);
    assert(loaded.dream_orbs[0].x==119 && loaded.dream_orbs[0].y==81);

    /* An actual moving Legendary sphere spawns a primary and two secondary
     * projectiles. Their positions and lifetimes must survive a checkpoint
     * without an extra hit, while malformed values must be rejected before
     * the first post-restart movement tick. */
    Game projectile;
    game_new(&projectile,53);
    projectile.screen=STATE_SPHERE;
    projectile.ext_selection=EXT_TORNADUS;
    projectile.session_species=15;
    projectile.capture_timeout=120;
    projectile.projectile_enabled=1;
    projectile.sphere_x=105;projectile.sphere_y=90;
    projectile.aim_x=200;projectile.aim_y=120;
    projectile.projectile_cooldown=0;
    game_tick(&projectile);
    assert(projectile.projectile_active && projectile.projectile_extra[0].active);
    assert(projectile.projectile_extra[1].active);
    assert(save_backend_write(&backend,&projectile));
    reload(&backend,&loaded);
    assert(loaded.screen==STATE_SPHERE && loaded.projectile_active);
    assert(loaded.projectile_extra[0].active && loaded.projectile_extra[1].active);
    assert(loaded.projectile_extra[0].ttl==90 && loaded.projectile_hits==0);
    game_tick(&loaded);
    assert(loaded.screen==STATE_SPHERE && loaded.projectile_extra[0].ttl==89);
    assert(loaded.projectile_hits==0);

    for(int invalid=0;invalid<16;invalid++) {
        Game malformed=projectile;
        switch(invalid) {
            case 0: malformed.sphere_vx=2147483647;break;
            case 1: malformed.sphere_vy=(-2147483647-1);break;
            case 2: malformed.freeze_frames=301;break;
            case 3: malformed.slow_frames=301;break;
            case 4: malformed.projectile_vx=2147483647;break;
            case 5: malformed.projectile_vy=(-2147483647-1);break;
            case 6: malformed.projectile_lifetime=91;break;
            case 7: malformed.projectile_x=256;break;
            case 8: malformed.projectile_extra[0].vx=2147483647;break;
            case 9: malformed.projectile_extra[0].vy=(-2147483647-1);break;
            case 10: malformed.projectile_extra[0].ttl=91;break;
            case 11: malformed.projectile_extra[0].x=256;break;
            case 12: malformed.projectile_queued=3;break;
            case 13: malformed.projectile_cooldown=161;break;
            case 14: malformed.projectile_extra[0].active=2;break;
            case 15: malformed.projectile_enabled=0;break;
        }
        assert(save_backend_write(&backend,&malformed));
        reload(&backend,&loaded);
        assert(loaded.screen==STATE_EXTENSIONS);
        assert(loaded.save.orbs==projectile.save.orbs);
    }

    /* Capture reward metadata must survive a restart without inventing an
     * unawardable Pokemon/item or turning a Simulator into a normal drop.
     * All malformed sessions are checksummed through the real write path. */
    for(int invalid=0;invalid<8;invalid++) {
        Game malformed=projectile;
        switch(invalid) {
            case 0: malformed.session_species=-1;break;
            case 1: malformed.session_species=26;break;
            case 2: malformed.session_item=0;break;
            case 3:
                malformed.session_type=1;
                malformed.session_item=0;
                break; /* Item encounter still claims a Pokemon species. */
            case 4:
                malformed.session_type=1;
                malformed.session_species=-1;
                malformed.session_item=-1;
                break;
            case 5:
                malformed.session_type=1;
                malformed.session_species=-1;
                malformed.session_item=RESEARCH_ITEM_TYPES;
                break;
            case 6:
                malformed.ext_selection=EXT_SIM_TORNADUS;
                malformed.session_item=-1;
                break;
            case 7:
                malformed.ext_selection=EXT_SIM_THUNDURUS;
                malformed.session_item=4;
                break; /* Simulator species must match its extension. */
        }
        assert(save_backend_write(&backend,&malformed));
        reload(&backend,&loaded);
        assert(loaded.screen==STATE_EXTENSIONS);
        assert(loaded.save.orbs==projectile.save.orbs);
    }
    Game item_sphere=projectile;
    item_sphere.ext_selection=EXT_DOWSING;
    item_sphere.session_type=1;
    item_sphere.session_species=-1;
    item_sphere.session_item=0; /* Item zero is valid, not a sentinel. */
    item_sphere.projectile_active=0;
    for(int i=0;i<MAX_EXTRA_PROJECTILES;i++)
        item_sphere.projectile_extra[i].active=0;
    assert(save_backend_write(&backend,&item_sphere));
    reload(&backend,&loaded);
    assert(loaded.screen==STATE_SPHERE && loaded.session_type==1);
    assert(loaded.session_species==-1 && loaded.session_item==0);
    /* A real item reward remains visible after restart only when its
     * corresponding item stack was actually committed. */
    Game item_result=item_sphere;
    game_capture(&item_result);
    assert(item_result.screen==STATE_RESULTS && item_result.session_caught==-2);
    assert(save_backend_write(&backend,&item_result));
    reload(&backend,&loaded);
    assert(loaded.screen==STATE_RESULTS && loaded.session_caught==-2);
    assert(loaded.session_item==0);
    int found_item=0;
    for(int i=0;i<MAX_ITEMS;i++)
        if(game_item_slot_kind(&loaded,i)==0)found_item=1;
    assert(found_item);

    Game simulator_sphere=item_sphere;
    simulator_sphere.ext_selection=EXT_SIM_TORNADUS;
    simulator_sphere.session_type=0;
    simulator_sphere.session_species=LEGEND_SPECIES_START;
    simulator_sphere.session_item=4;
    assert(save_backend_write(&backend,&simulator_sphere));
    reload(&backend,&loaded);
    assert(loaded.screen==STATE_SPHERE && loaded.session_type==0);
    assert(loaded.session_species==LEGEND_SPECIES_START);
    assert(loaded.session_item==4);

    /* A sidecar for a different save cannot revive old entities. */
    assert(save_backend_write(&backend,&g)); /* Replace corrupted sidecar. */
    Game newer=g;
    newer.screen=STATE_SHOP;
    newer.save.orbs+=17;
    assert(game_save(&newer,backend.active));
    reload(&backend,&loaded);
    assert(loaded.screen==STATE_SHOP && loaded.save.orbs==newer.save.orbs);
    /* Full Pokemon storage must resume at the exact unresolved choice, not
     * silently award a capture or discard the existing six Pokemon. */
    game_new(&g,91);
    g.screen=STATE_REPLACE;
    g.save.pending_count=MAX_CAUGHT;
    for(int i=0;i<MAX_CAUGHT;i++)g.save.pending[i]=(uint8_t)i;
    g.replace_kind=REPLACE_POKEMON;
    g.replace_value=8;
    g.replace_selected=2;
    g.session_species=8;
    assert(save_backend_write(&backend,&g));
    reload(&backend,&loaded);
    assert(loaded.screen==STATE_REPLACE);
    assert(loaded.replace_kind==REPLACE_POKEMON);
    assert(loaded.replace_value==8 && loaded.replace_selected==2);
    assert(loaded.save.pending_count==MAX_CAUGHT);
    assert(loaded.save.pending[2]==2);
    assert(game_replace_pending(&loaded,2));
    assert(loaded.screen==STATE_RESULTS && loaded.save.pending[2]==8);
    assert(save_backend_write(&backend,&loaded));
    reload(&backend,&g);
    assert(g.screen==STATE_RESULTS && g.save.pending[2]==8);
    assert(g.session_caught==8 && g.session_species==8);
    /* Corrupt but checksummed result claims cannot display a reward absent
     * from the authoritative save after restart. No private assets needed. */
    Game valid_results=g;
    for(int invalid=0;invalid<6;invalid++) {
        Game malformed=valid_results;
        switch(invalid) {
            case 0: malformed.session_caught=26;break;
            case 1: malformed.session_caught=-5;break;
            case 2: malformed.session_caught=7;break;
            case 3: malformed.session_caught=-2;malformed.session_item=-1;break;
            case 4: malformed.session_caught=-2;malformed.session_item=0;break;
            case 5: malformed.save.pending[2]=7;break;
        }
        assert(save_backend_write(&backend,&malformed));
        reload(&backend,&loaded);
        assert(loaded.screen==STATE_EXTENSIONS);
    }
    assert(save_backend_write(&backend,&valid_results));
    reload(&backend,&loaded);
    assert(loaded.screen==STATE_RESULTS && loaded.session_caught==8);
    assert(loaded.save.pending[2]==8);
    g=loaded;

    /* A malformed but internally checksummed runtime prompt must not trap
     * the user in an unfinishable replacement screen after reboot. */
    g.screen=STATE_REPLACE;
    g.replace_kind=REPLACE_NONE;
    assert(save_backend_write(&backend,&g));
    reload(&backend,&loaded);
    assert(loaded.screen==STATE_LAB);
    assert(loaded.save.pending[2]==8);

    /* A sphere with no remaining capture time cannot be resumed. */
    g.screen=STATE_SPHERE;
    g.replace_kind=REPLACE_NONE;
    g.capture_timeout=0;
    assert(save_backend_write(&backend,&g));
    reload(&backend,&loaded);
    assert(loaded.screen==STATE_EXTENSIONS);
    assert(loaded.save.pending[2]==8);

    /* Launcher-adjacent save migration must also migrate an in-flight
     * session, both from a healthy legacy primary and from its .bak pair.
     * No Dream Orbs may be charged twice when the migrated hunt resumes. */
    for(int from_backup=0;from_backup<2;from_backup++) {
        char migration_root[]="/tmp/dr_radar_legacy_XXXXXX";
        assert(mkdtemp(migration_root));
        char migration_rom[TW_MAX_PATH];
        assert(snprintf(migration_rom,sizeof migration_rom,
                        "%s/DreamRadarDSi.nds",migration_root)<(int)sizeof migration_rom);
        SaveBackend migration;
        assert(save_backend_init(&migration,migration_root,migration_rom));
        assert(migration.using_twilight_path);
        SaveBackend old_writer=migration;
        strcpy(old_writer.active,migration.legacy);
        Game old_session;
        game_new(&old_session,73);
        old_session.save.orbs=1000;
        old_session.save.total_orbs=1000;
        old_session.save.story_phase=1;
        old_session.save.cloud_count=2;
        game_begin_search(&old_session,EXT_DOWSING);
        assert(old_session.screen==STATE_RADAR && old_session.save.orbs==900);
        old_session.aim_x=97;
        assert(save_backend_write(&old_writer,&old_session));
        if(from_backup) {
            old_session.aim_x=155;
            assert(save_backend_write(&old_writer,&old_session));
            FILE *damaged=fopen(old_writer.active,"r+b");
            assert(damaged && fputc('X',damaged)!=EOF && fclose(damaged)==0);
        }
        Game migrated;
        game_new(&migrated,12);
        assert(save_backend_load(&migration,&migrated));
        assert(migration.migrated_legacy && migrated.requested_save);
        assert(migrated.screen==STATE_RADAR && migrated.aim_x==97);
        assert(migrated.active_clouds==2 && migrated.save.orbs==900);
        assert(migrated.save.searches==0);
        assert(save_backend_write(&migration,&migrated));
        Game reread;
        game_new(&reread,13);
        assert(save_backend_load(&migration,&reread));
        assert(!migration.migrated_legacy);
        assert(reread.screen==STATE_RADAR && reread.aim_x==97);
        assert(reread.active_clouds==2 && reread.save.orbs==900);
        assert(reread.save.searches==0);
    }

    puts("PASS: radar/sphere/results/replacement resume, exactly-once rewards, invalid checkpoint fallback");
    return 0;
}
