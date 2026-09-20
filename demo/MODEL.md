# Corrected room model

The supplied Blender scene was corrected only where the two room videos supported the requested seating-layout change. The original source file remains unchanged.

## What changed

- Student seating now has three blocks across the main six rows, separated by two descending interior stair aisles. The central block is wider than the side blocks.
- The same 28 student table groups were re-spanned along the room-width axis. Their heights, depths, top thicknesses, modesty-panel thicknesses, leg/foot shapes and original materials were retained.
- All 102 student chairs were moved as intact groups. No chair mesh was reshaped or replaced. The existing loose spare chair was moved intact to the adjacent rear-side landing so it no longer projects into an aisle.
- Two runs of intermediate treads and pale metal stair nosing were added, following the visible stair pattern. They reuse the original carpet material and one new light-metal nosing material.

## What stayed unchanged

The room shell, walls, original floor and tiers, ceiling and its original transparency, projectors, wall lights, doors, teaching area, left perimeter ramp, low ramp partition, wood cap and railings remain unchanged. All 38 original materials remain unchanged. The original camera animation remains in the export. No original objects were deleted. The original 236 hidden reference objects remain hidden in the corrected Blender file and excluded from the browser export.

At the rear looking toward the teaching wall, the original ramp is on the viewer's left. This is the source's positive-X side; the model was not mirrored.

## Evidence and limits

Both room videos were reviewed independently across their full duration with contact sheets and detailed frame inspection. Strong references include `IMG_4014 (1).MOV` at 284–288 seconds for the three-block layout and three visible chairs on a front side row; at 47/73/285 seconds for stair details; and `IMG_3707 (1).MOV` at 250 seconds for the intermediate stair treads and nosing. The perimeter ramp is visible at 190–215 seconds in IMG_3707 and 225–265 seconds in IMG_4014.

The main rows use a 3+8+3 distribution, while the source's two narrower rear rows retain nine chairs each in a continuous central block. These counts preserve the source's 102 student chairs and are a restrained reconstruction choice, not a measured seat survey. Exact widths and dimensions remain estimates. Main stair aisles are 1.10 m wide within the inherited scale. The unchanged narrower rear bay gives the final audience-right upper-tier aisle end a 0.70 m width; the main descent is 1.10 m. No claim of physical measurement or building-code compliance is made.

## Verification

- 310 original meshes are unchanged in geometry, transforms and material assignments, including the 236 hidden reference meshes and 74 visible architectural/fixture/teaching meshes.
- 309 chair component meshes retain their original local vertices, faces and materials and were translated only.
- 84 table components changed only their X spans or the X positions of intact pedestals/feet. Their Y/Z bounds match the source exactly.
- 42 stair/nosing meshes were added. All student and spare furniture across all eight rows was checked against both aisle strips; there are no furniture intrusions.
- The corrected GLB was imported back into Blender: 509 meshes and 70,008 triangles matched, with zero measured vertex-coordinate drift and matching material assignments. All exported PBR material values match the corrected Blender scene exactly.
- The source Blender file and the original baseline GLB hashes were checked again and remain unchanged.

The PNG/JPEG previews use added presentation lighting and camera framing only. The corrected Blender scene and browser model preserve the original materials. The browser supplies its own lighting.

## File fingerprints

Original source SHA-256: `e071c570e27805c28c68f06026a263e913a12a88efee13aea430617e3ea5ac89`

Corrected Blender SHA-256: `debe76955bd984db4a3d73797eb2a0ea807e4cb9abc35cb3605836d7305ce409`

Corrected GLB SHA-256: `8742c00004357a1857f503c883662be1fc62b20ae00055a739c46bda5a778d8f`

Structured evidence is in `room-correction-report.json`, `room-corrected-validation.json` and `room-corrected-manifest.json`.
