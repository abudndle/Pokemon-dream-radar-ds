#include "dr_mesh.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
int main(void) {
    DrMeshVertex v[3]={{0,0,0},{4096,0,0},{0,4096,0}};
    DrMeshTriangle t[1]={{0,1,2}};
    DrMesh mesh={3,1,v,t};
    uint16_t guarded[64*64+2]={0};
    guarded[0]=0x1234;guarded[64*64+1]=0x5678;
    assert(dr_mesh_solid_yaw(&mesh,guarded+1,64,64,16,48,16,0x7fff,0));
    assert(guarded[1+40*64+20]==0x7fff);
    assert(guarded[1+5*64+5]==0);
    assert(guarded[0]==0x1234 && guarded[64*64+1]==0x5678);
    assert(!dr_mesh_solid_yaw(&mesh,guarded+1,64,64,16,48,16,0x7fff,16));
    t[0].c=3;
    guarded[1+40*64+20]=0;
    assert(!dr_mesh_solid_yaw(&mesh,guarded+1,64,64,16,48,16,0x7fff,0));
    assert(guarded[1+40*64+20]==0);
    puts("PASS: flat filled mesh preview and bounds");
    return 0;
}
