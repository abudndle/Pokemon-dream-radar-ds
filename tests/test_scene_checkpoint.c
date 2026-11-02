#include "game.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <unistd.h>

/* Private save v3 scene checkpoints. This is host logic, not melonDS QA.
 * Transient radar/sphere/results sessions intentionally reopen Extensions:
 * full in-flight encounter serialization is a separate milestone. */
static void roundtrip(const char *path,GameScreen before,GameScreen expected) {
    Game g,restored;
    game_new(&g,37);
    g.save.intro_seen=1;
    g.save.orbs=456;
    g.save.pending_count=1;
    g.save.pending[0]=3;
    g.screen=before;
    g.ext_selection=EXT_DOWSING;
    g.page=3;
    uint32_t old_checksum=g.save.checksum;
    assert(game_save(&g,path));
    assert(g.save.checksum==old_checksum);
    assert(g.save.reserved[16]==0); /* Serialization never mutates live save. */
    struct stat st;
    assert(stat(path,&st)==0 && st.st_size==(off_t)sizeof(SaveData));
    game_new(&restored,1);
    assert(game_load(&restored,path));
    assert(restored.screen==expected);
    assert(restored.save.orbs==456);
    assert(restored.save.pending_count==1 && restored.save.pending[0]==3);
    assert(restored.ext_selection==EXT_DOWSING);
    assert(restored.page==3);
    assert(restored.save.reserved[16]==SAVE_UI_CHECKPOINT_MARKER);
    assert(restored.save.reserved[17]==(uint8_t)before);
    if(before==STATE_RADAR || before==STATE_SPHERE || before==STATE_RESULTS)
        assert(restored.requested_save); /* Replace unsafe checkpoint. */
}
int main(void) {
    char path[]="/tmp/dr_scene_checkpoint_XXXXXX";
    int fd=mkstemp(path);
    assert(fd>=0 && close(fd)==0);
    const GameScreen stable[]={
        STATE_TITLE,STATE_LAB,STATE_SHOP,STATE_EXTENSIONS,STATE_RECORDS,
        STATE_TRANSFER,STATE_SETTINGS,STATE_STORAGE,STATE_TIPS,
        STATE_ALBUM,STATE_CREDITS,STATE_PLACEHOLDER
    };
    for(unsigned i=0;i<sizeof stable/sizeof stable[0];i++)
        roundtrip(path,stable[i],stable[i]);
    roundtrip(path,STATE_RADAR,STATE_EXTENSIONS);
    roundtrip(path,STATE_SPHERE,STATE_EXTENSIONS);
    roundtrip(path,STATE_RESULTS,STATE_EXTENSIONS);
    roundtrip(path,STATE_REPLACE,STATE_LAB);
    roundtrip(path,STATE_DIALOGUE,STATE_LAB);
    roundtrip(path,STATE_CAMERA_QUICK,STATE_LAB);
    roundtrip(path,STATE_SD_SAVES,STATE_SETTINGS);
    roundtrip(path,(GameScreen)250,STATE_TITLE);

    Game g,restored;
    game_new(&g,99);
    g.screen=STATE_INTRO;
    assert(game_save(&g,path));
    game_new(&restored,1);
    assert(game_load(&restored,path) && restored.screen==STATE_INTRO);
    g.save.intro_seen=1;
    assert(game_save(&g,path));
    game_new(&restored,1);
    assert(game_load(&restored,path) && restored.screen==STATE_LAB);

    /* Legacy v3 save: no UI marker means the original title default. */
    game_new(&g,101);
    g.save.orbs=901;
    g.save.checksum=game_checksum(&g.save);
    FILE *f=fopen(path,"wb");
    assert(f && fwrite(&g.save,1,sizeof g.save,f)==sizeof g.save);
    assert(fclose(f)==0);
    game_new(&restored,1);
    assert(game_load(&restored,path));
    assert(restored.screen==STATE_TITLE && restored.save.orbs==901);
    assert(unlink(path)==0);
    puts("PASS: safe screen checkpoints, transient fallback, legacy v3 compatibility");
    return 0;
}
