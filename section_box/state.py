"""Mutable runtime state for the section box, with observer-pattern notifications.

The immutable ``SectionBox`` dataclass holds the geometry.  This wrapper adds:
* a single mutable reference that can be swapped atomically,
* a callback list so the UI, manipulator, and clipping modules stay in sync,
* helpers to read/write persistent settings via Carbonite.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Optional

import carb.settings

from .model import Face, SectionBox

from pxr import Gf

# Carbonite setting keys — must match config/extension.toml.
_KEY_ENABLED = "/persistent/exts/section.box/enabled"
_KEY_DEFAULT_SIZE = "/persistent/exts/section.box/defaultSize"
_KEY_DEFAULT_FACES = "/persistent/exts/section.box/defaultFaces"
_KEY_PERSIST_TO_STAGE = "/persistent/exts/section.box/persistToStage"
_KEY_STAGE_PRIM_PATH = "/persistent/exts/section.box/stagePrimPath"

Listener = Callable[["SectionBoxState"], None]


class SectionBoxState:
    """Observable, mutable container for the current section-box configuration."""

    def __init__(self) -> None:
        self._settings = carb.settings.get_settings()
        self._listeners: list[Listener] = []
        self._enabled: bool = False
        self._box: SectionBox = self._box_from_settings()

    # --- public properties ---------------------------------------------------

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        if value == self._enabled:
            return
        self._enabled = value
        self._settings.set(_KEY_ENABLED, value)
        self._notify()

    @property
    def box(self) -> SectionBox:
        return self._box

    @box.setter
    def box(self, value: SectionBox) -> None:
        self._box = value
        self._notify()

    @property
    def persist_to_stage(self) -> bool:
        return bool(self._settings.get(_KEY_PERSIST_TO_STAGE))

    @persist_to_stage.setter
    def persist_to_stage(self, value: bool) -> None:
        self._settings.set(_KEY_PERSIST_TO_STAGE, value)
        self._notify()

    @property
    def stage_prim_path(self) -> str:
        return str(self._settings.get(_KEY_STAGE_PRIM_PATH) or "/SectionBox")

    # --- observer pattern ----------------------------------------------------

    def add_listener(self, callback: Listener) -> None:
        if callback not in self._listeners:
            self._listeners.append(callback)

    def remove_listener(self, callback: Listener) -> None:
        try:
            self._listeners.remove(callback)
        except ValueError:
            pass

    # --- convenience mutators ------------------------------------------------

    def toggle_face(self, face: Face) -> None:
        """Toggle a single face on or off."""
        faces = set(self._box.faces)
        if face in faces:
            faces.discard(face)
        else:
            faces.add(face)
        self.box = SectionBox(
            transform=self._box.transform,
            size=self._box.size,
            faces=frozenset(faces),
        )

    def set_size_component(self, axis: int, value: float) -> None:
        """Set one axis of the size vector (0=X, 1=Y, 2=Z)."""
        components = [self._box.size[0], self._box.size[1], self._box.size[2]]
        components[axis] = max(0.0, value)
        self.box = SectionBox(
            transform=self._box.transform,
            size=Gf.Vec3d(*components),
            faces=self._box.faces,
        )

    def reset(self) -> None:
        """Reset to the defaults stored in persistent settings."""
        self._box = self._box_from_settings()
        self._notify()

    # --- internals -----------------------------------------------------------

    def _box_from_settings(self) -> SectionBox:
        raw_size = self._settings.get(_KEY_DEFAULT_SIZE)
        if raw_size and len(raw_size) == 3:
            size = Gf.Vec3d(*[float(v) for v in raw_size])
        else:
            size = Gf.Vec3d(100.0, 100.0, 100.0)

        raw_faces = self._settings.get(_KEY_DEFAULT_FACES)
        if raw_faces:
            faces = frozenset(Face[name] for name in raw_faces if name in Face.__members__)
        else:
            faces = frozenset(Face)

        return SectionBox(size=size, faces=faces)

    def _notify(self) -> None:
        for listener in list(self._listeners):
            try:
                listener(self)
            except Exception:  # noqa: BLE001
                import traceback
                traceback.print_exc()
