#include "dr_background.h"
#include "photo_album.h"
#include "platform_compat.h"

#define PIXELS ((size_t)DR_PHOTO_W*DR_PHOTO_H)

static int read_placeholder(const char *root,uint16_t *pixels,size_t count,
                            int *loaded,int *slot) {
    char path[128];
    if(!root || !*root || !pixels || count<PIXELS || !loaded || !slot ||
       !dr_placeholder_path(path,sizeof path,root))
        return 0;
    /* dr_photo_read validates exact headers/length and reads all encoded
     * pixels before writing to the destination. */
    if(!dr_photo_read(path,pixels,count))return 0;
    *loaded=1;
    *slot=-2;
    return 1;
}
int dr_background_import(const char *root,uint16_t *pixels,size_t count,
                         Game *game,int *loaded,int *slot) {
    if(!game)return 0;
    if(!read_placeholder(root,pixels,count,loaded,slot))return 0;
    game->save.reserved[9]=0;
    game->save.reserved[10]=0;
    game->save.reserved[11]=DR_BACKGROUND_IMPORT_MARKER;
    game->save.camera_enabled=0;
    game->requested_save=1;
    return 1;
}
int dr_background_restore(const char *root,uint16_t *pixels,size_t count,
                          const Game *game,int *loaded,int *slot) {
    if(!game || game->save.reserved[11]!=DR_BACKGROUND_IMPORT_MARKER)return 0;
    return read_placeholder(root,pixels,count,loaded,slot);
}
void dr_background_reset(Game *game,int *loaded,int *slot) {
    if(!game || !loaded || !slot)return;
    *loaded=0;
    *slot=-1;
    game->save.reserved[9]=0;
    game->save.reserved[10]=0;
    game->save.reserved[11]=0;
    game->requested_save=1;
}
