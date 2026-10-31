#include "dr_texture.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

/* Overlapping front/rear triangles: rear is drawn last on the first pass.
 * Draw both orders and verify that per-pixel depth, not index order, wins. */
static void check_overlap(int crossing) {
    DrMeshVertex v[6]={
        {0,0,-2048},{4096,0,-2048},{0,4096,-2048},
        {0,0,2048},{4096,0,2048},{0,4096,2048}
    };
    if(crossing) {
        v[0].z=v[1].z=v[2].z=0;
        v[3].z=4096;
        v[4].z=-4096;
        v[5].z=-4096;
    }
    DrMeshTriangle t[2]={{3,4,5},{0,1,2}};
    DrMesh mesh={6,2,v,t};
    DrTextureUV uv[6]={
        {0,0},{0,0},{0,0},
        {4096,0},{4096,0},{4096,0}
    };
    uint16_t texels[2]={0x801f,0xffff};
    DrTexture tex={2,1,6,uv,texels};
    uint16_t guarded[64*64+2]={0};
    uint16_t *frame=guarded+1;
    guarded[0]=0x1234;
    guarded[64*64+1]=0x5678;
    for(int order=0;order<2;order++) {
        memset(frame,0,64*64*sizeof *frame);
        assert(dr_texture_render_yaw(&mesh,&tex,frame,64,64,16,48,16,0));
        assert(frame[46*64+18]==0xffff);
        assert(frame[46*64+28]==(crossing?0x801f:0xffff));
        assert(guarded[0]==0x1234 && guarded[64*64+1]==0x5678);
        DrMeshTriangle tmp=t[0];t[0]=t[1];t[1]=tmp;
    }
    /* Depth is cleared between calls, including a scene with no front face. */
    mesh.triangles=1;
    t[0]=(DrMeshTriangle){0,1,2};
    memset(frame,0,64*64*sizeof *frame);
    assert(dr_texture_render_yaw(&mesh,&tex,frame,64,64,16,48,16,0));
    assert(frame[46*64+18]==0x801f);
    assert(frame[46*64+28]==0x801f);
    t[0].c=6;
    frame[46*64+18]=0x2222;
    assert(!dr_texture_render_yaw(&mesh,&tex,frame,64,64,16,48,16,0));
    assert(frame[46*64+18]==0x2222);
    t[0].c=2;
    assert(!dr_texture_render_yaw(&mesh,&tex,frame,64,64,16,48,16,16));
    assert(frame[46*64+18]==0x2222);
}
int main(void) {
    DrMeshVertex v={4096,0,0};
    int z=123;
    assert(dr_mesh_depth_vertex_yaw(&v,0,&z) && z==0);
    assert(dr_mesh_depth_vertex_yaw(&v,4,&z) && z==-4096);
    assert(dr_mesh_depth_vertex_yaw(&v,8,&z) && z==0);
    assert(!dr_mesh_depth_vertex_yaw(NULL,0,&z));
    assert(!dr_mesh_depth_vertex_yaw(&v,16,&z));
    assert(!dr_mesh_depth_vertex_yaw(&v,0,NULL));
    v.z=4096;
    assert(dr_mesh_depth_vertex_yaw(&v,0,&z) && z==4096);
    assert(dr_mesh_depth_vertex_yaw(&v,8,&z) && z==-4096);
    check_overlap(0);
    check_overlap(1);
    puts("PASS: model z-order, crossing faces, yaw and framebuffer guards");
    return 0;
}
