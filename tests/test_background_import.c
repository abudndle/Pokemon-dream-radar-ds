#include "dr_background.h"
#include "photo_album.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>
#define N (DR_PHOTO_W*DR_PHOTO_H)
static uint16_t original[N], pixels[N];
static void same(const Game *game,const Game *before,
                 int loaded,int loaded_before,int slot,int slot_before,
                 uint16_t sentinel) {
    assert(memcmp(game,before,sizeof *game)==0);
    assert(loaded==loaded_before && slot==slot_before);
    assert(pixels[0]==sentinel && pixels[N-1]==sentinel);
}
int main(void) {
    char root[]="/tmp/dr-background-XXXXXX", folder[256],file[320];
    assert(mkdtemp(root));
    assert(snprintf(folder,sizeof folder,"%s/DreamRadarDSi",root)>0);
    assert(mkdir(folder,0700)==0);
    assert(snprintf(file,sizeof file,"%s/placeholder.bmp",folder)>0);
    for(int i=0;i<N;i++)original[i]=(uint16_t)(0x8000u |
                                ((unsigned)(i/8)&31u) |
                                (((unsigned)(i/256)&31u)<<5));
    Game game={0};
    game.save.camera_enabled=1;
    game.save.reserved[9]=5;
    game.save.reserved[10]=7;
    game.save.reserved[11]=0xB6;
    game.capture_timeout=77;
    game.screen=STATE_SPHERE;
    game.selection=3;
    int loaded=1,slot=5;
    const uint16_t sentinel=0xAF13;
    for(int i=0;i<N;i++)pixels[i]=sentinel;
    Game before=game;
    assert(!dr_background_import(root,pixels,N,&game,&loaded,&slot));
    same(&game,&before,loaded,1,slot,5,sentinel);
    assert(!dr_background_import(NULL,pixels,N,&game,&loaded,&slot));
    assert(!dr_background_import(root,pixels,N-1,&game,&loaded,&slot));
    same(&game,&before,loaded,1,slot,5,sentinel);

    assert(dr_photo_write(file,original,N));
    /* Marker mismatches and invalid destination are non-mutating. */
    assert(!dr_background_restore(root,pixels,N,&game,&loaded,&slot));
    assert(!dr_background_import(root,NULL,N,&game,&loaded,&slot));
    same(&game,&before,loaded,1,slot,5,sentinel);

    assert(dr_background_import(root,pixels,N,&game,&loaded,&slot));
    assert(loaded==1 && slot==-2);
    assert(game.save.reserved[9]==0 && game.save.reserved[10]==0);
    assert(game.save.reserved[11]==DR_BACKGROUND_IMPORT_MARKER);
    assert(game.save.camera_enabled==0 && game.requested_save==1);
    assert(game.screen==STATE_SPHERE && game.selection==3);
    assert(game.capture_timeout==77); /* Import must not advance gameplay. */
    for(int i=0;i<N;i++)assert(pixels[i]==original[i]);

    /* Restoring from a saved marker must not set the dirty flag or camera. */
    Game saved=game;
    saved.requested_save=0;
    for(int i=0;i<N;i++)pixels[i]=sentinel;
    loaded=0;slot=-1;
    assert(dr_background_restore(root,pixels,N,&saved,&loaded,&slot));
    assert(loaded && slot==-2 && saved.requested_save==0);
    assert(saved.save.camera_enabled==0);
    for(int i=0;i<N;i++)assert(pixels[i]==original[i]);

    /* A damaged image preserves all currently rendered pixels and state. */
    FILE *f=fopen(file,"ab");assert(f);
    assert(fputc('x',f)!=EOF && fclose(f)==0);
    for(int i=0;i<N;i++)pixels[i]=sentinel;
    before=saved;loaded=0;slot=12;
    assert(!dr_background_restore(root,pixels,N,&saved,&loaded,&slot));
    same(&saved,&before,loaded,0,slot,12,sentinel);
    assert(!dr_background_import(root,pixels,N,&saved,&loaded,&slot));
    same(&saved,&before,loaded,0,slot,12,sentinel);
    assert(remove(file)==0);

    dr_background_reset(&saved,&loaded,&slot);
    assert(!loaded && slot==-1 && saved.requested_save==1);
    assert(!saved.save.reserved[9] && !saved.save.reserved[10] &&
           !saved.save.reserved[11]);
    assert(saved.save.camera_enabled==0);
    assert(saved.capture_timeout==77);
    assert(rmdir(folder)==0 && rmdir(root)==0);
    puts("PASS: atomic camera BMP import, restore, corrupt-file rollback, reset");
    return 0;
}
