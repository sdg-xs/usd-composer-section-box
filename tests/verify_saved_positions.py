"""Verify saved positions, undo, scene isolation, and root-layer ownership."""

import omni.kit.app
import omni.kit.undo
import omni.usd
from pxr import Gf

from section_box.model import Face, SectionBox


async def verify_saved_positions(extension, output):
    context = omni.usd.get_context()
    state = extension._state
    store = extension._positions
    controls = extension._window._position_controls
    stage = context.get_stage()
    layer = stage.GetRootLayer()
    first = SectionBox(size=Gf.Vec3d(12, 23, 34), faces=frozenset({Face.MIN_X, Face.MAX_Z}))
    first = first.rotated(1, 37).translated(Gf.Vec3d(10, 20, 30))
    state.box = first
    state.enabled = False
    # Explicit save must use root even if the user's edit target is session.
    stage.SetEditTarget(stage.GetSessionLayer())
    session_before = stage.GetSessionLayer().ExportToString()
    controls._name.set_value("Floor 1 / Észak")
    controls._on_action("save")
    assert len(store.list_positions()) == 1, controls._status.text
    first_path = controls._selected_path()
    assert layer.GetPrimAtPath(first_path)
    assert not stage.GetSessionLayer().GetPrimAtPath(first_path)
    assert stage.GetEditTarget().GetLayer() == stage.GetSessionLayer()
    assert stage.GetSessionLayer().ExportToString() == session_before
    assert not stage.GetPrimAtPath(first_path).GetAttribute("sectionBox:enabled")
    omni.kit.undo.undo()
    assert not store.list_positions() and not controls._positions
    omni.kit.undo.redo()
    assert len(controls._positions) == 1

    controls._name.set_value("  floor 1 / észak  ")
    controls._on_action("save")
    assert "already exists" in controls._status.text
    controls._name.set_value("   ")
    controls._on_action("save")
    assert "Enter a name" in controls._status.text
    assert len(store.list_positions()) == 1

    second = SectionBox(size=Gf.Vec3d(45, 56, 67)).rotated(2, 81)
    state.box = second
    controls._name.set_value("Roof")
    controls._on_action("save")
    second_path = controls._selected_path()
    assert len(store.list_positions()) == 2
    saved_root = layer.ExportToString()
    first_index = next(i + 1 for i, (path, _) in enumerate(controls._positions) if path == first_path)
    controls._combo.model.get_item_value_model().set_value(first_index)
    assert state.box == first and state.enabled
    omni.kit.undo.undo()
    assert state.box == second and not state.enabled and state.saved_position_path == second_path
    omni.kit.undo.redo()
    assert state.box == first and state.enabled and state.saved_position_path == first_path
    assert layer.ExportToString() == saved_root

    updated = first.translated(Gf.Vec3d(-2, 3, 8)).rotated(0, 12)
    state.edit(box=updated)
    controls._refresh(second_path)
    controls._on_action("load")
    omni.kit.undo.undo()
    assert state.box == updated
    assert layer.ExportToString() == saved_root
    controls._on_action("update")
    omni.kit.undo.undo()
    assert stage.GetPrimAtPath(first_path).GetAttribute("sectionBox:transform").Get() == first.transform
    omni.kit.undo.redo()
    assert stage.GetPrimAtPath(first_path).GetAttribute("sectionBox:transform").Get() == updated.transform

    # Locking the root still permits loading and adjusting the runtime box.
    layer.SetPermissionToEdit(False)
    try:
        store.load(second_path)
        assert state.box == second and state.enabled
        assert abs(extension._window._rotation_slider.model.as_float - 81) < 1e-4
        state.edit(box=second.translated(Gf.Vec3d(1, 2, 3)))
        for action in (
            lambda: store.save_new("Blocked"),
            lambda: store.update(first_path),
            lambda: store.delete(first_path),
        ):
            try:
                action()
            except ValueError as error:
                assert "read-only" in str(error)
            else:
                raise AssertionError("Read-only root accepted a saved-position edit")
    finally:
        layer.SetPermissionToEdit(True)

    store.load(first_path)
    assert state.box == updated
    store.delete(second_path)
    assert len(controls._positions) == 1
    omni.kit.undo.undo()
    assert len(controls._positions) == 2
    omni.kit.undo.redo()
    assert len(controls._positions) == 1
    assert state.box == updated
    try:
        store.delete("/Probe0")
    except ValueError:
        pass
    else:
        raise AssertionError("Deletion accepted an unrelated object")
    assert stage.GetPrimAtPath("/Probe0")

    saved_path = output / "saved-boxes.usda"
    assert layer.Export(str(saved_path))
    await context.new_stage_async()
    state.sync_stage()
    assert not state.enabled and not controls._positions
    assert state.box == SectionBox()
    await context.open_stage_async(str(saved_path))
    state.sync_stage()
    assert not state.enabled and state.saved_position_path == ""
    assert store.list_positions() == [(first_path, "Floor 1 / Észak")]
    assert controls._positions == store.list_positions()
    controls._combo.model.get_item_value_model().set_value(1)
    assert state.box == updated and state.enabled
    for _ in range(5):
        await omni.kit.app.get_app().next_update_async()
