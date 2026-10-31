/* Portable validator for the intermediate DRM1 Q12 mesh stream.
 * Validating geometry here does not imply DS GPU support or provenance.
 */
#ifndef DR_MESH_H
#define DR_MESH_H
#include <stddef.h>
#include <stdint.h>
typedef struct { int16_t x,y,z; } DrMeshVertex;
typedef struct { uint16_t a,b,c; } DrMeshTriangle;
typedef struct {
    uint16_t vertices,triangles;
    DrMeshVertex *vertex;
    DrMeshTriangle *triangle;
} DrMesh;
/* `out` must start zero-initialized or hold a previously decoded mesh.
 * On success the previous mesh is freed and replaced; failure leaves it intact. */
int dr_mesh_decode(const unsigned char *bytes,size_t size,DrMesh *out);
/* Read a standalone DRM1 mesh from an exact filesystem path. Only a complete
 * validated file is accepted; failure preserves the previous mesh unchanged.
 * `out` must be zero-initialized or previously initialized by this API. */
int dr_mesh_load_file(const char *path,DrMesh *out);
void dr_mesh_free(DrMesh *mesh);
/* Orthographic Q12-to-screen projection for a future software wireframe path. */
int dr_mesh_project_vertex(const DrMeshVertex *v,int cx,int cy,int scale,int *x,int *y);
/* Sixteen fixed-point yaw orientations for an optional model preview spin.
 * Step 0 matches the existing projection; step 4 turns +Z toward +X.
 * No floating-point or DS GPU dependency. */
int dr_mesh_project_vertex_yaw(const DrMeshVertex *v,int cx,int cy,int scale,
                               unsigned yaw_step,int *x,int *y);
/* Signed Q12 camera-space depth, positive towards the viewer. Matches the
 * 16-step yaw projection; returns zero without writing on bad inputs. */
int dr_mesh_depth_vertex_yaw(const DrMeshVertex *v,unsigned yaw_step,int *z);
/* Draw triangle edges into a caller-owned RGB555 framebuffer (no GPU). 
 * Returns 0 for invalid inputs; pixels outside the viewport are clipped. */
int dr_mesh_wireframe(const DrMesh *mesh,uint16_t *pixels,int width,int height,
                      int cx,int cy,int scale,uint16_t color);
/* Software wireframe with bounded 16-step yaw (0..15); invalid input draws
 * nothing. Does not implement original 3DS skeletal or texture animation. */
int dr_mesh_wireframe_yaw(const DrMesh *mesh,uint16_t *pixels,int width,int height,
                          int cx,int cy,int scale,uint16_t color,unsigned yaw_step);
/* Flat-color software triangle fill, with per-pixel 16-bit depth testing,
 * low-cost depth-based brightness, and clipping to the DS viewport.
 * Uses independent reusable 96 KiB scratch, not a per-frame allocation.
 * Does not replace the separate optional DRT1 texture renderer. */
int dr_mesh_solid_yaw(const DrMesh *mesh,uint16_t *pixels,int width,int height,
                      int cx,int cy,int scale,uint16_t color,unsigned yaw_step);
#endif
