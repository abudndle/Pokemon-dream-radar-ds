#include "dr_parts.h"
#include "dr_texture.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static void example(unsigned char bytes[44]) {
    memset(bytes,0,44);
    memcpy(bytes,"DRB1",4);
    bytes[4]=6;       /* six vertices, two independently moving groups */
    bytes[6]=2;bytes[7]=2;bytes[8]=4;
    bytes[17]=16;     /* pivot 1 x = 4096 in Q12 */
    bytes[25]=1;bytes[26]=1;bytes[27]=1;
    bytes[37]=64;     /* frame 1, group 0: +64 Y */
    bytes[40]=32;     /* frame 1, group 1: +32 X */
    bytes[43]=64;     /* frame 1, group 1: 90 degree yaw */
}
int main(void) {
    DrMeshVertex v[6]={
        {0,0,0},{4096,0,0},{0,4096,0},
        {4096,0,0},{8192,0,0},{4096,4096,0}
    };
    DrMeshTriangle tri[2]={{0,1,2},{3,4,5}};
    DrMesh mesh={6,2,v,tri};
    unsigned char bytes[44];
    example(bytes);
    DrParts parts={0};
    assert(dr_parts_decode(bytes,sizeof bytes,&mesh,&parts));
    assert(parts.vertices==6 && parts.groups==2 && parts.frames==2);
    assert(parts.ticks_per_frame==4 && parts.owner[2]==0 && parts.owner[3]==1);
    assert(parts.pivot[1].x==4096);

    const DrMesh *animated=dr_parts_frame(&parts,&mesh,0);
    assert(animated && animated->vertex!=v && animated->triangle==tri);
    assert(animated->vertex[0].y==0 && animated->vertex[4].x==8192);
    animated=dr_parts_frame(&parts,&mesh,2);
    assert(animated && animated->vertex[0].y==512);
    assert(animated->vertex[3].x==4352);
    assert(animated->vertex[4].x==7248 && animated->vertex[4].z==-2896);
    animated=dr_parts_frame(&parts,&mesh,4);
    assert(animated && animated->vertex[0].y==1024);
    assert(animated->vertex[3].x==4608);
    assert(animated->vertex[4].x==4608 && animated->vertex[4].z==-4096);
    animated=dr_parts_frame(&parts,&mesh,6);
    assert(animated && animated->vertex[0].y==512 &&
           animated->vertex[3].x==4352);
    animated=dr_parts_frame(&parts,&mesh,8);
    assert(animated && animated->vertex[0].y==0 &&
           animated->vertex[4].x==8192);
    assert(dr_parts_frame(&parts,&mesh,UINT32_MAX));
    assert(v[0].y==0 && v[4].x==8192 && tri[1].a==3);

    /* Result can be passed to both existing DS renderer variants, with
     * unchanged triangle list, indices, and per-vertex UV correspondence. */
    animated=dr_parts_frame(&parts,&mesh,2);
    uint16_t frame[64*64]={0};
    assert(dr_mesh_solid_yaw(animated,frame,64,64,16,48,16,0x7fff,0));
    assert(frame[40*64+20]!=0);
    DrTextureUV uv[6]={{0,0},{4096,0},{0,4096},
                        {0,0},{4096,0},{0,4096}};
    uint16_t texels[4]={0xffff,0xffff,0xffff,0xffff};
    DrTexture texture={2,2,6,uv,texels};
    memset(frame,0,sizeof frame);
    assert(dr_texture_render_yaw(animated,&texture,frame,64,64,16,48,16,0));
    assert(frame[40*64+20]==0xffff);

    uint8_t *saved=parts.owner;
    assert(!dr_parts_decode(bytes,sizeof bytes-1,&mesh,&parts));
    assert(parts.owner==saved);
    bytes[27]=2; /* invalid group ID */
    assert(!dr_parts_decode(bytes,sizeof bytes,&mesh,&parts));
    bytes[27]=1;
    bytes[9]=1; /* must be zero */
    assert(!dr_parts_decode(bytes,sizeof bytes,&mesh,&parts));
    bytes[9]=0;
    bytes[6]=17;
    assert(!dr_parts_decode(bytes,sizeof bytes,&mesh,&parts));
    bytes[6]=2;
    bytes[7]=9;
    assert(!dr_parts_decode(bytes,sizeof bytes,&mesh,&parts));
    bytes[7]=2;
    bytes[8]=0;
    assert(!dr_parts_decode(bytes,sizeof bytes,&mesh,&parts));
    bytes[8]=4;
    bytes[0]='X';
    assert(!dr_parts_decode(bytes,sizeof bytes,&mesh,&parts));
    bytes[0]='D';
    DrMesh bad={5,2,v,tri};
    assert(!dr_parts_decode(bytes,sizeof bytes,&bad,&parts));
    assert(!dr_parts_frame(&parts,&bad,0));
    assert(parts.owner==saved);

    /* Signed deltas and saturated int16 storage. */
    bytes[37]=192; /* group 0 moves down -64 */
    assert(dr_parts_decode(bytes,sizeof bytes,&mesh,&parts));
    animated=dr_parts_frame(&parts,&mesh,4);
    assert(animated && animated->vertex[0].y==-1024);
    v[0].y=-32768;
    animated=dr_parts_frame(&parts,&mesh,4);
    assert(animated && animated->vertex[0].y==-32768);
    v[0].y=0;
    example(bytes);
    /* Yaw shortest-way wrap: +120 -> -120 goes through 180 degrees. */
    bytes[35]=120;
    bytes[43]=136; /* signed -120 */
    assert(dr_parts_decode(bytes,sizeof bytes,&mesh,&parts));
    animated=dr_parts_frame(&parts,&mesh,2);
    assert(animated && animated->vertex[4].x==256 && animated->vertex[4].z==0);
    assert(animated->vertex[3].x==4352); /* pivot remains at group origin */

    char path[]="/tmp/drb1_parts_XXXXXX";
    int fd=mkstemp(path);assert(fd>=0);
    FILE *file=fdopen(fd,"wb");assert(file);
    example(bytes);
    assert(fwrite(bytes,1,sizeof bytes,file)==sizeof bytes);
    assert(fclose(file)==0);
    DrParts loaded={0};
    assert(dr_parts_load_file(path,&mesh,&loaded));
    assert(dr_parts_frame(&loaded,&mesh,4)->vertex[0].y==1024);
    file=fopen(path,"ab");assert(file);
    assert(fputc(7,file)!=EOF);
    assert(fclose(file)==0);
    uint8_t *old=loaded.owner;
    assert(!dr_parts_load_file(path,&mesh,&loaded));
    assert(old==loaded.owner);
    dr_parts_free(&loaded);
    assert(unlink(path)==0);
    assert(!dr_parts_load_file(path,&mesh,&loaded));

    dr_parts_free(&parts);
    assert(!parts.owner && !parts.scratch && !parts.preview.vertex);
    assert(!dr_parts_frame(&parts,&mesh,0));
    puts("PASS: DRB1 group pivots, partial motion, yaw, interpolation and safety");
    return 0;
}
