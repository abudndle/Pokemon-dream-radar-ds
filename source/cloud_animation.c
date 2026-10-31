#include "cloud_animation.h"
int dr_cloud_bob(uint32_t frame, int cloud_index) {
    if(cloud_index<0)return 0;
    unsigned phase=(unsigned)((frame/8u+(unsigned)cloud_index*3u)%8u);
    return phase<4u?(int)phase:7-(int)phase;
}
