#include "cloud_animation.h"
#include <assert.h>
#include <stdio.h>
int main(void) {
    for(int i=0;i<30;i++)for(unsigned f=0;f<512;f++) {
        int bob=dr_cloud_bob(f,i);
        assert(bob>=0 && bob<=3);
        assert(bob==dr_cloud_bob(f+64,i));
    }
    /* All 30 cloud slots must keep their distinct phased bob animation.
       A misleading local coding-agent draft once disabled every slot >=3;
       a mere 0..3 bounds test could not detect that regression. */
    for(int i=0;i<30;i++)for(unsigned step=0;step<8;step++) {
        unsigned phase=(step+(unsigned)i*3u)%8u;
        int expected=phase<4u?(int)phase:7-(int)phase;
        assert(dr_cloud_bob(step*8u,i)==expected);
    }
    assert(dr_cloud_bob(0,-1)==0);
    assert(dr_cloud_bob(0,0)!=dr_cloud_bob(0,1));
    puts("PASS: bounded, phased, repeating cloud animation");
    return 0;
}
