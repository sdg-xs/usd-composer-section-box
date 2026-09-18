"""Kit integration tests for the section_box extension.

These tests require the Kit runtime and are intended to be run via
``omni.kit.test`` or a Kit-aware pytest runner.
"""

from __future__ import annotations

import omni.kit.test
import omni.usd

from section_box.model import Face, SectionBox
from section_box.state import SectionBoxState


class TestSectionBoxExtension(omni.kit.test.AsyncTestCase):
    """Integration tests that verify the extension loads and functions correctly."""

    async def setUp(self):
        """Create a fresh state before each test."""
        self._state = SectionBoxState()

    async def tearDown(self):
        self._state = None

    # --- extension lifecycle -------------------------------------------------

    async def test_extension_loads(self):
        """The extension module imports without error."""
        import section_box
        self.assertIsNotNone(section_box.SectionBoxExtension)

    # --- state ---------------------------------------------------------------

    async def test_state_toggle_enabled(self):
        """Toggling enabled fires a notification."""
        notifications: list[bool] = []
        self._state.add_listener(lambda s: notifications.append(s.enabled))
        self._state.enabled = True
        self.assertTrue(self._state.enabled)
        self.assertEqual(notifications, [True])

        self._state.enabled = False
        self.assertFalse(self._state.enabled)
        self.assertEqual(notifications, [True, False])

    async def test_state_toggle_face(self):
        """toggle_face adds and removes individual faces."""
        # Default: all 6 faces.
        self.assertEqual(len(self._state.box.faces), 6)

        # Remove MIN_X.
        self._state.toggle_face(Face.MIN_X)
        self.assertNotIn(Face.MIN_X, self._state.box.faces)
        self.assertEqual(len(self._state.box.faces), 5)

        # Re-add MIN_X.
        self._state.toggle_face(Face.MIN_X)
        self.assertIn(Face.MIN_X, self._state.box.faces)
        self.assertEqual(len(self._state.box.faces), 6)

    async def test_state_set_size_component(self):
        """set_size_component updates a single axis."""
        self._state.set_size_component(0, 42.0)
        self.assertAlmostEqual(self._state.box.size[0], 42.0)
        # Other axes unchanged.
        self.assertAlmostEqual(self._state.box.size[1], 100.0)
        self.assertAlmostEqual(self._state.box.size[2], 100.0)

    async def test_state_reset(self):
        """reset() restores defaults from settings."""
        self._state.set_size_component(0, 999.0)
        self._state.reset()
        self.assertAlmostEqual(self._state.box.size[0], 100.0)

    # --- model methods -------------------------------------------------------

    async def test_active_planes_count(self):
        """active_planes returns one plane per active face."""
        box = SectionBox(faces=frozenset({Face.MIN_Z}))
        self.assertEqual(len(box.active_planes()), 1)

        box = SectionBox(faces=frozenset(Face))
        self.assertEqual(len(box.active_planes()), 6)

        box = SectionBox(faces=frozenset())
        self.assertEqual(len(box.active_planes()), 0)

    async def test_fit_to_selection_bounds(self):
        """for_bounds produces a box spanning the given extents."""
        from pxr import Gf

        box = SectionBox.for_bounds((-10.0, -20.0, -30.0), (10.0, 20.0, 30.0))
        self.assertEqual(box.size, Gf.Vec3d(20.0, 40.0, 60.0))
        self.assertEqual(
            box.transform.ExtractTranslation(), Gf.Vec3d(0.0, 0.0, 0.0)
        )

    # --- listener cleanup ----------------------------------------------------

    async def test_remove_listener(self):
        """Removing a listener stops further notifications."""
        count = [0]
        def listener(s):
            count[0] += 1

        self._state.add_listener(listener)
        self._state.enabled = True
        self.assertEqual(count[0], 1)

        self._state.remove_listener(listener)
        self._state.enabled = False
        self.assertEqual(count[0], 1)  # no further notification
