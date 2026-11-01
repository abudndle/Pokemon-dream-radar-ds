#ifndef DR_UI_SCENE_H
#define DR_UI_SCENE_H
#include <stddef.h>
/* Bounded, portable scene evaluated from source-derived BCLYT nodes and
 * privately staged BCLAN CLPA tracks. No proprietary files are bundled. */
typedef struct DrUiScene DrUiScene;
typedef struct { int x, y, w, h; } DrUiRect;
DrUiScene *dr_ui_scene_load(const char *path);
void dr_ui_scene_free(DrUiScene *scene);
/* Returns 1 only if all four live Touch00..Touch03 panes resolve to visible,
 * non-overlapping DS rectangles. On failure, callers use the bundled layout. */
int dr_ui_title_rects(const DrUiScene *scene,float frame,DrUiRect out[4]);
int dr_ui_title_hit(const DrUiRect rects[4],int x,int y);
/* Same bounded Touch00..Touch03 scene math for source-derived ScanList.
 * Caller renders and accepts touch using these same four rectangles. */
int dr_ui_rows_rects(const DrUiScene *scene,float frame,DrUiRect out[4]);
int dr_ui_rows_hit(const DrUiRect rects[4],int x,int y);
#endif
