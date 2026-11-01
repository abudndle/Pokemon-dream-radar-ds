#ifndef DREAM_RADAR_REFERENCE_LAYOUT_H
#define DREAM_RADAR_REFERENCE_LAYOUT_H
#include "game.h"
/* DS-scaled touch geometry from the player's original Dream Radar captures. */
void dr_support_center(int index, int *x, int *y); /* Same coordinates for rendering and touch */
int dr_support_at(int x, int y); /* 0=blue, 1=green, 2=orange, -1=none */
int dr_transfer_button_at(int x, int y); /* 0=Archive, 1=Back, -1=none */
void dr_transfer_slot_rect(int index,int *x,int *y,int *w,int *h);
int dr_transfer_slot_at(int x, int y); /* Pokemon 0..5, items 6..11, -1=none */
/* Original separate legendary research row: eight species-fixed cells. */
void dr_legendary_slot_rect(int index,int *x,int *y,int *w,int *h);
int dr_legendary_slot_at(int x,int y); /* 0..7 or -1 */
/* Shared draw / touch geometry for the 6-row Development Lab shop.
   These are DS adaptation values; not yet decoded from original .bclyt. */
int dr_lab_row_top(int index);
int dr_lab_hit(int x,int y,int count);
int dr_shop_row_top(int index);
int dr_shop_hit(int x, int y);
int dr_quad_hit(const int xy[8],int x,int y); /* Runtime convex touch area */
/* Results feedback never promises a save unless the write completed. */
const char *dr_research_save_status(int storage_ready,int save_pending);
int dr_remaining_clouds(const Game *g);
void dr_radar_counts(const Game *g, int *white, int *pink);
#endif
