/* The original Dream Radar keeps legends separate and transfers them first.
 * All exports in this port remain private text archives, NEVER retail Link.
 */
#include "game.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static void archive(Game *g,const char *path) {
    assert(game_export(g,path));
    assert(g->pending_export_signature);
    assert(game_release_archived_pending(g));
}

int main(void) {
    char path[]="/tmp/dr-special-research-XXXXXX";
    int fd=mkstemp(path);assert(fd>=0 && close(fd)==0);
    Game g;game_new(&g,17);
    assert(g.save.version==SAVE_VERSION && g.save.reserved[15]==LEGEND_STORAGE_MARKER);
    assert(!game_legendary_count(&g));
    assert(game_legendary_at(&g,0)==-1);
    assert(game_transfer_species(&g,0)==-1);
    g.save.pending_count=6;
    for(int i=0;i<6;i++)g.save.pending[i]=(uint8_t)i;
    g.save.reserved[14]=0xFF; /* all eight legendary slots occupied */
    assert(game_legendary_count(&g)==8);
    assert(game_transfer_count(&g)==6);
    for(int i=0;i<8;i++)assert(game_legendary_at(&g,i)==15+i);
    for(int i=0;i<6;i++)assert(game_transfer_species(&g,i)==15+i);
    assert(game_transfer_species(&g,-1)==-1);
    assert(game_transfer_species(&g,6)==-1);
    g.save.pending_items[0]=3;
    assert(game_export(&g,path));
    FILE *f=fopen(path,"rb");assert(f);
    char buf[2048]={0};
    assert(fread(buf,1,sizeof buf-1,f)>100 && fclose(f)==0);
    assert(strstr(buf,"Pokemon 1: Tornadus"));
    assert(strstr(buf,"Pokemon 6: Giratina"));
    assert(!strstr(buf,"Pokemon 7:"));
    assert(strstr(buf,"Retained for the next archive: 8 Pokemon"));
    assert(game_release_archived_pending(&g));
    assert(g.save.reserved[14]==0xC0);
    assert(g.save.pending_count==6 && g.save.pending[0]==0);
    assert(g.save.pending_items[0]==0);
    assert(!game_release_archived_pending(&g));
    assert(game_transfer_count(&g)==6);
    assert(game_transfer_species(&g,0)==21);
    assert(game_transfer_species(&g,1)==22);
    for(int i=0;i<4;i++)assert(game_transfer_species(&g,i+2)==i);
    archive(&g,path);
    assert(game_legendary_count(&g)==0);
    assert(g.save.pending_count==2);
    assert(g.save.pending[0]==4 && g.save.pending[1]==5);
    archive(&g,path);
    assert(g.save.pending_count==0 && !g.save.reserved[14]);
    assert(!game_export(NULL,path));
    assert(!game_release_archived_pending(&g));

    /* Legacy version-3 saves had legendary species in the ordinary queue.
       Migrate without changing the structure size or previous progress. */
    Game legacy;game_new(&legacy,99);
    legacy.save.reserved[15]=0;
    legacy.save.pending_count=5;
    const uint8_t old[]={1,15,18,2,22};
    memcpy(legacy.save.pending,old,sizeof old);
    legacy.save.story_phase=1;
    legacy.save.legends_caught=1;
    legacy.save.caught_count=3;
    legacy.save.checksum=game_checksum(&legacy.save);
    f=fopen(path,"wb");assert(f);
    assert(fwrite(&legacy.save,1,sizeof legacy.save,f)==sizeof legacy.save);
    assert(fclose(f)==0);
    Game restored;game_new(&restored,8);
    assert(game_load(&restored,path));
    assert(restored.requested_save);
    assert(restored.save.pending_count==2);
    assert(restored.save.pending[0]==1 && restored.save.pending[1]==2);
    assert(game_legendary_count(&restored)==3);
    assert(game_legendary_at(&restored,0)==15);
    assert(game_legendary_at(&restored,1)==18);
    assert(game_legendary_at(&restored,2)==22);
    assert(restored.save.caught_count==3 && restored.save.story_phase==1);
    assert(game_save(&restored,path));
    Game again;game_new(&again,77);
    assert(game_load(&again,path));
    assert(!again.requested_save);
    assert(again.save.reserved[15]==LEGEND_STORAGE_MARKER);
    assert(game_legendary_count(&again)==3);
    /* A malformed mixed layout must never overwrite an existing save. */
    again.save.pending[0]=15;
    assert(!game_save(&again,path));
    assert(!game_export(&again,path));
    again.save.pending[0]=1;
    again.screen=STATE_SPHERE;
    again.capture_timeout=100;
    again.session_type=0;
    again.session_species=15;
    unsigned count=again.save.caught_count;
    game_capture(&again);
    assert(again.screen==STATE_RESULTS && again.session_caught==-4);
    assert(game_legendary_count(&again)==3 && again.save.caught_count==count);
    assert(unlink(path)==0);
    puts("PASS: eight special legendary slots, six-per-archive priority, carry-over and v3 migration");
    return 0;
}
