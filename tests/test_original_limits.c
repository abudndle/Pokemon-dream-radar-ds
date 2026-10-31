#include "game.h"
#include <assert.h>
#include <stdio.h>

int main(void) {
    Game g; game_new(&g,42);
    assert(g.save.cloud_count==5); /* Initial exception: 5 clouds */
    for(int level=1;level<=5;level++) {
        g.save.upgrades[2]=(uint8_t)level;
        g.save.cloud_count=0;
        g.save.last_cloud_time=100;
        game_regen_clouds(&g,100+300*120);
        assert(g.save.cloud_count == 5*(level+1));
    }
    Game shop;game_new(&shop,123);
    shop.save.orbs=3100;
    for(int level=2;level<=5;level++) {
        assert(game_buy(&shop,0,0));
        assert(shop.save.upgrades[0]==level);
    }
    assert(shop.save.orbs==0);
    assert(!game_buy(&shop,0,0));
    assert(shop.save.upgrades[0]==5);
    assert(MAX_CAUGHT==6 && MAX_ITEMS==6);
    puts("PASS: 5 upgrade levels, 10..30 clouds, 6 Pokemon and item stacks");
    return 0;
}
