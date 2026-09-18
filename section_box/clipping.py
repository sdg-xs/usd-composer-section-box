"""Push the section box's cut plane into the active viewport.

RTX exposes exactly one section plane, not six: the render-settings schema has
``sectionPlane:plane``, a single ``[nx, ny, nz, -d]``.  So a six-sided box cannot
clip on six sides.  We cut on the first active face in ``Face`` order, which is
the first entry ``active_planes()`` returns.

The plane is written to the render product's ``omni:rtx:scene:sectionPlane:plane``
attribute rather than to ``/rtx/sectionPlane/plane`` directly — the same route
``omni.kit.window.section`` takes, because the raw setting breaks in a live session.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import carb
import carb.settings
import omni.usd
import omni.kit.viewport.utility as vp_util

if TYPE_CHECKING:
    from .state import SectionBoxState

# Mirrors omni.kit.window.section's constants, so both tools agree on the target.
_SETTING_SECTION_ENABLED = "/rtx/sectionPlane/enabled"
_PLANE_ATTR = "omni:rtx:scene:sectionPlane:plane"


class ClipPlaneController:
    """Bridges the section-box model to the renderer's single section plane."""

    def __init__(self, state: SectionBoxState) -> None:
        self._state = state
        self._active = False
        self._state.add_listener(self._on_state_changed)

    def destroy(self) -> None:
        self._state.remove_listener(self._on_state_changed)
        self._clear_plane()

    # --- listener callback ---------------------------------------------------

    def _on_state_changed(self, state: SectionBoxState) -> None:
        if state.enabled:
            self._push_plane()
        else:
            self._clear_plane()

    # --- viewport interaction ------------------------------------------------

    def _push_plane(self) -> None:
        """Send the box's leading active face to the renderer as the section plane."""
        try:
            planes = self._state.box.active_planes()
            if not planes:
                self._clear_plane()
                return

            nx, ny, nz, d = planes[0]
            if not self._set_plane_attribute([nx, ny, nz, d]):
                return

            carb.settings.get_settings().set(_SETTING_SECTION_ENABLED, True)
            self._active = True
        except Exception:  # noqa: BLE001
            carb.log_warn("[section.box] Failed to push the section plane")
            import traceback
            traceback.print_exc()

    def _clear_plane(self) -> None:
        """Switch the renderer's section plane back off."""
        if not self._active:
            return
        try:
            carb.settings.get_settings().set(_SETTING_SECTION_ENABLED, False)
            self._active = False
        except Exception:  # noqa: BLE001
            carb.log_warn("[section.box] Failed to clear the section plane")
            import traceback
            traceback.print_exc()

    @staticmethod
    def _set_plane_attribute(plane: list[float]) -> bool:
        """Write *plane* to the active render product. True when it landed."""
        viewport_api = ClipPlaneController._get_viewport_api()
        if viewport_api is None:
            carb.log_warn("[section.box] No active viewport; section plane not set")
            return False

        stage = omni.usd.get_context().get_stage()
        if stage is None:
            return False

        prim = stage.GetPrimAtPath(viewport_api.render_product_path)
        if not prim or not prim.IsValid():
            carb.log_warn("[section.box] Render product prim unavailable")
            return False

        attr = prim.GetAttribute(_PLANE_ATTR)
        if not attr:
            carb.log_warn(f"[section.box] {_PLANE_ATTR} missing on the render product")
            return False

        attr.Set(plane)
        return True

    @staticmethod
    def _get_viewport_api():
        """Return the active viewport API, or None if unavailable."""
        try:
            viewport_window = vp_util.get_active_viewport_window()
            if viewport_window is None:
                return None
            return viewport_window.viewport_api
        except Exception:  # noqa: BLE001
            return None
