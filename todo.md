# section.box — finish it

## Feature playbook steps

- [x] 1. `how` over the affected subsystem. Done inline: read all 10 modules, the manifest, the
      tests, the verifier, and the stock `omni.kit.window.section` reference implementation.
- [x] 2. `architect` for parallel design exploration. `architect skipped: the design space is
      pinned by the stock implementation on disk. RTX exposes one section plane, the reference
      extension writes it one way, and the fixes are corrections toward that known-good shape
      rather than a choice between shapes. The one real fork (accept one cutting face vs. fake
      six) is settled by evidence in Decisions below, not by exploration.`
- [ ] 3. Throughput checkpoint (below).
- [ ] 4. Delegate code-writing to a subagent, review its diff myself.
- [ ] 5. Verify on the matching surface.
- [ ] 6. Rebase into small, ordered commits.
- [ ] 7. `interrogate` if the design is contested.
- [ ] 8. Run **Opening a PR**. `skip: not a git remote; this is an unversioned local extension
      folder. Deliverable is the working tree plus a local commit series.`

## Throughput checkpoint

- **Blocking first steps.** `git init` plus a baseline commit, so the diff is reviewable at all.
  The `with_face` model addition gates the window.py fix that consumes it.
- **Independent workstreams.** `n/a: five files, one coupled change set, one owner. The data/
  asset generation is genuinely independent but too small to be worth a second worker.`
- **Shared mutable state.** One delegate owns the whole extension folder exclusively. No second
  writer, so nothing to separate. I do not touch the tree while it holds it.
- **Smallest safe decomposition.** One worker. The defects thread through a single state and
  notification path, so splitting them across workers would cost more coordination than it saves.

## Decisions I own

- **Keep the single cutting face. Do not fake six.** `omni.kit.window.section` on disk writes one
  `[nx, ny, nz, -d]` to `omni:rtx:scene:sectionPlane:plane`. RTX has one section plane. The fix is
  to stop the panel lying about it, by naming the live cutting face in the UI.
- **Face toggling moves into the pure model** as `SectionBox.with_face(face, active)`. A
  value-changed handler must be idempotent in the value. That kills the feedback loop and makes
  the behaviour testable headless in `verify_model.py`.
- **Mirror the stock plane write exactly**, including the session-layer `Usd.EditContext` and the
  `[0, 0, 0, 0]` reset on teardown.

## Defects to fix, in severity order

| # | File | Defect | Evidence |
| --- | --- | --- | --- |
| 1 | `manipulator.py:69` | `_AXIS_VECTORS` used, never imported. Every face-handle drag raises `NameError` | import list vs. use |
| 2 | `window.py:127` | Face checkbox handler calls `toggle_face` while `_on_state_changed` writes the same model. Feedback loop | read of both paths |
| 3 | `clipping.py` | Plane written with no `Usd.EditContext`, so it authors into the root layer and dirties the scene | stock impl wraps every write |
| 4 | `clipping.py` | `_clear_plane` never resets the plane attribute, so the last cut persists | stock resets to `[0,0,0,0]` |
| 5 | `toolbar.py:52` | `add_widget` returns `None`, so `_unregister` leaks the group and `checked` never syncs | `toolbar.py:83-95` has no return |
| 6 | `config/extension.toml`, `toolbar.py` | `data/` absent. `icon.png`, `preview.png`, `icon.svg`, `icon_active.svg` all missing | folder listing |
| 7 | `model.py:resized` | Clamps extent at 0 but still shifts the centre by the full `delta/2` | code read |
| 8 | `state.py` | `enabled` is written to settings, never read back at startup | `_box_from_settings` |
| 9 | `stage.py` | Authors USD on every notification, including every drag frame | `_on_state_changed` |
| 10 | `extension.py` | SceneView view/projection unset until the camera first moves | `_setup_viewport_manipulator` |
| 11 | `config/extension.toml` | `defaultSize` comment says half-extents, code treats it as full size | comment vs. `corners()` |
| 12 | `manipulator.py` | Unused `half`, unused `SectionBoxState` import, function-local `import math` | code read |

## Verification

- `./run-verify.sh` runs `verify_model.py` under Kit's Python with USD on the path.
  Baseline before any change: **13 checks passed**.
- New checks required for `with_face` and the `resized` clamp.
- Kit-surface defects (1, 3, 4, 5, 10) cannot run headless. They are verified by reading against
  the stock implementation, and flagged as needing a live Composer session.
