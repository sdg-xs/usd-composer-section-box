"""Run geometry-fit checks against real USD, standalone or through verify_selection()."""

from __future__ import annotations

import math
import random
import sys
import types
from pathlib import Path

if "section_box" not in sys.modules:
    # Plain USD Python can load geometry without executing the Kit extension entry point.
    package = types.ModuleType("section_box")
    package.__path__ = [str(Path(__file__).resolve().parents[1] / "section_box")]
    sys.modules["section_box"] = package

from pxr import Gf, Usd, UsdGeom

from section_box.footprint import convex_hull, minimum_rectangle
from section_box.selection import classify_visible_paths, fit_box_to_paths, fit_box_to_selection, selection_center


class Context:
    def __init__(self, stage, paths):
        self.stage, self.paths = stage, paths

    def get_stage(self):
        return self.stage

    def get_selection(self):
        return self

    def get_selected_prim_paths(self):
        return self.paths


def stage_for(up="Z"):
    stage = Usd.Stage.CreateInMemory()
    UsdGeom.SetStageUpAxis(stage, up)
    return stage


def rotation(degrees, up=2):
    axis = Gf.Vec3d(0)
    axis[up] = 1
    return Gf.Matrix4d().SetRotate(Gf.Rotation(axis, degrees))


def rectangle(stage, path, yaw=31, center=(0, 0, 0), size=(40, 10, 6), up=2):
    mesh = UsdGeom.Mesh.Define(stage, path)
    turn = rotation(yaw, up)
    points = [
        turn.Transform(Gf.Vec3d(*(sign[i] * size[i] / 2 for i in range(3)))) + Gf.Vec3d(*center)
        for sign in ((-1, -1, -1), (1, -1, -1), (-1, 1, -1), (1, 1, -1), (-1, -1, 1), (1, -1, 1), (-1, 1, 1), (1, 1, 1))
    ]
    mesh.CreatePointsAttr(points)
    mesh.CreateFaceVertexCountsAttr([4] * 6)
    mesh.CreateFaceVertexIndicesAttr([0, 2, 3, 1, 4, 5, 7, 6, 0, 1, 5, 4, 2, 6, 7, 3, 0, 4, 6, 2, 1, 3, 7, 5])
    return mesh


def world_points(mesh):
    matrix = UsdGeom.XformCache().GetLocalToWorldTransform(mesh.GetPrim())
    return [matrix.Transform(Gf.Vec3d(point)) for point in mesh.GetPointsAttr().Get()]


def check_box(box, points, expected_size=None, expected_frame=None, tolerance=2e-4):
    assert box is not None, "Geometry selection did not produce a box"
    inverse = box.transform.GetInverse()
    for point in points:
        local = inverse.Transform(point)
        assert all(abs(local[i]) <= box.size[i] / 2 + tolerance for i in range(3)), (
            "Fit cuts selected geometry",
            tuple(point),
            tuple(local),
            tuple(box.size),
        )
        for plane in box.active_planes():
            assert Gf.Dot(Gf.Vec3d(*plane[:3]), point) + plane[3] <= tolerance, "Clipping plane cuts selected geometry"
    if expected_size is not None:
        assert all(abs(a - b) <= tolerance for a, b in zip(sorted(box.size), sorted(expected_size))), (
            "Fitted dimensions do not follow geometry",
            tuple(box.size),
            expected_size,
        )
    axes = [box.transform.TransformDir(Gf.Vec3d(*(int(i == j) for i in range(3)))) for j in range(3)]
    assert Gf.IsClose(axes[2], Gf.Vec3d(0, 0, 1), 1e-10), "Fit tilted the top and bottom away from world XY"
    assert all(abs(axis.GetLength() - 1) < 1e-8 for axis in axes), "Fit transform carries scale"
    assert all(abs(Gf.Dot(axes[i], axes[j])) < 1e-8 for i in range(3) for j in range(i)), "Fit frame is not orthogonal"
    if expected_frame is not None:
        for i in range(3):
            expected = expected_frame.TransformDir(Gf.Vec3d(*(int(i == j) for j in range(3))))
            assert max(abs(Gf.Dot(expected, axis)) for axis in axes) > 1 - 1e-8, (
                "Box axes do not align with geometry",
                tuple(expected),
                [tuple(axis) for axis in axes],
            )


def check_optimal_footprint(box, points):
    check_box(box, points)
    xy = [(p[0] - points[0][0], p[1] - points[0][1]) for p in points]
    areas = []
    for i, (x, y) in enumerate(xy):
        for next_x, next_y in xy[i + 1 :]:
            dx, dy = next_x - x, next_y - y
            length = math.hypot(dx, dy)
            if length == 0:
                continue
            c, s = dx / length, dy / length
            u = [px * c + py * s for px, py in xy]
            v = [-px * s + py * c for px, py in xy]
            areas.append((max(u) - min(u)) * (max(v) - min(v)))
    if areas:
        expected = min(areas)
        assert abs(box.size[0] * box.size[1] - expected) < 1e-5 * max(1, expected)


def baked_rotation():
    stage = stage_for()
    UsdGeom.Xform.Define(stage, "/Building")
    mesh = rectangle(stage, "/Building/Mesh")
    box = fit_box_to_selection(Context(stage, ["/Building"]))
    check_box(box, world_points(mesh), (40, 10, 6), rotation(31))


def child_rotation():
    stage = stage_for()
    UsdGeom.Xform.Define(stage, "/Building")
    mesh = rectangle(stage, "/Building/Mesh", yaw=0)
    mesh.AddRotateZOp().Set(31)
    check_box(fit_box_to_selection(Context(stage, ["/Building"])), world_points(mesh), (40, 10, 6), rotation(31))


def georeferenced_rotation():
    stage = stage_for()
    parent = UsdGeom.Xform.Define(stage, "/Building")
    parent.AddTranslateOp().Set(Gf.Vec3d(6_500_000, -4_200_000, 175))
    parent.AddRotateZOp().Set(17)
    mesh = rectangle(stage, "/Building/Mesh")
    box = fit_box_to_selection(Context(stage, ["/Building"]))
    check_box(box, world_points(mesh), (40, 10, 6), rotation(48))
    assert Gf.IsClose(box.transform.ExtractTranslation(), Gf.Vec3d(6_500_000, -4_200_000, 175), 2e-4)


def multiple_branches():
    stage = stage_for()
    offset = rotation(31).TransformDir(Gf.Vec3d(30, 0, 0))
    left = rectangle(stage, "/Left/Mesh", center=-offset)
    right = rectangle(stage, "/Right/Mesh", center=offset)
    context = Context(stage, ["/Left", "/Right"])
    first = fit_box_to_selection(context)
    check_box(first, world_points(left) + world_points(right), (100, 10, 6), rotation(31))
    context.paths.reverse()
    second = fit_box_to_selection(context)
    assert Gf.IsClose(first.transform, second.transform, 1e-8) and Gf.IsClose(first.size, second.size, 1e-8), (
        "Selection ordering changes fit"
    )
    context.paths = ["/Left", "/Left/Mesh", "/Right"]
    third = fit_box_to_selection(context)
    assert Gf.IsClose(first.transform, third.transform, 1e-8) and Gf.IsClose(first.size, third.size, 1e-8), (
        "Overlapping selection changes fit"
    )
    explicit = fit_box_to_paths(stage, ["/Right", "/Left/Mesh", "/Left"])
    assert explicit == first, "Explicit paths and selection produce different fits"
    assert context.paths == ["/Left", "/Left/Mesh", "/Right"], "Explicit fit changed the selection"


def explicit_paths_time():
    stage = stage_for()
    cube = UsdGeom.Cube.Define(stage, "/Moving")
    translate = cube.AddTranslateOp()
    translate.Set(Gf.Vec3d(0, 0, 0), Usd.TimeCode(1))
    translate.Set(Gf.Vec3d(20, 0, 0), Usd.TimeCode(2))
    first = fit_box_to_paths(stage, ["/Moving"], time=Usd.TimeCode(1))
    second = fit_box_to_paths(stage, ["/Moving"], time=Usd.TimeCode(2))
    assert first is not None and second is not None
    assert first.transform.ExtractTranslation() == Gf.Vec3d(0, 0, 0)
    assert second.transform.ExtractTranslation() == Gf.Vec3d(20, 0, 0)
    assert first.size == second.size


def square_determinism():
    stage = stage_for()
    mesh = rectangle(stage, "/Square", size=(12, 12, 6))
    context = Context(stage, ["/Square"])
    first = fit_box_to_selection(context)
    check_box(first, world_points(mesh), (12, 12, 6), rotation(31))
    points = list(mesh.GetPointsAttr().Get())
    order = list(range(len(points)))
    random.Random(7).shuffle(order)
    old_to_new = {old: new for new, old in enumerate(order)}
    indices = list(mesh.GetFaceVertexIndicesAttr().Get())
    mesh.GetPointsAttr().Set([points[index] for index in order])
    mesh.GetFaceVertexIndicesAttr().Set([old_to_new[index] for index in indices])
    second = fit_box_to_selection(context)
    assert Gf.IsClose(first.transform, second.transform, 1e-8) and Gf.IsClose(first.size, second.size, 1e-8), (
        "Point ordering changes symmetric fit"
    )


def empty_and_degenerate():
    stage = stage_for()
    assert fit_box_to_paths(None, ["/Missing"]) is None
    assert fit_box_to_paths(stage, []) is None
    assert fit_box_to_paths(stage, ["/Missing"]) is None
    assert fit_box_to_selection(None) is None
    assert fit_box_to_selection(Context(None, ["/Missing"])) is None
    assert fit_box_to_selection(Context(stage, [])) is None
    assert fit_box_to_selection(Context(stage, ["/Missing"])) is None
    mesh = UsdGeom.Mesh.Define(stage, "/Empty")
    mesh.CreatePointsAttr([])
    assert fit_box_to_selection(Context(stage, ["/Empty"])) is None
    mesh.GetPointsAttr().Set([Gf.Vec3f(0)])
    box = fit_box_to_selection(Context(stage, ["/Empty"]))
    check_box(box, [Gf.Vec3d(0)], (0, 0, 0))


def world_xy_in_y_up_stage():
    stage = stage_for("Y")
    mesh = rectangle(stage, "/Building", size=(40, 6, 10), up=1)
    check_optimal_footprint(fit_box_to_selection(Context(stage, ["/Building"])), world_points(mesh))


def visibility_and_purpose():
    stage = stage_for()
    UsdGeom.Xform.Define(stage, "/Building")
    included = []
    for name, purpose, x in (("Main", "default", 0), ("Render", "render", 20), ("Proxy", "proxy", -20)):
        offset = rotation(31).TransformDir(Gf.Vec3d(x, 0, 0))
        mesh = rectangle(stage, f"/Building/{name}", center=offset)
        mesh.CreatePurposeAttr(purpose)
        included.extend(world_points(mesh))
    hidden_parent = UsdGeom.Xform.Define(stage, "/Building/Hidden")
    hidden_parent.CreateVisibilityAttr(UsdGeom.Tokens.invisible)
    rectangle(stage, "/Building/Hidden/Mesh", center=(1000, 1000, 0))
    guide = rectangle(stage, "/Building/Guide", center=(-1000, -1000, 0))
    guide.CreatePurposeAttr(UsdGeom.Tokens.guide)
    check_box(fit_box_to_selection(Context(stage, ["/Building"])), included, (80, 10, 6), rotation(31))
    UsdGeom.Xform.Define(stage, "/OnlyHidden")
    child = rectangle(stage, "/OnlyHidden/Mesh")
    child.CreateVisibilityAttr(UsdGeom.Tokens.invisible)
    visible, hidden, no_geometry = classify_visible_paths(
        stage, ["/Building/Main", "/Building/Hidden", "/Building/Guide", "/OnlyHidden", "/Missing"]
    )
    assert visible == ["/Building/Main"]
    assert hidden == ["/Building/Hidden", "/OnlyHidden"]
    assert no_geometry == ["/Building/Guide", "/Missing"]


def instance_geometry():
    stage = stage_for()
    UsdGeom.Xform.Define(stage, "/Prototype")
    rectangle(stage, "/Prototype/Mesh")
    instance = UsdGeom.Xform.Define(stage, "/Building")
    instance.GetPrim().GetReferences().AddInternalReference("/Prototype")
    instance.GetPrim().SetInstanceable(True)
    instance.AddRotateZOp().Set(17)
    assert instance.GetPrim().IsInstance()
    mesh = UsdGeom.Mesh(stage.GetPrimAtPath("/Building/Mesh"))
    assert mesh.GetPrim().IsInstanceProxy()
    check_box(fit_box_to_selection(Context(stage, ["/Building"])), world_points(mesh), (40, 10, 6), rotation(48))
    assert classify_visible_paths(stage, ["/Building"]) == (["/Building"], [], [])


def tilted_analytic_geometry():
    stage = stage_for()
    parent = UsdGeom.Xform.Define(stage, "/Building")
    parent.AddTranslateOp().Set(Gf.Vec3d(30, 40, -20))
    parent.AddRotateZOp().Set(35)
    cube = UsdGeom.Cube.Define(stage, "/Building/Cube")
    cube.AddTranslateOp().Set(Gf.Vec3d(7, -5, 2))
    cube.AddRotateYOp().Set(23)
    cube.AddScaleOp().Set(Gf.Vec3f(2, 3, 4))
    world = UsdGeom.XformCache().GetLocalToWorldTransform(cube.GetPrim())
    points = [world.Transform(Gf.Vec3d(x, y, z)) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
    box = fit_box_to_selection(Context(stage, ["/Building/Cube"]))
    check_optimal_footprint(box, points)
    assert Gf.IsClose(box.transform.ExtractTranslation(), world.Transform(Gf.Vec3d(0)), 1e-8)


def affine_containment():
    stage = stage_for()
    mesh = rectangle(stage, "/Building")
    affine = Gf.Matrix4d(-2, 0.3, 0, 0, 0.4, 3, 0.2, 0, 0, 0.1, 1, 0, 6500000, -4200000, 175, 1)
    mesh.AddTransformOp().Set(affine)
    check_box(fit_box_to_selection(Context(stage, ["/Building"])), world_points(mesh))


def purpose_override():
    stage = stage_for()
    guide_parent = UsdGeom.Xform.Define(stage, "/Building")
    guide_parent.CreatePurposeAttr(UsdGeom.Tokens.guide)
    mesh = rectangle(stage, "/Building/Renderable")
    mesh.CreatePurposeAttr(UsdGeom.Tokens.render)
    check_box(fit_box_to_selection(Context(stage, ["/Building"])), world_points(mesh), (40, 10, 6), rotation(31))


def mixed_geometry():
    stage = stage_for()
    mesh = rectangle(stage, "/Building/Mesh")
    cube = UsdGeom.Cube.Define(stage, "/Building/Cube")
    cube.AddTranslateOp().Set(Gf.Vec3d(70, 40, 9))
    cube.AddRotateXOp().Set(27)
    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_])
    bounds = cache.ComputeWorldBound(cube.GetPrim())
    corners = [bounds.GetMatrix().Transform(bounds.GetRange().GetCorner(i)) for i in range(8)]
    check_box(fit_box_to_selection(Context(stage, ["/Building"])), world_points(mesh) + corners)


def center_unchanged():
    stage = stage_for()
    mesh = rectangle(stage, "/Building", center=(40, 20, 10))
    context = Context(stage, ["/Building"])
    bounds = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_]).ComputeWorldBound(mesh.GetPrim())
    assert Gf.IsClose(selection_center(context), bounds.ComputeAlignedRange().GetMidpoint(), 1e-8)
    assert selection_center(Context(stage, [])) is None


def point_instancer_bounds():
    stage = stage_for()
    mesh = rectangle(stage, "/Building/Mesh")
    instancer = UsdGeom.PointInstancer.Define(stage, "/Building/Instances")
    prototype = UsdGeom.Cube.Define(stage, "/Building/Instances/Prototype")
    prototype.AddTranslateOp().Set(Gf.Vec3d(1000, 0, 0))
    instancer.CreatePrototypesRel().SetTargets([prototype.GetPath()])
    instancer.CreateProtoIndicesAttr([0, 0])
    instancer.CreatePositionsAttr([(-1000, 0, 0), (5000, 0, 0)])
    instancer.CreateInvisibleIdsAttr([1])
    box = fit_box_to_selection(Context(stage, ["/Building"]))
    cube_points = [Gf.Vec3d(x, y, z) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
    check_box(box, world_points(mesh) + cube_points, (40, 10, 6), rotation(31))


def empty_mesh_with_analytic_geometry():
    stage = stage_for()
    parent = UsdGeom.Xform.Define(stage, "/Building")
    parent.AddRotateYOp().Set(23)
    cube = UsdGeom.Cube.Define(stage, "/Building/Cube")
    cube.AddScaleOp().Set(Gf.Vec3f(2, 3, 4))
    UsdGeom.Mesh.Define(stage, "/Building/Empty").CreatePointsAttr([])
    world = UsdGeom.XformCache().GetLocalToWorldTransform(cube.GetPrim())
    points = [world.Transform(Gf.Vec3d(x, y, z)) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
    check_optimal_footprint(fit_box_to_selection(Context(stage, ["/Building"])), points)


def baked_tilted_asset():
    stage = stage_for()
    mesh = rectangle(stage, "/Asset", yaw=0)
    frame = rotation(23, 0) * rotation(-37, 1) * rotation(51)
    mesh.GetPointsAttr().Set([frame.Transform(Gf.Vec3d(p)) for p in mesh.GetPointsAttr().Get()])
    check_optimal_footprint(fit_box_to_selection(Context(stage, ["/Asset"])), world_points(mesh))


def nested_tilted_asset():
    stage = stage_for()
    building = UsdGeom.Xform.Define(stage, "/Property/Building")
    building.AddTranslateOp().Set(Gf.Vec3d(6500000, -4200000, 175))
    building.AddRotateZOp().Set(19)
    mesh = rectangle(stage, "/Property/Building/Asset", yaw=0, size=(2, 5, 11))
    tilt = rotation(-41, 0) * rotation(27, 1)
    mesh.AddTransformOp().Set(tilt)
    for path in ("/Property", "/Property/Building", "/Property/Building/Asset"):
        check_optimal_footprint(fit_box_to_selection(Context(stage, [path])), world_points(mesh))


def tilted_cube_symmetry():
    stage = stage_for()
    mesh = rectangle(stage, "/Asset", yaw=0, size=(12, 12, 12))
    frame = rotation(13, 0) * rotation(29, 1) * rotation(-17)
    points = [frame.Transform(Gf.Vec3d(p)) for p in mesh.GetPointsAttr().Get()]
    mesh.GetPointsAttr().Set(points)
    first = fit_box_to_selection(Context(stage, ["/Asset"]))
    check_optimal_footprint(first, world_points(mesh))
    order = list(range(len(points)))
    random.Random(11).shuffle(order)
    remap = {old: new for new, old in enumerate(order)}
    indices = mesh.GetFaceVertexIndicesAttr().Get()
    mesh.GetFaceVertexIndicesAttr().Set([remap[index] for index in indices])
    mesh.GetPointsAttr().Set([points[index] for index in order])
    second = fit_box_to_selection(Context(stage, ["/Asset"]))
    assert Gf.IsClose(first.transform, second.transform, 1e-7)
    assert Gf.IsClose(first.size, second.size, 1e-7)


def dense_geometry():
    stage = stage_for()
    mesh = rectangle(stage, "/Building", yaw=0)
    frame = rotation(31)
    points = [frame.Transform(Gf.Vec3d(x, y, z)) for x in range(-20, 21) for y in range(-5, 6) for z in range(-3, 4)]
    mesh.GetPointsAttr().Set(points)
    box = fit_box_to_selection(Context(stage, ["/Building"]))
    check_box(box, world_points(mesh), (40, 10, 6), frame)


def large_authored_coordinates():
    stage = stage_for()
    mesh = rectangle(stage, "/Asset", center=(6500000, -4200000, 175))
    mesh.AddTranslateOp().Set(Gf.Vec3d(3000000000, 2000000000, 400))
    check_optimal_footprint(fit_box_to_selection(Context(stage, ["/Asset"])), world_points(mesh))


def instance_cache_isolation():
    stage = stage_for()
    prototype = rectangle(stage, "/Prototype/Mesh", yaw=0)
    for index, (yaw, scale) in enumerate(((31, 1), (31, 1), (57, 2))):
        instance = UsdGeom.Xform.Define(stage, f"/Building/Part{index}")
        instance.GetPrim().GetReferences().AddInternalReference("/Prototype")
        instance.GetPrim().SetInstanceable(True)
        instance.AddTranslateOp().Set(Gf.Vec3d(index * 30, index * 7, index * 3))
        instance.AddRotateZOp().Set(yaw)
        instance.AddScaleOp().Set(Gf.Vec3f(scale, 1, 1))
    context = Context(stage, ["/Building"])
    for factor in (1, 2):
        if factor == 2:
            prototype.GetPointsAttr().Set([Gf.Vec3f(p) * factor for p in prototype.GetPointsAttr().Get()])
        points = [
            p
            for index in range(3)
            for p in world_points(UsdGeom.Mesh(stage.GetPrimAtPath(f"/Building/Part{index}/Mesh")))
        ]
        check_optimal_footprint(fit_box_to_selection(context), points)


def footprint_scale_invariance():
    generator = random.Random(42)
    for _ in range(20):
        points = [(generator.uniform(-5, 5), generator.uniform(-5, 5)) for _ in range(12)]
        reference = minimum_rectangle(convex_hull(points))
        expected = (reference.maximum[0] - reference.minimum[0]) * (reference.maximum[1] - reference.minimum[1])
        for scale in (1e-6, 1e6):
            fitted = minimum_rectangle(convex_hull([(x * scale, y * scale) for x, y in points]))
            area = (fitted.maximum[0] - fitted.minimum[0]) * (fitted.maximum[1] - fitted.minimum[1]) / scale**2
            assert abs(area - expected) < 1e-8 * expected, "Changing asset size changes the minimum-area fit"


def verify_selection():
    checks = [
        baked_rotation,
        child_rotation,
        georeferenced_rotation,
        multiple_branches,
        explicit_paths_time,
        square_determinism,
        empty_and_degenerate,
        world_xy_in_y_up_stage,
        visibility_and_purpose,
        instance_geometry,
        tilted_analytic_geometry,
        affine_containment,
        purpose_override,
        mixed_geometry,
        center_unchanged,
        point_instancer_bounds,
        empty_mesh_with_analytic_geometry,
        baked_tilted_asset,
        nested_tilted_asset,
        tilted_cube_symmetry,
        dense_geometry,
        large_authored_coordinates,
        instance_cache_isolation,
        footprint_scale_invariance,
    ]
    for check in checks:
        check()
        print(f"PASS {check.__name__}")
    return [check.__name__ for check in checks]


if __name__ == "__main__":
    verify_selection()
