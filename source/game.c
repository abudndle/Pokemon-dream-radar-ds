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
/* Dream Orbs start pink, then unlock green/orange/blue after each
 * Therian capture. Dominant color belongs to the most recently completed
 * search and is stored in previously unused v3 save bytes 12 and 13. */
OrbColor game_orb_color(const Game *g) {
    if(!g || g->save.reserved[13]!=ORB_COLOR_LAYOUT_MARKER)
        return ORB_PINK;
    unsigned color=g->save.reserved[12];
    unsigned unlocked=g->save.story_phase>3u?3u:g->save.story_phase;
    return color<=unlocked ? (OrbColor)color : ORB_PINK;
}
OrbColor game_orb_live_color(const Game *g) {
    if(!g)return ORB_PINK;
    unsigned unlocked=g->save.story_phase>3u?3u:g->save.story_phase;
    return (OrbColor)((g->save.frames_played/45u)%(unlocked+1u));
}
OrbColor game_dream_orb_color(const Game *g,int slot) {
    if(!g || slot<0 || slot>=MAX_DREAM_ORBS)return ORB_PINK;
    unsigned unlocked=g->save.story_phase>3u?3u:g->save.story_phase;
    unsigned phase=g->dream_orbs[slot].color_phase;
    return (OrbColor)(((g->save.frames_played/45u)+phase)%(unlocked+1u));
}
int game_active_dream_orbs(const Game *g) {
    if(!g)return 0;
    int count=0;
    for(int i=0;i<MAX_DREAM_ORBS;i++)if(g->dream_orbs[i].alive)count++;
    return count;
}
const char *game_orb_color_name(OrbColor color) {
    static const char *const names[]={"PINK","GREEN","ORANGE","BLUE"};
    return color>=ORB_PINK && color<ORB_COLOR_COUNT?names[color]:"UNKNOWN";
}
static void record_orb_reward(Game *g,OrbColor color) {
    unsigned current=g->session_color_counts[color];
    if(current<UINT16_MAX)g->session_color_counts[color]=(uint16_t)(current+1u);
    if(g->session_orbs<INT_MAX)g->session_orbs++;
    g->save.orbs=add_orbs_saturating(g->save.orbs,1u);
    g->save.total_orbs=add_orbs_saturating(g->save.total_orbs,1u);
    g->requested_save=1;
}
static void finish_orb_search(Game *g) {
    OrbColor winner=game_orb_color(g);
    unsigned highest=0;
    for(int i=0;i<ORB_COLOR_COUNT;i++) {
        unsigned count=g->session_color_counts[i];
        /* On ties, retain the previous predominant color where possible. */
        if(count>highest || (count==highest && count>0 && i==(int)winner)) {
            highest=count;
            winner=(OrbColor)i;
        }
    }
    if(highest && (g->save.reserved[12]!=(uint8_t)winner ||
                   g->save.reserved[13]!=ORB_COLOR_LAYOUT_MARKER)) {
        g->save.reserved[12]=(uint8_t)winner;
        g->save.reserved[13]=ORB_COLOR_LAYOUT_MARKER;
        g->requested_save=1;
    }
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
    g->save.reserved[12]=ORB_PINK;
    g->save.reserved[13]=ORB_COLOR_LAYOUT_MARKER;
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
    int migrated_orb_color=0;
    if(s.reserved[13]!=ORB_COLOR_LAYOUT_MARKER ||
       s.reserved[12]>s.story_phase) {
        s.reserved[12]=ORB_PINK;
        s.reserved[13]=ORB_COLOR_LAYOUT_MARKER;
        migrated_orb_color=1;
    }
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
    if(migrated_item_layout || repaired_background || migrated_orb_color)
        s.checksum=game_checksum(&s);
    g->save = s;
    if(migrated_item_layout || repaired_background || migrated_orb_color)
        g->requested_save=1;
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
/* Runtime-only orb entities. Shooting a cloud creates a cluster; each orb
 * requires a separate shot, cycles color, moves, and disappears after TTL.
 * This avoids granting currency simply for breaking a Dream Cloud. */
/* A research search is one outing even if it contains several Pokémon
 * encounters. Older callers expect the first result to count the outing;
 * later results and the final cloud never increment it a second time. */
static void count_search_once(Game *g) {
    if(g->search_counted)return;
    if(g->save.searches<UINT32_MAX)g->save.searches++;
    g->search_counted=1;
}
static int radar_has_remaining(const Game *g) {
    if(!g)return 0;
    for(int i=0;i<g->active_clouds && i<MAX_CLOUDS;i++)
        if(g->clouds[i].alive)return 1;
    return game_active_dream_orbs(g)>0;
}
static void discard_radar_entities(Game *g) {
    for(int i=0;i<MAX_CLOUDS;i++)g->clouds[i].alive=0;
    for(int i=0;i<MAX_DREAM_ORBS;i++)g->dream_orbs[i].alive=0;
    g->orb_chain_valid=0;
    g->orb_group_collected=0;
    g->orb_group_target=0;
    g->radar_resume_pending=0;
}
static void complete_radar_if_empty(Game *g) {
    if(g->screen!=STATE_RADAR)return;
    for(int i=0;i<g->active_clouds && i<MAX_CLOUDS;i++)
        if(g->clouds[i].alive)return;
    if(game_active_dream_orbs(g))return;
    finish_orb_search(g);
    count_search_once(g);
    g->radar_resume_pending=0;
    g->screen=STATE_RESULTS;
    g->requested_save=1;
}
static void spawn_dream_orbs(Game *g,int x,int y,int count,int chain) {
    const int ox[5]={-22,22,0,-12,12};
    const int oy[5]={-12,-12,22,12,12};
    if(count<1)return;
    if(count>5)count=5;
    /* Only one cluster is currently chain-eligible at once. Existing
     * separately spawned Orbs remain collectible but cancel split chains. */
    int already=game_active_dream_orbs(g);
    int created=0;
    for(int i=0;i<count;i++) {
        int slot=-1;
        for(int j=0;j<MAX_DREAM_ORBS;j++)
            if(!g->dream_orbs[j].alive){slot=j;break;}
        if(slot<0)break;
        DreamOrb *o=&g->dream_orbs[slot];
        o->x=x+ox[i];o->y=y+oy[i];
        if(o->x<8)o->x=8;
        if(o->x>247)o->x=247;
        if(o->y<8)o->y=8;
        if(o->y>183)o->y=183;
        o->vx=(i%2)?1:-1;
        o->vy=(i%3)?-1:1;
        o->ttl=chain?120-25*chain:210;
        if(o->ttl<45)o->ttl=45;
        o->color_phase=(uint8_t)i;
        o->alive=1;
        created++;
    }
    if(chain==0)g->orb_total_collected=0; /* Per-cloud chain cap. */
    g->orb_group_collected=0;
    g->orb_group_target=(uint8_t)created;
    g->orb_chain_valid=(uint8_t)(already==0 && (chain!=0 || count>=4) && created==count);
    g->orb_chain_stage=(uint8_t)chain;
}
static void capture_dream_orb(Game *g,int slot) {
    DreamOrb *o=&g->dream_orbs[slot];
    if(!o->alive)return;
    OrbColor color=game_dream_orb_color(g,slot);
    int x=o->x,y=o->y;
    o->alive=0;
    record_orb_reward(g,color);
    if(g->orb_group_collected<UINT8_MAX)g->orb_group_collected++;
    if(g->orb_total_collected<UINT8_MAX)g->orb_total_collected++;
    /* Four- or five-orb groups may spawn shrinking three-orb chains.
     * Per-cloud maximum is 20 collected orbs. */
    if(!game_active_dream_orbs(g) && g->orb_chain_valid &&
       g->orb_group_target>0 &&
       g->orb_group_collected==g->orb_group_target &&
       g->orb_chain_stage<5 && g->orb_total_collected<DREAM_ORB_CHAIN_LIMIT) {
        unsigned remaining=DREAM_ORB_CHAIN_LIMIT-g->orb_total_collected;
        int spawn=remaining<3u?(int)remaining:3;
        if(spawn>0)spawn_dream_orbs(g,x,y,spawn,g->orb_chain_stage+1);
    }
    complete_radar_if_empty(g);
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
    /* Explicit new-search requests supersede an unfinished radar outing,
       but only after checking the new extension is valid and affordable.
       A rejected request must not destroy still-collectible targets. */
    if(g->screen==STATE_RESULTS && g->radar_resume_pending)
        game_finish_pending_radar(g);
    g->save.orbs-=price;
    g->requested_save=1;
    g->ext_selection=ext;
    g->screen=STATE_RADAR;
    g->search_counted=0;
    g->radar_resume_pending=0;
    /* A new radar session must not retain the previous sphere timer. */
    g->capture_hp=0;g->capture_timeout=0;g->cloud_hit=0;
    g->projectile_active=0;g->projectile_enabled=0;
    g->projectile_hits=0;g->projectile_cooldown=0;
    g->projectile_queued=0;g->capture_motion_ticks=0;
    memset(g->projectile_extra,0,sizeof g->projectile_extra);
    memset(g->session_color_counts,0,sizeof g->session_color_counts);
    memset(g->dream_orbs,0,sizeof g->dream_orbs);
    g->orb_chain_stage=0;g->orb_chain_valid=0;
    g->orb_group_collected=0;g->orb_group_target=0;
    g->orb_total_collected=0;
    g->search_orb_color=(uint8_t)game_orb_color(g);
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
    /* Retail color preference data: each basic species only appears after
       its story unlock and favors one or more of the previous search's colors.
       Equal weights within an eligible group remain provisional until the
       original selection table is recovered. */
    static const uint8_t preferred_color_mask[15]={
        1,3,3,3,3, /* Munna, Swablu, Drifloon, Riolu, Sigilyph */
        3,3,       /* Igglybuff, Shuckle */
        5,5,6,3,   /* Staryu, Porygon, Ralts, Bronzor */
        2,8,9,5    /* Togepi, Smoochum, Spiritomb, Rotom */
    };
    static const uint8_t unlocked_at_phase[15]={
        0,0,0,0,0,1,1,2,2,2,2,3,3,3,3
    };
    int possibilities[15],count=0;
    int phase=g->save.story_phase>3?3:g->save.story_phase;
    unsigned wanted=1u<<(unsigned)g->search_orb_color;
    for(int i=0;i<15;i++) {
        if(unlocked_at_phase[i]<=phase && (preferred_color_mask[i]&wanted))
            possibilities[count++]=i;
    }
    if(count==0)return 0; /* Malformed color state: known safe Munna. */
    return possibilities[rnd(g)%(unsigned)count];
}
/* Approximate original Research Extension encounter bias while waiting for
 * exact 3DS tables. Retrieval favors Pokemon and Dowsing favors items; they
 * must never share an unconditional item-only result.
 * All non-cloud legendary, secret, and simulator extensions remain Pokemon. */
static int choose_item_encounter(Game *g) {
    switch(g->ext_selection) {
        case EXT_BASIC: return (rnd(g)%4u)==0u;       /* 25% items */
        case EXT_RETRIEVAL: return (rnd(g)%8u)==0u;   /* 12.5% items */
        case EXT_DOWSING: return (rnd(g)%8u)<7u;      /* 87.5% items */
        default: return 0;
    }
}
/* Original Simulator extensions fight the Therian species but award an item
 * instead of sending that legendary Pokemon. The six item IDs per Simulator
 * match the original English Item.msbt catalog and documented reward pools. */
static int simulator_reward_item(Game *g) {
    static const uint8_t pools[3][6] = {
        {4,17,15,16,7,20},   /* Alpha: PP Up, Heart Scale, Rare Candy, Star Piece, Max Revive, Life Orb */
        {18,17,15,16,19,21}, /* Beta: Dawn Stone, Heart Scale, Rare Candy, Star Piece, King's Rock, Focus Sash */
        {22,17,15,16,20,21}  /* Gamma: Eviolite, Heart Scale, Rare Candy, Star Piece, Life Orb, Focus Sash */
    };
    int index=g->ext_selection-EXT_SIM_TORNADUS;
    if(index<0 || index>=3)return -1;
    return pools[index][rnd(g)%6u];
}
/* DS-compatible approximation of the original Sphere's energy-ball attack.
 * Attack cadence and damage are provisional: originals depend on species.
 * A moving beam aim can dodge an incoming ball or shoot it directly. */
/* Distinct encounter profiles provide DS-friendly variation in sphere
 * geometry, movement and attack cadence. All values are intentionally
 * provisional: the original 3DS per-species parameter tables remain unknown.
 * Dedicated legendary extensions and Therian simulators share the toughest
 * category; ordinary species differ deterministically, without rerolling a
 * difficulty after a failed or retried capture. */
CaptureProfile game_capture_profile(const Game *g) {
    static const CaptureProfile profiles[] = {
        {CAPTURE_DRIFT,     22,1,90,160,120,1},
        {CAPTURE_SWIFT,     19,2,55,110,180,2},
        {CAPTURE_ERRATIC,   16,3,32, 95,210,2},
        {CAPTURE_LEGENDARY, 16,3,24, 70,300,3},
        {CAPTURE_ITEM,      20,2,65,125,150,1}
    };
    if(!g)return profiles[CAPTURE_DRIFT];
    if((g->ext_selection>=EXT_TORNADUS &&
        g->ext_selection<=EXT_LUGIA) ||
       (g->ext_selection>=EXT_SIM_TORNADUS &&
        g->ext_selection<=EXT_SIM_LANDORUS) ||
       (g->session_species>=15 && g->session_species<=22))
        return profiles[CAPTURE_LEGENDARY];
    if(g->session_type==1)return profiles[CAPTURE_ITEM];
    if(g->session_species<0 || g->session_species>25)
        return profiles[CAPTURE_DRIFT];
    return profiles[g->session_species%3];
}
static void finish_projectile(Game *g) {
    g->projectile_active=0;
    /* Within a burst, launch the next ball after a short staggered pause.
     * This DS approximation launches at most one ball at a time. */
    g->projectile_cooldown=g->projectile_queued>0 ? 12 :
        game_capture_profile(g).attack_interval;
}
static int projectile_speed(int delta) {
    if(delta>0)return delta>60?3:delta>24?2:1;
    if(delta<0)return delta< -60?-3:delta< -24?-2:-1;
    return 0;
}
static int extra_balls_live(const Game *g) {
    for(int i=0;i<MAX_EXTRA_PROJECTILES;i++)
        if(g->projectile_extra[i].active)return 1;
    return 0;
}
static void clear_extra_balls(Game *g) {
    for(int i=0;i<MAX_EXTRA_PROJECTILES;i++)g->projectile_extra[i].active=0;
}
static void spawn_legendary_balls(Game *g) {
    if(game_capture_profile(g).type!=CAPTURE_LEGENDARY)return;
    for(int i=0;i<MAX_EXTRA_PROJECTILES;i++) {
        ExtraProjectile *p=&g->projectile_extra[i];
        int offset=i==0?-18:18;
        p->x=g->projectile_x+offset;p->y=g->projectile_y;
        if(p->x<8)p->x=8;
        if(p->x>247)p->x=247;
        int target=g->aim_x+offset;
        if(target<8)target=8;
        if(target>247)target=247;
        p->vx=projectile_speed(target-p->x);
        p->vy=projectile_speed(g->aim_y-p->y);
        if(!p->vx && !p->vy)p->vy=2;
        p->ttl=90;p->active=1;
    }
}
static void tick_extra_balls(Game *g) {
    for(int i=0;i<MAX_EXTRA_PROJECTILES;i++) {
        ExtraProjectile *p=&g->projectile_extra[i];
        if(!p->active)continue;
        if(p->ttl<=1 || p->x<0 || p->x>255 ||
           p->y<0 || p->y>191) {p->active=0;continue;}
        p->x+=p->vx;p->y+=p->vy;p->ttl--;
        if(p->x<0 || p->x>255 || p->y<0 || p->y>191) {
            p->active=0;continue;
        }
        int64_t dx=(int64_t)p->x-g->aim_x;
        int64_t dy=(int64_t)p->y-g->aim_y;
        if(g->aim_x>=0 && g->aim_x<=255 &&
           g->aim_y>=0 && g->aim_y<=191 && dx*dx+dy*dy<=9*9) {
            p->active=0;
            if(g->projectile_hits<INT_MAX)g->projectile_hits++;
            int penalty=game_capture_profile(g).attack_penalty;
            g->capture_timeout=g->capture_timeout<=penalty?0:
                               g->capture_timeout-penalty;
        }
    }
}
static void tick_primary_ball(Game *g) {
    if(!g->projectile_enabled || g->screen!=STATE_SPHERE)return;
    if(g->projectile_active) {
        if(g->projectile_x<0 || g->projectile_x>255 ||
           g->projectile_y<0 || g->projectile_y>191 ||
           g->projectile_lifetime<=0) {
            finish_projectile(g);return;
        }
        g->projectile_x+=g->projectile_vx;
        g->projectile_y+=g->projectile_vy;
        g->projectile_lifetime--;
        if(g->projectile_x<0 || g->projectile_x>255 ||
           g->projectile_y<0 || g->projectile_y>191 ||
           g->projectile_lifetime<=0) {
            finish_projectile(g);return;
        }
        int64_t dx=(int64_t)g->projectile_x-g->aim_x;
        int64_t dy=(int64_t)g->projectile_y-g->aim_y;
        if(g->aim_x>=0 && g->aim_x<=255 &&
           g->aim_y>=0 && g->aim_y<=191 &&
           dx*dx+dy*dy<=9*9) {
            finish_projectile(g);
            if(g->projectile_hits<INT_MAX)g->projectile_hits++;
            int penalty=game_capture_profile(g).attack_penalty;
            if(g->capture_timeout<=penalty)g->capture_timeout=0;
            else g->capture_timeout-=penalty;
        }
        return;
    }
    if(extra_balls_live(g))return;
    if(g->projectile_cooldown>0){g->projectile_cooldown--;return;}
    if(g->sphere_x<0 || g->sphere_x>255 ||
       g->sphere_y<0 || g->sphere_y>191 ||
       g->aim_x<0 || g->aim_x>255 ||
       g->aim_y<0 || g->aim_y>191)return;
    g->projectile_x=g->sphere_x;g->projectile_y=g->sphere_y;
    g->projectile_vx=projectile_speed(g->aim_x-g->sphere_x);
    g->projectile_vy=projectile_speed(g->aim_y-g->sphere_y);
    if(!g->projectile_vx && !g->projectile_vy)g->projectile_vy=2;
    g->projectile_lifetime=90;
    g->projectile_active=1;
    if(game_capture_profile(g).type==CAPTURE_LEGENDARY) {
        g->projectile_queued=0;
        spawn_legendary_balls(g);
    } else if(g->projectile_queued>0)g->projectile_queued--;
    else g->projectile_queued=game_capture_profile(g).attack_burst-1;
    g->projectile_cooldown=game_capture_profile(g).attack_interval;
}
static void tick_projectile(Game *g) {
    if(!g->projectile_enabled || g->screen!=STATE_SPHERE)return;
    tick_extra_balls(g);
    tick_primary_ball(g);
}
static void start_sphere(Game *g) {
    g->screen=STATE_SPHERE;
    g->projectile_enabled=1;
    g->projectile_active=0;
    g->projectile_queued=0;
    clear_extra_balls(g);
    g->capture_motion_ticks=0;
    g->projectile_lifetime=0;
    g->projectile_hits=0;
    g->capture_timeout= (g->ext_selection==EXT_BASIC && g->save.story_phase==0 && g->save.searches==0) ? 9999 * 60 : (90+g->save.upgrades[1]*30)*60;
    g->sphere_x=105;g->sphere_y=90;
    g->sphere_vx=0;g->sphere_vy=0;
    g->capture_hp=0;
    /* Start every capture with a fresh movement and support state. */
    g->capture_timeout=g->capture_timeout<1?1:g->capture_timeout;
    /* Temporary support effects cannot carry over from another encounter. */
    g->freeze_frames=0;
    g->slow_frames=0;
    /* Dedicated legendary and special encounters cannot randomly turn into
       an item. Only cloud-search modes roll the item encounter chance. */
    /* Item/Pokemon reward distribution depends on the Extension. The
       thresholds are provisional until the exact original tables are known. */
    g->session_type = choose_item_encounter(g);
    /* Do not consume a Pokemon species roll for item-only research sessions.
       A non-Pokemon result has no species to transfer or display. */
    g->session_species=g->session_type ? -1 : choice_species(g);
    /* Prototype drop selection: broaden item variety as story research progresses.
       The 23 labels are original; these drop probabilities are NOT extracted
       from the original encounter/item tables. */
    static const int item_pool_sizes[4]={6,11,17,23};
    int phase=g->save.story_phase>3?3:g->save.story_phase;
    /* Simulator fights still display the Therian Pokemon, but their reward
       is an item from the matching six-item pool, not a duplicate legendary.
       Ordinary Pokemon-only encounters never have an unrelated item. */
    if(g->ext_selection>=EXT_SIM_TORNADUS &&
       g->ext_selection<=EXT_SIM_LANDORUS)
        g->session_item=simulator_reward_item(g);
    else
        g->session_item=g->session_type ?
            (int)(rnd(g)%(uint32_t)item_pool_sizes[phase]) : -1;
    CaptureProfile profile=game_capture_profile(g);
    g->sphere_vx=profile.speed;
    g->sphere_vy=profile.speed>1?profile.speed-1:1;
    g->projectile_cooldown=profile.attack_interval;
}
/* Support effects belong to gameplay state, never the renderer. A failed
   activation must not consume inventory or trigger a save. */
int game_use_support(Game *g, int slot) {
    if (!g || g->screen != STATE_SPHERE || g->capture_timeout <= 0 ||
        slot < 0 || slot >= 3 || g->save.goods[slot] == 0 ||
        g->save.goods[slot] > 9) return 0;
    /* Do not consume another effect item while its full effect is active. */
    if (slot == 0) {
        if (g->freeze_frames >= 300) return 0;
        g->freeze_frames = 300;
    } else if (slot == 1) {
        if (g->slow_frames >= 300) return 0;
        g->slow_frames = 300;
    } else {
        /* Never spend an Energy Recharge if its timer cannot increase.
           Saturate the addition without overflowing signed arithmetic. */
        if (g->capture_timeout <= 0 || g->capture_timeout >= 2147483647) return 0;
        if (g->capture_timeout > 2147483647 - 1500)
            g->capture_timeout = 2147483647;
        else g->capture_timeout += 1500;
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
        /* Orbs must be shot separately; prioritize a small orb near the
           reticle over the larger cloud underneath. */
        int hit_orb=-1;
        int64_t closest_orb=11*11;
        for(int i=0;i<MAX_DREAM_ORBS;i++) {
            const DreamOrb *o=&g->dream_orbs[i];
            if(!o->alive || o->x<0 || o->x>255 || o->y<0 || o->y>191)continue;
            int64_t dx=(int64_t)o->x-g->aim_x;
            int64_t dy=(int64_t)o->y-g->aim_y;
            int64_t dist=dx*dx+dy*dy;
            if(dist<closest_orb){closest_orb=dist;hit_orb=i;}
        }
        if(hit_orb>=0){capture_dream_orb(g,hit_orb);return;}
        /* When cloud hit circles overlap, choose the closest cloud. */
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
                /* The spawned sphere is one encounter, not the end of the
                   whole search. Remaining clouds/Orbs pause in memory. */
                g->radar_resume_pending=radar_has_remaining(g);
                start_sphere(g);return;
            }
            /* Pink clouds yield 3..5 depending on their animated size;
             * a non-encounter storm cloud produces exactly four. */
            int count=c->kind?4:3+(int)((g->save.frames_played/30u)%3u);
            spawn_dream_orbs(g,c->x,c->y,count,0);
            complete_radar_if_empty(g);
        }
    } else if (g->screen==STATE_SPHERE) {
        for(int i=0;i<MAX_EXTRA_PROJECTILES;i++) {
            ExtraProjectile *p=&g->projectile_extra[i];
            if(!p->active || p->x<0 || p->x>255 ||
               p->y<0 || p->y>191)continue;
            int64_t dx=(int64_t)p->x-g->aim_x;
            int64_t dy=(int64_t)p->y-g->aim_y;
            if(dx*dx+dy*dy<=12*12){p->active=0;return;}
        }
        /* Shoot an incoming energy ball before it reaches the aim point. */
        if(g->projectile_active &&
           g->projectile_x>=0 && g->projectile_x<=255 &&
           g->projectile_y>=0 && g->projectile_y<=191) {
            int64_t px=(int64_t)g->projectile_x-g->aim_x;
            int64_t py=(int64_t)g->projectile_y-g->aim_y;
            if(px*px+py*py<=12*12) {
                finish_projectile(g);
                return;
            }
        }
        /* An expired encounter must not be captured between timer ticks. */
        if(g->capture_timeout<=0)return;
        /* Sphere coordinates must be on the DS viewport. Squaring two
           arbitrary signed 32-bit coordinates could overflow int64_t. */
        if(g->sphere_x<0 || g->sphere_x>255 ||
           g->sphere_y<0 || g->sphere_y>191)return;
        int64_t dx=(int64_t)g->sphere_x-g->aim_x, dy=(int64_t)g->sphere_y-g->aim_y;
        int radius=game_capture_profile(g).hit_radius;
        if (dx*dx+dy*dy<(int64_t)radius*radius) {
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
    /* End only this encounter. Preserve clouds/Orbs and their color
       tallies until the player finishes or explicitly abandons the scan. */
    if(!g->radar_resume_pending || !radar_has_remaining(g)) {
        g->radar_resume_pending=0;
        finish_orb_search(g);
    }
    g->projectile_active=0;
    g->projectile_enabled=0;
    clear_extra_balls(g);
    /* Support effects are encounter-local, including on successful captures
       and when full storage opens a replacement decision. */
    g->freeze_frames=0;
    g->slow_frames=0;
    count_search_once(g);
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
    /* A simulator challenge cannot award another transferable legendary:
       it awards its own item pool while still rendering the Therian fight.
       Reuse the normal six-stack storage/replacement path. */
    int is_simulator=g->ext_selection>=EXT_SIM_TORNADUS &&
                     g->ext_selection<=EXT_SIM_LANDORUS;
    if(is_simulator && (g->session_type!=0 ||
       g->session_species!=15+g->ext_selection-EXT_SIM_TORNADUS))
        return;
    if(g->session_type==1 || is_simulator) {
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
/* The results screen is a checkpoint: A continues this exact radar
 * outing without paying again, rerolling clouds or resetting orb totals.
 * B explicitly abandons the remainder and settles the previous color. */
int game_resume_radar(Game *g) {
    if(!g || g->screen!=STATE_RESULTS || !g->radar_resume_pending ||
       !radar_has_remaining(g))return 0;
    g->screen=STATE_RADAR;
    g->radar_resume_pending=0;
    g->session_caught=-1;
    g->session_species=-1;
    g->session_item=-1;
    g->session_type=0;
    g->capture_timeout=0;
    g->capture_hp=0;
    g->replaced_slot=-1;
    g->projectile_active=0;
    g->projectile_enabled=0;
    clear_extra_balls(g);
    return 1;
}
int game_finish_pending_radar(Game *g) {
    if(!g || g->screen!=STATE_RESULTS || !g->radar_resume_pending)return 0;
    finish_orb_search(g);
    count_search_once(g);
    discard_radar_entities(g);
    g->requested_save=1;
    return 1;
}
int game_leave_search(Game *g) {
    if(!g || (g->screen!=STATE_RADAR && g->screen!=STATE_SPHERE))return 0;
    finish_orb_search(g);
    discard_radar_entities(g);
    g->projectile_active=0;
    g->projectile_enabled=0;
    clear_extra_balls(g);
    count_search_once(g);
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
    if (g->screen==STATE_RADAR) {
        for(int i=0;i<MAX_DREAM_ORBS;i++) {
            DreamOrb *o=&g->dream_orbs[i];
            if(!o->alive)continue;
            if(o->ttl<=1){o->alive=0;g->orb_chain_valid=0;continue;}
            o->ttl--;
            o->x+=o->vx;o->y+=o->vy;
            if(o->x<=8 || o->x>=247) {
                if(o->x<8)o->x=8;
                if(o->x>247)o->x=247;
                o->vx=-o->vx;
            }
            if(o->y<=8 || o->y>=183) {
                if(o->y<8)o->y=8;
                if(o->y>183)o->y=183;
                o->vy=-o->vy;
            }
        }
        complete_radar_if_empty(g);
    }
    if (g->screen==STATE_SPHERE) {
        /* Apply effects to the entire current frame before decrementing.
           Otherwise the last frozen frame moves one tick too early. */
        int frozen_this_frame = g->freeze_frames > 0;
        int slowed_this_frame = g->slow_frames > 0;
        if (g->freeze_frames>0) g->freeze_frames--;
        if (g->slow_frames>0) g->slow_frames--;
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
            /* Swift/erratic/legendary spheres periodically break their
               trajectory. Timing is measured only on actual movement
               frames, so Freeze and Dragnet remain predictable. */
            CaptureProfile profile=game_capture_profile(g);
            if(g->capture_motion_ticks<INT_MAX)g->capture_motion_ticks++;
            if(profile.turn_frames>0 &&
               g->capture_motion_ticks%profile.turn_frames==0) {
                int turn=g->capture_motion_ticks/profile.turn_frames;
                g->sphere_vx=(turn&1)?-profile.speed:profile.speed;
                g->sphere_vy=(turn&2)?-profile.speed:profile.speed;
            }
        }
        if (!frozen_this_frame && (!slowed_this_frame || g->save.frames_played%3u==0u))
            tick_projectile(g);
        if (g->capture_timeout>0) g->capture_timeout--;
        if (g->capture_timeout<=0) {
            if(!g->radar_resume_pending || !radar_has_remaining(g)) {
                g->radar_resume_pending=0;
                finish_orb_search(g);
            }
            g->capture_timeout=0;
            g->projectile_active=0;
            g->projectile_enabled=0;
            clear_extra_balls(g);
            g->screen=STATE_RESULTS;g->session_caught=-1;
            g->session_item=-1;g->session_species=-1;g->session_type=0;
            g->capture_hp=0;
            g->freeze_frames=0;g->slow_frames=0;
            count_search_once(g);
            g->requested_save=1;
            msg(g,"The Pokemon escaped!");
        }
    }
}
int game_buy(Game *g, int kind, int idx) {
    if (!g) return 0;
    static const int costs[]={0,100,500,1000,1500};
    if (kind==0) {
        if (idx<0 || idx>=3) return 0;
        int level=g->save.upgrades[idx];
        if (level<1 || level>5) {msg(g,"Invalid equipment level.");return 0;}
        if (level==5) {msg(g,"Already at maximum level.");return 0;}
        int cost=costs[level];
        if (g->save.orbs<(uint32_t)cost) {msg(g,"Not enough Dream Orbs.");return 0;}
        g->save.orbs-=cost;g->save.upgrades[idx]++;g->requested_save=1;
        msg(g,"Equipment upgraded!");return 1;
    }
    if (kind==1) {
        if (idx<0 || idx>=3)return 0;
        int cost=(idx==0) ? 100 : 50;
        /* Capacity is checked first so a full inventory reports the
           actionable reason even when the player also lacks Dream Orbs. */
        if (g->save.goods[idx]>9) {msg(g,"Invalid support inventory.");return 0;}
        if (g->save.goods[idx]==9) {msg(g,"Cannot carry more.");return 0;}
        if (g->save.orbs<(uint32_t)cost) {msg(g,"Not enough Dream Orbs.");return 0;}
        g->save.orbs-=cost;g->save.goods[idx]++;g->requested_save=1;
        msg(g,"Support item purchased!");return 1;
    }
    return 0;
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
