#include "dr_title_art.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum { DR_TITLE_PIXELS = 256 * 192 };
static int read_opaque_raw(const char *filename,uint16_t *dst,size_t count) {
    FILE *file=fopen(filename,"rb");
    if(!file)return 0;
    int good=fseek(file,0,SEEK_END)==0 &&
             ftell(file)==(long)(count * 2) &&
             fseek(file,0,SEEK_SET)==0;
    if(good){
        for(size_t i=0;i<count;i++){
            unsigned char bytes[2];
            if(fread(bytes,1,2,file)!=2){good=0;break;}
            uint16_t pixel=(uint16_t)((unsigned)bytes[0] | ((unsigned)bytes[1]<<8));
            if(!(pixel&0x8000u)){good=0;break;}
            dst[i]=pixel;
        }
    }
    if(fclose(file)!=0)good=0;
    return good;
}
int dr_title_art_load(const char *storage_root,uint16_t *top,
                      uint16_t *bottom,size_t pixel_count) {
    if(!storage_root || !*storage_root || !top || !bottom ||
       top==bottom || pixel_count!=DR_TITLE_PIXELS) return 0;
    char top_path[256],bottom_path[256];
    size_t len=strlen(storage_root);
    const char *sep=storage_root[len-1]=='/'?"":"/";
    int n=snprintf(top_path,sizeof top_path,"%s%sDreamRadarDSi/UI/title_top.raw",
                   storage_root,sep);
    if(n<0 || n>=(int)sizeof top_path)return 0;
    n=snprintf(bottom_path,sizeof bottom_path,
               "%s%sDreamRadarDSi/UI/title_bottom.raw",storage_root,sep);
    if(n<0 || n>=(int)sizeof bottom_path)return 0;
    uint16_t *candidate=malloc(pixel_count*2u*2u);
    if(!candidate)return 0;
    int good=read_opaque_raw(top_path,candidate,pixel_count) &&
             read_opaque_raw(bottom_path,candidate+pixel_count,pixel_count);
    if(good){
        memcpy(top,candidate,pixel_count*2u);
        memcpy(bottom,candidate+pixel_count,pixel_count*2u);
    }
    free(candidate);
    return good;
}
