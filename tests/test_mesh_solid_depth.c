#include "dr_mesh.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#define W 64
#define H 64
#define SAMPLE(x,y) frame[(y)*W+(x)]

/* Color with R=G=B=8. Q12 depth +2048 -> light 14/12 -> RGB 9,
 * Q12 depth 0 -> RGB 8, Q12 depth -2048 -> light 10/12 -> RGB 7. */
#define BASE 0xA108u
#define NEAR 0xA529u
#define FAR 0x9CE7u

static void verify_surface_order(int crossing) {
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
    uint16_t guarded[W*H+2]={0};
    uint16_t *frame=guarded+1;
    guarded[0]=0x1234;
    guarded[W*H+1]=0x5678;
    for(int order=0;order<3;order++) {
        memset(frame,0,W*H*sizeof *frame);
        assert(dr_mesh_solid_yaw(&mesh,frame,W,H,16,48,16,BASE,0));
        assert(SAMPLE(18,46)==NEAR);
        assert(SAMPLE(28,46)==(crossing?BASE:NEAR));
        assert(SAMPLE(5,5)==0);
        assert(guarded[0]==0x1234 && guarded[W*H+1]==0x5678);
        if(order==0) {
            DrMeshTriangle swap=t[0];t[0]=t[1];t[1]=swap;
        } else if(order==1) {
            for(int k=0;k<2;k++) {
                uint16_t swap=t[k].a;t[k].a=t[k].c;t[k].c=swap;
            }
        }
    }

    /* The next draw must not remember front surfaces from the last frame. */
    mesh.triangles=1;
    t[0]=(DrMeshTriangle){0,1,2};
    memset(frame,0,W*H*sizeof *frame);
    assert(dr_mesh_solid_yaw(&mesh,frame,W,H,16,48,16,BASE,0));
    assert(SAMPLE(18,46)==(crossing?BASE:FAR));
    assert(SAMPLE(28,46)==(crossing?BASE:FAR));

    /* Invalid triangle index and yaw must reject before framebuffer writes. */
    t[0].c=6;
    SAMPLE(18,46)=0x2222;
    assert(!dr_mesh_solid_yaw(&mesh,frame,W,H,16,48,16,BASE,0));
    assert(SAMPLE(18,46)==0x2222);
    t[0].c=2;
    assert(!dr_mesh_solid_yaw(&mesh,frame,W,H,16,48,16,BASE,16));
    assert(SAMPLE(18,46)==0x2222);
    assert(guarded[0]==0x1234 && guarded[W*H+1]==0x5678);
}
int main(void) {
    verify_surface_order(0);
    verify_surface_order(1);
    DrMeshVertex v[3]={{0,0,0},{4096,0,0},{0,4096,0}};
    DrMeshTriangle t[1]={{0,1,2}};
    DrMesh mesh={3,1,v,t};
    uint16_t screen[W*H]={0};
    /* All channels are preserved exactly at zero depth, including old
     * callers that pass a color without the opaque display-enable bit. */
    assert(dr_mesh_solid_yaw(&mesh,screen,W,H,16,48,16,0x7fff,0));
    assert(screen[40*W+20]==0x7fff);
    v[0].x=-32768;
    v[0].y=-32768;
    v[0].z=-32768;
    v[1].x=32767;
    v[1].y=-32768;
    v[1].z=32767;
    v[2].x=-32768;
    v[2].y=32767;
    v[2].z=32767;
    assert(dr_mesh_solid_yaw(&mesh,screen,W,H,16,48,16,BASE,15));
    puts("PASS: flat-color Z ordering, crossing surfaces, yaw, clipping, guards");
    return 0;
}
