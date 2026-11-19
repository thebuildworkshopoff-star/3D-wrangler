"""Write named Z-up COLLADA meshes for SketchUp from the shared parts schema."""
import json
import math
from datetime import datetime, timezone
from pathlib import Path
import sys
import xml.etree.ElementTree as ET


def add(parent, tag, text=None, **attributes):
    element = ET.SubElement(parent, tag, attributes)
    element.text = text
    return element


def write(parts, destination):
    if not parts or len({p["name"] for p in parts}) != len(parts):
        raise ValueError("Provide geometry with unique part names.")
    root = ET.Element("COLLADA", xmlns="http://www.collada.org/2005/11/COLLADASchema", version="1.4.1")
    asset = add(root, "asset")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    add(asset, "created", now)
    add(asset, "modified", now)
    add(asset, "unit", name="inch", meter="0.0254")
    add(asset, "up_axis", "Z_UP")
    effects = add(root, "library_effects")
    materials = add(root, "library_materials")
    geometry = add(root, "library_geometries")
    scene = add(add(root, "library_visual_scenes"), "visual_scene", id="model")
    groups, palette = {}, {}
    for i, part in enumerate(parts):
        material = part["material"]
        if material not in palette:
            mid = "material" + str(len(palette))
            palette[material] = mid
            effect = add(effects, "effect", id=mid+"fx")
            technique = add(add(effect, "profile_COMMON"), "technique", sid="common")
            diffuse = add(add(technique, "lambert"), "diffuse")
            add(diffuse, "color", " ".join(str(v / 255) for v in part["color"])+" 1")
            add(add(materials, "material", id=mid, name=material), "instance_effect", url="#"+mid+"fx")
        mid = palette[material]
        key = "g"+str(i)
        mesh = add(add(geometry, "geometry", id=key, name=part["name"]), "mesh")
        source = add(mesh, "source", id=key+"p")
        vertices = part["vertices"]
        if not vertices or any(len(v)!=3 or not all(math.isfinite(x) for x in v) for v in vertices):
            raise ValueError("Invalid vertices in "+part["name"])
        add(source, "float_array", " ".join(format(x, ".12g") for v in vertices for x in v),
            id=key+"xyz", count=str(3*len(vertices)))
        accessor = add(add(source, "technique_common"), "accessor", source="#"+key+"xyz",
                       stride="3", count=str(len(vertices)))
        for axis in "XYZ":
            add(accessor, "param", name=axis, type="float")
        add(add(mesh,"vertices",id=key+"v"),"input",semantic="POSITION",source="#"+key+"p")
        tris = [tri[:3] for tri in part["triangles"]]
        if not tris or any(len(set(tri))!=3 or min(tri)<0 or max(tri)>=len(vertices) for tri in tris):
            raise ValueError("Invalid triangles in "+part["name"])
        block = add(mesh,"triangles",material="finish",count=str(len(tris)))
        add(block,"input",semantic="VERTEX",source="#"+key+"v",offset="0")
        add(block,"p"," ".join(str(v) for tri in tris for v in tri))
        label = part["assembly"]
        if label not in groups:
            groups[label] = add(scene,"node",name=label,id="assembly"+str(len(groups)))
        node=add(groups[label],"node",name=part["name"],id="part"+str(i))
        add(node,"translate"," ".join(map(str,part["pivot"])))
        instance=add(node,"instance_geometry",url="#"+key)
        binding=add(add(instance,"bind_material"),"technique_common")
        add(binding,"instance_material",symbol="finish",target="#"+mid)
    add(add(root,"scene"),"instance_visual_scene",url="#model")
    with destination.open("xb") as file:
        ET.ElementTree(root).write(file, encoding="utf-8", xml_declaration=True)


if __name__=="__main__":
    write(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")),Path(sys.argv[2]))
