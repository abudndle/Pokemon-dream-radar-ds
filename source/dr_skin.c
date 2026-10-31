#include "dr_skin.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Match the 16-sample yaw convention used by the existing DRM1 viewer.
 * Interpolate at 256 equally-spaced phases with integer-only arithmetic. */
static const int16_t cos16[16]={
    4096,3784,2896,1567,0,-1567,-2896,-3784,
    -4096,-3784,-2896,-1567,0,1567,2896,3784
};
static const int16_t sin16[16]={
    0,1567,2896,3784,4096,3784,2896,1567,
    0,-1567,-2896,-3784,-4096,-3784,-2896,-1567
};
static unsigned read16(const unsigned char *p) {
    return (unsigned)p[0] | ((unsigned)p[1]<<8);
}
static int16_t signed16(const unsigned char *p) {
    unsigned n=read16(p);
    return (int16_t)(n<32768u?(int)n:(int)n-65536);
}
static int8_t signed8(unsigned n) {
    return (int8_t)(n<128u?(int)n:(int)n-256);
}
static size_t expected_size(unsigned vertices,unsigned bones,unsigned frames) {
    return 10u+8u*(size_t)bones+3u*(size_t)vertices+
           4u*(size_t)bones*frames;
}
static int16_t clamp16(int64_t value) {
    if(value<-32768)return -32768;
    if(value>32767)return 32767;
    return (int16_t)value;
}
static void trig(uint8_t phase,int32_t *cs,int32_t *sn) {
    unsigned idx=phase>>4,frac=phase&15u,next=(idx+1u)&15u;
    *cs=((int32_t)cos16[idx]*(int32_t)(16u-frac)+
         (int32_t)cos16[next]*(int32_t)frac)/16;
    *sn=((int32_t)sin16[idx]*(int32_t)(16u-frac)+
         (int32_t)sin16[next]*(int32_t)frac)/16;
}
void dr_skin_free(DrSkin *skin) {
    if(!skin)return;
    free(skin->bone);
    free(skin->influence);
    free(skin->poses);
    free(skin->scratch);
    memset(skin,0,sizeof *skin);
}
int dr_skin_decode(const unsigned char *bytes,size_t size,
                   const DrMesh *mesh,DrSkin *out) {
    if(!bytes || !mesh || !mesh->vertex || !mesh->triangle || !out ||
       size<10 || memcmp(bytes,"DRK1",4)!=0)return 0;
    unsigned nv=read16(bytes+4),nb=bytes[6],nf=bytes[7],ticks=bytes[8];
    if(bytes[9]!=0 || nv<3 || nv>DR_SKIN_MAX_VERTICES ||
       nv!=mesh->vertices || nb<1 || nb>DR_SKIN_MAX_BONES ||
       nf<2 || nf>DR_SKIN_MAX_FRAMES || ticks<1 || ticks>60 ||
       size!=expected_size(nv,nb,nf))return 0;

    DrSkin next={0};
    next.bone=(DrSkinBone*)malloc(nb*sizeof *next.bone);
    next.influence=(DrSkinInfluence*)malloc(nv*sizeof *next.influence);
    next.poses=(DrSkinPose*)malloc((size_t)nf*nb*sizeof *next.poses);
    next.scratch=(DrMeshVertex*)malloc(nv*sizeof *next.scratch);
    if(!next.bone || !next.influence || !next.poses || !next.scratch) {
        dr_skin_free(&next);
        return 0;
    }
    const unsigned char *p=bytes+10;
    for(unsigned i=0;i<nb;i++,p+=8) {
        unsigned parent=p[6];
        if(p[7]!=0 || (parent!=255u && parent>=i)) {
            dr_skin_free(&next);
            return 0;
        }
        next.bone[i].x=signed16(p);
        next.bone[i].y=signed16(p+2);
        next.bone[i].z=signed16(p+4);
        next.bone[i].parent=(uint8_t)parent;
    }
    for(unsigned i=0;i<nv;i++,p+=3) {
        if(p[0]>=nb || p[1]>=nb) {
            dr_skin_free(&next);
            return 0;
        }
        next.influence[i].a=p[0];
        next.influence[i].b=p[1];
        next.influence[i].weight=p[2];
    }
    for(unsigned i=0;i<nf*nb;i++,p+=4) {
        next.poses[i].tx=signed8(p[0]);
        next.poses[i].ty=signed8(p[1]);
        next.poses[i].tz=signed8(p[2]);
        next.poses[i].yaw=signed8(p[3]);
    }
    next.vertices=(uint16_t)nv;
    next.bones=(uint8_t)nb;
    next.frames=(uint8_t)nf;
    next.ticks_per_frame=(uint8_t)ticks;
    dr_skin_free(out);
    *out=next;
    return 1;
}
int dr_skin_load_file(const char *path,const DrMesh *mesh,DrSkin *out) {
    if(!path || !*path || !mesh || !mesh->vertex || !mesh->triangle ||
       !out)return 0;
    FILE *f=fopen(path,"rb");
    if(!f)return 0;
    unsigned char header[10];
    int valid=fread(header,1,10,f)==10 && memcmp(header,"DRK1",4)==0 &&
              header[9]==0;
    size_t size=0;
    if(valid) {
        unsigned nv=read16(header+4),nb=header[6],nf=header[7];
        unsigned ticks=header[8];
        if(nv<3 || nv>DR_SKIN_MAX_VERTICES || nv!=mesh->vertices ||
           nb<1 || nb>DR_SKIN_MAX_BONES ||
           nf<2 || nf>DR_SKIN_MAX_FRAMES ||
           ticks<1 || ticks>60)valid=0;
        else size=expected_size(nv,nb,nf);
    }
    if(valid && (fseek(f,0,SEEK_END)!=0 || ftell(f)!=(long)size ||
                 fseek(f,0,SEEK_SET)!=0))valid=0;
    unsigned char *bytes=NULL;
    if(valid) {
        bytes=(unsigned char*)malloc(size);
        if(!bytes || fread(bytes,1,size,f)!=size)valid=0;
    }
    if(fclose(f)!=0)valid=0;
    if(valid)valid=dr_skin_decode(bytes,size,mesh,out);
    free(bytes);
    return valid;
}
const DrMesh *dr_skin_frame(DrSkin *skin,const DrMesh *base,uint32_t tick) {
    if(!skin || !base || !base->vertex || !base->triangle ||
       !skin->bone || !skin->influence || !skin->poses || !skin->scratch ||
       base->vertices!=skin->vertices ||
       skin->vertices<3 || skin->vertices>DR_SKIN_MAX_VERTICES ||
       skin->bones<1 || skin->bones>DR_SKIN_MAX_BONES ||
       skin->frames<2 || skin->frames>DR_SKIN_MAX_FRAMES ||
       skin->ticks_per_frame<1 || skin->ticks_per_frame>60)return NULL;

    unsigned span=skin->ticks_per_frame;
    unsigned time=tick%(span*skin->frames);
    unsigned first=time/span,second=(first+1u)%skin->frames,blend=time%span;
    int64_t worldx[DR_SKIN_MAX_BONES],worldy[DR_SKIN_MAX_BONES];
    int64_t worldz[DR_SKIN_MAX_BONES];
    int32_t cs[DR_SKIN_MAX_BONES],sn[DR_SKIN_MAX_BONES];
    uint8_t yaw[DR_SKIN_MAX_BONES];
    /* Parent indices must be smaller, so every parent world transform is
     * ready when its child is calculated. Compute only 16 such transforms. */
    for(unsigned i=0;i<skin->bones;i++) {
        DrSkinBone bone=skin->bone[i];
        unsigned parent=bone.parent;
        if(parent!=255u && parent>=i)return NULL;
        DrSkinPose a=skin->poses[first*skin->bones+i];
        DrSkinPose b=skin->poses[second*skin->bones+i];
        int32_t tx=((int)a.tx*(int)(span-blend)+
                    (int)b.tx*(int)blend)/(int)span*16;
        int32_t ty=((int)a.ty*(int)(span-blend)+
                    (int)b.ty*(int)blend)/(int)span*16;
        int32_t tz=((int)a.tz*(int)(span-blend)+
                    (int)b.tz*(int)blend)/(int)span*16;
        int diff=(int)b.yaw-(int)a.yaw;
        if(diff>128)diff-=256;
        if(diff<-128)diff+=256;
        uint8_t local_yaw=(uint8_t)((int)a.yaw+diff*(int)blend/(int)span);
        if(parent==255u) {
            worldx[i]=(int64_t)bone.x+tx;
            worldy[i]=(int64_t)bone.y+ty;
            worldz[i]=(int64_t)bone.z+tz;
            yaw[i]=local_yaw;
        } else {
            DrSkinBone ancestor=skin->bone[parent];
            int64_t relx=(int64_t)bone.x-ancestor.x+tx;
            int64_t relz=(int64_t)bone.z-ancestor.z+tz;
            worldx[i]=worldx[parent]+
                      (relx*cs[parent]+relz*sn[parent])/4096;
            worldz[i]=worldz[parent]+
                      (relz*cs[parent]-relx*sn[parent])/4096;
            worldy[i]=worldy[parent]+(int64_t)bone.y-ancestor.y+ty;
            yaw[i]=(uint8_t)(yaw[parent]+local_yaw);
        }
        trig(yaw[i],&cs[i],&sn[i]);
    }
    /* Validate every influence before mutating any scratch output. */
    for(unsigned i=0;i<skin->vertices;i++) {
        if(skin->influence[i].a>=skin->bones ||
           skin->influence[i].b>=skin->bones)return NULL;
    }
    for(unsigned i=0;i<skin->vertices;i++) {
        DrMeshVertex vertex=base->vertex[i];
        DrSkinInfluence influence=skin->influence[i];
        unsigned indices[2]={influence.a,influence.b};
        int64_t result[2][3];
        for(unsigned k=0;k<2;k++) {
            unsigned b=indices[k];
            int64_t x=(int64_t)vertex.x-skin->bone[b].x;
            int64_t z=(int64_t)vertex.z-skin->bone[b].z;
            result[k][0]=worldx[b]+(x*cs[b]+z*sn[b])/4096;
            result[k][1]=worldy[b]+(int64_t)vertex.y-skin->bone[b].y;
            result[k][2]=worldz[b]+(z*cs[b]-x*sn[b])/4096;
        }
        unsigned w=influence.weight;
        int64_t bx=(result[0][0]*(int64_t)w+
                    result[1][0]*(int64_t)(255u-w))/255;
        int64_t by=(result[0][1]*(int64_t)w+
                    result[1][1]*(int64_t)(255u-w))/255;
        int64_t bz=(result[0][2]*(int64_t)w+
                    result[1][2]*(int64_t)(255u-w))/255;
        skin->scratch[i].x=clamp16(bx);
        skin->scratch[i].y=clamp16(by);
        skin->scratch[i].z=clamp16(bz);
    }
    skin->preview.vertices=base->vertices;
    skin->preview.triangles=base->triangles;
    skin->preview.vertex=skin->scratch;
    skin->preview.triangle=base->triangle;
    return &skin->preview;
}
