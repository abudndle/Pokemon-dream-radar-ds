#include "game.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>

int main(void) {
    Game g;
    game_new(&g,7);
    g.save.last_cloud_time=0;
    g.requested_save=0;
    game_regen_clouds(&g,0);
    assert(g.save.last_cloud_time==0 && !g.requested_save);
    game_regen_clouds(&g,1000);
    assert(g.save.last_cloud_time==1000 && g.requested_save);
    g.requested_save=0;
    game_regen_clouds(&g,1001);
    assert(!g.requested_save);
    g.save.cloud_count=0;
    g.save.last_cloud_time=1000;
    game_regen_clouds(&g,1299);
    assert(g.save.cloud_count==0 && g.save.last_cloud_time==1000);
    game_regen_clouds(&g,1300);
    assert(g.save.cloud_count==1 && g.save.last_cloud_time==1300);
    g.save.last_cloud_time=1;
    g.save.cloud_count=0;
    game_regen_clouds(&g,UINT32_MAX);
    assert(g.save.cloud_count==10);
    assert(g.save.last_cloud_time<=UINT32_MAX);
    g.save.cloud_count=9;
    g.save.upgrades[2]=5;
    g.save.last_cloud_time=10000;
    game_regen_clouds(&g,UINT32_MAX);
    assert(g.save.cloud_count==30);
    g.save.last_cloud_time=5000;
    g.requested_save=0;
    game_regen_clouds(&g,4000);
    assert(g.save.last_cloud_time==4000);
    assert(g.save.cloud_count==30 && g.requested_save);
    puts("PASS: recharge intervals, huge clock jumps, caps, clock rollback");
    return 0;
}
