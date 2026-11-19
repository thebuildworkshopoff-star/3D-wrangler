"""Package a Codex-modelled scene or a Studio GLB using Blender background mode."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import runpy
import sys
import tempfile

import bpy
from mathutils import Vector


def options():
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--reference", type=Path)
    source.add_argument("--chat-reference")
    geometry = parser.add_mutually_exclusive_group(required=True)
    geometry.add_argument("--recipe", type=Path)
    geometry.add_argument("--mesh", type=Path)
    parser.add_argument("--size-mm", nargs=2, metavar=("AXIS", "LENGTH"))
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1:])


def scene_bounds(objects):
    graph = bpy.context.evaluated_depsgraph_get()
    low = [math.inf] * 3
    high = [-math.inf] * 3
    for obj in objects:
        evaluated = obj.evaluated_get(graph)
        mesh = evaluated.to_mesh()
        try:
            if mesh is None or not len(mesh.polygons):
                continue
            matrix = evaluated.matrix_world
            aligned = all(sum(abs(matrix[i][j]) > 1e-9 for j in range(3)) <= 1
                          for i in range(3))
            coords = (map(Vector, evaluated.bound_box) if aligned
                      else (vertex.co for vertex in mesh.vertices))
            for coord in coords:
                point = matrix @ coord
                for i in range(3):
                    low[i] = min(low[i], point[i])
                    high[i] = max(high[i], point[i])
        finally:
            evaluated.to_mesh_clear()
    if not all(math.isfinite(v) for v in low + high):
        raise ValueError("Expected finite model geometry with faces")
    return Vector(low), Vector(high)


def fit_size(objects, axis, length):
    low, high = scene_bounds(objects)
    span = (high - low)[("X", "Y", "Z").index(axis.upper())]
    metres = float(length) / 1000
    if span <= 0 or not math.isfinite(metres) or metres <= 0:
        raise ValueError("Scale requires a nonzero axis extent and positive length")
    roots = [obj for obj in bpy.context.scene.objects if obj.parent is None]
    scale = bpy.data.objects.new("Reference scale", None)
    bpy.context.scene.collection.objects.link(scale)
    for obj in roots:
        obj.parent = scale
    scale.scale = (metres / span,) * 3
    bpy.context.view_layer.update()


def studio(low, high, direction):
    scene = bpy.context.scene
    center = (low + high) / 2
    radius = (high - low).length / 2
    if radius <= 0 or direction.length == 0:
        raise ValueError("A visible extent and a nonzero preview direction are required")
    rig = bpy.data.collections.new("Preview studio")
    scene.collection.children.link(rig)
    camera = bpy.data.objects.new("Overview", bpy.data.cameras.new("Overview"))
    rig.objects.link(camera)
    camera.location = center + direction.normalized() * radius * 4
    camera.rotation_euler = (-direction).to_track_quat("-Z", "Y").to_euler()
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = radius * 2.2
    camera.data.clip_start = radius * 0.005
    camera.data.clip_end = radius * 12
    scene.camera = camera
    for name, position, energy in [
        ("Key", (-3, -4, 5), 520), ("Fill", (4, -2, 2), 250), ("Rim", (1, 4, 4), 450)
    ]:
        lamp = bpy.data.lights.new(name, "AREA")
        obj = bpy.data.objects.new(name, lamp)
        rig.objects.link(obj)
        obj.location = center + Vector(position).normalized() * radius * 3
        obj.rotation_euler = (center - obj.location).to_track_quat("-Z", "Y").to_euler()
        lamp.energy = energy * radius ** 2
        lamp.size = radius * 1.6
    world = bpy.data.worlds.new("Neutral studio")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.19, 0.21, 0.24, 1)
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 12
    scene.cycles.use_denoising = True
    scene.render.resolution_x = scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                region = area.spaces.active.region_3d
                region.view_rotation = camera.rotation_euler.to_quaternion()
                region.view_distance = radius * 3.5
                region.view_location = center
                area.spaces.active.overlay.show_extras = False
                area.spaces.active.shading.color_type = "MATERIAL"


def checked(status, action):
    if "FINISHED" not in status:
        raise RuntimeError(f"{action} returned {status}")


def main():
    args = options()
    destination = args.output.resolve()
    if destination.exists():
        raise FileExistsError(destination)
    if args.reference:
        reference = {"file": args.reference.name,
                     "sha256": hashlib.sha256(args.reference.read_bytes()).hexdigest()}
    else:
        reference = {"chat_attachment": args.chat_reference}
    bpy.ops.wm.read_factory_settings(use_empty=True)
    direction = (1, -1.6, 0.95)
    if args.mesh:
        checked(bpy.ops.import_scene.gltf(filepath=str(args.mesh.resolve())), "GLB import")
    else:
        recipe = runpy.run_path(str(args.recipe.resolve()), run_name="__main__")
        direction = recipe.get("preview_direction", direction)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    objects = [obj for obj in scene.objects
               if obj.type in {"MESH", "CURVE", "SURFACE", "FONT", "META"} and not obj.hide_render]
    bpy.context.view_layer.update()
    if args.size_mm:
        fit_size(objects, *args.size_mm)
    low, high = scene_bounds(objects)
    if min(high - low) <= 0:
        raise ValueError("Expected a three-dimensional subject")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as temp:
        stage = Path(temp) / "model-package"
        stage.mkdir()
        checked(bpy.ops.export_scene.gltf(filepath=str(stage / "model.glb"), export_format="GLB",
                                         export_apply=bool(args.recipe),
                                         use_renderable=True, export_cameras=False,
                                         export_lights=False), "GLB export")
        studio(low, high, Vector(direction))
        bpy.ops.file.pack_all()
        bpy.context.preferences.filepaths.save_version = 0
        scene.render.filepath = "//preview.png"
        checked(bpy.ops.wm.save_as_mainfile(filepath=str(stage / "model.blend")), "Blend save")
        checked(bpy.ops.render.render(write_still=True), "Preview render")
        for filename in ("model.glb", "model.blend", "preview.png"):
            if (stage / filename).stat().st_size <= 0:
                raise RuntimeError(f"Empty {filename}")
        report = {"reference": reference, "geometry_source": (args.recipe or args.mesh).name,
                  "size_mm_xyz": [round(v * 1000, 3) for v in high - low],
                  "parts": sorted(obj.name for obj in objects), "blender": bpy.app.version_string}
        (stage / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        stage.rename(destination)
    print("Saved model package to", destination)


if __name__ == "__main__":
    main()
