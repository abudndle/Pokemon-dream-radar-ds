#include "dr_animation.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define DR_ANIM_MAX_VERTICES 2048u
#define DR_ANIM_MAX_FRAMES 8u
#define DR_ANIM_MAX_TICKS 60u

static unsigned read16(const unsigned char *p) {
    return (unsigned)p[0] | ((unsigned)p[1]<<8);
}
static size_t payload_size(unsigned vertices,unsigned frames) {
    return (size_t)vertices*frames*3u;
}
void dr_animation_free(DrAnimation *animation) {
    if(!animation)return;
    free(animation->delta);
    free(animation->scratch);
    memset(animation,0,sizeof *animation);
}
int dr_animation_decode(const unsigned char *bytes,size_t length,
                        const DrMesh *mesh,DrAnimation *out) {
    if(!bytes || !mesh || !mesh->vertex || !mesh->triangle || !out ||
       length<8 || memcmp(bytes,"DRA1",4)!=0)return 0;
    unsigned vertices=read16(bytes+4),frames=bytes[6],ticks=bytes[7];
    if(vertices<3 || vertices>DR_ANIM_MAX_VERTICES ||
       vertices!=mesh->vertices ||
       frames<2 || frames>DR_ANIM_MAX_FRAMES ||
       ticks<1 || ticks>DR_ANIM_MAX_TICKS ||
       length!=8u+payload_size(vertices,frames))return 0;

    DrAnimation next={0};
    size_t count=payload_size(vertices,frames);
    next.delta=(int8_t*)malloc(count);
    next.scratch=(DrMeshVertex*)malloc((size_t)vertices*sizeof *next.scratch);
    if(!next.delta || !next.scratch) {
        dr_animation_free(&next);
        return 0;
    }
    for(size_t i=0;i<count;i++) {
        unsigned value=bytes[8u+i];
        next.delta[i]=(int8_t)(value<128u?(int)value:(int)value-256);
    }
    next.vertices=(uint16_t)vertices;
    next.frames=(uint8_t)frames;
    next.ticks_per_frame=(uint8_t)ticks;
    dr_animation_free(out);
    *out=next;
    return 1;
}
int dr_animation_load_file(const char *path,const DrMesh *mesh,DrAnimation *out) {
    if(!path || !*path || !mesh || !mesh->vertex || !mesh->triangle ||
       !out)return 0;
    FILE *f=fopen(path,"rb");
    if(!f)return 0;
    unsigned char hdr[8];
    int valid=fread(hdr,1,8,f)==8 && memcmp(hdr,"DRA1",4)==0;
    size_t length=0;
    if(valid) {
        unsigned n=read16(hdr+4),frames=hdr[6],ticks=hdr[7];
        if(n<3 || n>DR_ANIM_MAX_VERTICES || n!=mesh->vertices ||
           frames<2 || frames>DR_ANIM_MAX_FRAMES ||
           ticks<1 || ticks>DR_ANIM_MAX_TICKS)valid=0;
        else length=8u+payload_size(n,frames);
    }
    if(valid && (fseek(f,0,SEEK_END)!=0 || ftell(f)!=(long)length ||
                 fseek(f,0,SEEK_SET)!=0))valid=0;
    unsigned char *bytes=NULL;
    if(valid) {
        bytes=(unsigned char*)malloc(length);
        if(!bytes || fread(bytes,1,length,f)!=length)valid=0;
    }
    if(fclose(f)!=0)valid=0;
    if(valid)valid=dr_animation_decode(bytes,length,mesh,out);
    free(bytes);
    return valid;
}
static int16_t clamp16(int32_t n) {
    if(n<-32768)return -32768;
    if(n>32767)return 32767;
    return (int16_t)n;
}
const DrMesh *dr_animation_frame(DrAnimation *animation,const DrMesh *base,
                                 uint32_t ticks) {
    if(!animation || !base || !base->vertex || !base->triangle ||
       !animation->delta || !animation->scratch ||
       base->vertices!=animation->vertices ||
       animation->vertices<3 || animation->vertices>DR_ANIM_MAX_VERTICES ||
       animation->frames<2 || animation->frames>DR_ANIM_MAX_FRAMES ||
       animation->ticks_per_frame<1 ||
       animation->ticks_per_frame>DR_ANIM_MAX_TICKS)return NULL;
    unsigned span=animation->ticks_per_frame;
    unsigned period=animation->frames*span;
    unsigned time=ticks%period;
    unsigned frame=time/span;
    unsigned next=(frame+1u)%animation->frames;
    unsigned blend=time%span;
    for(unsigned i=0;i<animation->vertices;i++) {
        size_t a=((size_t)frame*animation->vertices+i)*3u;
        size_t b=((size_t)next*animation->vertices+i)*3u;
        int32_t dx=((int)animation->delta[a]*(int)(span-blend)+
                    (int)animation->delta[b]*(int)blend)/(int)span;
        int32_t dy=((int)animation->delta[a+1u]*(int)(span-blend)+
                    (int)animation->delta[b+1u]*(int)blend)/(int)span;
        int32_t dz=((int)animation->delta[a+2u]*(int)(span-blend)+
                    (int)animation->delta[b+2u]*(int)blend)/(int)span;
        animation->scratch[i].x=clamp16((int32_t)base->vertex[i].x+dx*16);
        animation->scratch[i].y=clamp16((int32_t)base->vertex[i].y+dy*16);
        animation->scratch[i].z=clamp16((int32_t)base->vertex[i].z+dz*16);
    }
    /* Borrow triangles: original topology, indices and UV lookup unchanged. */
    animation->preview.vertices=base->vertices;
    animation->preview.triangles=base->triangles;
    animation->preview.vertex=animation->scratch;
    animation->preview.triangle=base->triangle;
    return &animation->preview;
}
