"""Extension entry point — wires up all section-box subsystems.

Kit calls ``on_startup`` when the extension is enabled and ``on_shutdown``
when it is disabled or the application closes.
"""

from __future__ import annotations

from typing import Optional

import carb
import omni.ext
import omni.ui.scene as sc
import omni.kit.viewport.utility as vp_util

from .state import SectionBoxState
from .clipping import ClipPlaneController
from .stage import StageSerializer
from .window import SectionBoxWindow
from .toolbar import ToolbarButton
from .manipulator_model import SectionBoxManipulatorModel
from .manipulator import SectionBoxManipulator


class SectionBoxExtension(omni.ext.IExt):
    """Omniverse Kit extension that provides an interactive section box."""

    def __init__(self) -> None:
        super().__init__()
        self._state: Optional[SectionBoxState] = None
        self._clip_controller: Optional[ClipPlaneController] = None
        self._stage_serializer: Optional[StageSerializer] = None
        self._window: Optional[SectionBoxWindow] = None
        self._toolbar: Optional[ToolbarButton] = None
        self._manipulator_model: Optional[SectionBoxManipulatorModel] = None
        self._manipulator: Optional[SectionBoxManipulator] = None
        self._scene_view: Optional[sc.SceneView] = None
        self._viewport_sub = None

    # --- lifecycle -----------------------------------------------------------

    def on_startup(self, ext_id: str) -> None:
        carb.log_info(f"[section.box] Starting up (ext_id={ext_id})")

        # 1. State — the single source of truth.
        self._state = SectionBoxState()

        # 2. Clip-plane controller — pushes planes to the renderer.
        self._clip_controller = ClipPlaneController(self._state)

        # 3. Stage serializer — optional USD persistence.
        self._stage_serializer = StageSerializer(self._state)

        # 4. UI window panel.
        self._window = SectionBoxWindow(self._state)

        # 5. Toolbar button.
        self._toolbar = ToolbarButton(self._state, self._window, ext_id)

        # 6. Viewport manipulator overlay.
        self._setup_viewport_manipulator()

        carb.log_info("[section.box] Ready")

    def on_shutdown(self) -> None:
        carb.log_info("[section.box] Shutting down")

        # Tear down in reverse order.
        self._teardown_viewport_manipulator()

        if self._toolbar:
            self._toolbar.destroy()
            self._toolbar = None

        if self._window:
            self._window.destroy()
            self._window = None

        if self._stage_serializer:
            self._stage_serializer.destroy()
            self._stage_serializer = None

        if self._clip_controller:
            self._clip_controller.destroy()
            self._clip_controller = None

        self._state = None
        carb.log_info("[section.box] Shut down complete")

    # --- viewport manipulator setup ------------------------------------------

    def _setup_viewport_manipulator(self) -> None:
        """Register the section-box manipulator into the active viewport."""
        try:
            viewport_window = vp_util.get_active_viewport_window()
            if viewport_window is None:
                carb.log_warn(
                    "[section.box] No active viewport window found; "
                    "manipulator will not be available."
                )
                return

            self._manipulator_model = SectionBoxManipulatorModel(self._state)

            # Get or create a SceneView overlay on the viewport.
            with viewport_window.get_frame("section_box_overlay"):
                self._scene_view = sc.SceneView(
                    aspect_ratio_policy=sc.AspectRatioPolicy.PRESERVE_ASPECT_FIT
                )
                with self._scene_view.scene:
                    self._manipulator = SectionBoxManipulator(
                        model=self._manipulator_model
                    )

            # Keep the SceneView's projection in sync with the viewport camera.
            viewport_api = viewport_window.viewport_api
            self._viewport_sub = viewport_api.subscribe_to_view_change(
                self._on_viewport_changed
            )

        except Exception:  # noqa: BLE001
            carb.log_warn("[section.box] Failed to set up viewport manipulator")
            import traceback
            traceback.print_exc()

    def _teardown_viewport_manipulator(self) -> None:
        self._viewport_sub = None
        if self._manipulator:
            self._manipulator.destroy()
            self._manipulator = None
        if self._manipulator_model:
            self._manipulator_model.destroy()
            self._manipulator_model = None
        self._scene_view = None

    def _on_viewport_changed(self, viewport_api) -> None:
        """Update the SceneView matrices when the camera moves."""
        if self._scene_view is None:
            return
        try:
            view = viewport_api.view
            projection = viewport_api.projection
            self._scene_view.model.set_floats("view", list(view))
            self._scene_view.model.set_floats("projection", list(projection))
        except Exception:  # noqa: BLE001
            pass
