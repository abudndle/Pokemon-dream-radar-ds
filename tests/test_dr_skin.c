#include "dr_skin.h"
#include "dr_texture.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

/* Two bones: root at origin and child at x=4096. Frame one rotates both
 * +90 degrees; the child inherits root yaw and turns another +90 degrees.
 * Vertex five has two weights instead of belonging to one rigid piece. */
static void make_stream(unsigned char bytes[60]) {
    memset(bytes,0,60);
    memcpy(bytes,"DRK1",4);
    bytes[4]=6; bytes[6]=2; bytes[7]=2; bytes[8]=4;
    bytes[16]=255;              /* root parent sentinel */
    bytes[19]=16;               /* child pivot X = 4096 */
    bytes[24]=0;                /* child parent = root */
    for(unsigned i=0;i<3;i++) {
        bytes[26+3*i]=0;
        bytes[26+3*i+1]=0;
        bytes[26+3*i+2]=255;
    }
    for(unsigned i=3;i<5;i++) {
        bytes[26+3*i]=1;
        bytes[26+3*i+1]=1;
        bytes[26+3*i+2]=255;
    }
    bytes[41]=0; bytes[42]=1; bytes[43]=128; /* root/child blend */
    bytes[55]=64;                 /* frame1 root yaw=90 degrees */
    bytes[57]=64;                 /* frame1 child Y = +1024 Q12 */
    bytes[59]=64;                 /* frame1 child local yaw=90 degrees */
}
int main(void) {
    DrMeshVertex v[6]={
        {0,0,0},{4096,0,0},{0,4096,0},
        {4096,0,0},{8192,0,0},{8192,4096,0}
    };
    DrMeshTriangle tris[2]={{0,1,2},{3,4,5}};
    DrMesh mesh={6,2,v,tris};
    unsigned char bytes[60];
    make_stream(bytes);
    DrSkin skin={0};
    assert(dr_skin_decode(bytes,sizeof bytes,&mesh,&skin));
    assert(skin.bones==2 && skin.vertices==6 &&
           skin.frames==2 && skin.ticks_per_frame==4);
    assert(skin.bone[0].parent==255 && skin.bone[1].parent==0);
    assert(skin.influence[5].weight==128);
    const DrMesh *p=dr_skin_frame(&skin,&mesh,0);
    assert(p && p->vertex!=v && p->triangle==tris);
    for(unsigned i=0;i<6;i++) {
        assert(p->vertex[i].x==v[i].x);
        assert(p->vertex[i].y==v[i].y);
        assert(p->vertex[i].z==v[i].z);
    }
    p=dr_skin_frame(&skin,&mesh,2);
    assert(p);
    assert(p->vertex[1].x==2896 && p->vertex[1].z==-2896);
    assert(p->vertex[3].x==2896 && p->vertex[3].y==512 &&
           p->vertex[3].z==-2896);
    assert(p->vertex[4].x==2896 && p->vertex[4].y==512 &&
           p->vertex[4].z==-6992);
    p=dr_skin_frame(&skin,&mesh,4);
    assert(p);
    assert(p->vertex[1].x==0 && p->vertex[1].z==-4096);
    assert(p->vertex[3].x==0 && p->vertex[3].y==1024 &&
           p->vertex[3].z==-4096);
    assert(p->vertex[4].x==-4096 && p->vertex[4].y==1024 &&
           p->vertex[4].z==-4096);
    assert(p->vertex[5].x==-2039 && p->vertex[5].y==4605 &&
           p->vertex[5].z==-6152);
    p=dr_skin_frame(&skin,&mesh,6);
    assert(p && p->vertex[3].y==512);
    p=dr_skin_frame(&skin,&mesh,8);
    assert(p && p->vertex[4].x==8192 && p->vertex[5].y==4096);
    p=dr_skin_frame(&skin,&mesh,UINT32_MAX);
    assert(p && p->vertex[3].y==256);
    assert(v[1].x==4096 && v[5].y==4096);

    /* Both existing rasterizers consume the borrowed geometry and preserve
     * each original triangle index and texture-coordinate lookup. */
    p=dr_skin_frame(&skin,&mesh,2);
    uint16_t frame[64*64]={0};
    assert(dr_mesh_solid_yaw(p,frame,64,64,16,48,16,0x7fff,0));
    assert(frame[40*64+18]!=0);
    DrTextureUV uv[6]={{0,0},{4096,0},{0,4096},
                        {0,0},{4096,0},{0,4096}};
    uint16_t texel[4]={0xffff,0xffff,0xffff,0xffff};
    DrTexture texture={2,2,6,uv,texel};
    memset(frame,0,sizeof frame);
    assert(dr_texture_render_yaw(p,&texture,frame,64,64,16,48,16,0));
    assert(frame[40*64+18]==0xffff);

    /* Invalid streams never replace accepted allocations. */
    DrSkinBone *saved=skin.bone;
    assert(!dr_skin_decode(bytes,sizeof bytes-1,&mesh,&skin));
    assert(skin.bone==saved);
    bytes[0]='X';
    assert(!dr_skin_decode(bytes,sizeof bytes,&mesh,&skin));
    bytes[0]='D';
    bytes[9]=1;
    assert(!dr_skin_decode(bytes,sizeof bytes,&mesh,&skin));
    bytes[9]=0;
    bytes[16]=0;               /* root parenting itself forms a cycle */
    assert(!dr_skin_decode(bytes,sizeof bytes,&mesh,&skin));
    bytes[16]=255;
    bytes[24]=1;               /* child parenting itself forms a cycle */
    assert(!dr_skin_decode(bytes,sizeof bytes,&mesh,&skin));
    bytes[24]=0;
    bytes[25]=1;               /* reserved bone byte */
    assert(!dr_skin_decode(bytes,sizeof bytes,&mesh,&skin));
    bytes[25]=0;
    bytes[42]=2;               /* influence points outside bone list */
    assert(!dr_skin_decode(bytes,sizeof bytes,&mesh,&skin));
    bytes[42]=1;
    bytes[6]=17;
    assert(!dr_skin_decode(bytes,sizeof bytes,&mesh,&skin));
    bytes[6]=2;
    bytes[7]=9;
    assert(!dr_skin_decode(bytes,sizeof bytes,&mesh,&skin));
    bytes[7]=2;
    bytes[8]=0;
    assert(!dr_skin_decode(bytes,sizeof bytes,&mesh,&skin));
    bytes[8]=4;
    DrMesh invalid_mesh={7,2,v,tris};
    assert(!dr_skin_decode(bytes,sizeof bytes,&invalid_mesh,&skin));
    assert(!dr_skin_frame(&skin,&invalid_mesh,0));
    assert(skin.bone==saved);

    /* A partial failure of live owner validation must leave scratch intact. */
    p=dr_skin_frame(&skin,&mesh,0);
    assert(p);
    skin.influence[5].b=2;
    assert(!dr_skin_frame(&skin,&mesh,1));
    assert(p->vertex[1].x==4096);
    skin.influence[5].b=1;
    assert(dr_skin_frame(&skin,&mesh,0));

    /* Int16 saturation with large base vertices + local translation. */
    make_stream(bytes);
    bytes[55]=0;  /* root phase neutral */
    bytes[52]=127; /* frame1 root tx: +2032 Q12 */
    assert(dr_skin_decode(bytes,sizeof bytes,&mesh,&skin));
    v[0].x=32767;
    p=dr_skin_frame(&skin,&mesh,4);
    assert(p && p->vertex[0].x==32767);
    v[0].x=0;
    make_stream(bytes);

    char path[]="/tmp/drk1_skin_XXXXXX";
    int fd=mkstemp(path);assert(fd>=0);
    FILE *f=fdopen(fd,"wb");assert(f);
    assert(fwrite(bytes,1,sizeof bytes,f)==sizeof bytes);
    assert(fclose(f)==0);
    DrSkin disk={0};
    assert(dr_skin_load_file(path,&mesh,&disk));
    assert(dr_skin_frame(&disk,&mesh,4)->vertex[4].x==-4096);
    f=fopen(path,"ab");assert(f);
    assert(fputc(1,f)!=EOF);
    assert(fclose(f)==0);
    DrSkinBone *prior=disk.bone;
    assert(!dr_skin_load_file(path,&mesh,&disk));
    assert(disk.bone==prior);
    dr_skin_free(&disk);
    assert(unlink(path)==0);
    assert(!dr_skin_load_file(path,&mesh,&disk));
    dr_skin_free(&skin);
    assert(!skin.bone && !skin.scratch && !skin.preview.vertex);
    assert(!dr_skin_frame(&skin,&mesh,0));
    puts("PASS: DRK1 hierarchy, 2-weight skinning, interpolation and strict bounds");
    return 0;
}
