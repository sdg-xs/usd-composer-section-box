"""Exercise Scene UI's real drag recognition with deterministic mouse rays."""

import omni.kit.app
import omni.kit.undo
import omni.ui as ui
import omni.ui.scene as sc

from section_box.manipulator import SectionBoxManipulator, _ResizeDragGesture, _TranslateDragGesture
from section_box.manipulator_model import SectionBoxManipulatorModel
from section_box.model import Face, SectionBox
from section_box.state import SectionBoxState


class DragInput(sc.GestureManager):
    def __init__(self):
        super().__init__()
        self.step = -10
        self.trace = []

    def amend_input(self, event):
        step = min(self.step, 12)
        event.mouse = sc.Vector2(min(max(step - 2, 0), 8) * 0.0125, 0)
        event.mouse_origin = sc.Vector3(event.mouse[0] * 100, 0, 5)
        event.mouse_direction = sc.Vector3(0, 0, -1)
        event.clicked = step == 1
        event.down = 1 <= step <= 10
        event.released = step == 11
        self.step += 1
        if step in (0, 1, 3):
            self.trace.append((step, list(event.mouse_origin), list(event.mouse_direction)))
        return event


async def verify_gestures():
    app = omni.kit.app.get_app()
    for mode in ("translate", "resize"):
        resize = mode == "resize"
        state = SectionBoxState()
        state.box = SectionBox()
        undo_count = len(omni.kit.undo.get_undo_stack())
        model = SectionBoxManipulatorModel(state)
        window = ui.Window("Section Box drag check", width=400, height=400)
        with window.frame:
            projection = [0.01, 0, 0, 0, 0, 0.01, 0, 0, 0, 0, 0.001, 0, 0, 0, 0, 1]
            view = sc.SceneView(sc.CameraModel(projection, sc.Matrix44.get_translation_matrix(0, 0, -5)))
            with view.scene:
                gesture = _ResizeDragGesture(model, Face.MAX_X) if resize else _TranslateDragGesture(model)
                manager = DragInput()
                gesture.manager = manager
                SectionBoxManipulator._create_handle(7, ui.color.white, gesture)
        try:
            for _ in range(45):
                await app.next_update_async()
            expected_position = 5 if resize else 10
            assert abs(state.box.transform.ExtractTranslation()[0] - expected_position) < 0.01, (
                mode,
                state.box.transform.ExtractTranslation(),
                manager.trace,
            )
            assert abs(state.box.size[0] - (110 if resize else 100)) < 0.01
            assert len(omni.kit.undo.get_undo_stack()) == undo_count + 1
            moved_box = state.box
            omni.kit.undo.undo()
            assert state.box == SectionBox()
            omni.kit.undo.redo()
            assert state.box == moved_box
        finally:
            view.scene.clear()
            window.destroy()
            model.destroy()
            state.destroy()
