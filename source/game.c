/* Portable game rules; compiled in BlocksDS and host-unit tests. */
#include "game.h"
#include "item_catalog_generated.h"
#include <string.h>
#include <stdio.h>
#include <limits.h>
#include <fcntl.h>
#include <unistd.h>

static uint32_t rnd(Game *g) {
    uint32_t x = g->save.random_seed;
    if (!x) x = 0xc013ac9u;
    x ^= x << 13; x ^= x >> 17; x ^= x << 5;
    return (g->save.random_seed = x);
}
static int minimum(int a, int b) { return a < b ? a : b; }
static uint32_t add_orbs_saturating(uint32_t value, uint32_t amount) {
    return value > UINT32_MAX - amount ? UINT32_MAX : value + amount;
}
static void invalidate_archive(Game *g) {
    g->pending_export_signature=0;
    g->archive_confirm=0;
}
static void msg(Game *g, const char *s) {
    snprintf(g->message, sizeof(g->message), "%s", s);
    g->messages = 180;
}
static const char *cart_names[] = {
    "Diamond", "Pearl", "Platinum", "HeartGold", "SoulSilver",
    "Black", "White", "Black 2", "White 2", "Unknown"
};
static const char *ext_names[EXT_COUNT] = {
    "Basic Extension", "Eureka Alpha", "Eureka Beta", "Eureka Gamma",
    "Temporal Extension", "Spatial Extension", "Renegade Extension",
    "Rainbow Extension", "Diving Extension", "Special Extension A",
    "Special Extension B", "Special Extension C",
    "Retrieval Extension", "Dowsing Extension", "Simulator Alpha",
    "Simulator Beta", "Simulator Gamma"
};
// Species list used for the small playable selection, not a full encounter-table reproduction.
static const char *species_names[] = {
    "Munna", "Swablu", "Drifloon", "Riolu", "Sigilyph", "Igglybuff",
    "Shuckle", "Staryu", "Porygon", "Ralts", "Bronzor", "Togepi",
    "Smoochum", "Spiritomb", "Rotom", "Tornadus", "Thundurus", "Landorus",
    "Dialga", "Palkia", "Giratina", "Ho-Oh", "Lugia", "Beldum", "Slowpoke", "Hoothoot"
};
const char *game_item_name(int item) {
    return item >= 0 && item < RESEARCH_ITEM_TYPES ? original_item_names[item] : "Unknown item";
}
const char *game_species_name(int id) {
    return id >= 0 && id < (int)(sizeof species_names/sizeof *species_names) ? species_names[id] : "Unknown";
}
const char *game_cart_name(CartGame g) { return (g >= 0 && g <= GAME_UNKNOWN) ? cart_names[g] : "Unknown"; }
const char *game_extension_name(int e) { return (e >= 0 && e < EXT_COUNT) ? ext_names[e] : "Unknown extension"; }

CartGame game_identify_cart(const char *id) {
    // First three bytes match the NDS game-code prefix. Last is region.
    if (!id || !id[0] || !id[1] || !id[2]) return GAME_UNKNOWN;
    const char *prefixes[] = {"ADA", "APA", "CPU", "IPK", "IPG", "IRB", "IRA", "IRE", "IRD"};
    for (int i=0; i<9; i++) if (id[0]==prefixes[i][0] && id[1]==prefixes[i][1] && id[2]==prefixes[i][2]) return (CartGame)i;
    return GAME_UNKNOWN;
}
uint32_t game_checksum(const SaveData *p) {
    const uint8_t *b = (const uint8_t *)p;
    uint32_t h = 2166136261u;
    const size_t end = offsetof(SaveData, checksum);
    for (size_t i = 0; i < sizeof *p; i++) {
        if (i >= end && i < end+sizeof p->checksum) continue;
        h = (h ^ b[i]) * 16777619u;
    }
    return h;
}
void game_new(Game *g, uint32_t seed) {
    /* Public game initialization must safely reject an absent destination. */
    if (!g) return;
    memset(g, 0, sizeof *g);
    g->save.magic = SAVE_MAGIC; g->save.version = SAVE_VERSION;
    g->save.random_seed = seed ? seed : 0x12345678u;
    g->save.reserved[8]=ITEM_LAYOUT_MARKER;
    for(int i=0;i<MAX_ITEMS;i++)g->save.reserved[2+i]=(uint8_t)(i+1);
    g->replaced_slot=-1;
    /* No reward or encounter exists at startup. A valid ID of zero is
       Munna/item 0, not an appropriate unset sentinel. */
    g->session_caught=-1;
    g->session_item=-1;
    g->session_species=-1;
    for (int i = 0; i < 3; i++) g->save.upgrades[i] = 1;
    g->save.cloud_count = 5;
    g->save.camera_enabled = 1;
    g->save.optical_aim = 0;
    g->screen = STATE_TITLE;
    g->cart = GAME_UNKNOWN;
    g->cart_source = CART_SOURCE_NONE;
    g->aim_x = 128; g->aim_y = 96;
}
int game_load(Game *g, const char *file) {
    if (!g || !file || !*file) return 0;
    FILE *f = fopen(file,"rb"); if (!f) return 0;
    SaveData s;
    int ok = fread(&s,1,sizeof s,f)==sizeof s;
    /* An oversized or concatenated file is not a valid private save. */
    if(ok && fgetc(f)!=EOF)ok=0;
    if(fclose(f)!=0)ok=0;
    if (!ok || s.magic != SAVE_MAGIC || s.version != SAVE_VERSION || s.checksum != game_checksum(&s)) return 0;
    if (s.cloud_count>MAX_CLOUDS || s.pending_count>MAX_CAUGHT ||
        s.story_phase>3 || (s.legends_caught & ~31u) ||
        s.intro_seen>1 || s.optical_aim>1 || s.camera_enabled>1 ||
        s.reserved[0]>3 || s.reserved[1]>7) return 0;
    /* Optional background metadata must never invalidate otherwise sound
       game progress. Repair an out-of-range selection after checksum
       verification, and persist the repaired record on the next save. */
    int repaired_background=0;
    if(s.reserved[11]==0xB6u &&
       ((unsigned)s.reserved[9] | ((unsigned)s.reserved[10]<<8))>=1000u) {
        s.reserved[9]=0;
        s.reserved[10]=0;
        s.reserved[11]=0;
        repaired_background=1;
    }
    for (int i=0;i<3;i++) if (s.upgrades[i]<1 || s.upgrades[i]>5 || s.goods[i]>9) return 0;
    for (int i=0;i<MAX_CAUGHT;i++) if (i<s.pending_count && s.pending[i]>25) return 0;
    /* Older v3 homebrew saves indexed item stacks by item ID. Reconstruct
       type metadata in unused bytes without changing save size/version. */
    int migrated_item_layout=0;
    if(s.reserved[8]!=ITEM_LAYOUT_MARKER) {
        migrated_item_layout=1;
        s.reserved[8]=ITEM_LAYOUT_MARKER;
        for(int i=0;i<MAX_ITEMS;i++)s.reserved[2+i]=(uint8_t)(i+1);
    } else {
        for(int i=0;i<MAX_ITEMS;i++) {
            if(s.reserved[2+i]<1 || s.reserved[2+i]>RESEARCH_ITEM_TYPES)return 0;
        }
    }
    /* Any in-memory migration changes checksummed fields. Keep the live
       record internally consistent before the repaired snapshot is written. */
    if(migrated_item_layout || repaired_background)
        s.checksum=game_checksum(&s);
    g->save = s;
    if(migrated_item_layout || repaired_background)g->requested_save=1;
    /* The three secret research extensions persist in unused reserved bytes,
       preserving version 3 save compatibility with previous milestone builds. */
    g->special_unlocked = s.reserved[1];
    return 1;
}
int game_save(Game *g, const char *file) {
    if (!g || !file || !*file) return 0;
    /* Prepare an immutable snapshot before opening the destination.
       This preserves live state and avoids creating an empty file if
       snapshot preparation ever changes or fails in future. */
    SaveData snapshot=g->save;
    /* Do not truncate a valid save with a runtime record the loader would
       reject. Check the gameplay-critical bounded fields before fopen(). */
    if(snapshot.magic!=SAVE_MAGIC || snapshot.version!=SAVE_VERSION ||
       snapshot.pending_count>MAX_CAUGHT || snapshot.cloud_count>MAX_CLOUDS ||
       snapshot.story_phase>3 || (snapshot.legends_caught & ~31u) ||
       snapshot.intro_seen>1 || snapshot.optical_aim>1 ||
       snapshot.camera_enabled>1 || snapshot.reserved[0]>3 ||
       snapshot.reserved[1]>7 ||
       snapshot.reserved[8]!=ITEM_LAYOUT_MARKER)return 0;
    for(int i=0;i<3;i++)
        if(snapshot.upgrades[i]<1 || snapshot.upgrades[i]>5 ||
           snapshot.goods[i]>9)return 0;
    for(int i=0;i<snapshot.pending_count;i++)
        if(snapshot.pending[i]>25)return 0;
    for(int i=0;i<MAX_ITEMS;i++)
        if(snapshot.reserved[2+i]<1 ||
           snapshot.reserved[2+i]>RESEARCH_ITEM_TYPES)return 0;
    snapshot.checksum=game_checksum(&snapshot);
    FILE *f=fopen(file,"wb"); if (!f) return 0;
    int okay = fwrite(&snapshot,1,sizeof snapshot,f)==sizeof snapshot;
    if (fclose(f)) okay=0;
    return okay;
}
void game_regen_clouds(Game *g, uint32_t now) {
    if (!g) return;
    if (!g->save.last_cloud_time) {
        /* Persist the initial anchor so a restart does not reset recharge.
           A zero clock reading cannot establish a usable anchor. */
        if (now) { g->save.last_cloud_time=now; g->requested_save=1; }
        return;
    }
    if (now < g->save.last_cloud_time) { // reset after clock adjustment; do not award clouds
        g->save.last_cloud_time=now;g->requested_save=1;return;
    }
    /* A malformed upgrade value must not create an impossible reservoir. */
    uint32_t upgrade=g->save.upgrades[2];
    if(upgrade<1u)upgrade=1u;
    if(upgrade>5u)upgrade=5u;
    /* The DS clock is second-granularity. Preserve the partial interval
       until it completes rather than rounding early. */
    uint32_t elapsed = now - g->save.last_cloud_time;
    uint32_t steps = elapsed / 300u;
    if (steps > 0) {
        /* Keep elapsed intervals unsigned: large clock jumps must not
           overflow a signed int or reduce the accumulated cloud count. */
        uint32_t capacity = 5u*(upgrade+1u);
        if (capacity > MAX_CLOUDS) capacity = MAX_CLOUDS;
        uint32_t count = (uint32_t)g->save.cloud_count;
        if (count > capacity) count = capacity;
        if (steps >= capacity-count) count = capacity;
        else count += steps;
        g->save.cloud_count=(uint8_t)count;
        /* Even when already full, advance the recharge anchor to avoid
           a stockpile of elapsed time instantly refilling spent clouds. */
        /* The unsigned product is bounded by elapsed, so this addition
           cannot wrap when now is at or below UINT32_MAX. */
        g->save.last_cloud_time+=steps*300u;
        g->requested_save=1;
    }
}
const char *game_cart_source_name(CartSource source) {
    switch (source) {
        case CART_SOURCE_SLOT1: return "Slot-1 cartridge";
        case CART_SOURCE_TWILIGHT_SD: return "TWiLight SD save";
        default: return "No active game";
    }
}
void game_set_cart_source(Game *g, CartGame cart, CartSource source) {
    if (!g) return;
    /* A new selection completely REPLACES the previous active game.
       Never aggregate game identities to unlock multiple legends. */
    if (cart < GAME_DIAMOND || cart >= GAME_UNKNOWN || source == CART_SOURCE_NONE ||
        (source != CART_SOURCE_SLOT1 && source != CART_SOURCE_TWILIGHT_SD)) {
        g->cart = GAME_UNKNOWN;
        g->cart_source = CART_SOURCE_NONE;
    } else {
        g->cart = cart;
        g->cart_source = source;
    }
    g->cart_read_attempted=1;
}
void game_set_cart(Game *g, CartGame cart) {
    game_set_cart_source(g,cart,CART_SOURCE_SLOT1);
}
int game_extension_price(int ext) {
    if (ext<0 || ext>=EXT_COUNT) return -1;
    if (ext==EXT_RETRIEVAL || ext==EXT_DOWSING) return 100;
    if (ext >= EXT_SIM_TORNADUS && ext <= EXT_SIM_LANDORUS) return 400+(ext-EXT_SIM_TORNADUS)*200;
    return 0;
}
int game_extension_unlocked(Game *g, int ext) {
    if (!g || ext<0 || ext>=EXT_COUNT) return 0;
    if (ext == EXT_BASIC) return 1;
    if (ext >= EXT_TORNADUS && ext <= EXT_LANDORUS) {
        const uint32_t thresholds[]={400,1500,3000};
        int phase=ext-EXT_TORNADUS;
        return g->save.story_phase==phase && g->save.total_orbs>=thresholds[phase];
    }
    if (ext==EXT_RETRIEVAL) return g->save.total_orbs>=200;
    if (ext==EXT_DOWSING) return g->save.story_phase>=1;
    if (ext>=EXT_SIM_TORNADUS && ext<=EXT_SIM_LANDORUS) return g->save.story_phase>=3;
    if (ext>=EXT_BELDUM && ext<=EXT_HOOTHOOT)
        return (g->special_unlocked & (1<<(ext-EXT_BELDUM)))!=0;
    if (ext >= EXT_DIALGA && ext <= EXT_LUGIA) {
        if (g->save.story_phase < 3) return 0;
        if (g->save.legends_caught & (1 << (ext - EXT_DIALGA))) return 0;
        return g->cart == (CartGame)(ext - EXT_DIALGA);
    }
    return 0;
}
void game_secret_key(Game *g, int key) {
    if (!g) return;
    // International secret codes; key values are DS KEY_* bitmasks supplied by caller.
    const int codes[3][8]={{6,5,7,4,3,9,8,0}, {6,7,5,4,2,9,8,0}, {9,8,2,3,4,5,2,3}};
    const int sizes[3]={7,7,8};
    for (int i=0;i<3;i++) {
        int j=g->cheat_progress[i];
        /* Runtime progress is not saved; sanitize it before indexing a code. */
        if (j<0 || j>=sizes[i]) j=0;
        if (key==codes[i][j]) j++;
        else j=(key==codes[i][0])?1:0;
        if (j==sizes[i]) {
            g->special_unlocked |= 1<<i;
            g->save.reserved[1]=(uint8_t)g->special_unlocked;
            g->requested_save=1;
            msg(g,"Special research extension permanently unlocked!");j=0;
        }
        g->cheat_progress[i]=j;
    }
}
void game_begin_search(Game *g, int ext) {
    if (!g) return;
    /* Never restart an encounter or replace an unresolved storage choice. */
    if (g->screen==STATE_RADAR || g->screen==STATE_SPHERE || g->screen==STATE_REPLACE) return;
    if (ext<0 || ext>=EXT_COUNT || !game_extension_unlocked(g,ext)) { msg(g,"This Extension is locked.");return; }
    /* All three cloud-based research modes need at least one cloud.
       Never charge a paid extension when there is nothing to scan. */
    if (!g->save.cloud_count &&
        (ext==EXT_BASIC || ext==EXT_RETRIEVAL || ext==EXT_DOWSING)) {
        msg(g,"No Dream Clouds yet. Wait for them to return.");
        return;
    }
    /* Full storage now offers an explicit, cancelable replacement choice AFTER
       capture. No one-time encounter flag changes before acceptance. */
    int price=game_extension_price(ext);
    if (g->save.orbs < (uint32_t)price) {msg(g,"Not enough Dream Orbs for this search."); return;}
    g->save.orbs-=price;
    g->requested_save=1;
    g->ext_selection=ext;
    g->screen=STATE_RADAR;
    /* A new radar session must not retain the previous sphere timer. */
    g->capture_hp=0;g->capture_timeout=0;g->cloud_hit=0;
    g->session_orbs=0; g->session_caught=-1;g->session_item=-1;
    /* Starting a new radar scan must not expose the previous species. */
    g->session_species=-1;
    g->replace_kind=REPLACE_NONE;g->replace_confirm=0;g->replaced_slot=-1;
    g->session_type=0;g->freeze_frames=0;g->slow_frames=0;
    g->aim_x=128;g->aim_y=90;
    g->active_clouds = (ext==EXT_BASIC || ext==EXT_RETRIEVAL || ext==EXT_DOWSING)
                     ? minimum(MAX_CLOUDS,g->save.cloud_count) : 1;
    if (ext==EXT_BASIC || ext==EXT_RETRIEVAL || ext==EXT_DOWSING) {
        g->save.cloud_count=0;g->requested_save=1;
    }
    for (int i=0;i<MAX_CLOUDS;i++) {
        Cloud *c = &g->clouds[i];
        /* Spread active clouds across the radar instead of stacking hit
           targets at nearly identical screen positions. Keep retries bounded
           even when the screen is crowded with 30 clouds. */
        if (i<g->active_clouds) {
            for (int attempt=0;attempt<32;attempt++) {
                c->x=24+(rnd(g)%207);c->y=24+(rnd(g)%129);
                int overlaps=0;
                for (int j=0;j<i;j++) {
                    int dx=c->x-g->clouds[j].x,dy=c->y-g->clouds[j].y;
                    if(dx*dx+dy*dy<20*20) { overlaps=1;break; }
                }
                if(!overlaps)break;
            }
        } else {
            c->x=0;c->y=0; /* Inactive clouds never need random placement. */
        }
        c->alive=(i<g->active_clouds);c->cooldown=0;
        c->kind=c->alive && (((i%5)==0 || ext!=EXT_BASIC)?1:0);
    }
}
static int choice_species(Game *g) {
    int ext = g->ext_selection;
    if (ext >= EXT_TORNADUS && ext <= EXT_LANDORUS) return 15+(ext - EXT_TORNADUS);
    if (ext >= EXT_SIM_TORNADUS && ext <= EXT_SIM_LANDORUS) return 15+(ext-EXT_SIM_TORNADUS);
    if (ext >= EXT_DIALGA && ext <= EXT_LUGIA) return 18+(ext-EXT_DIALGA);
    if (ext >= EXT_BELDUM && ext <= EXT_HOOTHOOT) return 23+(ext-EXT_BELDUM);
    static const int pools[4][6] = {{0,1,2,3,4,0}, {5,6,1,2,4,3}, {7,8,9,10,3,4}, {11,12,13,14,4,8}};
    return pools[minimum(3,g->save.story_phase)][rnd(g)%6];
}
static void start_sphere(Game *g) {
    g->screen=STATE_SPHERE;
    g->capture_timeout= (g->ext_selection==EXT_BASIC && g->save.story_phase==0 && g->save.searches==0) ? 9999 * 60 : (90+g->save.upgrades[1]*30)*60;
    g->sphere_x=105;g->sphere_y=90;
    g->sphere_vx=1+(rnd(g)%3);g->sphere_vy=1+(rnd(g)%2);
    g->capture_hp=0;
    /* Start every capture with a fresh movement and support state. */
    g->capture_timeout=g->capture_timeout<1?1:g->capture_timeout;
    /* Temporary support effects cannot carry over from another encounter. */
    g->freeze_frames=0;
    g->slow_frames=0;
    /* Dedicated legendary and special encounters cannot randomly turn into
       an item. Only cloud-search modes roll the item encounter chance. */
    /* Retrieval and Dowsing are item-focused research; ordinary cloud
       hunting retains the provisional one-in-four item encounter roll. */
    g->session_type = (g->ext_selection==EXT_RETRIEVAL ||
                       g->ext_selection==EXT_DOWSING ||
                       (g->ext_selection==EXT_BASIC && (rnd(g)%4)==0)) ? 1:0;
    /* Do not consume a Pokemon species roll for item-only research sessions.
       A non-Pokemon result has no species to transfer or display. */
    g->session_species=g->session_type ? -1 : choice_species(g);
    /* Prototype drop selection: broaden item variety as story research progresses.
       The 23 labels are original; these drop probabilities are NOT extracted
       from the original encounter/item tables. */
    static const int item_pool_sizes[4]={6,11,17,23};
    int phase=g->save.story_phase>3?3:g->save.story_phase;
    /* Pokemon-only encounters must not roll or expose an unrelated item. */
    g->session_item=g->session_type ? (int)(rnd(g)%(uint32_t)item_pool_sizes[phase]) : -1;
}
/* Support effects belong to gameplay state, never the renderer. A failed
   activation must not consume inventory or trigger a save. */
SupportStatus game_support_status(const Game *g, int slot) {
    if (!g || slot < 0 || slot >= 3 || g->screen != STATE_SPHERE ||
        g->capture_timeout <= 0) return SUPPORT_UNAVAILABLE;
    /* Show ongoing effects even after the last charge has been spent. */
    if ((slot == 0 && g->freeze_frames > 0) ||
        (slot == 1 && g->slow_frames > 0)) return SUPPORT_ACTIVE;
    if (g->save.goods[slot] == 0) return SUPPORT_EMPTY;
    if (g->save.goods[slot] > 9 ||
        (slot == 2 && g->capture_timeout == INT_MAX)) return SUPPORT_UNAVAILABLE;
    return SUPPORT_READY;
}
int game_use_support(Game *g, int slot) {
    if (!g || slot < 0 || slot >= 3) return 0;
    SupportStatus status = game_support_status(g,slot);
    if (status != SUPPORT_READY) {
        if (status == SUPPORT_ACTIVE) msg(g,"This support effect is still active.");
        else if (status == SUPPORT_EMPTY) msg(g,"No charges left. Restock in the Development Lab.");
        else msg(g,"Support unavailable. Use it during an active encounter.");
        return 0;
    }
    /* Preserve every remaining effect frame; never spend a charge refreshing. */
    if (slot == 0) {
        g->freeze_frames = 300;
        msg(g,"Vortex Charge: target frozen for 5 seconds.");
    } else if (slot == 1) {
        g->slow_frames = 300;
        msg(g,"Dragnet Charge: target slowed for 5 seconds.");
    } else {
        /* Never spend an Energy Recharge if its timer cannot increase.
           Saturate the addition without overflowing signed arithmetic. */
        if (g->capture_timeout <= 0 || g->capture_timeout >= 2147483647) return 0;
        if (g->capture_timeout > 2147483647 - 1500)
            g->capture_timeout = 2147483647;
        else g->capture_timeout += 1500;
        msg(g,"Energy Recharge: encounter time extended.");
    }
    g->save.goods[slot]--;
    g->requested_save = 1;
    return 1;
}
void game_fire(Game *g) {
    if (!g) return;
    /* Aim comes from input devices; reject invalid coordinates before doing
       distance arithmetic (including extreme external input values). */
    if(g->aim_x<0 || g->aim_x>255 || g->aim_y<0 || g->aim_y>191)return;
    if (g->screen==STATE_RADAR) {
        /* When hit circles overlap, choose the closest cloud, not the
           lowest array index. This keeps stylus aiming deterministic. */
        int selected=-1;
        int64_t nearest=19*19;
        for (int i=0;i<g->active_clouds && i<MAX_CLOUDS;i++) {
            const Cloud *c=&g->clouds[i];
            /* Corrupt or uninitialized coordinates are not hittable. This
               also bounds squared distances before any arithmetic. */
            if(c->x<0 || c->x>255 || c->y<0 || c->y>191)continue;
            int64_t dx=(int64_t)c->x-g->aim_x,dy=(int64_t)c->y-g->aim_y;
            int64_t distance=dx*dx+dy*dy;
            if(c->alive && distance<nearest) {
                nearest=distance;
                selected=i;
            }
        }
        if(selected>=0) {
            Cloud *c=&g->clouds[selected];
            c->alive=0;
            /* Damaged runtime counters must not overflow on a successful hit. */
            if(g->cloud_hit<0)g->cloud_hit=0;
            if(g->cloud_hit<INT_MAX)g->cloud_hit++;
            if (c->kind && (g->ext_selection!=EXT_BASIC || (rnd(g)%3)==0)) {
                start_sphere(g);return;
            }
            int reward = 3+(rnd(g)%5);
            g->session_orbs=g->session_orbs>INT_MAX-reward ? INT_MAX : g->session_orbs+reward;
            g->save.orbs=add_orbs_saturating(g->save.orbs,(uint32_t)reward);
            g->save.total_orbs=add_orbs_saturating(g->save.total_orbs,(uint32_t)reward);
            g->requested_save=1;
            if (g->cloud_hit >= g->active_clouds) {
                if(g->save.searches<UINT32_MAX)g->save.searches++;
                g->screen=STATE_RESULTS;
                g->requested_save=1;
            }
        }
    } else if (g->screen==STATE_SPHERE) {
        /* An expired encounter must not be captured between timer ticks. */
        if(g->capture_timeout<=0)return;
        /* Sphere coordinates must be on the DS viewport. Squaring two
           arbitrary signed 32-bit coordinates could overflow int64_t. */
        if(g->sphere_x<0 || g->sphere_x>255 ||
           g->sphere_y<0 || g->sphere_y>191)return;
        int64_t dx=(int64_t)g->sphere_x-g->aim_x, dy=(int64_t)g->sphere_y-g->aim_y;
        if (dx*dx+dy*dy<22*22) {
            /* Clamp damaged runtime state and never overflow capture HP. */
            int level=g->save.upgrades[0];
            if(level<1 || level>5)return;
            int damage=level*(g->freeze_frames>0 ? 5 : 3);
            if(g->capture_hp<0)g->capture_hp=0;
            if(g->capture_hp>=240-damage)g->capture_hp=240;
            else g->capture_hp+=damage;
            if (g->capture_hp>=240) game_capture(g);
        }
    }
}
/* Item IDs and quantities are separate. Previously the item ID was the
   array index; version-3 saves are migrated in game_load(). */
int game_item_slot_kind(const Game *g, int slot) {
    if(!g || slot<0 || slot>=MAX_ITEMS || !g->save.pending_items[slot])return -1;
    int type=(int)g->save.reserved[2+slot]-1;
    return (type>=0 && type<RESEARCH_ITEM_TYPES) ? type : -1;
}
static void accept_pokemon(Game *g, int species) {
    if(species>=15 && species<=17 && g->save.story_phase == species-15)
        g->save.story_phase++;
    if(species>=18 && species<=22)
        g->save.legends_caught |= (uint8_t)(1u<<(species-18));
    /* Keep lifetime capture records monotonic at the save format limit. */
    if(g->save.caught_count<UINT32_MAX)g->save.caught_count++;
    g->session_caught=species;
}
static void conclude_capture(Game *g) {
    /* Support effects are encounter-local, including on successful captures
       and when full storage opens a replacement decision. */
    g->freeze_frames=0;
    g->slow_frames=0;
    if(g->save.searches<UINT32_MAX)g->save.searches++;
    g->requested_save=1;
    g->screen=STATE_RESULTS;
    g->replace_kind=REPLACE_NONE;
    g->replace_confirm=0;
}
/* A missing or full type stack can use a genuinely empty stack slot. */
static int item_available_slot(const Game *g, int item) {
    for(int i=0;i<MAX_ITEMS;i++)
        if(game_item_slot_kind(g,i)==item &&
           g->save.pending_items[i]<MAX_ITEM_STACK)return i;
    for(int i=0;i<MAX_ITEMS;i++)if(!g->save.pending_items[i])return i;
    return -1;
}
void game_capture(Game *g) {
    /* All capture entry points must enforce the active encounter timer. */
    if(!g || g->screen!=STATE_SPHERE || g->capture_timeout<=0)return;
    /* Only defined Pokemon (0) and item (1) encounter types award rewards. */
    if(g->session_type!=0 && g->session_type!=1)return;
    /* Simulator results never take a research slot, even if an unexpected
       encounter type arrives from a damaged or out-of-sync runtime state. */
    if(g->ext_selection>=EXT_SIM_TORNADUS && g->ext_selection<=EXT_SIM_LANDORUS) {
        g->session_caught=-3;
        conclude_capture(g);
        return;
    }
    if(g->session_type==1) {
        int item=g->session_item;
        if(item<0 || item>=RESEARCH_ITEM_TYPES) {
            g->session_caught=-4;
            conclude_capture(g);
            return;
        }
        int slot=item_available_slot(g,item);
        if(slot>=0) {
            invalidate_archive(g);
            g->save.reserved[2+slot]=(uint8_t)(item+1);
            /* item_available_slot only chooses a non-full stack or an empty
               slot, so this increment is guaranteed to stay within 1..255. */
            g->save.pending_items[slot]++;
            g->session_caught=-2;
            conclude_capture(g);
            return;
        }
        g->replace_kind=REPLACE_ITEM;
        g->replace_value=item;
    } else {
        int species=g->session_species;
        if(species<0 || species>25) {
            g->session_caught=-4;
            conclude_capture(g);
            return;
        }
        if(g->save.pending_count<MAX_CAUGHT) {
            invalidate_archive(g);
            g->save.pending[g->save.pending_count++]=(uint8_t)species;
            accept_pokemon(g,species);
            conclude_capture(g);
            return;
        }
        g->replace_kind=REPLACE_POKEMON;
        g->replace_value=species;
    }
    /* Full: pause safely for a deliberate slot choice. No data changes yet. */
    g->replace_selected=0;
    g->replace_confirm=0;
    /* Encounter has stopped while the player decides what to keep. */
    g->freeze_frames=0;
    g->slow_frames=0;
    g->screen=STATE_REPLACE;
    msg(g,"Storage full: choose a slot to replace, or press B to keep it.");
}
int game_replace_pending(Game *g, int slot) {
    if(!g || g->screen!=STATE_REPLACE)return 0;
    if(g->replace_kind==REPLACE_POKEMON) {
        /* Both the selected slot and saved queue length must fit the actual
           six-element array, even when runtime state is damaged. */
        if(g->save.pending_count>MAX_CAUGHT ||
           slot<0 || slot>=MAX_CAUGHT || slot>=g->save.pending_count ||
           g->replace_value<0 || g->replace_value>25)return 0;
        invalidate_archive(g);
        g->save.pending[slot]=(uint8_t)g->replace_value;
        accept_pokemon(g,g->replace_value);
    } else if(g->replace_kind==REPLACE_ITEM) {
        if(slot<0 || slot>=MAX_ITEMS || !g->save.pending_items[slot] ||
           g->replace_value<0 || g->replace_value>=RESEARCH_ITEM_TYPES)return 0;
        invalidate_archive(g);
        g->save.reserved[2+slot]=(uint8_t)(g->replace_value+1);
        g->save.pending_items[slot]=1;
        g->session_caught=-2;
    } else return 0;
    g->replaced_slot=slot;
    conclude_capture(g);
    msg(g,"Research slot replaced. Previous contents discarded.");
    return 1;
}
int game_cancel_pending_replace(Game *g) {
    if(!g || g->screen!=STATE_REPLACE || g->replace_kind==REPLACE_NONE)return 0;
    g->session_caught=-4;
    /* Declining full storage earns neither the proposed Pokemon nor item. */
    g->session_species=-1;
    g->session_item=-1;
    g->session_type=0;
    g->replaced_slot=-1;
    conclude_capture(g);
    msg(g,"Replacement canceled; stored Pokemon and items kept.");
    return 1;
}
int game_leave_search(Game *g) {
    if(!g || (g->screen!=STATE_RADAR && g->screen!=STATE_SPHERE))return 0;
    if(g->save.searches<UINT32_MAX)g->save.searches++;
    g->screen=STATE_RESULTS;
    g->freeze_frames=0;
    g->slow_frames=0;
    g->capture_timeout=0;
    /* Back exits without awarding an unfinished capture or item. */
    g->session_caught=-1;
    g->session_item=-1;
    g->session_species=-1;
    g->session_type=0;
    g->capture_hp=0;
    g->requested_save=1;
    return 1;
}
void game_tick(Game *g) {
    if (!g) return;
    /* The play-time counter is persisted as uint32_t; never wrap to zero. */
    if (g->save.frames_played<UINT32_MAX)g->save.frames_played++;
    if (g->messages>0)g->messages--;
    if (g->screen==STATE_SPHERE) {
        /* Apply effects to the entire current frame before decrementing.
           Otherwise the last frozen frame moves one tick too early. */
        int frozen_this_frame = g->freeze_frames > 0;
        int slowed_this_frame = g->slow_frames > 0;
        if (g->freeze_frames>0) g->freeze_frames--;
        /* Freeze already prevents all movement. Preserve Dragnet's remaining
           duration until the frozen frame ends instead of wasting it. */
        if (g->slow_frames>0 && !frozen_this_frame) g->slow_frames--;
        if (!frozen_this_frame && (!slowed_this_frame || g->save.frames_played%3==0)) {
            /* Use wide intermediates: malformed velocities must never trigger
               signed overflow before the viewport clamp. */
            int64_t nx=(int64_t)g->sphere_x+g->sphere_vx;
            int64_t ny=(int64_t)g->sphere_y+g->sphere_vy;
            /* Bounce based on the unclamped position; clamping first hides
               boundary crossings and leaves the target stuck at an edge. */
            g->sphere_x=nx<20?20:nx>236?236:(int)nx;
            g->sphere_y=ny<30?30:ny>164?164:(int)ny;
            if (nx<20 && g->sphere_vx<0)
                g->sphere_vx=g->sphere_vx==INT32_MIN?INT32_MAX:-g->sphere_vx;
            if (nx>236 && g->sphere_vx>0)g->sphere_vx=-g->sphere_vx;
            if (ny<30 && g->sphere_vy<0)
                g->sphere_vy=g->sphere_vy==INT32_MIN?INT32_MAX:-g->sphere_vy;
            if (ny>164 && g->sphere_vy>0)g->sphere_vy=-g->sphere_vy;
        }
        if (g->capture_timeout>0) g->capture_timeout--;
        if (g->capture_timeout<=0) {
            g->capture_timeout=0;
            g->screen=STATE_RESULTS;g->session_caught=-1;
            g->session_item=-1;g->session_species=-1;g->session_type=0;
            g->capture_hp=0;
            g->freeze_frames=0;g->slow_frames=0;
            if(g->save.searches<UINT32_MAX)g->save.searches++;
            g->requested_save=1;
            msg(g,"The Pokemon escaped!");
        }
    }
}
PurchaseStatus game_purchase_status(const Game *g,int kind,int idx,int *cost) {
    static const int costs[]={0,100,500,1000,1500};
    if(cost)*cost=0;
    if(!g || idx<0 || idx>=3)return PURCHASE_INVALID;
    int price;
    if (kind==0) {
        int level=g->save.upgrades[idx];
        if(level<1 || level>5)return PURCHASE_INVALID;
        if(level==5)return PURCHASE_MAX;
        price=costs[level];
    } else if(kind==1) {
        if(g->save.goods[idx]>9)return PURCHASE_INVALID;
        if(g->save.goods[idx]==9)return PURCHASE_FULL;
        price=idx==0?100:50;
    } else return PURCHASE_INVALID;
    if(cost)*cost=price;
    return g->save.orbs<(uint32_t)price?PURCHASE_POOR:PURCHASE_READY;
}
int game_buy(Game *g, int kind, int idx) {
    if(!g)return 0;
    int cost=0;
    PurchaseStatus status=game_purchase_status(g,kind,idx,&cost);
    if(status!=PURCHASE_READY) {
        if(status==PURCHASE_MAX)msg(g,"Already at maximum level.");
        else if(status==PURCHASE_FULL)msg(g,"Cannot carry more.");
        else if(status==PURCHASE_POOR)msg(g,"Not enough Dream Orbs.");
        else if(idx>=0 && idx<3 && kind==0)msg(g,"Invalid equipment level.");
        else if(idx>=0 && idx<3 && kind==1)msg(g,"Invalid support inventory.");
        return 0;
    }
    g->save.orbs-=(uint32_t)cost;
    if(kind==0)g->save.upgrades[idx]++;
    else g->save.goods[idx]++;
    g->requested_save=1;
    msg(g,kind==0?"Equipment upgraded!":"Support item purchased!");
    return 1;
}
static uint32_t pending_signature(const Game *g) {
    uint32_t h=2166136261u;
    h=(h ^ g->save.pending_count)*16777619u;
    for(int i=0;i<g->save.pending_count && i<MAX_CAUGHT;i++)
        h=(h ^ g->save.pending[i])*16777619u;
    for(int i=0;i<MAX_ITEMS;i++) {
        h=(h ^ g->save.pending_items[i])*16777619u;
        h=(h ^ (g->save.pending_items[i] ? g->save.reserved[2+i] : 0))*16777619u;
    }
    return h ? h : 1;
}
int game_release_archived_pending(Game *g) {
    if(!g || g->save.pending_count>MAX_CAUGHT)return 0;
    /* An archive signature must not authorize clearing data whose layout
       no longer matches the current private-save item format. */
    if(g->save.reserved[8]!=ITEM_LAYOUT_MARKER)return 0;
    for(int i=0;i<g->save.pending_count;i++)
        if(g->save.pending[i]>25)return 0;
    for(int i=0;i<MAX_ITEMS;i++)
        if(g->save.pending_items[i] &&
           (g->save.reserved[2+i]<1 ||
            g->save.reserved[2+i]>RESEARCH_ITEM_TYPES))return 0;
    if(!g->pending_export_signature ||
       g->pending_export_signature!=pending_signature(g))return 0;
    int have_pending=g->save.pending_count>0;
    for(int i=0;i<MAX_ITEMS;i++)if(g->save.pending_items[i])have_pending=1;
    if(!have_pending)return 0;
    invalidate_archive(g);
    g->save.pending_count=0;
    memset(g->save.pending,0,sizeof g->save.pending);
    memset(g->save.pending_items,0,sizeof g->save.pending_items);
    g->requested_save=1;
    return 1;
}
int game_export(Game *g, const char *path) {
    /* This is a private TEXT archive, not an official Unova Link transfer.
       Stage the export beside the destination so a failed write or rename
       cannot destroy the previous complete archive. */
    if (!g || !path || !*path) return 0;
    g->pending_export_signature=0;
    if(g->save.pending_count>MAX_CAUGHT)return 0;
    for(int i=0;i<g->save.pending_count;i++)
        if(g->save.pending[i]>25)return 0;
    for(int i=0;i<MAX_ITEMS;i++)
        if(g->save.pending_items[i] &&
           (g->save.reserved[2+i]<1 ||
            g->save.reserved[2+i]>RESEARCH_ITEM_TYPES))return 0;
    size_t n=strlen(path);
    if (n > 480) return 0;
    char temporary[512];
    snprintf(temporary,sizeof temporary,"%s.tmp",path);
    /* Create the staging file atomically: never overwrite an existing file,
       including if one appears between checking and opening the path. */
    int fd=open(temporary,O_WRONLY|O_CREAT|O_EXCL,0600);
    if(fd<0)return 0;
    FILE *f=fdopen(fd,"wb");
    if(!f) { close(fd); remove(temporary); return 0; }
    int ok=1;
    if (fprintf(f,"DREAM_RADAR_DSI_PENDING_V1\nSource: unofficial demake\nTarget: Black 2 / White 2\n")<0) ok=0;
    if (fprintf(f,"WARNING: not compatible with Unova Link; do not inject into a cartridge save.\n")<0) ok=0;
    if (fprintf(f,"Orbs: %lu\n",(unsigned long)g->save.orbs)<0) ok=0;
    for (int i=0;i<g->save.pending_count && ok;i++)
        if (fprintf(f,"Pokemon %d: %s\n",i+1,game_species_name(g->save.pending[i]))<0) ok=0;
    for (int i=0;i<MAX_ITEMS && ok;i++) if(g->save.pending_items[i])
        if (fprintf(f,"Item slot %d: %s x%d\n",i+1,
                    game_item_name(game_item_slot_kind(g,i)),g->save.pending_items[i])<0) ok=0;
    if (fflush(f)!=0) ok=0;
    if (fclose(f)!=0) ok=0;
    if (!ok) { remove(temporary); return 0; }
    if (rename(temporary,path)!=0) { remove(temporary); return 0; }
    g->pending_export_signature=pending_signature(g);
    return 1;
}
