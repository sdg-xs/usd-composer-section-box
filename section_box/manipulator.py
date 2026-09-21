"""Persistent viewport shapes for moving and resizing the section box."""

from __future__ import annotations

import omni.ui as ui
import omni.ui.scene as sc
from pxr import Gf

from .manipulator_model import SectionBoxManipulatorModel
from .model import AXIS_VECTORS, EDGE_INDICES, Face

_WIRE_COLOR = ui.color(0.2, 0.85, 1.0, 0.9)
_FACE_COLOR = [0.2, 0.85, 1.0, 0.08]
_HANDLE_COLOR = ui.color(1.0, 0.6, 0.1, 1.0)
_CENTER_COLOR = ui.color(1.0, 1.0, 0.2, 1.0)


class _BoxDragGesture(sc.DragGesture):
    def __init__(self, model: SectionBoxManipulatorModel, **kwargs):
        super().__init__(**kwargs)
        self._model = model

    def on_began(self):
        self._model.state.begin_edit()

    def on_ended(self):
        self._model.state.end_edit()


class _TranslateDragGesture(_BoxDragGesture):
    def on_changed(self):
        moved = self.sender.gesture_payload.moved
        state = self._model.state
        state.edit(box=state.box.translated(Gf.Vec3d(*moved)))


class _ResizeDragGesture(_BoxDragGesture):
    def __init__(self, model: SectionBoxManipulatorModel, face: Face, **kwargs):
        super().__init__(model, **kwargs)
        self._face = face

    def on_changed(self):
        box = self._model.state.box
        moved = Gf.Vec3d(*self.sender.gesture_payload.moved)
        outward = box.transform.TransformDir(AXIS_VECTORS[self._face.axis] * self._face.sign)
        length = outward.GetLength()
        if length == 0.0:
            return
        delta = Gf.Dot(moved, outward / length) / length
        self._model.state.edit(box=box.resized(self._face, delta))


class SectionBoxManipulator(sc.Manipulator):
    def __init__(self, model: SectionBoxManipulatorModel, **kwargs):
        self._model = model
        self._root = None
        self._lines = []
        self._faces = {}
        self._handles = {}
        self._center = None
        super().__init__(model=model, **kwargs)

    def on_build(self):
        self._lines = []
        self._faces = {}
        self._handles = {}
        with sc.Transform() as self._root:
            for _ in EDGE_INDICES:
                self._lines.append(sc.Line([0, 0, 0], [0, 0, 0], color=_WIRE_COLOR, thickness=1.5))
            for face in Face:
                self._faces[face] = sc.PolygonMesh([[0, 0, 0]] * 4, [_FACE_COLOR] * 4, [4], [0, 1, 2, 3])
                self._handles[face] = self._create_handle(5.0, _HANDLE_COLOR, _ResizeDragGesture(self._model, face))
            self._center = self._create_handle(7.0, _CENTER_COLOR, _TranslateDragGesture(self._model))
        self._update_geometry()

    @staticmethod
    def _create_handle(radius, color, gesture):
        with sc.Transform() as position:
            with sc.Transform(look_at=sc.Transform.LookAt.CAMERA, scale_to=sc.Space.SCREEN):
                sc.Rectangle(radius * 2, radius * 2, color=color, gesture=gesture)
        return position

    def on_model_updated(self, item):
        # Keep gesture senders alive throughout a drag instead of rebuilding them.
        if self._root is not None:
            self._update_geometry()

    def _update_geometry(self):
        state = self._model.state
        self._root.visible = state.enabled and state.show_box
        box = state.box
        corners = [list(point) for point in box.corners()]
        for line, (a, b) in zip(self._lines, EDGE_INDICES):
            line.start, line.end = corners[a], corners[b]
            line.visible = any(
                bool(a & (1 << face.axis)) == bool(b & (1 << face.axis)) == (face.sign > 0)
                for face in box.faces
            )
        for face in Face:
            indices = [i for i in range(8) if bool(i & (1 << face.axis)) == (face.sign > 0)]
            # Corner bit order makes a perimeter in 0, 1, 3, 2 order, even after rotation.
            self._faces[face].positions = [corners[indices[i]] for i in (0, 1, 3, 2)]
            self._faces[face].visible = face in box.faces
            self._handles[face].visible = face in box.faces
            local = AXIS_VECTORS[face.axis] * face.sign * box.size[face.axis] * 0.5
            self._handles[face].transform = sc.Matrix44.get_translation_matrix(*box.transform.Transform(local))
        self._center.transform = sc.Matrix44.get_translation_matrix(*box.transform.ExtractTranslation())
