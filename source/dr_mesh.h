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
#endif
