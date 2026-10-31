#include "cloud_animation.h"
#include <assert.h>
#include <stdio.h>
int main(void) {
    for(int i=0;i<30;i++)for(unsigned f=0;f<512;f++) {
        int bob=dr_cloud_bob(f,i);
        assert(bob>=0 && bob<=3);
        assert(bob==dr_cloud_bob(f+64,i));
    }
    assert(dr_cloud_bob(0,-1)==0);
    assert(dr_cloud_bob(0,0)!=dr_cloud_bob(0,1));
    puts("PASS: bounded, phased, repeating cloud animation");
    return 0;
}
