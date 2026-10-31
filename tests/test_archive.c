/* Homebrew export is a text-only archive, NOT a Black 2 / White 2 transfer. */
#include "game.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main(void) {
    Game g;game_new(&g,42);
    g.save.story_phase=3;
    g.save.pending_count=2;
    g.save.pending[0]=18;  /* Dialga */
    g.save.pending[1]=22;  /* Lugia */
    g.save.legends_caught=(1<<0)|(1<<4);
    g.save.pending_items[2]=3;
    assert(!game_release_archived_pending(&g));
    assert(!game_export(&g,"/path-that-does-not-exist/export.txt"));
    assert(g.save.pending_count==2);

    char filename[]="/tmp/dr_archive_XXXXXX";
    int fd=mkstemp(filename);assert(fd>=0);close(fd);
    assert(game_export(&g,filename));
    assert(g.pending_export_signature!=0);
    FILE *f=fopen(filename,"rb");assert(f);
    char text[2048]={0};assert(fread(text,1,sizeof(text)-1,f)>80);fclose(f);
    assert(strstr(text,"not compatible with Unova Link"));
    assert(strstr(text,"Dialga") && strstr(text,"Lugia"));
    /* Queue changes AFTER archive invalidate the one-click release. */
    g.save.pending[1]=21;
    assert(!game_release_archived_pending(&g));
    assert(g.save.pending_count==2);
    assert(game_export(&g,filename));
    assert(game_release_archived_pending(&g));
    assert(g.save.pending_count==0 && g.save.pending_items[2]==0);
    assert(g.save.story_phase==3 && g.save.legends_caught==((1<<0)|(1<<4)));
    assert(g.requested_save && !game_release_archived_pending(&g));

    /* Failed replacement must leave the previous valid archive untouched.
       A directory destination permits staging, but rename must fail. */
    char badpath[]="/tmp/dr_export_directory_XXXXXX";
    assert(mkdtemp(badpath));
    Game blocked;game_new(&blocked,17);
    blocked.save.pending_count=1;blocked.save.pending[0]=18;
    assert(!game_export(&blocked,badpath));
    assert(blocked.pending_export_signature==0);
    char leftover[512];snprintf(leftover,sizeof leftover,"%s.tmp",badpath);
    assert(access(leftover,F_OK)!=0);
    assert(rmdir(badpath)==0);
    /* Existing staging files belong to their creator and must not be
       truncated or removed by our export routine. */
    char existing[512];snprintf(existing,sizeof existing,"%s.tmp",filename);
    FILE *guard=fopen(existing,"wb");assert(guard);
    assert(fputs("KEEP-ME",guard)>=0);assert(fclose(guard)==0);
    assert(!game_export(&blocked,filename));
    guard=fopen(existing,"rb");assert(guard);
    char preserved[16]={0};
    assert(fread(preserved,1,7,guard)==7);fclose(guard);
    assert(strcmp(preserved,"KEEP-ME")==0);
    assert(unlink(existing)==0);
    /* Rejected paths also never authorize releasing the queue. */
    assert(!game_export(&blocked,"/not-real-parent/dr_export.txt"));
    assert(!game_release_archived_pending(&blocked));

    /* Secret extensions are stored in previously reserved save bytes. */
    Game secret;game_new(&secret,1);
    const int input[]={6,5,7,4,3,9,8};
    for(unsigned i=0;i<sizeof(input)/sizeof(input[0]);i++)game_secret_key(&secret,input[i]);
    assert(game_extension_unlocked(&secret,EXT_BELDUM));
    assert(secret.save.reserved[1]&1);
    assert(game_save(&secret,filename));
    Game reloaded;game_new(&reloaded,2);
    assert(game_load(&reloaded,filename));
    assert(game_extension_unlocked(&reloaded,EXT_BELDUM));
    unlink(filename);
    puts("PASS: text archive export/explicit release, stale-archive protection, durable secret unlock");
    return 0;
}
