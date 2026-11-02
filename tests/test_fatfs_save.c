/* Model FatFs rename semantics: an existing destination is never replaced.
 * This test uses the real game_save() and game_load() APIs with a host linker
 * wrapper, so a Linux-only POSIX rename implementation cannot hide failures.
 */
#include "game.h"
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <unistd.h>

extern int __real_rename(const char *source, const char *destination);

int __wrap_rename(const char *source, const char *destination) {
    if(access(destination,F_OK)==0) {
        errno=EEXIST;
        return -1;
    }
    return __real_rename(source,destination);
}

int main(void) {
    char dir[]="/tmp/dr_fat_save_XXXXXX";
    assert(mkdtemp(dir));
    char path[256],backup[256];
    assert(snprintf(path,sizeof path,"%s/progress.sav",dir)<(int)sizeof path);
    assert(snprintf(backup,sizeof backup,"%s.bak",path)<(int)sizeof backup);
    Game g,loaded;
    game_new(&g,19);
    g.save.orbs=11;
    assert(game_save(&g,path));
    g.save.orbs=42;
    assert(game_save(&g,path)); /* Must not rename over an existing target. */
    game_new(&loaded,22);
    assert(game_load(&loaded,path));
    assert(loaded.save.orbs==42);
    /* Last committed state remains recoverable under a second write. */
    game_new(&loaded,24);
    assert(game_load(&loaded,backup));
    assert(loaded.save.orbs==11);
    g.save.orbs=99;
    assert(game_save(&g,path));
    game_new(&loaded,25);
    assert(game_load(&loaded,path));
    assert(loaded.save.orbs==99);
    assert(game_load(&loaded,backup));
    assert(loaded.save.orbs==42);
    assert(unlink(path)==0);
    assert(unlink(backup)==0);
    assert(rmdir(dir)==0);
    puts("PASS: repeated Dream Radar saves rotate FAT-compatible backups");
    return 0;
}
