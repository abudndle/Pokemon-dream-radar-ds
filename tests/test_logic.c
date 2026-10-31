#include "game.h"
#include <assert.h>
#include <string.h>
#include <stdio.h>

static void complete_sphere(Game *g, int extension) {
    game_begin_search(g,extension);
    assert(g->screen==STATE_RADAR);
    g->aim_x=g->clouds[0].x;
    g->aim_y=g->clouds[0].y;
    game_fire(g);
    assert(g->screen==STATE_SPHERE);
    game_capture(g);
    assert(g->screen==STATE_RESULTS);
}
int main(void) {
    Game g;game_new(&g,0xf00d);
    assert(g.save.upgrades[0]==1 && g.save.cloud_count==5);
    assert(game_item_slot_kind(NULL,0)==-1);
    game_capture(NULL);
    assert(!game_replace_pending(NULL,0));
    assert(!game_cancel_pending_replace(NULL));
    assert(!game_buy(NULL,0,0));
    game_secret_key(NULL,0);
    g.cheat_progress[0]=999;
    g.cheat_progress[1]=-5;
    game_secret_key(&g,12345);
    assert(g.cheat_progress[0]==0 && g.cheat_progress[1]==0);

    g.save.orbs=1000;
    g.save.upgrades[0]=0;
    assert(!game_buy(&g,0,0) && g.save.orbs==1000);
    g.save.upgrades[0]=6;
    assert(!game_buy(&g,0,0) && g.save.orbs==1000);
    g.save.upgrades[0]=1;
    g.save.orbs=0;
    g.save.goods[1]=255;
    g.save.orbs=1000;
    assert(!game_buy(&g,1,1) && g.save.orbs==1000 && g.save.goods[1]==255);
    g.save.goods[1]=9;
    assert(!game_buy(&g,1,1) && g.save.orbs==1000);
    g.save.goods[1]=9;
    g.save.orbs=0;
    assert(!game_buy(&g,1,1));
    assert(strcmp(g.message,"Cannot carry more.")==0);
    g.save.goods[1]=0;
    g.save.orbs=100;
    assert(game_buy(&g,1,1));
    assert(g.save.goods[1]==1 && g.save.orbs==50);
    g.save.goods[1]=0;
    g.save.orbs=0;

    game_set_cart_source(NULL,GAME_BLACK2,CART_SOURCE_SLOT1);
    game_set_cart(NULL,GAME_BLACK2);
    assert(game_identify_cart("ADAE")==GAME_DIAMOND);
    assert(game_identify_cart("APAJ")==GAME_PEARL);
    assert(game_identify_cart("CPUF")==GAME_PLATINUM);
    assert(game_identify_cart("IPKE")==GAME_HEARTGOLD);
    assert(game_identify_cart("IPGJ")==GAME_SOULSILVER);
    assert(game_identify_cart("IRBO")==GAME_BLACK);
    assert(game_identify_cart("IRAO")==GAME_WHITE);
    assert(game_identify_cart("IREO")==GAME_BLACK2);
    assert(game_identify_cart("IRDO")==GAME_WHITE2);
    assert(game_identify_cart("MEEP")==GAME_UNKNOWN);
    assert(game_extension_unlocked(&g,EXT_BASIC));
    assert(!game_extension_unlocked(NULL,EXT_BASIC));
    assert(!game_extension_unlocked(&g,-1));
    assert(!game_extension_unlocked(&g,EXT_COUNT));
    assert(game_extension_price(-1)==-1);
    assert(game_extension_price(EXT_COUNT)==-1);
    assert(game_extension_price(EXT_RETRIEVAL)==100);

    assert(!game_extension_unlocked(&g,EXT_TORNADUS));
    assert(!game_extension_unlocked(&g,EXT_DIALGA));
    g.save.total_orbs=401;g.save.orbs=400;
    assert(game_extension_unlocked(&g,EXT_TORNADUS));
    complete_sphere(&g,EXT_TORNADUS);
    assert(g.save.story_phase==1);
    g.save.total_orbs=1501;
    complete_sphere(&g,EXT_THUNDURUS);
    assert(g.save.story_phase==2);
    g.save.total_orbs=3001;
    complete_sphere(&g,EXT_LANDORUS);
    assert(g.save.story_phase==3);
    assert(g.save.pending_count==3);
    game_set_cart(&g,GAME_DIAMOND);
    assert(g.cart_source==CART_SOURCE_SLOT1);
    game_set_cart_source(&g,GAME_PEARL,CART_SOURCE_TWILIGHT_SD);
    assert(g.cart==GAME_PEARL && g.cart_source==CART_SOURCE_TWILIGHT_SD);
    assert(!game_extension_unlocked(&g,EXT_DIALGA));
    assert(game_extension_unlocked(&g,EXT_PALKIA));
    game_set_cart(&g,GAME_DIAMOND);
    assert(g.cart_source==CART_SOURCE_SLOT1);
    assert(game_extension_unlocked(&g,EXT_DIALGA));
    assert(!game_extension_unlocked(&g,EXT_PALKIA));
    complete_sphere(&g,EXT_DIALGA);
    assert(g.save.legends_caught&1);
    assert(!game_extension_unlocked(&g,EXT_DIALGA));
    /* Full storage must never consume one-time species or invent a transfer. */
    g.save.pending_count=MAX_CAUGHT;
    game_set_cart(&g,GAME_HEARTGOLD);
    assert(game_extension_unlocked(&g,EXT_HOOH));
    game_begin_search(&g,EXT_HOOH);
    assert(g.screen==STATE_RADAR);
    assert(game_extension_unlocked(&g,EXT_HOOH));
    g.screen=STATE_SPHERE;
    g.session_type=0;
    g.session_species=21;
    g.ext_selection=EXT_HOOH;
    uint8_t legends_before=g.save.legends_caught;
    game_capture(&g);
    assert(g.screen==STATE_REPLACE && g.replace_kind==REPLACE_POKEMON);
    assert(g.save.pending_count==MAX_CAUGHT);
    assert(g.save.legends_caught==legends_before);
    assert(game_cancel_pending_replace(&g));
    assert(g.screen==STATE_RESULTS && g.session_caught==-4);
    assert(g.save.legends_caught==legends_before);
    g.save.pending_count=4;
    /* Clearing the single active game removes every cartridge-based unlock. */
    game_set_cart_source(&g,GAME_UNKNOWN,CART_SOURCE_NONE);
    assert(g.cart==GAME_UNKNOWN && g.cart_source==CART_SOURCE_NONE);
    assert(!game_extension_unlocked(&g,EXT_PALKIA));
    game_set_cart_source(&g,GAME_HEARTGOLD,CART_SOURCE_TWILIGHT_SD);
    assert(game_extension_unlocked(&g,EXT_HOOH));
    assert(!game_extension_unlocked(&g,EXT_PALKIA));
    g.save.orbs=3100;
    assert(game_buy(&g,0,0));assert(g.save.upgrades[0]==2);
    assert(game_buy(&g,1,0));assert(g.save.goods[0]==1);
    g.save.checksum=game_checksum(&g.save);
    assert(game_save(&g,"/tmp/dream_radar_logic_test.sav"));
    Game other;game_new(&other,0xabcd);
    assert(game_load(&other,"/tmp/dream_radar_logic_test.sav"));
    assert(other.save.legends_caught==g.save.legends_caught);
    /* Loading a legacy layout migrates its item metadata and requests a
       new private save only once the migrated state is installed. */
    SaveData legacy=g.save;
    legacy.reserved[8]=0;
    legacy.checksum=game_checksum(&legacy);
    FILE *legacy_file=fopen("/tmp/dream_radar_legacy_test.sav","wb");
    assert(legacy_file);
    assert(fwrite(&legacy,1,sizeof legacy,legacy_file)==sizeof legacy);
    assert(fclose(legacy_file)==0);
    Game migrated;game_new(&migrated,0x5555);
    migrated.requested_save=0;
    assert(game_load(&migrated,"/tmp/dream_radar_legacy_test.sav"));
    assert(migrated.save.reserved[8]==ITEM_LAYOUT_MARKER);
    assert(migrated.requested_save==1);
    remove("/tmp/dream_radar_legacy_test.sav");
    other.save.magic=0;
    assert(other.save.checksum != game_checksum(&other.save));
    assert(game_export(&g,"/tmp/dream_radar_logic_export.txt"));
    puts("PASS: single active game, source replacement, IDs, legends, upgrades, save, export");
    return 0;
}
