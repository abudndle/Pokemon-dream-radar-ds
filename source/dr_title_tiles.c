#include "dr_title_tiles.h"
#include <stdio.h>
#include <string.h>

enum { DR_W=256, DR_H=192, DR_PIXELS=64, DR_HEADER=12,
       DR_LENGTH=DR_HEADER+DR_TITLE_TILE_COUNT*DR_PIXELS*2 };
static unsigned short u16le(const unsigned char *p){
    return (unsigned short)((unsigned)p[0] | ((unsigned)p[1]<<8));
}
static uint32_t u32le(const unsigned char *p){
    return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);
}
static uint32_t crc32(const unsigned char *data,unsigned count){
    uint32_t crc=0xffffffffu;
    for(unsigned i=0;i<count;i++){
        crc^=data[i];
        for(int bit=0;bit<8;bit++)
            crc=(crc>>1)^(0xedb88320u & (uint32_t)-(int)(crc&1u));
    }
    return ~crc;
}
int dr_title_tiles_load(const char *root,DrTitleTiles *out){
    if(!root || !*root || !out)return 0;
    char path[240];
    size_t length=strlen(root);
    int n=snprintf(path,sizeof path,"%s%sDreamRadarDSi/UI/title_tiles.drtt",
                   root,root[length-1]=='/'?"":"/");
    if(n<=0 || n>=(int)sizeof path)return 0;
    FILE *f=fopen(path,"rb");if(!f)return 0;
    unsigned char data[DR_LENGTH];
    int good=fseek(f,0,SEEK_END)==0 && ftell(f)==DR_LENGTH &&
             fseek(f,0,SEEK_SET)==0 && fread(data,1,sizeof data,f)==sizeof data;
    if(fclose(f)!=0)good=0;
    if(!good || memcmp(data,"DTT1",4)!=0 || u16le(data+4)!=1 ||
       u16le(data+6)!=DR_TITLE_TILE_COUNT ||
       u32le(data+8)!=crc32(data+DR_HEADER,DR_LENGTH-DR_HEADER))return 0;
    DrTitleTiles candidate;
    for(int k=0;k<DR_TITLE_TILE_COUNT;k++){
        unsigned opaque=0;
        for(int i=0;i<DR_PIXELS;i++){
            uint16_t color=u16le(data+DR_HEADER+2*(k*DR_PIXELS+i));
            candidate.pixels[k][i]=color;
            opaque |= color&15u;
        }
        if(!opaque)return 0;
    }
    memcpy(out,&candidate,sizeof candidate);
    return 1;
}
static uint16_t sample9(const DrTitleTiles *tiles,int base,int x,int y,int w,int h){
    /* Each corner is the original 8x8 texture, retargeted to a 6px edge.
       Edges repeat their respective corner's matching seam, while the
       original fifth bitmap supplies the solid/animated interior color. */
    const int edge=6;
    int left=x<edge,right=x>=w-edge,top=y<edge,bottom=y>=h-edge;
    int tile,tx,ty;
    if(top && left){tile=0;tx=x*8/edge;ty=y*8/edge;}
    else if(top && right){tile=1;tx=(x-(w-edge))*8/edge;ty=y*8/edge;}
    else if(bottom && left){tile=2;tx=x*8/edge;ty=(y-(h-edge))*8/edge;}
    else if(bottom && right){tile=3;tx=(x-(w-edge))*8/edge;ty=(y-(h-edge))*8/edge;}
    else if(top){tile=0;tx=7;ty=y*8/edge;}
    else if(bottom){tile=2;tx=7;ty=(y-(h-edge))*8/edge;}
    else if(left){tile=0;tx=x*8/edge;ty=7;}
    else if(right){tile=1;tx=(x-(w-edge))*8/edge;ty=7;}
    else{tile=4;tx=4;ty=4;}
    return tiles->pixels[base+tile][ty*8+tx];
}
static uint16_t blend(uint16_t dst,uint16_t rgba4){
    unsigned alpha=rgba4&15u;
    if(!alpha)return dst;
    unsigned sr=(rgba4>>12)&15u,sg=(rgba4>>8)&15u,sb=(rgba4>>4)&15u;
    unsigned r=(sr*31u+7u)/15u,g=(sg*31u+7u)/15u,b=(sb*31u+7u)/15u;
    if(alpha!=15u){
        r=(((unsigned)dst&31u)*(15u-alpha)+r*alpha+7u)/15u;
        g=((((unsigned)dst>>5)&31u)*(15u-alpha)+g*alpha+7u)/15u;
        b=((((unsigned)dst>>10)&31u)*(15u-alpha)+b*alpha+7u)/15u;
    }
    return (uint16_t)(0x8000u|r|(g<<5)|(b<<10));
}
int dr_title_tiles_draw(uint16_t *framebuffer,const DrTitleTiles *tiles,
                        int x,int y,int w,int h,int selected){
    if(!framebuffer || !tiles || (selected!=0 && selected!=1) ||
       x<0 || y<0 || w<12 || h<12 || x>DR_W-w || y>DR_H-h)return 0;
    for(int py=0;py<h;py++){
        uint16_t *row=framebuffer+(y+py)*DR_W+x;
        for(int px=0;px<w;px++){
            uint16_t dst=blend(row[px],sample9(tiles,0,px,py,w,h));
            if(selected)dst=blend(dst,sample9(tiles,5,px,py,w,h));
            row[px]=dst;
        }
    }
    return 1;
}
