"""Write and reopen a grouped model using the installed SketchUp 2026 C API."""
import ctypes as c
import json
import os
from pathlib import Path
import sys

folder=Path("C:/Program Files/SketchUp/SketchUp 2026/SketchUp")
dll_directory=os.add_dll_directory(str(folder))
sdk=c.CDLL(str(folder/"SketchUpAPI.dll"))
Ref=c.c_void_p
Size=c.c_size_t
ptr=c.byref
class Point(c.Structure):
    _fields_=[("x",c.c_double),("y",c.c_double),("z",c.c_double)]

def call(name,*args):
    result=getattr(sdk,name)(*args)
    if result:
        raise RuntimeError(f"{name} returned {result}")

def get(name,*args):
    ref=Ref()
    call(name,*args,ptr(ref))
    return ref

def count(name,*args):
    n=Size()
    call(name,*args,ptr(n))
    return n.value

def new_group(entities,name):
    ref=get("SUGroupCreate")
    call("SUGroupSetName",ref,name.encode())
    call("SUEntitiesAddGroup",entities,ref)
    return ref,get("SUGroupGetEntities",ref)

def groups(entities):
    n=count("SUEntitiesGetNumGroups",entities)
    refs=(Ref*n)()
    got=count("SUEntitiesGetGroups",entities,Size(n),refs)
    assert got==n
    return [Ref(r) for r in refs]

def group_name(ref):
    string=get("SUStringCreate")
    call("SUGroupGetName",ref,ptr(string))
    length=count("SUStringGetUTF8Length",string)
    buffer=c.create_string_buffer(length+1)
    count("SUStringGetUTF8",string,Size(len(buffer)),buffer)
    call("SUStringRelease",ptr(string))
    return buffer.value.decode()

def write(parts,model):
    entities=get("SUModelGetEntities",model)
    mats={}
    collections={}
    sdk.SUGroupToDrawingElement.restype=Ref
    for part in parts:
        name=part["assembly"]
        if name not in collections:
            collections[name]=new_group(entities,name)[1]
        group,inside=new_group(collections[name],part["name"])
        position=(c.c_double*16)(1,0,0,0, 0,1,0,0, 0,0,1,0, *part["pivot"],1)
        call("SUGroupSetTransform",group,ptr(position))
        name=part["material"]
        if name not in mats:
            mat=get("SUMaterialCreate")
            call("SUMaterialSetName",mat,name.encode())
            rgba=(c.c_ubyte*4)(*part["color"],255)
            call("SUMaterialSetColor",mat,ptr(rgba))
            call("SUModelAddMaterials",model,Size(1),ptr(mat))
            mats[name]=mat
        call("SUDrawingElementSetMaterial",Ref(sdk.SUGroupToDrawingElement(group)),mats[name])
        geometry=get("SUGeometryInputCreate")
        points=(Point*len(part["vertices"]))(*(Point(*p) for p in part["vertices"]))
        call("SUGeometryInputSetVertices",geometry,Size(len(points)),points)
        for tri in part["triangles"]:
            loop=get("SULoopInputCreate")
            for i in tri[:3]:
                call("SULoopInputAddVertexIndex",loop,Size(i))
            for i,smooth in enumerate(tri[3:]):
                if smooth:
                    call("SULoopInputEdgeSetSoft",loop,Size(i),c.c_bool(True))
                    call("SULoopInputEdgeSetSmooth",loop,Size(i),c.c_bool(True))
            call("SUGeometryInputAddFace",geometry,ptr(loop),None)
        call("SUEntitiesFill",inside,geometry,c.c_bool(True))
        call("SUGeometryInputRelease",ptr(geometry))
    camera=get("SUModelGetCamera",model)
    low=[float("inf")]*3
    high=[-float("inf")]*3
    for part in parts:
        for vertex in part["vertices"]:
            for axis,offset in enumerate(part["pivot"]):
                value=vertex[axis]+offset
                low[axis]=min(low[axis],value)
                high[axis]=max(high[axis],value)
    center=[(a+b)/2 for a,b in zip(low,high)]
    span=sum((a-b)**2 for a,b in zip(low,high))**.5
    eye=Point(center[0]-.88*span,center[1]-1.6*span,center[2]+.52*span)
    target,up=Point(*center),Point(0,0,1)
    call("SUCameraSetOrientation",camera,ptr(eye),ptr(target),ptr(up))
    call("SUCameraSetOrthographicFrustumHeight",camera,c.c_double(span*1.16))

def verify(parts,model):
    expected={p["name"]:(p["assembly"],p["material"]) for p in parts}
    found={}
    faces=0
    for group in groups(get("SUModelGetEntities",model)):
        label=group_name(group)
        for piece in groups(get("SUGroupGetEntities",group)):
            name=group_name(piece)
            n=count("SUEntitiesGetNumFaces",get("SUGroupGetEntities",piece))
            assert n>0,(name,n)
            mat=get("SUDrawingElementGetMaterial",Ref(sdk.SUGroupToDrawingElement(piece)))
            string=get("SUStringCreate")
            call("SUMaterialGetName",mat,ptr(string))
            buf=c.create_string_buffer(256)
            count("SUStringGetUTF8",string,Size(256),buf)
            call("SUStringRelease",ptr(string))
            found[name]=(label,buf.value.decode())
            faces+=n
    assert expected==found,(expected.keys()-found.keys(),found.keys()-expected.keys())
    print(f"Reopened and checked {len(found)} named parts, {len(set(a for a,m in found.values()))} assemblies, {faces} faces")

parts=json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
dest=Path(sys.argv[2]).resolve()
if dest.exists():
    raise FileExistsError(dest)
sdk.SUInitialize()
try:
    model=get("SUModelCreate")
    write(parts,model)
    call("SUModelSaveToFile",model,os.fsencode(dest))
    call("SUModelRelease",ptr(model))
    model=Ref()
    status=c.c_int()
    call("SUModelCreateFromFileWithStatus",ptr(model),os.fsencode(dest),ptr(status))
    verify(parts,model)
    call("SUModelRelease",ptr(model))
finally:
    sdk.SUTerminate()
