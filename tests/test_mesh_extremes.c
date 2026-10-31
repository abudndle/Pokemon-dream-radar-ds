#include "dr_mesh.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
/* Very large Q12 coordinates should never corrupt a 256x192 buffer. */
int main(void) {
    DrMeshVertex v[3]={{-32768,-32768,0},{32767,32767,0},{0,0,0}};
    DrMeshTriangle t[1]={{0,1,2}};
    DrMesh m={3,1,v,t};
    static uint16_t pixels[256*192+2];
    pixels[0]=0x1234;
    pixels[256*192+1]=0x5678;
    assert(dr_mesh_wireframe_yaw(&m,pixels+1,256,192,128,96,256,0x7fff,0));
    assert(pixels[0]==0x1234 && pixels[256*192+1]==0x5678);
    puts("PASS: extreme DRM1 projection preserves framebuffer guards");
    return 0;
}
