"""Selected USD geometry expressed as a fitted box or a world-space center."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pxr import Gf, Usd, UsdGeom

from .model import SectionBox

if TYPE_CHECKING:
    from omni.usd import UsdContext


def fit_box_to_selection(context: UsdContext | None) -> SectionBox | None:
    """Fit in the selection's common rigid frame, keeping scale in the dimensions."""
    bounds = _selection_bounds(context, oriented=True)
    if bounds is None:
        return None
    transform = bounds.GetMatrix()
    transform.SetTranslateOnly(transform.Transform(bounds.GetRange().GetMidpoint()))
    return SectionBox(transform=transform, size=bounds.GetRange().GetSize())


def selection_center(context: UsdContext | None) -> Gf.Vec3d | None:
    """Return the combined world-aligned midpoint, or None for empty selection."""
    bounds = _selection_bounds(context, oriented=False)
    return bounds.ComputeAlignedRange().GetMidpoint() if bounds is not None else None


def _selection_bounds(usd_context: UsdContext | None, *, oriented: bool) -> Gf.BBox3d | None:
    if usd_context is None:
        return None
    selection = usd_context.get_selection()
    paths = selection.get_selected_prim_paths() if selection else []
    if not paths:
        return None

    stage = usd_context.get_stage()
    if stage is None:
        return None

    prims = [stage.GetPrimAtPath(path) for path in paths]
    prims = [prim for prim in prims if prim.IsValid()]
    if not prims:
        return None

    frame = Gf.Matrix4d(1)
    if oriented:
        common_path = prims[0].GetPath()
        for prim in prims[1:]:
            common_path = common_path.GetCommonPrefix(prim.GetPath())
        world_transform = UsdGeom.XformCache().GetLocalToWorldTransform(stage.GetPrimAtPath(common_path))
        # Keep scale in the extents so the box's transform stays rigid.
        frame.SetRotate(Gf.Transform(world_transform).GetRotation())

    inverse_frame = frame.GetInverse()
    bbox_cache = UsdGeom.BBoxCache(
        Usd.TimeCode.Default(),
        [UsdGeom.Tokens.default_, UsdGeom.Tokens.render, UsdGeom.Tokens.proxy],
    )
    total_range = Gf.Range3d()
    for prim in prims:
        bbox = bbox_cache.ComputeWorldBound(prim)
        local_bbox = Gf.BBox3d(bbox.GetRange(), bbox.GetMatrix() * inverse_frame)
        total_range = Gf.Range3d.GetUnion(total_range, local_bbox.ComputeAlignedRange())

    if total_range.IsEmpty():
        return None

    return Gf.BBox3d(total_range, frame)
