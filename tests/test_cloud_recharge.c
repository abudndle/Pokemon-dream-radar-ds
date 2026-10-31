#include "game.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>

int main(void) {
    game_regen_clouds(NULL,1000); /* Invalid caller must not crash. */
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
    /* Verify the timer survives a genuine private save/load round trip. */
    const char *path="/tmp/dream_radar_cloud_recharge_test.sav";
    assert(game_save(&g,path));
    Game restored;
    game_new(&restored,99);
    assert(game_load(&restored,path));
    assert(restored.save.last_cloud_time==1000);
    assert(restored.save.cloud_count==g.save.cloud_count);
    game_regen_clouds(&restored,1300);
    assert(restored.save.cloud_count==g.save.cloud_count+1);
    assert(remove(path)==0);
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
    /* A full reservoir must not bank recharge time for instant replenishment
       after a cloud is spent; only the remainder of the interval carries. */
    game_new(&g,17);
    g.save.cloud_count=10;
    g.save.last_cloud_time=1000;
    game_regen_clouds(&g,10000);
    assert(g.save.cloud_count==10 && g.save.last_cloud_time==10000);
    g.save.cloud_count=9;
    game_regen_clouds(&g,10001);
    assert(g.save.cloud_count==9);
    game_regen_clouds(&g,10300);
    assert(g.save.cloud_count==10);
    /* Corrupt upgrade bytes must not grant beyond a real level-five cap. */
    game_new(&g,19);
    g.save.cloud_count=0;g.save.last_cloud_time=1;
    g.save.upgrades[2]=255;
    game_regen_clouds(&g,100000);
    assert(g.save.cloud_count==30);
    game_new(&g,20);
    g.save.cloud_count=0;g.save.last_cloud_time=1;
    g.save.upgrades[2]=0;
    game_regen_clouds(&g,100000);
    assert(g.save.cloud_count==10);
    /* Near UINT32_MAX the anchor advances without wrapping. */
    game_new(&g,21);
    g.save.last_cloud_time=UINT32_MAX-601u;
    g.save.cloud_count=0;
    game_regen_clouds(&g,UINT32_MAX);
    assert(g.save.cloud_count==2);
    assert(g.save.last_cloud_time==UINT32_MAX-1u);
    /* Partial recharge intervals survive successive clock polls. */
    game_new(&g,22);
    g.save.cloud_count=0;g.save.last_cloud_time=1000;
    game_regen_clouds(&g,1200);
    assert(g.save.cloud_count==0 && g.save.last_cloud_time==1000);
    game_regen_clouds(&g,1300);
    assert(g.save.cloud_count==1 && g.save.last_cloud_time==1300);
    game_regen_clouds(&g,1599);
    assert(g.save.cloud_count==1 && g.save.last_cloud_time==1300);
    game_regen_clouds(&g,1600);
    assert(g.save.cloud_count==2 && g.save.last_cloud_time==1600);
    /* A zero RTC reading cannot establish a timer anchor or award clouds. */
    game_new(&g,23);
    g.save.cloud_count=0;g.save.last_cloud_time=0;g.requested_save=0;
    game_regen_clouds(&g,0);
    assert(g.save.cloud_count==0 && g.save.last_cloud_time==0);
    assert(!g.requested_save);
    game_regen_clouds(&g,10);
    assert(g.save.cloud_count==0 && g.save.last_cloud_time==10);
    game_regen_clouds(&g,310);
    assert(g.save.cloud_count==1 && g.save.last_cloud_time==310);
    puts("PASS: recharge intervals, huge clock jumps, caps, clock rollback");
    return 0;
}
