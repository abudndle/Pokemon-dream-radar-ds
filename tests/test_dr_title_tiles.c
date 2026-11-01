#include "dr_title_tiles.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

enum { W=256,H=192 };
static uint16_t image[W*H+2];
int main(int argc,char **argv){
    assert(argc==3);
    DrTitleTiles tiles;
    memset(&tiles,0,sizeof tiles);
    assert(dr_title_tiles_load(argv[1],&tiles));
    DrTitleTiles saved=tiles;
    assert(!dr_title_tiles_load(argv[2],&tiles));
    assert(memcmp(&tiles,&saved,sizeof tiles)==0);
    for(int i=0;i<W*H+2;i++)image[i]=0x8000;
    image[0]=0x1234;image[W*H+1]=0x5678;
    uint16_t *fb=image+1;
    assert(dr_title_tiles_draw(fb,&tiles,13,45,229,27,0));
    uint16_t gray=fb[(45+13)*W+13+100];
    assert(gray!=0x8000);
    assert(dr_title_tiles_draw(fb,&tiles,13,45,229,27,1));
    uint16_t selected=fb[(45+13)*W+13+100];
    assert(gray!=selected);
    assert((selected&0x03e0u) >= (gray&0x03e0u));
    assert(!dr_title_tiles_draw(fb,&tiles,-1,45,229,27,0));
    assert(!dr_title_tiles_draw(fb,&tiles,13,45,500,27,0));
    assert(!dr_title_tiles_draw(fb,&tiles,13,189,229,27,0));
    assert(!dr_title_tiles_draw(fb,&tiles,13,45,11,27,0));
    assert(!dr_title_tiles_draw(fb,&tiles,13,45,229,27,2));
    assert(!dr_title_tiles_draw(NULL,&tiles,13,45,229,27,0));
    assert(image[0]==0x1234 && image[W*H+1]==0x5678);
    puts("PASS: private source-derived TitleList windows, focus cursor, bounds and corrupt fallback");
}
