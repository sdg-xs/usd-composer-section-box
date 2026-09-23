# Graph Report - section.box  (2026-09-23)

## Corpus Check
- Corpus is ~13,861 words - fits in a single context window. You may not need a graph.

## Summary
- 347 nodes · 790 edges · 25 communities (10 shown, 15 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 72 edges (avg confidence: 0.89)
- Token cost: 5,324 input · 2,071 output

## Community Hubs (Navigation)
- Box Model and Integration
- Viewport Manipulation
- Selection Fit Verification
- Extension and Clip Planes
- Box State and Undo
- Geometry Footprint Fitting
- Box Model Verification
- Saved Position Controls
- Extension Behavior Tests
- Section Box Panel
- Inactive Toolbar Icon
- Shell Verification Runner
- USD Bounding Box
- Active Toolbar Icon
- System Design Document
- Geometry Fit Design
- Kit Runtime Version
- Extension User Guide
- Python Code Linting
- Property Setter
- Saved Preset Location

## God Nodes (most connected - your core abstractions)
1. `SectionBoxState` - 49 edges
2. `SectionBox` - 32 edges
3. `Context` - 27 edges
4. `Face` - 25 edges
5. `verify_selection()` - 24 edges
6. `SavedPositionStore` - 23 edges
7. `stage_for()` - 23 edges
8. `SectionBoxWindow` - 22 edges
9. `rectangle()` - 21 edges
10. `SectionBoxManipulatorModel` - 19 edges

## Surprising Connections (you probably didn't know these)
- `TestSectionBoxExtension` --uses--> `Face`  [INFERRED]
  tests/test_extension.py → section_box/model.py
- `verify_gestures()` --uses--> `Face`  [INFERRED]
  tests/verify_gestures.py → section_box/model.py
- `TestSectionBoxExtension` --uses--> `SectionBox`  [INFERRED]
  tests/test_extension.py → section_box/model.py
- `TestSectionBoxExtension` --uses--> `SectionBoxState`  [INFERRED]
  tests/test_extension.py → section_box/state.py
- `verify_saved_positions()` --uses--> `Face`  [INFERRED]
  tests/verify_saved_positions.py → section_box/model.py

## Import Cycles
- None detected.

## Communities (25 total, 15 thin omitted)

### Community 0 - "Box Model and Integration"
Cohesion: 0.05
Nodes (45): asyncio, carb_settings, collections_abc, dataclasses, Enum, json, omni_kit_commands, omni_kit_test (+37 more)

### Community 1 - "Viewport Manipulation"
Cohesion: 0.10
Nodes (19): carb, omni_ext, omni_kit_app, omni_kit_viewport_utility, omni_ui_scene, Apply all enabled box faces to the active viewport's RTX render product., Extension entry point — wires up all section-box subsystems. Kit calls…, _BoxDragGesture (+11 more)

### Community 2 - "Selection Fit Verification"
Cohesion: 0.23
Nodes (35): random, fit_box_to_selection(), Fit visible geometry with horizontal top and bottom faces., affine_containment(), baked_rotation(), baked_tilted_asset(), center_unchanged(), check_box() (+27 more)

### Community 3 - "Extension and Clip Planes"
Cohesion: 0.09
Nodes (10): omni_kit_widget_toolbar, pathlib, ClipPlaneController, Omniverse Kit extension that provides an interactive section box., Register the section-box manipulator into the active viewport., SectionBoxExtension, section_box — Interactive section-box clipping tool for the Omniverse viewport., Section Box toggle on Kit's main toolbar. (+2 more)

### Community 4 - "Box State and Undo"
Cohesion: 0.13
Nodes (4): EditSectionBox, Inspection, setter, SectionBoxState

### Community 5 - "Geometry Footprint Fitting"
Cohesion: 0.10
Nodes (24): ArrayLike, math, Matrix4d, MeshCache, numpy, numpy_typing, Point2, Prim (+16 more)

### Community 6 - "Box Model Verification"
Cohesion: 0.13
Nodes (21): importlib_util, Plane, sys, case_box(), check_absolute_z_rotation(), check_all_six_planes(), check_corners_and_edges(), check_degenerate_zero_thickness() (+13 more)

### Community 7 - "Saved Position Controls"
Cohesion: 0.17
Nodes (5): Path, execute(), SavedPositionControls, SavedPositionStore, Stage

### Community 8 - "Extension Behavior Tests"
Cohesion: 0.09
Nodes (11): for_bounds produces a box spanning the given extents., Removing a listener stops further notifications., Integration tests that verify the extension loads and functions correctly., Create a fresh state before each test., The extension module imports without error., Toggling enabled fires a notification., toggle_face adds and removes individual faces., set_size_component updates a single axis. (+3 more)

### Community 9 - "Section Box Panel"
Cohesion: 0.15
Nodes (6): SavedPositionStore, Keep the UI widgets in sync when the model changes externally., Standalone ``omni.ui.Window`` with section-box controls., SectionBoxWindow, SectionBoxState, setter

## Knowledge Gaps
- **10 isolated node(s):** `run-verify.sh script`, `Wireframe box with solid visible edges and dashed hidden edges`, `Pale blue wireframe box icon`, `Cyan wireframe cube icon with dashed hidden edges`, `Ruff` (+5 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 126 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **15 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `SectionBox` connect `Box Model and Integration` to `Viewport Manipulation`, `Selection Fit Verification`, `Box State and Undo`, `Geometry Footprint Fitting`, `Box Model Verification`, `Saved Position Controls`, `Extension Behavior Tests`?**
  _High betweenness centrality (0.210) - this node is a cross-community bridge._
- **Why does `SectionBoxState` connect `Box State and Undo` to `Box Model and Integration`, `Viewport Manipulation`, `Extension and Clip Planes`, `Saved Position Controls`, `Extension Behavior Tests`?**
  _High betweenness centrality (0.188) - this node is a cross-community bridge._
- **Why does `SectionBoxWindow` connect `Section Box Panel` to `Box Model and Integration`, `Viewport Manipulation`, `Extension and Clip Planes`, `Geometry Footprint Fitting`?**
  _High betweenness centrality (0.109) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `SectionBoxState` (e.g. with `ClipPlaneController` and `EditSectionBox`) actually correct?**
  _`SectionBoxState` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `SectionBox` (e.g. with `SaveSectionBoxPosition` and `SavedPositionStore`) actually correct?**
  _`SectionBox` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 8 inferred relationships involving `Face` (e.g. with `_ResizeDragGesture` and `SectionBoxManipulator`) actually correct?**
  _`Face` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 23 inferred relationships involving `verify_selection()` (e.g. with `affine_containment()` and `baked_rotation()`) actually correct?**
  _`verify_selection()` has 23 INFERRED edges - model-reasoned connections that need verification._
## Update integrity notes

Gemini processed three documents and discarded 11 nodes attributed to undispatched code files. Document coverage is sparse. Local AST extraction supplies the code nodes. The merged graph has four self-loop edges and no missing or dangling endpoints. The raw incremental AST extraction had 48 references outside the changed-file subset and 33 endpoint-pair collapses in the undirected graph.

The previous two document hyperedges were removed when DESIGN.md was re-extracted. Gemini did not return replacement hyperedges.
