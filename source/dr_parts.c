#include "dr_parts.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* 16-sample Q12 yaw, identical to the DR_MESH world-spin axis.
 * Linearly interpolate the table for 256 substeps per full rotation. */
static const int16_t cos16[16]={
    4096,3784,2896,1567,0,-1567,-2896,-3784,
    -4096,-3784,-2896,-1567,0,1567,2896,3784
};
static const int16_t sin16[16]={
    0,1567,2896,3784,4096,3784,2896,1567,
    0,-1567,-2896,-3784,-4096,-3784,-2896,-1567
};
static unsigned read16(const unsigned char *p) {
    return (unsigned)p[0]|((unsigned)p[1]<<8);
}
static int16_t signed16(const unsigned char *p) {
    unsigned n=read16(p);
    return (int16_t)(n<32768u?(int)n:(int)n-65536);
}
static int8_t signed8(unsigned n) {
    return (int8_t)(n<128u?(int)n:(int)n-256);
}
static int16_t clamp16(int64_t v) {
    if(v<-32768)return -32768;
    if(v>32767)return 32767;
    return (int16_t)v;
}
static size_t file_size(unsigned vertices,unsigned groups,unsigned frames) {
    return 10u+(size_t)groups*6u+vertices+(size_t)frames*groups*4u;
}
void dr_parts_free(DrParts *parts) {
    if(!parts)return;
    free(parts->owner);
    free(parts->pivot);
    free(parts->poses);
    free(parts->scratch);
    memset(parts,0,sizeof *parts);
}
int dr_parts_decode(const unsigned char *bytes,size_t length,
                    const DrMesh *mesh,DrParts *out) {
    if(!bytes || !mesh || !mesh->vertex || !mesh->triangle || !out ||
       length<10 || memcmp(bytes,"DRB1",4)!=0)return 0;
    unsigned vertices=read16(bytes+4),groups=bytes[6],frames=bytes[7];
    unsigned ticks=bytes[8];
    if(bytes[9]!=0 || vertices<3 || vertices>DR_PARTS_MAX_VERTICES ||
       vertices!=mesh->vertices || groups<1 || groups>DR_PARTS_MAX_GROUPS ||
       frames<2 || frames>DR_PARTS_MAX_FRAMES ||
       ticks<1 || ticks>60 || length!=file_size(vertices,groups,frames))
        return 0;
    DrParts next={0};
    next.owner=(uint8_t*)malloc(vertices);
    next.pivot=(DrPartPivot*)malloc(groups*sizeof *next.pivot);
    next.poses=(DrPartPose*)malloc((size_t)frames*groups*sizeof *next.poses);
    next.scratch=(DrMeshVertex*)malloc((size_t)vertices*sizeof *next.scratch);
    if(!next.owner || !next.pivot || !next.poses || !next.scratch) {
        dr_parts_free(&next);
        return 0;
    }
    const unsigned char *p=bytes+10;
    for(unsigned i=0;i<groups;i++,p+=6) {
        next.pivot[i].x=signed16(p);
        next.pivot[i].y=signed16(p+2);
        next.pivot[i].z=signed16(p+4);
    }
    for(unsigned i=0;i<vertices;i++) {
        if(p[i]>=groups) {
            dr_parts_free(&next);
            return 0;
        }
        next.owner[i]=p[i];
    }
    p+=vertices;
    for(unsigned i=0;i<frames*groups;i++,p+=4) {
        next.poses[i].tx=signed8(p[0]);
        next.poses[i].ty=signed8(p[1]);
        next.poses[i].tz=signed8(p[2]);
        next.poses[i].yaw=signed8(p[3]);
    }
    next.vertices=(uint16_t)vertices;
    next.groups=(uint8_t)groups;
    next.frames=(uint8_t)frames;
    next.ticks_per_frame=(uint8_t)ticks;
    dr_parts_free(out);
    *out=next;
    return 1;
}
int dr_parts_load_file(const char *path,const DrMesh *mesh,DrParts *out) {
    if(!path || !*path || !mesh || !mesh->vertex || !mesh->triangle ||
       !out)return 0;
    FILE *f=fopen(path,"rb");
    if(!f)return 0;
    unsigned char header[10];
    int ok=fread(header,1,sizeof header,f)==sizeof header &&
           memcmp(header,"DRB1",4)==0 && header[9]==0;
    size_t length=0;
    if(ok) {
        unsigned vertices=read16(header+4),groups=header[6];
        unsigned frames=header[7],ticks=header[8];
        if(vertices<3 || vertices>DR_PARTS_MAX_VERTICES ||
           vertices!=mesh->vertices ||
           groups<1 || groups>DR_PARTS_MAX_GROUPS ||
           frames<2 || frames>DR_PARTS_MAX_FRAMES ||
           ticks<1 || ticks>60)ok=0;
        else length=file_size(vertices,groups,frames);
    }
    if(ok && (fseek(f,0,SEEK_END)!=0 || ftell(f)!=(long)length ||
              fseek(f,0,SEEK_SET)!=0))ok=0;
    unsigned char *bytes=NULL;
    if(ok) {
        bytes=(unsigned char*)malloc(length);
        if(!bytes || fread(bytes,1,length,f)!=length)ok=0;
    }
    if(fclose(f)!=0)ok=0;
    if(ok)ok=dr_parts_decode(bytes,length,mesh,out);
    free(bytes);
    return ok;
}
const DrMesh *dr_parts_frame(DrParts *parts,const DrMesh *base,
                             uint32_t ticks) {
    if(!parts || !base || !base->vertex || !base->triangle ||
       !parts->owner || !parts->pivot || !parts->poses || !parts->scratch ||
       parts->vertices<3 || parts->vertices>DR_PARTS_MAX_VERTICES ||
       base->vertices!=parts->vertices ||
       parts->groups<1 || parts->groups>DR_PARTS_MAX_GROUPS ||
       parts->frames<2 || parts->frames>DR_PARTS_MAX_FRAMES ||
       parts->ticks_per_frame<1 || parts->ticks_per_frame>60)return NULL;
    unsigned span=parts->ticks_per_frame;
    unsigned tick=ticks%(span*parts->frames);
    unsigned first=tick/span,second=(first+1u)%parts->frames,blend=tick%span;
    int32_t dx[DR_PARTS_MAX_GROUPS],dy[DR_PARTS_MAX_GROUPS];
    int32_t dz[DR_PARTS_MAX_GROUPS],cs[DR_PARTS_MAX_GROUPS],sn[DR_PARTS_MAX_GROUPS];
    for(unsigned group=0;group<parts->groups;group++) {
        DrPartPose a=parts->poses[first*parts->groups+group];
        DrPartPose b=parts->poses[second*parts->groups+group];
        dx[group]=((int)a.tx*(int)(span-blend)+(int)b.tx*(int)blend)/(int)span;
        dy[group]=((int)a.ty*(int)(span-blend)+(int)b.ty*(int)blend)/(int)span;
        dz[group]=((int)a.tz*(int)(span-blend)+(int)b.tz*(int)blend)/(int)span;
        int delta=(int)b.yaw-(int)a.yaw;
        if(delta>128)delta-=256;
        if(delta<-128)delta+=256;
        uint8_t phase=(uint8_t)((int)a.yaw+delta*(int)blend/(int)span);
        unsigned idx=phase>>4,frac=phase&15u,nxt=(idx+1u)&15u;
        cs[group]=((int32_t)cos16[idx]*(int32_t)(16u-frac)+
                   (int32_t)cos16[nxt]*(int32_t)frac)/16;
        sn[group]=((int32_t)sin16[idx]*(int32_t)(16u-frac)+
                   (int32_t)sin16[nxt]*(int32_t)frac)/16;
    }
    for(unsigned i=0;i<parts->vertices;i++) {
        unsigned group=parts->owner[i];
        if(group>=parts->groups)return NULL;
        DrMeshVertex v=base->vertex[i];
        DrPartPivot p=parts->pivot[group];
        int32_t x=(int32_t)v.x-p.x,z=(int32_t)v.z-p.z;
        int64_t rotated_x=(int64_t)x*cs[group]+(int64_t)z*sn[group];
        int64_t rotated_z=(int64_t)z*cs[group]-(int64_t)x*sn[group];
        parts->scratch[i].x=clamp16((int64_t)p.x+rotated_x/4096+
                                   (int64_t)dx[group]*16);
        parts->scratch[i].y=clamp16((int64_t)v.y+dy[group]*16);
        parts->scratch[i].z=clamp16((int64_t)p.z+rotated_z/4096+
                                   (int64_t)dz[group]*16);
    }
    parts->preview.vertices=base->vertices;
    parts->preview.triangles=base->triangles;
    parts->preview.vertex=parts->scratch;
    parts->preview.triangle=base->triangle;
    return &parts->preview;
}
