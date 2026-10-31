#include "reference_layout.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

static void quote(Game *g,int kind,int idx,PurchaseStatus expected,int price) {
    Game before;
    if(g)before=*g;
    int cost=-1;
    assert(game_purchase_status(g,kind,idx,&cost)==expected);
    assert(cost==price);
    assert(game_purchase_status(g,kind,idx,NULL)==expected);
    if(g)assert(!memcmp(&before,g,sizeof before));
}
static void label(Game *g,int row,const char *expected) {
    Game before;
    if(g)before=*g;
    char text[24];
    dr_shop_purchase_label(g,row,text,sizeof text);
    assert(!strcmp(text,expected));
    if(g)assert(!memcmp(&before,g,sizeof before));
}
int main(void) {
    Game g;game_new(&g,42);
    const int costs[]={0,100,500,1000,1500};
    for(int idx=0;idx<3;idx++)for(int level=1;level<5;level++) {
        g.save.upgrades[idx]=level;
        g.save.orbs=costs[level]-1;
        quote(&g,0,idx,PURCHASE_POOR,costs[level]);
        label(&g,idx,"NEED 1");
        SaveData before=g.save;g.requested_save=0;
        assert(!game_buy(&g,0,idx));
        assert(!memcmp(&before,&g.save,sizeof before) && !g.requested_save);
        g.save.orbs=costs[level];
        quote(&g,0,idx,PURCHASE_READY,costs[level]);
        assert(game_buy(&g,0,idx));
        assert(g.save.orbs==0 && g.save.upgrades[idx]==level+1 && g.requested_save);
    }
    for(int idx=0;idx<3;idx++) {
        g.save.upgrades[idx]=5;g.save.orbs=0;
        quote(&g,0,idx,PURCHASE_MAX,0);label(&g,idx,"MAX");
        g.requested_save=0;
        assert(!game_buy(&g,0,idx) && !g.requested_save);
        for(int count=0;count<9;count++) {
            int cost=idx==0?100:50;
            g.save.goods[idx]=count;g.save.orbs=cost-1;
            quote(&g,1,idx,PURCHASE_POOR,cost);label(&g,idx+3,"NEED 1");
            SaveData before=g.save;g.requested_save=0;
            assert(!game_buy(&g,1,idx));
            assert(!memcmp(&before,&g.save,sizeof before) && !g.requested_save);
            g.save.orbs=cost+7;
            quote(&g,1,idx,PURCHASE_READY,cost);
            label(&g,idx+3,idx==0?"BUY 100":"BUY 50");
            assert(game_buy(&g,1,idx));
            assert(g.save.orbs==7 && g.save.goods[idx]==count+1 && g.requested_save);
        }
        g.save.orbs=0;g.save.goods[idx]=9;
        quote(&g,1,idx,PURCHASE_FULL,0);label(&g,idx+3,"FULL");
        g.requested_save=0;
        assert(!game_buy(&g,1,idx) && !g.requested_save);
        g.save.goods[idx]=255;
        quote(&g,1,idx,PURCHASE_INVALID,0);label(&g,idx+3,"INVALID");
        g.save.upgrades[idx]=0;
        quote(&g,0,idx,PURCHASE_INVALID,0);label(&g,idx,"INVALID");
        g.save.upgrades[idx]=255;
        quote(&g,0,idx,PURCHASE_INVALID,0);
    }
    quote(NULL,0,0,PURCHASE_INVALID,0);
    quote(&g,0,-1,PURCHASE_INVALID,0);
    quote(&g,1,3,PURCHASE_INVALID,0);
    quote(&g,2,0,PURCHASE_INVALID,0);
    label(&g,-1,"INVALID");label(NULL,0,"INVALID");
    char tiny[2]={'x','x'};
    dr_shop_purchase_label(&g,0,tiny,sizeof tiny);assert(tiny[1]=='\0');
    dr_shop_purchase_label(&g,0,NULL,0);
    puts("PASS: shop quotes, prices, capacity, affordability and purchase mutations");
    return 0;
}
