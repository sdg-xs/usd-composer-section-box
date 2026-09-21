# Section box system design

Approved during the design interview on 2026-09-21. Initial supported runtime: Kit 110.2.

## Product contract

The extension supports model inspection with one runtime section box. Six enabled faces retain geometry inside the box. Cuts stay open and source geometry is unchanged.

- Only the active viewport clips. Its overlay follows the same viewport.
- Opening a scene or enabling the extension starts unclipped. Saved positions remain available.
- Fit to Selection matches bounds and orientation and enables clipping. Multiple selections use their common ancestor's orientation.
- Center on Selection moves the box without changing its dimensions or orientation.
- Section Box Active controls clipping. Show Box independently controls the outline and handles while clipping is active.
- Only active faces show their fill, outline, and resize handle. Shared edges remain visible if either adjacent face is active. The center handle remains available for moving the box.
- Selecting a saved position immediately restores its transform, dimensions, and active faces, then enables clipping.
- Temporary adjustments never overwrite saved positions. Save New creates a named position; Update replaces the selected position; Delete removes it.
- Changing positions does not prompt to save temporary adjustments. Undo can recover them.
- Positions belong to the main scene file, regardless of the current USD edit target. Users save the scene to persist changes to disk.
- Read-only scenes allow inspection and loading positions. Saving, updating, or deleting positions requires a writable scene copy.
- Box edits and saved-position changes use Kit undo/redo. A completed drag is one undo step.

## Responsibilities

| Module | Owns |
| --- | --- |
| model.py | Box geometry, corners, planes, rotation, translation, resizing |
| state.py | Current inspection state, stage identity, scene-change reset, continuous edit boundaries |
| commands.py | Undoable runtime snapshots and root-layer position edits |
| window.py | Panel controls and action callbacks |
| selection.py | Selection bounds, common-ancestor orientation, fitted boxes, and world-space centers |
| saved_position_controls.py | Named-position selector and explicit save/update/delete controls |
| saved_positions.py | SavedPositionStore, position validation, and root-layer storage |
| clipping.py | Active render-product clipping overrides in the session layer |
| manipulator.py / manipulator_model.py | Viewport handles and runtime geometry synchronization |
| extension.py / toolbar.py | Wiring, viewport attachment, lifecycle, toolbar |

Panel controls and handles submit changes through the state edit API. It previews continuous edits in memory, then records one command at the end. Commands apply complete runtime snapshots, so fitting and loading restore geometry and activation together during undo.

Each command belongs to the scene generation in which it was created. Commands from a closed scene or unloaded extension cannot mutate a new scene. The extension does not clear unrelated application undo history.

## Code organization

Runtime modules stay directly under `section_box/`. Verification code lives under `tests/`; root scripts launch checks and build the install archive. `config/` contains the Kit manifest, and `data/` contains icons. Generated checks and packages go to the ignored `verification/` and `dist/` folders.

The architecture review compared flat capability modules with separate USD, viewport, and UI packages. It selected the flat layout because each module already owns a distinct responsibility, and extra packages would add import and lifecycle changes without simplifying callers. Selection calculations now have their own module, so the window only requests a fitted box or a center.

```python
positions = SavedPositionStore(state)
window = SectionBoxWindow(state, positions)
toolbar = ToolbarButton(state, window)

box = fit_box_to_selection(state.active_context())
if box is not None:
    state.edit(box=box, enabled=True)

path = positions.save_new("Floor 1")
positions.load(path)
```

`fit_box_to_selection(context)` returns a `SectionBox` or `None`; `selection_center(context)` returns a world-space `Gf.Vec3d` or `None`. Both use one private bounds calculation. `SavedPositionStore` exposes `list_positions`, `save_new`, `load`, `update`, and `delete`. Its list contains `(path, name)` pairs; the path identifies a scene position. `Inspection.saved_position_path` tracks the selected position independently of temporary edits.

This layout accepts direct Kit and USD dependencies in exchange for short call paths. It retains the existing geometry API, command boundaries, and scene schema. The extension owns overlay attachment and teardown, including the stored frame needed when a viewport closes. Position commands explicitly notify controls after USD-only edits even when the runtime snapshot is unchanged.

The viewport manipulator reads the inspection state directly. Its Scene UI adapter forwards one notification per state change without keeping separate position, size, or transform values. Geometry updates preserve the existing handles throughout a drag.

## Storage and rendering

Named positions use Scope prims under /SectionBox/Presets with UUID identifiers. Attributes store the display name, double-precision transform, dimensions, and active face names. Names are unique within a scene, ignoring case. Activation and overlay visibility are runtime state and are not stored in new positions.

Existing named positions remain readable; their old enabled attribute is ignored. Legacy current-box autosave data is left intact but is no longer restored or updated.

Saved-position commands explicitly target the root layer and reserve only the affected position for undo. Deletion authors an inactive opinion in the root layer so a weaker-layer position cannot reappear accidentally.

Clipping writes plane coefficients and the enabled flag to the active render product in the session layer. It restores prior authored values on disable, viewport switch, or shutdown. It does not use the global RTX enable setting. Selection, storage, and rendering use the active viewport's USD context.

## Verification and delivery

Geometry checks run with Kit's USD Python libraries. An isolated Kit app verifies rendering, control synchronization, real drag gestures, undo/redo, saved-position round trips, root-layer ownership, read-only behavior, stage resets, and viewport isolation.

The distribution contains only the runtime Python modules, Kit manifest, and two toolbar icons. Documentation and development tools remain in the source checkout. Colleagues add the installed section.box folder's parent directory as an extension search path in Kit 110.2 and enable section.box.
