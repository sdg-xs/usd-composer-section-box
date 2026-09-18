import importlib.util
import sys
from pathlib import Path

from pxr import Gf

# Loaded by path, not as section_box.model: the package __init__ pulls in Kit, which plain CPython lacks.
_MODEL_PATH = Path(__file__).resolve().parent / "section_box" / "model.py"
_spec = importlib.util.spec_from_file_location("section_box_model", _MODEL_PATH)
model = importlib.util.module_from_spec(_spec)
# dataclasses resolves the deferred annotations through sys.modules, so register before executing.
sys.modules[_spec.name] = model
_spec.loader.exec_module(model)

Face = model.Face
SectionBox = model.SectionBox
EDGE_INDICES = model.EDGE_INDICES

TOLERANCE = 1e-9

Plane = tuple[float, float, float, float]


def close(actual: float, expected: float) -> bool:
    return abs(actual - expected) <= TOLERANCE


def planes_close(actual: list[Plane], expected: list[Plane]) -> bool:
    if len(actual) != len(expected):
        return False
    return all(
        close(a, e)
        for actual_plane, expected_plane in zip(actual, expected)
        for a, e in zip(actual_plane, expected_plane)
    )


def point_close(actual: Gf.Vec3d, expected: tuple[float, float, float]) -> bool:
    return all(close(actual[i], expected[i]) for i in range(3))


def case_box() -> SectionBox:
    return SectionBox(
        transform=Gf.Matrix4d(1.0),
        size=Gf.Vec3d(2.0, 4.0, 6.0),
        faces=frozenset({Face.MIN_Z}),
    )


def check_default_faces() -> str:
    assert SectionBox().faces == frozenset(Face), (
        f"a bare SectionBox enables all 6 faces, got {SectionBox().faces}"
    )
    return "default faces are all 6"


def check_min_z_plane() -> str:
    planes = case_box().active_planes()
    assert planes_close(planes, [(0.0, 0.0, -1.0, -3.0)]), (
        f"MIN_Z on a size-6 depth cuts 3 units below the centre, got {planes}"
    )
    return "MIN_Z plane of an identity box at the origin"


def check_max_x_plane_translated() -> str:
    box = SectionBox(
        transform=Gf.Matrix4d(1.0).SetTranslate(Gf.Vec3d(10.0, 20.0, 30.0)),
        size=Gf.Vec3d(2.0, 4.0, 6.0),
        faces=frozenset({Face.MAX_X}),
    )
    planes = box.active_planes()
    assert planes_close(planes, [(1.0, 0.0, 0.0, -11.0)]), (
        f"MAX_X sits 1 unit past a centre at x=10, so the plane offset is 11, got {planes}"
    )
    return "MAX_X plane picks up the translation"


def check_inverted_flips_normal() -> str:
    planes = case_box().inverted().active_planes()
    assert planes_close(planes, [(0.0, 0.0, 1.0, -3.0)]), (
        f"inverting MIN_Z gives MAX_Z, the same distance out with the normal flipped, got {planes}"
    )
    return "inverted() swaps MIN_Z for MAX_Z"


def check_degenerate_zero_thickness() -> str:
    box = SectionBox(
        transform=Gf.Matrix4d(1.0),
        size=Gf.Vec3d(2.0, 4.0, 0.0),
        faces=frozenset({Face.MIN_Z}),
    )
    planes = box.active_planes()
    assert planes_close(planes, [(0.0, 0.0, -1.0, 0.0)]), (
        f"a zero-depth box reduces to the renderer's original single plane through the origin, got {planes}"
    )
    return "zero depth matches the original single-plane convention"


def check_rotated_90_about_local_x() -> str:
    planes = case_box().rotated(0, 90.0).active_planes()
    assert planes_close(planes, [(0.0, 1.0, 0.0, -3.0)]), (
        f"turning 90 degrees about local X swings the MIN_Z normal onto +Y, got {planes}"
    )
    return "rotated(0, 90) swings the MIN_Z plane onto +Y"


def check_rotation_composes() -> str:
    box = case_box()
    half_turn = box.rotated(0, 180.0).active_planes()
    assert planes_close(half_turn, [(0.0, 0.0, 1.0, -3.0)]), (
        f"a half turn about X points the MIN_Z normal back along +Z, got {half_turn}"
    )
    twice = box.rotated(0, 90.0).rotated(0, 90.0).active_planes()
    assert planes_close(twice, [(0.0, 0.0, 1.0, -3.0)]), (
        f"two quarter turns land on the same plane as one half turn, got {twice}"
    )
    assert planes_close(twice, half_turn), (
        f"composed rotation must agree with the single rotation, got {twice} against {half_turn}"
    )
    return "two quarter turns equal one half turn"


def check_for_bounds() -> str:
    box = SectionBox.for_bounds((-1.0, -2.0, -3.0), (5.0, 6.0, 7.0))
    assert box.size == Gf.Vec3d(6.0, 8.0, 10.0), (
        f"size is the full extent of the bounds, got {box.size}"
    )
    assert box.transform.ExtractTranslation() == Gf.Vec3d(2.0, 2.0, 2.0), (
        f"the box centres on the midpoint of the bounds, got {box.transform.ExtractTranslation()}"
    )
    corners = box.corners()
    assert any(point_close(c, (-1.0, -2.0, -3.0)) for c in corners), (
        f"the minimum bound is corner 0, got {corners}"
    )
    assert any(point_close(c, (5.0, 6.0, 7.0)) for c in corners), (
        f"the maximum bound is corner 7, got {corners}"
    )
    return "for_bounds spans the given bounds exactly"


def check_corners_and_edges() -> str:
    corners = case_box().corners()
    assert len(corners) == 8, f"a box has 8 corners, got {len(corners)}"
    distinct = {tuple(round(c[i], 9) for i in range(3)) for c in corners}
    assert len(distinct) == 8, f"a non-degenerate box has 8 distinct corners, got {distinct}"
    assert len(EDGE_INDICES) == 12, f"a box has 12 edges, got {len(EDGE_INDICES)}"
    assert all(bin(a ^ b).count("1") == 1 for a, b in EDGE_INDICES), (
        f"an edge joins corners differing on one axis only, got {EDGE_INDICES}"
    )
    assert len(set(EDGE_INDICES)) == 12, f"no edge is listed twice, got {EDGE_INDICES}"
    return "8 distinct corners and 12 single-bit edges"


def check_with_alignment() -> str:
    box = SectionBox(
        transform=Gf.Matrix4d(1.0).SetTranslate(Gf.Vec3d(10.0, 20.0, 30.0)),
        size=Gf.Vec3d(2.0, 4.0, 6.0),
        faces=frozenset({Face.MIN_Z}),
    )
    planes = box.with_alignment(0).active_planes()
    assert planes_close(planes, [(-1.0, 0.0, 0.0, 7.0)]), (
        f"aligning local +Z to world +X puts the MIN_Z normal on -X, 3 units in from x=10, got {planes}"
    )
    identity_planes = case_box().with_alignment(2).active_planes()
    assert planes_close(identity_planes, [(0.0, 0.0, -1.0, -3.0)]), (
        f"aligning to Z is the identity rotation and changes nothing, got {identity_planes}"
    )
    return "with_alignment sets local +Z onto the chosen world axis"


def check_invalid_axis_rejected() -> str:
    box = case_box()
    for name, call in (("with_alignment", lambda: box.with_alignment(3)), ("rotated", lambda: box.rotated(3, 90.0))):
        try:
            call()
        except ValueError:
            continue
        raise AssertionError(f"{name} must reject axis 3, there are only 3 axes")
    return "with_alignment and rotated reject axis 3"


def check_translated() -> str:
    box = case_box()
    moved = box.translated(Gf.Vec3d(10.0, 0.0, 0.0))
    new_pos = moved.transform.ExtractTranslation()
    assert point_close(new_pos, (10.0, 0.0, 0.0)), (
        f"translated shifts the centre by the offset, got {new_pos}"
    )
    assert moved.size == box.size, "translated does not change the size"
    assert moved.faces == box.faces, "translated does not change the faces"
    return "translated() shifts the centre, preserves size and faces"


def check_resized() -> str:
    box = case_box()  # size (2, 4, 6), faces {MIN_Z}, centre at origin
    grown = box.resized(Face.MAX_X, 4.0)
    assert close(grown.size[0], 6.0), (
        f"growing MAX_X by 4 takes width from 2 to 6, got {grown.size[0]}"
    )
    # The opposite face (MIN_X) should stay fixed.
    old_min_x = -box.size[0] / 2.0  # -1.0
    new_min_x = grown.transform.ExtractTranslation()[0] - grown.size[0] / 2.0
    assert close(new_min_x, old_min_x), (
        f"the opposite face stays fixed: expected {old_min_x}, got {new_min_x}"
    )
    # Shrinking below zero clamps to 0.
    shrunk = box.resized(Face.MAX_X, -100.0)
    assert close(shrunk.size[0], 0.0), (
        f"size clamps to 0 when delta overshoots, got {shrunk.size[0]}"
    )
    return "resized() grows/shrinks on one axis, opposite face stays fixed"


CHECKS = (
    check_default_faces,
    check_min_z_plane,
    check_max_x_plane_translated,
    check_inverted_flips_normal,
    check_degenerate_zero_thickness,
    check_rotated_90_about_local_x,
    check_rotation_composes,
    check_for_bounds,
    check_corners_and_edges,
    check_with_alignment,
    check_invalid_axis_rejected,
    check_translated,
    check_resized,
)


def main() -> None:
    for index, check in enumerate(CHECKS, start=1):
        print(f"ok {index:2d}  {check()}")
    print(f"\n{len(CHECKS)} checks passed")


if __name__ == "__main__":
    main()
