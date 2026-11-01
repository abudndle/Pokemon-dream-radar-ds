#include "dr_title_art.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

enum {PIXELS=256*192};
static uint16_t top[PIXELS], bottom[PIXELS];
static void write_raw(const char *name,uint16_t color,int trailing){
    FILE *f=fopen(name,"wb");assert(f);
    for(int i=0;i<PIXELS;i++){
        unsigned char pixel[2]={(unsigned char)color,(unsigned char)(color>>8)};
        assert(fwrite(pixel,1,2,f)==2);
    }
    if(trailing)assert(fputc(0,f)!=EOF);
    assert(fclose(f)==0);
}
int main(void){
    char root[]="/tmp/dream-radar-title-art-XXXXXX";
    assert(mkdtemp(root));
    char dir[240],ui[280],t[320],b[320];
    snprintf(dir,sizeof dir,"%s/DreamRadarDSi",root);
    snprintf(ui,sizeof ui,"%s/UI",dir);
    assert(mkdir(dir,0700)==0);assert(mkdir(ui,0700)==0);
    snprintf(t,sizeof t,"%s/title_top.raw",ui);
    snprintf(b,sizeof b,"%s/title_bottom.raw",ui);
    for(int i=0;i<PIXELS;i++){top[i]=0x8123;bottom[i]=0x8456;}
    assert(!dr_title_art_load(root,top,bottom,PIXELS));
    write_raw(t,0x9c02,0);
    assert(!dr_title_art_load(root,top,bottom,PIXELS)); /* missing bottom */
    for(int i=0;i<PIXELS;i++)assert(top[i]==0x8123 && bottom[i]==0x8456);
    write_raw(b,0x9ce1,1);
    assert(!dr_title_art_load(root,top,bottom,PIXELS)); /* trailing bytes */
    for(int i=0;i<PIXELS;i++)assert(top[i]==0x8123 && bottom[i]==0x8456);
    write_raw(b,0x0065,0);
    assert(!dr_title_art_load(root,top,bottom,PIXELS)); /* transparent */
    for(int i=0;i<PIXELS;i++)assert(top[i]==0x8123 && bottom[i]==0x8456);
    write_raw(b,0xa367,0);
    assert(dr_title_art_load(root,top,bottom,PIXELS));
    for(int i=0;i<PIXELS;i++)assert(top[i]==0x9c02 && bottom[i]==0xa367);
    write_raw(t,0x0123,0);
    assert(!dr_title_art_load(root,top,bottom,PIXELS));
    for(int i=0;i<PIXELS;i++)assert(top[i]==0x9c02 && bottom[i]==0xa367);
    assert(!dr_title_art_load(NULL,top,bottom,PIXELS));
    assert(!dr_title_art_load(root,top,bottom,PIXELS-1));
    assert(!dr_title_art_load(root,top,top,PIXELS));
    assert(remove(t)==0);assert(remove(b)==0);
    assert(rmdir(ui)==0);assert(rmdir(dir)==0);assert(rmdir(root)==0);
    puts("PASS: private original title art pair, strict RGB555 length and atomic fallback");
}
