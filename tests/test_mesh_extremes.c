#include "dr_mesh.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
int main(void) {
    /* A long diagonal must clip to a 256x192 viewport, not walk millions
     * of off-screen pixels; guard words must remain untouched. */
    DrMeshVertex v[3]={{-32768,-32768,0},{32767,32767,0},{0,4096,0}};
    DrMeshTriangle t[1]={{0,1,2}};
    DrMesh m={3,1,v,t};
    static uint16_t guarded[256*192+2];
    guarded[0]=0x1234;guarded[256*192+1]=0x5678;
    assert(dr_mesh_wireframe_yaw(&m,guarded+1,256,192,128,96,256,0x7fff,0));
    assert(guarded[0]==0x1234 && guarded[256*192+1]==0x5678);
    unsigned colored=0;
    for(unsigned i=1;i<=256*192;i++)colored+=guarded[i]==0x7fff;
    assert(colored>0);
    puts("PASS: extreme mesh coordinates clip safely to viewport");
    return 0;
}
