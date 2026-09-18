"""Viewport manipulator — draws the section box wireframe and interactive handles.

Renders:
* 12-edge wireframe from ``corners()`` + ``EDGE_INDICES``
* Semi-transparent face shading on active clip faces
* Centre sphere (translate drag gesture)
* 6 face-centre handles (resize drag gesture)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import omni.ui as ui
import omni.ui.scene as sc

from pxr import Gf

from .model import Face, EDGE_INDICES, SectionBox
from .manipulator_model import SectionBoxManipulatorModel

if TYPE_CHECKING:
    from .state import SectionBoxState

# Visual constants.
_WIRE_COLOR = ui.color(0.2, 0.85, 1.0, 0.9)
_ACTIVE_FACE_COLOR = ui.color(0.2, 0.85, 1.0, 0.15)
_HANDLE_COLOR = ui.color(1.0, 0.6, 0.1, 1.0)
_CENTER_COLOR = ui.color(1.0, 1.0, 0.2, 1.0)
_HANDLE_RADIUS = 4.0
_CENTER_RADIUS = 6.0

# Maps each Face to the two axes (u, v) that span that face's quad, and the
# sign along the face's own axis.
_FACE_QUAD_AXES: dict[Face, tuple[int, int]] = {
    Face.MIN_X: (1, 2), Face.MAX_X: (1, 2),
    Face.MIN_Y: (0, 2), Face.MAX_Y: (0, 2),
    Face.MIN_Z: (0, 1), Face.MAX_Z: (0, 1),
}


class _TranslateDragGesture(sc.DragGesture):
    """Drag the centre handle to translate the box."""

    def __init__(self, model: SectionBoxManipulatorModel, **kwargs):
        super().__init__(**kwargs)
        self._model = model

    def on_changed(self):
        # gesture_payload.moved is the delta since the previous event, not the
        # total since on_began, so each one is applied on top of the last.
        moved = self.sender.gesture_payload.moved
        current = self._model.get_as_floats(self._model.get_item("position"))
        new_pos = [current[i] + moved[i] for i in range(3)]
        self._model.set_floats(self._model.get_item("position"), new_pos)


class _ResizeDragGesture(sc.DragGesture):
    """Drag a face handle to resize the box along that face's axis."""

    def __init__(self, model: SectionBoxManipulatorModel, face: Face, **kwargs):
        super().__init__(**kwargs)
        self._model = model
        self._face = face

    def on_changed(self):
        box = self._model.state.box
        moved = self.sender.gesture_payload.moved
        # The drag arrives in world space, so project it onto the face's outward
        # direction in world space — indexing moved[axis] only works unrotated.
        outward = box.transform.TransformDir(
            _AXIS_VECTORS[self._face.axis] * self._face.sign
        )
        length = outward.GetLength()
        if length == 0.0:
            return
        outward = outward / length
        delta = Gf.Dot(Gf.Vec3d(moved[0], moved[1], moved[2]), outward)
        self._model.state.box = box.resized(self._face, delta)


class SectionBoxManipulator(sc.Manipulator):
    """Draws the section box wireframe and interactive handles in the viewport."""

    def __init__(self, model: SectionBoxManipulatorModel, **kwargs):
        super().__init__(model=model, **kwargs)
        self._model: SectionBoxManipulatorModel = model

    def on_build(self):
        """Called by the scene framework whenever the model signals a change."""
        state = self._model.state
        if not state.enabled:
            return

        box = state.box
        corners = box.corners()

        # --- wireframe edges -------------------------------------------------
        for i, j in EDGE_INDICES:
            a, b = corners[i], corners[j]
            sc.Line(
                [a[0], a[1], a[2]],
                [b[0], b[1], b[2]],
                color=_WIRE_COLOR,
                thickness=1.5,
            )

        # --- semi-transparent shading on active faces ------------------------
        half = box.size * 0.5
        for face in Face:
            if face not in box.faces:
                continue
            self._draw_face_quad(box, face, corners)

        # --- centre translate handle -----------------------------------------
        centre = box.transform.ExtractTranslation()
        with sc.Transform(transform=sc.Matrix44.get_translation_matrix(
            centre[0], centre[1], centre[2]
        )):
            sc.Arc(
                _CENTER_RADIUS,
                color=_CENTER_COLOR,
                thickness=2.0,
                gesture=_TranslateDragGesture(self._model),
            )

        # --- face-centre resize handles --------------------------------------
        for face in Face:
            face_centre = self._face_centre(box, face)
            with sc.Transform(transform=sc.Matrix44.get_translation_matrix(
                face_centre[0], face_centre[1], face_centre[2]
            )):
                sc.Arc(
                    _HANDLE_RADIUS,
                    color=_HANDLE_COLOR,
                    thickness=2.0,
                    gesture=_ResizeDragGesture(self._model, face),
                )

    def on_model_updated(self, item):
        """Invalidate the visual when any model item changes."""
        self.invalidate()

    # --- helpers -------------------------------------------------------------

    @staticmethod
    def _face_centre(box: SectionBox, face: Face) -> Gf.Vec3d:
        """Compute the world-space centre of a face."""
        axis = face.axis
        half = box.size * 0.5
        local = Gf.Vec3d(0.0, 0.0, 0.0)
        local[axis] = half[axis] * face.sign
        return box.transform.Transform(local)

    @staticmethod
    def _draw_face_quad(
        box: SectionBox, face: Face, corners: list[Gf.Vec3d]
    ) -> None:
        """Draw a semi-transparent quad for an active face."""
        # Identify the 4 corners that lie on this face.
        axis = face.axis
        bit = 1 << axis
        positive = face.sign > 0
        indices = [
            i for i in range(8)
            if bool(i & bit) == positive
        ]
        if len(indices) != 4:
            return

        # Sort corners into a winding order for the quad.
        pts = [corners[i] for i in indices]
        centre = sum((p for p in pts), Gf.Vec3d(0, 0, 0)) * 0.25
        # Simple planar sort by angle around the face centre.
        u_axis, v_axis = _FACE_QUAD_AXES[face]

        import math
        def angle_key(p):
            return math.atan2(
                (p - centre)[v_axis],
                (p - centre)[u_axis],
            )

        pts.sort(key=angle_key)

        # Draw as two triangles (sc doesn't have a filled quad primitive).
        for tri_indices in ((0, 1, 2), (0, 2, 3)):
            verts = []
            for ti in tri_indices:
                p = pts[ti]
                verts.extend([p[0], p[1], p[2]])
            sc.TriangleStrip(
                verts,
                colors=[_ACTIVE_FACE_COLOR],
            )
