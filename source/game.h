#ifndef DREAM_RADAR_GAME_H
#define DREAM_RADAR_GAME_H
#include <stdint.h>
#include <stddef.h>
#define MAX_CAUGHT 6
#define MAX_CLOUDS 30
#define MAX_DREAM_ORBS 24
#define DREAM_ORB_CHAIN_LIMIT 20
#define MAX_ITEMS 6  /* Six pending item STACK slots. */
#define RESEARCH_ITEM_TYPES 23 /* Original English Item.msbt ITEM_00..ITEM_22. */
#define MAX_ITEM_STACK 255
/* reserved[2..7] carry type+1 for occupied item slots; reserved[8] marks layout. */
#define ITEM_LAYOUT_MARKER 0xA7u
#define ORB_COLOR_LAYOUT_MARKER 0xD4u
/* reserved[12]=dominant color from last completed search;
 * reserved[13]=marker; session tallies are runtime-only. */
#define SAVE_MAGIC 0x44525244u
#define SAVE_VERSION 3u

typedef enum { GAME_DIAMOND, GAME_PEARL, GAME_PLATINUM, GAME_HEARTGOLD,
               GAME_SOULSILVER, GAME_BLACK, GAME_WHITE,
               GAME_BLACK2, GAME_WHITE2, GAME_UNKNOWN } CartGame;
/* There is exactly one active game: physical Slot-1 OR one SD save. */
typedef enum { CART_SOURCE_NONE, CART_SOURCE_SLOT1, CART_SOURCE_TWILIGHT_SD } CartSource;
typedef enum { EXT_BASIC, EXT_TORNADUS, EXT_THUNDURUS, EXT_LANDORUS,
               EXT_DIALGA, EXT_PALKIA, EXT_GIRATINA, EXT_HOOH, EXT_LUGIA,
               EXT_BELDUM, EXT_SLOWPOKE, EXT_HOOTHOOT, EXT_RETRIEVAL, EXT_DOWSING,
               EXT_SIM_TORNADUS, EXT_SIM_THUNDURUS, EXT_SIM_LANDORUS, EXT_COUNT } Extension;
typedef enum { STATE_TITLE, STATE_INTRO, STATE_LAB, STATE_SHOP, STATE_EXTENSIONS,
               STATE_RADAR, STATE_SPHERE, STATE_RESULTS, STATE_RECORDS,
               STATE_TRANSFER, STATE_SETTINGS, STATE_SD_SAVES, STATE_DIALOGUE,
               STATE_REPLACE, STATE_STORAGE, STATE_TIPS, STATE_ALBUM, STATE_CREDITS, STATE_PLACEHOLDER } GameScreen;
typedef enum { REPLACE_NONE, REPLACE_POKEMON, REPLACE_ITEM } ReplaceKind;
typedef enum { ORB_PINK, ORB_GREEN, ORB_ORANGE, ORB_BLUE, ORB_COLOR_COUNT } OrbColor;
/* Provisional DS difficulty categories, not extracted 3DS battle parameters. */
typedef enum { CAPTURE_DRIFT, CAPTURE_SWIFT, CAPTURE_ERRATIC,
               CAPTURE_LEGENDARY, CAPTURE_ITEM } CaptureClass;
typedef struct {
    CaptureClass type;
    int hit_radius, speed, turn_frames;
    int attack_interval, attack_penalty, attack_burst;
} CaptureProfile;

typedef struct {
    uint32_t magic, version;
    uint32_t orbs, total_orbs, searches, caught_count, frames_played;
    uint32_t last_cloud_time, random_seed, checksum;
    uint8_t upgrades[3]; // Beam, Energy, Visoscope: 1..5
    uint8_t goods[3]; // Vortex, Dragnet, Energy Recharge
    uint8_t story_phase; // Eureka stages completed: Tornadus/Thundurus/Landorus
    uint8_t intro_seen, optical_aim, camera_enabled;
    uint8_t legends_caught; // bit 0..4
    uint8_t cloud_count, pending_count, pending[MAX_CAUGHT];
    uint8_t pending_items[MAX_ITEMS]; /* Item stack quantities, one stack per slot */
    uint8_t reserved[20]; /* reserved[0] = last completed Burnet story dialogue (0..3) */
} SaveData;

typedef struct {
    int x, y, alive, kind, cooldown;
} Cloud;
typedef struct {
    int x,y,vx,vy,ttl;
    uint8_t alive;
    uint8_t color_phase; /* per-orb offset during color cycling */
} DreamOrb;

typedef struct {
    SaveData save;
    GameScreen screen;
    int selection, page, intro_page, result_page, ext_selection;
    int story_event, story_event_page;
    int capture_hp, capture_timeout, sphere_x, sphere_y, sphere_vx, sphere_vy;
    /* Runtime-only hostile sphere energy ball. Not part of save data. */
    int projectile_enabled, projectile_active;
    int projectile_x, projectile_y, projectile_vx, projectile_vy;
    int projectile_cooldown, projectile_lifetime, projectile_hits;
    int projectile_queued, capture_motion_ticks; /* Runtime-only per-encounter state. */
    int aim_x, aim_y, freeze_frames, slow_frames, active_clouds, cloud_hit;
    int session_orbs, session_caught, session_type, session_species, session_item;
    /* Runtime-only: preserve unfinished radar entities across sphere results. */
    int radar_resume_pending, search_counted;
    uint16_t session_color_counts[ORB_COLOR_COUNT];
    uint8_t search_orb_color; /* saved dominant color at search start */
    DreamOrb dream_orbs[MAX_DREAM_ORBS];
    uint8_t orb_chain_stage,orb_chain_valid;
    uint8_t orb_group_collected,orb_group_target;
    uint8_t orb_total_collected;
    int camera_ok, camera_active, camera_tracking, camera_error;
    int messages, requested_save, cart_read_attempted, special_unlocked, cheat_progress[3];
    uint32_t pending_export_signature; /* Runtime proof of a successfully written text archive. */
    int archive_confirm; /* Explicit two-button queue release; NOT a retail transfer. */
    ReplaceKind replace_kind; /* Runtime only: never persists as an active prompt. */
    int replace_value, replace_selected, replace_confirm, replaced_slot;
    CartGame cart;
    CartSource cart_source; /* Runtime only: never persists as an inserted game. */
    Cloud clouds[MAX_CLOUDS];
    char message[180];
} Game;

void game_new(Game *g, uint32_t seed);
int game_load(Game *g, const char *path);
int game_save(Game *g, const char *path);
void game_regen_clouds(Game *g, uint32_t now);
void game_begin_search(Game *g, int extension);
void game_fire(Game *g);
int game_use_support(Game *g, int slot);
void game_tick(Game *g);
CaptureProfile game_capture_profile(const Game *g);
OrbColor game_orb_color(const Game *g);
OrbColor game_orb_live_color(const Game *g);
OrbColor game_dream_orb_color(const Game *g,int slot);
int game_active_dream_orbs(const Game *g);
const char *game_orb_color_name(OrbColor color);
/* End active radar/capture session safely when Back is pressed. */
int game_leave_search(Game *g);
/* Resume after an intermediate result or explicitly abandon remaining clouds. */
int game_resume_radar(Game *g);
int game_finish_pending_radar(Game *g);
int game_buy(Game *g, int kind, int idx);
void game_capture(Game *g);
/* Full queue: choose one occupied slot, or decline; never auto-overwrite. */
int game_replace_pending(Game *g, int slot);
int game_cancel_pending_replace(Game *g);
int game_item_slot_kind(const Game *g, int slot);
const char *game_item_name(int item);
int game_extension_unlocked(Game *g, int ext);
int game_extension_price(int ext);
void game_secret_key(Game *g, int key);
int game_export(Game *g, const char *path);
int game_release_archived_pending(Game *g); /* Never runs unless archive exists & is current. */
CartGame game_identify_cart(const char *gamecode);
const char *game_cart_name(CartGame game);
const char *game_extension_name(int ext);
const char *game_species_name(int species);
void game_set_cart(Game *g, CartGame cart);
void game_set_cart_source(Game *g, CartGame cart, CartSource source);
const char *game_cart_source_name(CartSource source);
uint32_t game_checksum(const SaveData *p);
#endif
