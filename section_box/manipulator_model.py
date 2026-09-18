"""``omni.ui.scene.AbstractManipulatorModel`` bridge for the section box.

Translates ``SectionBoxState`` into the data interface that
``omni.ui.scene.Manipulator`` expects, and propagates drag-gesture updates
back to the state.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import omni.ui.scene as sc

from pxr import Gf

from .model import Face, SectionBox

if TYPE_CHECKING:
    from .state import SectionBoxState


class SectionBoxManipulatorModel(sc.AbstractManipulatorModel):
    """Model that feeds section-box data to the viewport manipulator."""

    class PositionItem(sc.AbstractManipulatorItem):
        """Represents a 3-component position value."""

        def __init__(self) -> None:
            super().__init__()
            self.value: list[float] = [0.0, 0.0, 0.0]

    class SizeItem(sc.AbstractManipulatorItem):
        """Represents the box's 3-component size."""

        def __init__(self) -> None:
            super().__init__()
            self.value: list[float] = [100.0, 100.0, 100.0]

    class TransformItem(sc.AbstractManipulatorItem):
        """Represents the full 4×4 transform as a flat 16-float list (row-major)."""

        def __init__(self) -> None:
            super().__init__()
            self.value: list[float] = list(_identity_flat())

    def __init__(self, state: SectionBoxState) -> None:
        super().__init__()
        self._state = state
        self._position = SectionBoxManipulatorModel.PositionItem()
        self._size = SectionBoxManipulatorModel.SizeItem()
        self._transform = SectionBoxManipulatorModel.TransformItem()

        self._sync_from_state()
        self._state.add_listener(self._on_state_changed)

    def destroy(self) -> None:
        self._state.remove_listener(self._on_state_changed)

    # --- AbstractManipulatorModel interface ----------------------------------

    def get_as_floats(self, item: sc.AbstractManipulatorItem) -> list[float]:
        if isinstance(item, SectionBoxManipulatorModel.PositionItem):
            return list(item.value)
        if isinstance(item, SectionBoxManipulatorModel.SizeItem):
            return list(item.value)
        if isinstance(item, SectionBoxManipulatorModel.TransformItem):
            return list(item.value)
        return []

    def set_floats(self, item: sc.AbstractManipulatorItem, value: list[float]) -> None:
        if isinstance(item, SectionBoxManipulatorModel.PositionItem):
            item.value = list(value)
            offset = Gf.Vec3d(value[0], value[1], value[2]) - self._state.box.transform.ExtractTranslation()
            self._state.box = self._state.box.translated(offset)
        elif isinstance(item, SectionBoxManipulatorModel.SizeItem):
            item.value = list(value)
            self._state.box = SectionBox(
                transform=self._state.box.transform,
                size=Gf.Vec3d(value[0], value[1], value[2]),
                faces=self._state.box.faces,
            )
        self._item_changed(item)

    def get_item(self, name: str) -> Optional[sc.AbstractManipulatorItem]:
        if name == "position":
            return self._position
        if name == "size":
            return self._size
        if name == "transform":
            return self._transform
        return None

    # --- state sync ----------------------------------------------------------

    @property
    def state(self) -> SectionBoxState:
        return self._state

    def _on_state_changed(self, state: SectionBoxState) -> None:
        self._sync_from_state()
        self._item_changed(self._position)
        self._item_changed(self._size)
        self._item_changed(self._transform)

    def _sync_from_state(self) -> None:
        box = self._state.box
        t = box.transform.ExtractTranslation()
        self._position.value = [t[0], t[1], t[2]]
        self._size.value = [box.size[0], box.size[1], box.size[2]]

        flat: list[float] = []
        for row in range(4):
            for col in range(4):
                flat.append(box.transform[row, col])
        self._transform.value = flat


def _identity_flat() -> list[float]:
    m = Gf.Matrix4d(1.0)
    return [m[r, c] for r in range(4) for c in range(4)]
