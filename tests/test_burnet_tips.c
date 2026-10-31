#include "burnet_tips_generated.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
int main(void){
    assert(BURNET_TIP_COUNT==30);
    for(unsigned i=0;i<BURNET_TIP_COUNT;i++) {
        assert(burnet_tips[i] && strlen(burnet_tips[i])>20);
        assert(strlen(burnet_tips[i])<240);
        for(const char *p=burnet_tips[i];*p;p++)assert((unsigned char)*p>=32 && (unsigned char)*p<=126);
    }
    assert(strstr(burnet_tips[0],"Dream Orbs"));
    puts("PASS: 30 original Burnet talk messages, all safe for DS prototype font");
    return 0;
}
