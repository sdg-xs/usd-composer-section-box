# Geometry-aligned selection fit

## Problem and contract

Fit Selection derives its orientation from selected geometry. The box rotates only around world Z, keeping its top and bottom faces parallel to world XY. Tilted assets are enclosed by an upright box.

An identity building root can contain rotated geometry. Rotation can also be baked into mesh points. Inferring the frame from a selected prim or common ancestor misses both cases. Georeferenced translation and scale must remain correct.

## Usage

The panel keeps its existing call and one undoable edit:

```python
box = fit_box_to_selection(state.active_context())
if box is not None:
    state.edit(box=box, enabled=True)

center = selection_center(state.active_context())
```

A selected parent includes its visible descendant geometry. Several selected branches produce one combined box. Empty geometry returns `None`. Center on Selection retains its combined world-aligned midpoint behavior.

## Shape

`selection.py` owns USD traversal and transforms. `footprint.py` owns convex hulls and minimum-area rectangles. State, clipping, overlay, and saved positions continue to consume `SectionBox` with an orthonormal transform and full dimensions. The public selection API does not change.

All authored mesh vertices contribute to a minimum-area XY rectangle. A convex hull preserves every horizontal projection without retaining interior points. Rotating calipers avoids quadratic rectangle search. Equal-area candidates have a deterministic angle convention. Analytic and other non-mesh geometry contribute conservative USD bounds in the same fitting calculation. No branch preserves pitch or roll.

Calculations use doubles and subtract an anchor before applying large georeferenced translations. Scale, shear, and reflection affect coordinates and dimensions, not the rigid output frame. Existing precision loss in authored float32 points cannot be recovered.

Selection roots are deduplicated by ancestry. Invisible subtrees are skipped. Purpose is evaluated per drawable because descendants can override it. Point instancers contribute their masked USD bound without counting prototype definitions as separate geometry. Fitting reads the default USD time and does not author scene changes.

## Synthesis decision

Convex-hull fitting was chosen over wall-direction inference because it defines a minimum-area result without mesh topology, confidence thresholds, or property-specific angles. Covariance-based orientation can change with vertex density and becomes ambiguous for square footprints. World Z is fixed by the horizontal-face requirement.

## Tradeoffs

- Minimum footprint area is a defined geometric objective. Irregular wings or outliers can make its angle differ from the dominant walls.
- All authored mesh points count, including unused points. Non-mesh bounds can conservatively enlarge the result.
- A tilted asset's upright box can be larger than a fully tilted box.
- Exact hull storage grows with the exterior vertex count. Performance must be measured on expanded instances, not just prototype meshes.

## Implementation reconciliation

NumPy from Kit's pip archive transforms points in double-precision chunks. Points strictly inside a support polygon can be discarded without changing the hull. Native-instance projections are reused by prototype path and exact linear transform within one fit. Local origins are subtracted before projection. No cache survives a fit call.

The final read-only saved-scene check took 1.95 seconds. Its XY footprint was about 63.66 by 69.17 scene units at 33.31 degrees, compared with the old world-aligned 77.88 by 85.19 footprint. All 3,196,675 included mesh vertices passed the actual six-plane containment check. The root layer remained unchanged. This saved-file result does not claim to reproduce unsaved live Composer state.

`run-verify.ps1` runs the model and selection checks, including scaled copies of irregular shapes to verify that fitting does not depend on asset size. An independent all-pairs orientation oracle passed 500 random planar clouds and a 100,000-vertex convex-circle stress case. `run-verify-kit.ps1` checks panel actions, undo/redo, rendered clipping, saved positions, viewport isolation, and gestures in an isolated Kit app.
