"""Section Box control panel — an ``omni.ui.Window`` for interactive configuration.

Provides sliders for size, checkboxes for faces, alignment buttons, invert,
fit-to-selection, rotation, and a persist-to-stage toggle.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import omni.kit.commands
import omni.usd
import omni.ui as ui

from pxr import Gf, UsdGeom

from .model import Face

if TYPE_CHECKING:
    from .state import SectionBoxState

WINDOW_TITLE = "Section Box"

# Axis labels used in the UI.
_AXIS_LABELS = ("X", "Y", "Z")

# Face pairs grouped by axis for layout.
_FACE_PAIRS: tuple[tuple[Face, Face], ...] = (
    (Face.MIN_X, Face.MAX_X),
    (Face.MIN_Y, Face.MAX_Y),
    (Face.MIN_Z, Face.MAX_Z),
)


class SectionBoxWindow:
    """Standalone ``omni.ui.Window`` with section-box controls."""

    def __init__(self, state: SectionBoxState) -> None:
        self._state = state
        self._window: Optional[ui.Window] = None
        self._size_sliders: list[ui.FloatSlider] = []
        self._face_checkboxes: dict[Face, ui.CheckBox] = {}
        self._enabled_checkbox: Optional[ui.CheckBox] = None
        self._persist_checkbox: Optional[ui.CheckBox] = None
        self._rotation_slider: Optional[ui.FloatSlider] = None
        self._rotation_axis: int = 2  # default rotation axis: Z

        self._build_window()
        self._state.add_listener(self._on_state_changed)

    def destroy(self) -> None:
        self._state.remove_listener(self._on_state_changed)
        if self._window:
            self._window.destroy()
            self._window = None
        self._size_sliders.clear()
        self._face_checkboxes.clear()

    @property
    def visible(self) -> bool:
        return self._window.visible if self._window else False

    @visible.setter
    def visible(self, value: bool) -> None:
        if self._window:
            self._window.visible = value

    # --- window construction -------------------------------------------------

    def _build_window(self) -> None:
        self._window = ui.Window(WINDOW_TITLE, width=320, height=480)
        with self._window.frame:
            with ui.ScrollingFrame():
                with ui.VStack(spacing=6, height=0):
                    self._build_enable_section()
                    ui.Spacer(height=4)
                    self._build_size_section()
                    ui.Spacer(height=4)
                    self._build_faces_section()
                    ui.Spacer(height=4)
                    self._build_actions_section()
                    ui.Spacer(height=4)
                    self._build_rotation_section()
                    ui.Spacer(height=4)
                    self._build_persistence_section()

    def _build_enable_section(self) -> None:
        with ui.CollapsableFrame("Enable", collapsed=False):
            with ui.HStack(height=24, spacing=8):
                ui.Label("Section Box Active", width=0)
                model = ui.SimpleBoolModel(self._state.enabled)
                self._enabled_checkbox = ui.CheckBox(model=model, width=24)
                model.add_value_changed_fn(
                    lambda m: setattr(self._state, "enabled", m.as_bool)
                )

    def _build_size_section(self) -> None:
        with ui.CollapsableFrame("Size", collapsed=False):
            with ui.VStack(spacing=4):
                self._size_sliders = []
                for axis in range(3):
                    with ui.HStack(height=24, spacing=8):
                        ui.Label(f"  {_AXIS_LABELS[axis]}", width=40)
                        model = ui.SimpleFloatModel(self._state.box.size[axis])
                        slider = ui.FloatSlider(model=model, min=0.1, max=10000.0)
                        # Capture axis in closure.
                        a = axis
                        model.add_value_changed_fn(
                            lambda m, _a=a: self._state.set_size_component(_a, m.as_float)
                        )
                        self._size_sliders.append(slider)

    def _build_faces_section(self) -> None:
        with ui.CollapsableFrame("Active Faces", collapsed=False):
            with ui.VStack(spacing=4):
                for face_min, face_max in _FACE_PAIRS:
                    with ui.HStack(height=24, spacing=8):
                        for face in (face_min, face_max):
                            checked = face in self._state.box.faces
                            model = ui.SimpleBoolModel(checked)
                            cb = ui.CheckBox(model=model, width=24)
                            ui.Label(face.name, width=60)
                            f = face  # capture
                            model.add_value_changed_fn(
                                lambda m, _f=f: self._state.toggle_face(_f)
                            )
                            self._face_checkboxes[face] = cb

    def _build_actions_section(self) -> None:
        with ui.CollapsableFrame("Actions", collapsed=False):
            with ui.VStack(spacing=4):
                with ui.HStack(height=28, spacing=8):
                    ui.Label("Align to:", width=60)
                    for axis in range(3):
                        a = axis
                        ui.Button(
                            _AXIS_LABELS[axis],
                            width=40,
                            clicked_fn=lambda _a=a: self._on_align(int(_a)),
                        )

                with ui.HStack(height=28, spacing=8):
                    ui.Button("Invert", clicked_fn=self._on_invert)
                    ui.Button("Fit to Selection", clicked_fn=self._on_fit_to_selection)
                    ui.Button("Reset", clicked_fn=self._on_reset)

    def _build_rotation_section(self) -> None:
        with ui.CollapsableFrame("Rotation", collapsed=True):
            with ui.VStack(spacing=4):
                with ui.HStack(height=24, spacing=8):
                    ui.Label("Axis:", width=40)
                    for axis in range(3):
                        a = axis

                        def _set_axis(_a=a):
                            self._rotation_axis = int(_a)

                        ui.Button(
                            _AXIS_LABELS[axis],
                            width=40,
                            clicked_fn=_set_axis,
                        )
                with ui.HStack(height=24, spacing=8):
                    ui.Label("Degrees:", width=60)
                    model = ui.SimpleFloatModel(0.0)
                    self._rotation_slider = ui.FloatSlider(
                        model=model, min=-180.0, max=180.0
                    )
                ui.Button(
                    "Apply Rotation",
                    height=28,
                    clicked_fn=lambda: self._on_rotate(model.as_float),
                )

    def _build_persistence_section(self) -> None:
        with ui.CollapsableFrame("Stage Persistence", collapsed=True):
            with ui.VStack(spacing=4):
                with ui.HStack(height=24, spacing=8):
                    ui.Label("Save to USD Stage", width=0)
                    model = ui.SimpleBoolModel(self._state.persist_to_stage)
                    self._persist_checkbox = ui.CheckBox(model=model, width=24)
                    model.add_value_changed_fn(
                        lambda m: setattr(self._state, "persist_to_stage", m.as_bool)
                    )
                ui.Label(
                    "  When enabled, the section box is saved with the scene.",
                    word_wrap=True,
                    height=0,
                )

    # --- action callbacks ----------------------------------------------------

    def _on_align(self, axis: int) -> None:
        self._state.box = self._state.box.with_alignment(axis)

    def _on_invert(self) -> None:
        self._state.box = self._state.box.inverted()

    def _on_fit_to_selection(self) -> None:
        usd_context = omni.usd.get_context()
        if usd_context is None:
            return
        selection = usd_context.get_selection()
        paths = selection.get_selected_prim_paths() if selection else []
        if not paths:
            return

        stage = usd_context.get_stage()
        if stage is None:
            return

        bbox_cache = UsdGeom.BBoxCache(0.0, [UsdGeom.Tokens.default_])
        total_range = Gf.Range3d()
        for path in paths:
            prim = stage.GetPrimAtPath(path)
            if prim.IsValid():
                bbox = bbox_cache.ComputeWorldBound(prim)
                total_range = Gf.Range3d.GetUnion(total_range, bbox.GetRange())

        if total_range.IsEmpty():
            return

        minimum = total_range.GetMin()
        maximum = total_range.GetMax()
        self._state.box = self._state.box.for_bounds(
            (minimum[0], minimum[1], minimum[2]),
            (maximum[0], maximum[1], maximum[2]),
        )

    def _on_reset(self) -> None:
        self._state.reset()

    def _on_rotate(self, degrees: float) -> None:
        self._state.box = self._state.box.rotated(self._rotation_axis, degrees)

    # --- state synchronisation -----------------------------------------------

    def _on_state_changed(self, state: SectionBoxState) -> None:
        """Keep the UI widgets in sync when the model changes externally."""
        if not self._window:
            return
        # Re-sync the enabled checkbox.
        if self._enabled_checkbox and self._enabled_checkbox.model:
            self._enabled_checkbox.model.set_value(state.enabled)

        # Re-sync size sliders.
        for axis, slider in enumerate(self._size_sliders):
            if slider.model:
                slider.model.set_value(state.box.size[axis])

        # Re-sync face checkboxes.
        for face, cb in self._face_checkboxes.items():
            if cb.model:
                cb.model.set_value(face in state.box.faces)

        # Re-sync persist checkbox.
        if self._persist_checkbox and self._persist_checkbox.model:
            self._persist_checkbox.model.set_value(state.persist_to_stage)
