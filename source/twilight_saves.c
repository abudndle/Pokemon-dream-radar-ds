#include "twilight_saves.h"
#include <ctype.h>
#include <dirent.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>

static int eql_ci(const char *a, const char *b) {
    while (*a && *b) {
        if (tolower((unsigned char)*a) != tolower((unsigned char)*b)) return 0;
        a++; b++;
    }
    return *a==0 && *b==0;
}
static const char *file_ext(const char *name) {
    const char *dot=strrchr(name,'.');
    const char *sep=strrchr(name,'/');
    return dot && (!sep || dot>sep) ? dot : "";
}
int twilight_is_supported_rom(const char *name) {
    const char *ext=file_ext(name);
    return eql_ci(ext,".nds") || eql_ci(ext,".dsi") || eql_ci(ext,".srl") || eql_ci(ext,".app");
}
/* A ROM's four-byte game code is at 0x0c, NOT at the start of a .sav file. */
int twilight_read_nds_code(const char *path, char out[5]) {
    FILE *f=fopen(path,"rb");
    if (!f) return 0;
    if (fseek(f,12,SEEK_SET)!=0 || fread(out,1,4,f)!=4) {fclose(f);return 0;}
    fclose(f);
    out[4]=0;
    for (int i=0;i<4;i++)
        if (!isalnum((unsigned char)out[i])) return 0;
    return game_identify_cart(out)!=GAME_UNKNOWN;
}
static int join(char *out,size_t cap,const char *dir,const char *name) {
    size_t n=strlen(dir);
    return snprintf(out,cap,"%s%s%s",dir,(n && dir[n-1]=='/')?"":"/",name)>0 &&
           strlen(out)<cap-1;
}
/* snprintf truncation must not turn two distinct files into the same path. */
static int safe_join(char *out,size_t cap,const char *dir,const char *name) {
    size_t d=strlen(dir), f=strlen(name), extra=(d && dir[d-1]=='/')?0:1;
    if (d+extra+f+1>cap)return 0;
    return join(out,cap,dir,name);
}
int twilight_homebrew_save_path(const char *rom_path, char *out, size_t cap) {
    if(!rom_path || !out || !twilight_is_supported_rom(rom_path))return 0;
    const char *slash=strrchr(rom_path,'/');
    const char *dot=strrchr(rom_path,'.');
    if(!slash || !dot || dot<slash || dot==slash+1)return 0;
    size_t folder=(size_t)(slash-rom_path);
    size_t basename=(size_t)(dot-(slash+1));
    /* The ROM's base name is included so that multiple homebrew apps cannot collide.
       No basename may be 'Pokemon Black 2' unless the *homebrew ROM* is named that;
       the dedicated suffix below prevents collisions in that case too. */
    const char *suffix=".dreamradar.sav";
    size_t needed=folder+strlen("/saves/")+basename+strlen(suffix)+1;
    if(needed>cap)return 0;
    memcpy(out,rom_path,folder);out[folder]=0;
    strcat(out,"/saves/");
    strncat(out,slash+1,basename);
    strcat(out,suffix);
    return 1;
}
static int save_file_size(const char *path, uint32_t *size) {
    struct stat st;
    if(stat(path,&st)!=0 || !S_ISREG(st.st_mode))return 0;
    /* Avoid accepting empty/dummy files or massive unrelated files as saves.
       This checks plausible size only, NOT a Pokémon save's integrity. */
    if(st.st_size<65536 || st.st_size>8*1024*1024)return 0;
    *size=(uint32_t)st.st_size;
    return 1;
}
/* A lightweight read-only sample fingerprint for selected retail saves.
 * Not a complete integrity check and not a replacement for real save parsing. */
static int save_sample_fingerprint(const char *path,uint32_t size,uint32_t *out) {
    FILE *f=fopen(path,"rb");if(!f)return 0;
    uint32_t h=2166136261u;
    unsigned char sample[32];
    long offsets[]={0,(long)size/2-16,(long)size-32};
    int ok=1;
    for(unsigned i=0;i<3;i++) {
        if(fseek(f,offsets[i],SEEK_SET)!=0 || fread(sample,1,sizeof sample,f)!=sizeof sample) {
            ok=0;break;
        }
        for(unsigned j=0;j<sizeof sample;j++) h=(h ^ sample[j])*16777619u;
    }
    if(fclose(f)!=0)ok=0;
    if(ok)*out=h;
    return ok;
}
static void check_save(TwilightSaveEntry *entry,const char *dir,
                       const char *base,TwilightSaveLocation kind) {
    char path[TW_MAX_PATH];uint32_t size;
    if(!safe_join(path,sizeof path,dir,base))return;
    uint32_t fingerprint;
    if(save_file_size(path,&size) && save_sample_fingerprint(path,size,&fingerprint)) {
        entry->save_fingerprint=fingerprint;
        strncpy(entry->save_path,path,sizeof(entry->save_path)-1);
        entry->save_path[sizeof(entry->save_path)-1]=0;
        entry->save_size=size;entry->location=kind;
    }
}
/* Do not trust scanner output after the SD card or files change. */
int twilight_validate_entry(const TwilightSaveEntry *entry) {
    if(!entry || entry->game == GAME_UNKNOWN)return 0;
    char code[5]; uint32_t size;
    if(!twilight_read_nds_code(entry->rom_path,code) ||
       memcmp(code,entry->game_code,4)!=0 ||
       game_identify_cart(code)!=entry->game)return 0;
    /* ROM-only identification is valid for an extension unlock; never write a save. */
    if(entry->location==TW_SAVE_NONE)return 1;
    if(!save_file_size(entry->save_path,&size) || size!=entry->save_size)return 0;
    uint32_t fingerprint;
    if(!save_sample_fingerprint(entry->save_path,size,&fingerprint) ||
       fingerprint!=entry->save_fingerprint)return 0;
    return 1;
}
static void scan_one_dir(TwilightSaveIndex *idx,const char *root,const char *directory) {
    DIR *dp=opendir(directory);
    if(!dp)return;
    idx->dirs_scanned++;
    struct dirent *ent;
    while((ent=readdir(dp))) {
        if(!twilight_is_supported_rom(ent->d_name))continue;
        if(idx->count>=TW_MAX_ENTRIES){idx->truncated=1;break;}
        char rom_path[TW_MAX_PATH],code[5];
        if(!safe_join(rom_path,sizeof rom_path,directory,ent->d_name))continue;
        struct stat st;
        if(stat(rom_path,&st)!=0 || !S_ISREG(st.st_mode) || st.st_size<512)continue;
        if(!twilight_read_nds_code(rom_path,code))continue;
        /* The same launcher directory may be included in the search roots. */
        int seen=0;
        for(unsigned i=0;i<idx->count;i++)
            if(strcmp(idx->entries[i].rom_path,rom_path)==0){seen=1;break;}
        if(seen)continue;
        size_t len=strlen(ent->d_name), ext=strlen(file_ext(ent->d_name));
        if(len<=ext || len-ext+7>=256)continue;
        char sibling_saves[TW_MAX_PATH],global_saves[TW_MAX_PATH];
        int have_sibling=safe_join(sibling_saves,sizeof sibling_saves,directory,"saves");
        int have_global=safe_join(global_saves,sizeof global_saves,root,"_nds/TWiLightMenu/saves");
        unsigned found=0;
        for(unsigned slot=0;slot<10;slot++) {
            char savename[256];
            memcpy(savename,ent->d_name,len-ext);
            int suffix=snprintf(savename+len-ext,sizeof savename-(len-ext),
                                slot==0?".sav":".sav%u",slot);
            if(suffix<=0 || len-ext+(size_t)suffix>=sizeof savename)continue;
            TwilightSaveEntry e={0};
            strcpy(e.rom_path,rom_path);
            memcpy(e.game_code,code,5);
            e.game=game_identify_cart(code);
            e.save_slot=(uint8_t)slot;
            if(have_sibling)check_save(&e,sibling_saves,savename,TW_SAVE_NEXT_TO_ROM);
            if(!e.location)check_save(&e,directory,savename,TW_SAVE_GAME_FOLDER);
            if(!e.location && have_global)check_save(&e,global_saves,savename,TW_SAVE_TWLMENU_FOLDER);
            if(!e.location)continue;
            if(idx->count>=TW_MAX_ENTRIES){idx->truncated=1;break;}
            idx->entries[idx->count++]=e;
            idx->with_saves++;
            found++;
        }
        if(!found && idx->count<TW_MAX_ENTRIES) {
            TwilightSaveEntry e={0};
            strcpy(e.rom_path,rom_path);
            memcpy(e.game_code,code,5);
            e.game=game_identify_cart(code);
            idx->entries[idx->count++]=e;
        }
        if(idx->truncated)break;
    }
    closedir(dp);
}

void twilight_scan(TwilightSaveIndex *idx,const char *root,const char *rom_dir) {
    memset(idx,0,sizeof *idx);
    if(!root || !root[0])return;
    char path[TW_MAX_PATH];
    if(rom_dir && rom_dir[0])scan_one_dir(idx,root,rom_dir);
    const char *dirs[]={"roms/nds","roms","games","nds",""};
    for(size_t i=0;i<sizeof dirs/sizeof *dirs;i++) {
        if(dirs[i][0]) {
            if(!safe_join(path,sizeof path,root,dirs[i]))continue;
        } else {
            if(strlen(root)>=sizeof path)continue;
            strcpy(path,root);
        }
        scan_one_dir(idx,root,path);
    }
}
