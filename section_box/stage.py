"""USD stage persistence for the section box.

When ``persist_to_stage`` is enabled, the current section-box configuration is
written to a custom USD prim so it survives scene save / reload.  When a stage
with a saved section box is opened, the state is restored automatically.

The prim uses custom attributes under the ``sectionBox:`` namespace to avoid
collision with standard USD schemas.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import carb
import omni.usd

from pxr import Gf, Sdf, Usd, UsdGeom

from .model import Face, SectionBox

if TYPE_CHECKING:
    from .state import SectionBoxState

# Custom attribute names under the ``sectionBox:`` namespace.
_NS = "sectionBox"
_ATTR_SIZE = f"{_NS}:size"
_ATTR_TRANSFORM = f"{_NS}:transform"
_ATTR_FACES = f"{_NS}:faces"
_ATTR_ENABLED = f"{_NS}:enabled"


class StageSerializer:
    """Reads and writes ``SectionBox`` state from / to a USD prim."""

    def __init__(self, state: SectionBoxState) -> None:
        self._state = state
        self._stage_event_sub = None
        self._writing = False  # guard against re-entrant notifications

        self._state.add_listener(self._on_state_changed)
        self._subscribe_stage_events()

    def destroy(self) -> None:
        self._state.remove_listener(self._on_state_changed)
        self._stage_event_sub = None

    # --- stage event subscription --------------------------------------------

    def _subscribe_stage_events(self) -> None:
        usd_context = omni.usd.get_context()
        if usd_context is None:
            return
        events = usd_context.get_stage_event_stream()
        self._stage_event_sub = events.create_subscription_to_pop(
            self._on_stage_event
        )

    def _on_stage_event(self, event) -> None:
        """When a stage opens, try to restore the section box from the prim."""
        if event.type == int(omni.usd.StageEventType.OPENED):
            self._try_restore()

    # --- write to stage ------------------------------------------------------

    def _on_state_changed(self, state: SectionBoxState) -> None:
        if self._writing:
            return
        if not state.persist_to_stage:
            return
        self._write_to_stage()

    def _write_to_stage(self) -> None:
        stage = self._get_stage()
        if stage is None:
            return

        prim_path = self._state.stage_prim_path
        prim = stage.GetPrimAtPath(prim_path)
        if not prim.IsValid():
            prim = stage.DefinePrim(prim_path, "Scope")

        box = self._state.box

        # Size as a double3.
        size_attr = prim.GetAttribute(_ATTR_SIZE)
        if not size_attr.IsValid():
            size_attr = prim.CreateAttribute(
                _ATTR_SIZE, Sdf.ValueTypeNames.Double3, custom=True
            )
        size_attr.Set(box.size)

        # Transform as a matrix4d.
        xform_attr = prim.GetAttribute(_ATTR_TRANSFORM)
        if not xform_attr.IsValid():
            xform_attr = prim.CreateAttribute(
                _ATTR_TRANSFORM, Sdf.ValueTypeNames.Matrix4d, custom=True
            )
        xform_attr.Set(box.transform)

        # Active faces as a string array.
        faces_attr = prim.GetAttribute(_ATTR_FACES)
        if not faces_attr.IsValid():
            faces_attr = prim.CreateAttribute(
                _ATTR_FACES, Sdf.ValueTypeNames.StringArray, custom=True
            )
        faces_attr.Set([face.name for face in box.faces])

        # Enabled flag.
        enabled_attr = prim.GetAttribute(_ATTR_ENABLED)
        if not enabled_attr.IsValid():
            enabled_attr = prim.CreateAttribute(
                _ATTR_ENABLED, Sdf.ValueTypeNames.Bool, custom=True
            )
        enabled_attr.Set(self._state.enabled)

    # --- read from stage -----------------------------------------------------

    def _try_restore(self) -> None:
        """Attempt to read section-box state from the current stage."""
        if not self._state.persist_to_stage:
            return

        stage = self._get_stage()
        if stage is None:
            return

        prim_path = self._state.stage_prim_path
        prim = stage.GetPrimAtPath(prim_path)
        if not prim.IsValid():
            return

        try:
            self._writing = True  # prevent re-entrant write from the listener

            size_attr = prim.GetAttribute(_ATTR_SIZE)
            xform_attr = prim.GetAttribute(_ATTR_TRANSFORM)
            faces_attr = prim.GetAttribute(_ATTR_FACES)
            enabled_attr = prim.GetAttribute(_ATTR_ENABLED)

            size = size_attr.Get() if size_attr.IsValid() else None
            transform = xform_attr.Get() if xform_attr.IsValid() else None
            face_names = faces_attr.Get() if faces_attr.IsValid() else None
            enabled = enabled_attr.Get() if enabled_attr.IsValid() else None

            if size is None and transform is None:
                return  # nothing saved

            box_args: dict = {}
            if size is not None:
                box_args["size"] = Gf.Vec3d(size)
            if transform is not None:
                box_args["transform"] = Gf.Matrix4d(transform)
            if face_names is not None:
                faces = frozenset(
                    Face[name]
                    for name in face_names
                    if name in Face.__members__
                )
                box_args["faces"] = faces

            self._state.box = SectionBox(**box_args)

            if enabled is not None:
                self._state.enabled = bool(enabled)

        except Exception:  # noqa: BLE001
            carb.log_warn("[section.box] Failed to restore section box from stage")
            import traceback
            traceback.print_exc()
        finally:
            self._writing = False

    def remove_from_stage(self) -> None:
        """Delete the section-box prim from the current stage."""
        stage = self._get_stage()
        if stage is None:
            return
        prim_path = self._state.stage_prim_path
        prim = stage.GetPrimAtPath(prim_path)
        if prim.IsValid():
            stage.RemovePrim(prim_path)

    # --- helpers -------------------------------------------------------------

    @staticmethod
    def _get_stage() -> Optional[Usd.Stage]:
        usd_context = omni.usd.get_context()
        if usd_context is None:
            return None
        return usd_context.get_stage()
