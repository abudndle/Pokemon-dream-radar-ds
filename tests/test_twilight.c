/* Host test of multiple discovered saves and exactly ONE selected active game.
 * Retail save files are read-only. */
#include "game.h"
#include "twilight_saves.h"
#include "save_backend.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

static void path(char *dst, size_t n, const char *dir, const char *part) {
    assert(snprintf(dst,n,"%s/%s",dir,part) < (int)n);
}
static void make_rom(const char *filename, const char *id) {
    unsigned char h[512]={0};memcpy(h+12,id,4);
    FILE *f=fopen(filename,"wb");assert(f);
    assert(fwrite(h,1,sizeof h,f)==sizeof h);assert(!fclose(f));
}
static void make_save(const char *filename) {
    FILE *f=fopen(filename,"wb");assert(f);
    assert(fseek(f,524287,SEEK_SET)==0);assert(fputc(0xa5,f)!=EOF);assert(!fclose(f));
}
int main(void) {
    char root[]="/tmp/dr_twilight_XXXXXX";assert(mkdtemp(root));
    char roms[TW_MAX_PATH],saves[TW_MAX_PATH],p[TW_MAX_PATH];
    path(roms,sizeof roms,root,"roms");assert(!mkdir(roms,0700));
    path(p,sizeof p,roms,"nds");assert(!mkdir(p,0700));strcpy(roms,p);
    path(saves,sizeof saves,roms,"saves");assert(!mkdir(saves,0700));
    path(p,sizeof p,roms,"Diamond.nds");make_rom(p,"ADAE");
    path(p,sizeof p,saves,"Diamond.sav");make_save(p);
    path(p,sizeof p,saves,"Diamond.sav1");make_save(p);
    path(p,sizeof p,saves,"Diamond.sav2");make_save(p);
    path(p,sizeof p,roms,"SoulSilver.nds");make_rom(p,"IPGE");
    path(p,sizeof p,saves,"SoulSilver.sav");make_save(p);

    TwilightSaveIndex idx;twilight_scan(&idx,root,roms);
    assert(idx.count==4 && idx.with_saves==4);
    for(unsigned i=0;i<idx.count;i++) {
        assert(idx.entries[i].location);
        assert(twilight_validate_entry(&idx.entries[i]));
    }
    unsigned diamond_slots=0;
    for(unsigned i=0;i<idx.count;i++)
        if(idx.entries[i].game==GAME_DIAMOND)
            diamond_slots |= 1u<<idx.entries[i].save_slot;
    assert(diamond_slots==0x7u);
    Game g;game_new(&g,11);g.save.story_phase=3;
    const TwilightSaveEntry *diamond=NULL,*silver=NULL;
    for(unsigned i=0;i<idx.count;i++) {
        if(idx.entries[i].game==GAME_DIAMOND)diamond=&idx.entries[i];
        if(idx.entries[i].game==GAME_SOULSILVER)silver=&idx.entries[i];
    }
    assert(diamond && silver);
    game_set_cart_source(&g,diamond->game,CART_SOURCE_TWILIGHT_SD);
    assert(g.cart==GAME_DIAMOND);
    assert(game_extension_unlocked(&g,EXT_DIALGA));
    assert(!game_extension_unlocked(&g,EXT_LUGIA));
    game_set_cart_source(&g,silver->game,CART_SOURCE_TWILIGHT_SD);
    assert(g.cart==GAME_SOULSILVER);
    assert(game_extension_unlocked(&g,EXT_LUGIA));
    assert(!game_extension_unlocked(&g,EXT_DIALGA));
    game_set_cart(&g,GAME_PEARL);
    assert(g.cart_source==CART_SOURCE_SLOT1 && g.cart==GAME_PEARL);
    assert(!game_extension_unlocked(&g,EXT_LUGIA));

    char homebrew[TW_MAX_PATH],savepath[TW_MAX_PATH];
    path(homebrew,sizeof homebrew,roms,"DreamRadarDSi.nds");
    assert(twilight_homebrew_save_path(homebrew,savepath,sizeof savepath));
    assert(strstr(savepath,"DreamRadarDSi.dreamradar.sav"));
    assert(!strstr(savepath,"Diamond.sav"));
    SaveBackend b;assert(save_backend_init(&b,root,homebrew));
    assert(b.using_twilight_path);
    assert(!strcmp(b.active,savepath));
    assert(save_backend_write(&b,&g));
    Game loaded;game_new(&loaded,22);
    assert(save_backend_load(&b,&loaded));
    assert(loaded.save.story_phase==3);
    /* Active card selection is never persisted as an inserted cartridge. */
    assert(loaded.cart==GAME_UNKNOWN && loaded.cart_source==CART_SOURCE_NONE);
    path(p,sizeof p,saves,"Diamond.sav");
    struct stat st;assert(!stat(p,&st) && st.st_size==524288);
    FILE *f=fopen(p,"rb");assert(f);assert(fseek(f,-1,SEEK_END)==0);assert(fgetc(f)==0xa5);fclose(f);
    /* ROM identification must not require a save. */
    char pearlrom[TW_MAX_PATH];path(pearlrom,sizeof pearlrom,roms,"Pearl.nds");
    make_rom(pearlrom,"APAE");
    TwilightSaveIndex romonly;twilight_scan(&romonly,root,roms);
    const TwilightSaveEntry *pearl=NULL;
    for(unsigned i=0;i<romonly.count;i++)
        if(romonly.entries[i].game==GAME_PEARL)pearl=&romonly.entries[i];
    assert(pearl && pearl->location==TW_SAVE_NONE && twilight_validate_entry(pearl));
    /* Never activate a save entry after its ROM or save has been replaced. */
    TwilightSaveEntry stale=*diamond;
    assert(twilight_validate_entry(&stale));
    f=fopen(stale.rom_path,"r+b");assert(f);
    assert(!fseek(f,12,SEEK_SET));assert(fwrite("APAE",1,4,f)==4);assert(!fclose(f));
    assert(!twilight_validate_entry(&stale));
    /* Identically sized save replacement must not validate just by length. */
    TwilightSaveEntry changed=*silver;
    assert(twilight_validate_entry(&changed));
    f=fopen(changed.save_path,"r+b");assert(f);
    assert(fseek(f,262144,SEEK_SET)==0);
    assert(fputc(0xA1,f)!=EOF);assert(!fclose(f));
    assert(!twilight_validate_entry(&changed));
    puts("PASS: numbered slots, single active game, read-only saves, ROM/save stale checks");
    return 0;
}
