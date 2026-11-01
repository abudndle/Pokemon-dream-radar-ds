#ifndef DREAM_RADAR_TITLE_RUNTIME_H
#define DREAM_RADAR_TITLE_RUNTIME_H
#include "dr_pane_runtime.h"
#include "title_panes_generated.h"

/* Title rows derived from original MnIf_S_TitleList:
 * Pos/SRT00/L00..03/Touch00..03 BCLYT nodes. Both drawing and touch call
 * into the same resolved pane frames. A private owner-supplied CLPA clip
 * may override transforms through dr_title_runtime_frame().
 */
int dr_title_runtime_frame(const DrUiAnimation *animation,float frame);
int dr_title_runtime_rect(int row,DrPaneRect *out);
int dr_title_runtime_hit(int x,int y);
int dr_title_runtime_available(void);
#endif
