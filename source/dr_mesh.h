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
int dr_mesh_decode(const unsigned char *bytes,size_t size,DrMesh *out);
void dr_mesh_free(DrMesh *mesh);
/* Orthographic Q12-to-screen projection for a future software wireframe path. */
int dr_mesh_project_vertex(const DrMeshVertex *v,int cx,int cy,int scale,int *x,int *y);
/* Sixteen fixed-point yaw orientations for an optional model preview spin.
 * Step 0 matches the existing projection; step 4 turns +Z toward +X.
 * No floating-point or DS GPU dependency. */
int dr_mesh_project_vertex_yaw(const DrMeshVertex *v,int cx,int cy,int scale,
                               unsigned yaw_step,int *x,int *y);
/* Draw triangle edges into a caller-owned RGB555 framebuffer (no GPU). 
 * Returns 0 for invalid inputs; pixels outside the viewport are clipped. */
int dr_mesh_wireframe(const DrMesh *mesh,uint16_t *pixels,int width,int height,
                      int cx,int cy,int scale,uint16_t color);
/* Software wireframe with bounded 16-step yaw (0..15); invalid input draws
 * nothing. Does not implement original 3DS skeletal or texture animation. */
int dr_mesh_wireframe_yaw(const DrMesh *mesh,uint16_t *pixels,int width,int height,
                          int cx,int cy,int scale,uint16_t color,unsigned yaw_step);
#endif
