"""Extension entry point — wires up all section-box subsystems.

Kit calls ``on_startup`` when the extension is enabled and ``on_shutdown``
when it is disabled or the application closes.
"""

from __future__ import annotations

from typing import Optional

import carb
import omni.ext
import omni.kit.app
import omni.kit.viewport.utility as vp_util
import omni.ui.scene as sc

from .clipping import ClipPlaneController
from .manipulator import SectionBoxManipulator
from .manipulator_model import SectionBoxManipulatorModel
from .saved_positions import SavedPositionStore
from .state import SectionBoxState
from .toolbar import ToolbarButton
from .window import SectionBoxWindow


_runtime_state: SectionBoxState | None = None


def get_runtime_state() -> SectionBoxState | None:
    """Return the state owned by the running extension, if available."""
    return _runtime_state


class SectionBoxExtension(omni.ext.IExt):
    """Omniverse Kit extension that provides an interactive section box."""

    def __init__(self) -> None:
        super().__init__()
        self._state: Optional[SectionBoxState] = None
        self._clip_controller: Optional[ClipPlaneController] = None
        self._positions: Optional[SavedPositionStore] = None
        self._window: Optional[SectionBoxWindow] = None
        self._toolbar: Optional[ToolbarButton] = None
        self._manipulator_model: Optional[SectionBoxManipulatorModel] = None
        self._manipulator: Optional[SectionBoxManipulator] = None
        self._scene_view: Optional[sc.SceneView] = None
        self._viewport_api = None
        self._viewport_window = None
        self._overlay_frame = None
        self._update_sub = None

    # --- lifecycle -----------------------------------------------------------

    def on_startup(self, ext_id: str) -> None:
        global _runtime_state
        carb.log_info(f"[section.box] Starting up (ext_id={ext_id})")

        self._state = SectionBoxState()
        self._clip_controller = ClipPlaneController(self._state)
        self._positions = SavedPositionStore(self._state)
        self._window = SectionBoxWindow(self._state, self._positions)
        self._toolbar = ToolbarButton(self._state, self._window)

        self._setup_viewport_manipulator()
        self._update_sub = (
            omni.kit.app.get_app()
            .get_update_event_stream()
            .create_subscription_to_pop(self._on_update, name="section.box.viewport")
        )

        _runtime_state = self._state
        carb.log_info("[section.box] Ready")

    def on_shutdown(self) -> None:
        global _runtime_state
        carb.log_info("[section.box] Shutting down")

        if _runtime_state is self._state:
            _runtime_state = None

        # Tear down in reverse order.
        self._update_sub = None
        self._teardown_viewport_manipulator()

        if self._toolbar:
            self._toolbar.destroy()
            self._toolbar = None

        if self._window:
            self._window.destroy()
            self._window = None

        self._positions = None

        if self._clip_controller:
            self._clip_controller.destroy()
            self._clip_controller = None

        if self._state:
            self._state.destroy()
            self._state = None
        carb.log_info("[section.box] Shut down complete")

    # --- viewport manipulator setup ------------------------------------------

    def _setup_viewport_manipulator(self) -> None:
        """Register the section-box manipulator into the active viewport."""
        try:
            viewport_window = vp_util.get_active_viewport_window(usd_context_name=None)
            if viewport_window is None:
                return

            self._viewport_window = viewport_window

            self._manipulator_model = SectionBoxManipulatorModel(self._state)

            # Get or create a SceneView overlay on the viewport.
            self._overlay_frame = viewport_window.get_frame("section_box_overlay")
            with self._overlay_frame:
                self._scene_view = sc.SceneView(aspect_ratio_policy=sc.AspectRatioPolicy.PRESERVE_ASPECT_FIT)
                with self._scene_view.scene:
                    self._manipulator = SectionBoxManipulator(model=self._manipulator_model)

            # Keep the SceneView's projection in sync with the viewport camera.
            self._viewport_api = viewport_window.viewport_api
            self._viewport_api.add_scene_view(self._scene_view)

        except Exception:  # noqa: BLE001
            carb.log_warn("[section.box] Failed to set up viewport manipulator")
            import traceback

            traceback.print_exc()

    def _teardown_viewport_manipulator(self) -> None:
        if self._viewport_api and self._scene_view:
            self._viewport_api.remove_scene_view(self._scene_view)
        self._viewport_api = None
        if self._manipulator:
            self._manipulator.destroy()
            self._manipulator = None
        if self._manipulator_model:
            self._manipulator_model.destroy()
            self._manipulator_model = None
        if self._scene_view:
            self._scene_view.scene.clear()
        self._scene_view = None
        if self._overlay_frame:
            self._overlay_frame.clear()
        self._overlay_frame = None
        self._viewport_window = None

    def _on_update(self, event) -> None:
        if vp_util.get_active_viewport_window(usd_context_name=None) != self._viewport_window:
            self._teardown_viewport_manipulator()
            self._setup_viewport_manipulator()
