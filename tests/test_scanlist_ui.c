#include <assert.h>
#include <stdio.h>
#include "dr_ui_scene.h"

/* Geometry is recovered from MnIf_S_ScanList.bclyt, not drawn by hand. */
static void assert_scanlist(const DrUiScene *scene, DrUiRect out[4]) {
    assert(dr_ui_four_row_rects(scene, 0, out));
    for (int i = 0; i < 4; i++) {
        assert(out[i].x >= 3 && out[i].x <= 5);
        assert(out[i].y >= 35+32*i && out[i].y <= 37+32*i);
        assert(out[i].w >= 239 && out[i].w <= 241);
        assert(out[i].h >= 27 && out[i].h <= 29);
        assert(dr_ui_title_hit(out, out[i].x+out[i].w/2,
                               out[i].y+out[i].h/2) == i);
    }
    assert(dr_ui_title_hit(out, 0, 0) == -1);
    assert(dr_ui_title_hit(out, 256, 192) == -1);
}
int main(int argc, char **argv) {
    assert(argc == 4);
    DrUiScene *base = dr_ui_scene_load(argv[1]);
    assert(base);
    DrUiRect rects[4], moving[4];
    assert_scanlist(base, rects);
    DrUiScene *clip = dr_ui_scene_load(argv[2]);
    assert(clip);
    assert_scanlist(clip, moving);
    assert(dr_ui_four_row_rects(clip, 10, moving));
    assert(moving[0].y >= rects[0].y+7 && moving[0].y <= rects[0].y+9);
    for (int i = 1; i < 4; i++) {
        assert(moving[i].x == rects[i].x);
        assert(moving[i].y == rects[i].y);
    }
    assert(dr_ui_four_row_rects(clip, 100, moving));
    assert(moving[0].y >= rects[0].y+7 && moving[0].y <= rects[0].y+9);
    assert(!dr_ui_scene_load(argv[3]));
    dr_ui_scene_free(clip);
    dr_ui_scene_free(base);
    puts("PASS: original 4-row ScanList positions, per-pane CLPA, touch, malformed inputs");
    return 0;
}
