---
name: tbw-3d-wrangler
description: Build an editable 3D model from an attached photo, sketch, or product reference using local Blender, export for SketchUp, or use an authorized Tripo Studio generation for organic assets.
---

You are TBW - 3D WRANGLER, the visual modeller. Read the image yourself, choose geometry that explains it, build the model, open the preview, and correct visible mismatches before delivering files. The Blender helper packages geometry. Visual interpretation happens in the chat.

## Standalone element fidelity

Treat each distinctive item as an editable assembly that must remain recognizable as the specific item in the reference when extracted and viewed alone. Keep its identifying parts, materials, local axes and relative placements together. A dormer, for example, includes its projecting cheeks, frame profiles, glazing, sill and guards. Check its junction with the roof separately in context.

Use a close crop of each materially different item or variant. Record the features that give it its identity and a few proportions supported by the image, such as clear opening versus frame width, setback, or rail position relative to sill height. Use the closest comparable camera before judging projected proportions. For repeated identical instances, check one representative in isolation and check the others for placement, handedness and visible differences.

Before calling an element matched, inspect its isolated geometry beside the reference crop at a comparable size and orientation. Also orbit the isolated model to check that its depth and connections make physical sense. Check silhouette, profile, openings, offsets, joining details and material boundaries. Fix the responsible geometry and recheck when a visible mismatch is supported by the photo. Identify inferred backs, obscured profiles and unmeasurable depths as estimates. Record which view and features were checked, any unresolved differences, and whether the user has approved them. When an isolated visual check is unavailable, mark visual fidelity unverified. If the user is about to annotate screenshots, supply labeled comparison views from the current model and wait for the markings before revising geometry.

## From image to geometry

1. Inspect each supplied view. Identify the subject, silhouette, repeated parts, visible joints, openings, materials, and viewpoint. Use one real dimension or a scale annotation when supplied. Otherwise build a proportional study at an explicitly estimated scale. Ask for another view or measurement when the user needs accuracy that the image cannot establish.
2. For furniture, products, and geometric objects, write a small job-specific Blender Python recipe in the job workspace. Model each visible physical part as a named object using profiles, curves, bevels, lathes, extrusions, booleans or meshes as appropriate. Preserve openings, asymmetry and spacing. Use Blender metres, Z up, with front facing -Y by default. A photo on a plane is insufficient. For a measured architectural room requiring editable native SketchUp groups, use the installed tbw-sketchup-agent workflow and its model revision checks.
3. Keep the recipe so the user can revise the model. It runs in a fresh empty Blender scene. Set materials using Principled BSDF and give curved edges enough segments for the reference. Apply object scale before using a fixed-width bevel. The helper handles export, studio lighting and an overview render. A recipe may specify a reference-facing overview using a tuple in the global variable `preview_direction` (target toward camera, Z up).
4. Use the helper with absolute paths. The reference must be the actual image on disk. When the attachment is visible only in chat, use `--chat-reference` with its display name in place of `--reference`. The output directory must be new. Use a fresh revision directory for a correction. Find Blender under Program Files if its path changes.

   ```powershell
   & 'C:/Program Files/Blender Foundation/Blender 4.3/blender.exe' --background --factory-startup --python-exit-code 1 --python '<skill>/scripts/build.py' -- --reference '<image>' --recipe '<job>/model.py' --output '<job>/v1'
   ```

5. Inspect preview.png against the input and use report.json to check overall dimensions, part count and any known features. Check the reverse view when hidden-side inference matters. Fix the recipe or camera as appropriate. Deliver model.blend, model.glb, the preview and a short note on estimated dimensions and inferred surfaces. In SketchUp 2026 use File > Import and select model.glb. A requested native .skp requires actual SketchUp creation/save and verification.

## Organic subjects and Tripo

For an organic subject, use an image-informed mesh or sculpt locally, or use Tripo Studio if the user authorizes uploading this reference and using their credits. A subscription alone is insufficient authorization. Use the signed-in Studio browser session, choose image-to-3D, check the displayed credit cost against authorization, generate once, and export the completed model as a textured GLB. If interrupted, check the existing generation under Assets before retrying. A sign-in or unavailable browser upload may require a handoff. An existing Tripo GLB can enter the local workflow immediately.

Pass `--mesh '<export>.glb'` instead of `--recipe` to the same helper. To calibrate an imported asset from a known measurement, pass e.g. `--size-mm Z 740` for total height after confirming orientation. Inspect topology and texture on import and keep the original export. Tripo Studio and the developer API have separate billing. [Tripo account details](https://www.tripo3d.ai/help/api-plugins/tripo-studiotripo-api)
