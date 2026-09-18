"""Kit toolbar integration — adds a toggle button to the main viewport toolbar.

The button enables / disables section-box clipping with a single click.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import carb
import omni.ext
import omni.kit.widget.toolbar as toolbar_module

if TYPE_CHECKING:
    from .state import SectionBoxState
    from .window import SectionBoxWindow


class ToolbarButton:
    """Section Box toggle button on the Kit toolbar."""

    def __init__(
        self,
        state: SectionBoxState,
        window: SectionBoxWindow,
        ext_id: str,
    ) -> None:
        self._state = state
        self._window = window
        self._ext_id = ext_id
        self._button = None

        self._register()
        self._state.add_listener(self._on_state_changed)

    def destroy(self) -> None:
        self._state.remove_listener(self._on_state_changed)
        self._unregister()

    # --- toolbar registration ------------------------------------------------

    def _register(self) -> None:
        try:
            toolbar = toolbar_module.get_instance()
            if toolbar is None:
                return

            # Resolve icon paths relative to the extension's data directory.
            ext_manager = omni.ext.get_ext_manager()
            ext_path = ext_manager.get_ext_path(self._ext_id) if ext_manager else ""

            self._button = toolbar.add_widget(
                toolbar_module.SimpleToolButton(
                    name="section_box_toggle",
                    tooltip="Toggle Section Box",
                    icon_path=f"{ext_path}/data/icon.svg" if ext_path else "",
                    icon_checked_path=f"{ext_path}/data/icon_active.svg" if ext_path else "",
                    hotkey=None,
                    toggled_fn=self._on_toggled,
                ),
                priority=900,
            )
        except Exception:  # noqa: BLE001
            carb.log_warn("[section.box] Could not register toolbar button")
            import traceback
            traceback.print_exc()

    def _unregister(self) -> None:
        if self._button is None:
            return
        try:
            toolbar = toolbar_module.get_instance()
            if toolbar:
                toolbar.remove_widget(self._button)
        except Exception:  # noqa: BLE001
            pass
        self._button = None

    # --- callbacks -----------------------------------------------------------

    def _on_toggled(self, checked: bool) -> None:
        self._state.enabled = checked
        # Also show / hide the control panel when toggling from the toolbar.
        if self._window:
            self._window.visible = checked

    def _on_state_changed(self, state: SectionBoxState) -> None:
        """Keep the toolbar button in sync if state changes externally."""
        if self._button is not None:
            try:
                self._button.checked = state.enabled
            except Exception:  # noqa: BLE001
                pass
