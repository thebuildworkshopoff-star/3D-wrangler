"""Extract the saved Blender meshes and their smooth edges for the native SKP."""
import bpy
import json
import math
import sys
from pathlib import Path

def srgb(v):
    return round(255 * (12.92*v if v <= .0031308 else 1.055*v**(1/2.4)-.055))

parts=[]
for obj in bpy.context.scene.objects:
    if obj.type!="MESH":
        continue
    mesh=obj.data
    mesh.calc_loop_triangles()
    edges={}
    for tri in mesh.loop_triangles:
        for edge in tri.edge_keys:
            edges.setdefault(tuple(sorted(edge)),[]).append(tri.normal.copy())
    soft={k for k, ns in edges.items() if len(ns)==2 and ns[0].dot(ns[1])>math.cos(math.radians(42))}
    world=obj.matrix_world
    pivot=world.translation
    material=obj.data.materials[0]
    triangles=[]
    for tri in mesh.loop_triangles:
        ids=list(tri.vertices)
        smooth=[tuple(sorted((i,ids[(j+1)%3]))) in soft for j,i in enumerate(ids)]
        triangles.append(ids+smooth)
    parts.append(dict(name=obj.name,assembly=obj.users_collection[0].name,
                      material=material.name,color=[srgb(v) for v in material.diffuse_color[:3]],
                      pivot=list(pivot/.0254),vertices=[list((world @ v.co-pivot)/.0254) for v in mesh.vertices],
                      triangles=triangles))
Path(sys.argv[-1]).write_text(json.dumps(parts,separators=(",",":")),encoding="utf-8")
