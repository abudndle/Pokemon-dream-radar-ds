#include "game.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

/* Verify that gameplay rewards survive the on-disk private save format. */
int main(void) {
    char path[]="/tmp/dr_progress_XXXXXX";
    int fd=mkstemp(path);
    assert(fd>=0);
    assert(close(fd)==0);
    Game g, loaded;
    game_new(&g,13579);
    g.screen=STATE_SPHERE;
    g.capture_timeout=100;
    g.session_type=0;
    g.session_species=15;
    g.ext_selection=EXT_TORNADUS;
    game_capture(&g);
    assert(g.screen==STATE_RESULTS && g.save.story_phase==1);
    g.screen=STATE_SPHERE;
    g.capture_timeout=100;
    g.session_type=1;
    g.session_item=7;
    g.ext_selection=EXT_RETRIEVAL;
    game_capture(&g);
    assert(g.screen==STATE_RESULTS);
    assert(g.save.pending_count==1 && g.save.pending[0]==15);
    assert(g.save.pending_items[0]==1);
    assert(game_item_slot_kind(&g,0)==7);
    uint32_t searches=g.save.searches;
    assert(game_save(&g,path));
    game_new(&loaded,98765);
    assert(game_load(&loaded,path));
    assert(loaded.save.story_phase==1);
    assert(loaded.save.caught_count==1);
    assert(loaded.save.pending_count==1 && loaded.save.pending[0]==15);
    assert(loaded.save.pending_items[0]==1);
    assert(game_item_slot_kind(&loaded,0)==7);
    assert(loaded.save.searches==searches);
    assert(loaded.save.reserved[8]==ITEM_LAYOUT_MARKER);
    /* Invalid runtime state cannot truncate previously valid progress. */
    Game invalid=g;
    invalid.save.pending_count=MAX_CAUGHT+1;
    assert(!game_save(&invalid,path));
    invalid=g;
    invalid.save.pending_items[0]=1;
    invalid.save.reserved[2]=0;
    assert(!game_save(&invalid,path));
    /* Reject every invalid header/settings flag that the loader rejects.
       Each rejected write must leave the previous valid file in place. */
    for(int field=0;field<7;field++) {
        invalid=g;
        switch(field) {
            case 0: invalid.save.magic=0;break;
            case 1: invalid.save.version=SAVE_VERSION+1;break;
            case 2: invalid.save.intro_seen=2;break;
            case 3: invalid.save.optical_aim=2;break;
            case 4: invalid.save.camera_enabled=2;break;
            case 5: invalid.save.reserved[0]=4;break;
            case 6: invalid.save.reserved[1]=8;break;
        }
        assert(!game_save(&invalid,path));
    }
    game_new(&loaded,98765);
    assert(game_load(&loaded,path));
    assert(loaded.save.pending_count==1 && loaded.save.pending[0]==15);
    assert(game_item_slot_kind(&loaded,0)==7);
    /* Corrupt the stored Pokémon ID without updating its checksum.
       A second load must reject it and leave a fresh game unchanged. */
    FILE *corrupt=fopen(path,"r+b");
    assert(corrupt);
    assert(fseek(corrupt,(long)offsetof(SaveData,pending),SEEK_SET)==0);
    int old=fgetc(corrupt);
    assert(old!=EOF);
    assert(fseek(corrupt,-1L,SEEK_CUR)==0);
    assert(fputc(old ^ 1,corrupt)!=EOF);
    assert(fclose(corrupt)==0);
    game_new(&loaded,24680);
    assert(!game_load(&loaded,path));
    assert(loaded.save.pending_count==0);
    assert(loaded.save.caught_count==0);
    assert(loaded.save.story_phase==0);
    assert(unlink(path)==0);
    puts("PASS: captured Pokémon, research items and progression survive save reload");
    return 0;
}
