"""Place a camera in a space and work out what it sees.

`view()` returns a plain dict (JSON-friendly) with:
  camera   position, heading, fields of view;
  bounds   which side (wall or open backdrop) the frame's left edge, centre and right edge land on;
  subject  where a person stands in the frame, whether we see her front, back or profile, and which frame side her
           right/left side is on;
  objects  every object with its frame placement (h: left / centre / right third, v: low / mid / high, depth),
           how much of it is in frame, and whether it stands behind the subject;
  mirrors  for each reflective object in frame: what the camera sees in it (objects and the subject, with the same
           placement fields, exact by reflecting the scene through the mirror plane), and whether the camera itself
           shows up in it.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .scene import Obj, SceneError, Space, heading

FG, MG = 1.5, 3.5  # depth bands (metres): foreground < FG <= midground < MG <= background
BODY_W, BODY_H = 0.45, 1.6  # a standing subject's width and height (metres)


@dataclass
class Camera:
    x: float
    y: float
    z: float
    yaw: float  # degrees, 0 = east, 90 = north
    hfov: float = 60.0
    aspect: float = 2 / 3  # width / height; 2/3 = a vertical frame

    @property
    def vfov(self) -> float:
        return math.degrees(2 * math.atan(math.tan(math.radians(self.hfov) / 2) / self.aspect))

    def project(self, p) -> tuple[float, float, float] | None:
        """World point -> (u, v, forward distance); u, v in [-1, 1] are inside the frame (u: left -> right,
        v: bottom -> top). None when the point is behind the camera."""
        yaw = math.radians(self.yaw)
        dx, dy = p[0] - self.x, p[1] - self.y
        f = dx * math.cos(yaw) + dy * math.sin(yaw)
        r = dx * math.sin(yaw) - dy * math.cos(yaw)
        if f <= 0.05:
            return None
        u = (r / f) / math.tan(math.radians(self.hfov) / 2)
        v = ((p[2] - self.z) / f) / math.tan(math.radians(self.vfov) / 2)
        return u, v, f


def _third(u: float) -> str:
    return "left" if u < -1 / 3 else "right" if u > 1 / 3 else "centre"


def _band(v: float) -> str:
    return "low" if v < -1 / 3 else "high" if v > 1 / 3 else "mid"


def _depth(dist: float) -> str:
    return "foreground" if dist < FG else "midground" if dist < MG else "background"


def _place(cam: Camera, pts) -> dict:
    """Frame placement of a set of world points (one object's samples)."""
    proj = [cam.project(p) for p in pts]
    front = [q for q in proj if q]
    if not front:
        return {"in_frame": 0.0, "where": "behind the camera"}
    us = [q[0] for q in front]
    vs = [q[1] for q in front]
    umin, umax, vmin, vmax = min(us), max(us), min(vs), max(vs)
    if len(front) < len(proj):  # straddles the camera plane: it runs off one side of the frame
        umin, umax = (min(umin, -9), umax) if sum(us) < 0 else (umin, max(umax, 9))
    if umax < -1 or umin > 1 or vmax < -1 or vmin > 1:
        side = "off the left edge" if umax < -1 else "off the right edge" if umin > 1 else "below the frame" if vmax < -1 else "above the frame"
        return {"in_frame": 0.0, "where": side}
    if umax <= -1 or umin >= 1 or vmax <= -1 or vmin >= 1:
        return {"in_frame": 0.0, "where": "at the frame edge"}
    cu0, cu1 = max(umin, -1), min(umax, 1)
    cv0, cv1 = max(vmin, -1), min(vmax, 1)
    frac_u = (cu1 - cu0) / (umax - umin) if umax > umin else 1.0
    frac_v = (cv1 - cv0) / (vmax - vmin) if vmax > vmin else 1.0
    cut = [s for s, c in (("left edge", umin < -1), ("right edge", umax > 1), ("bottom edge", vmin < -1), ("top edge", vmax > 1)) if c]
    dist = min(q[2] for q in front)
    if round(frac_u * frac_v, 2) == 0:
        return {"in_frame": 0.0, "where": "at the frame edge"}
    return {"in_frame": round(frac_u * frac_v, 2), "h": _third((cu0 + cu1) / 2), "v": _band((cv0 + cv1) / 2),
            "u": [round(cu0, 2), round(cu1, 2)], "depth": _depth(dist), "distance": round(dist, 2), "cut_by": cut}


def _ray_side(space: Space, x: float, y: float, deg: float) -> dict:
    """The side a ground-level ray from (x, y) reaches first, and whether it is a wall or open."""
    dx, dy = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    hits = []
    if dx > 1e-9:
        hits.append(((space.w - x) / dx, "E"))
    if dx < -1e-9:
        hits.append((-x / dx, "W"))
    if dy > 1e-9:
        hits.append(((space.d - y) / dy, "N"))
    if dy < -1e-9:
        hits.append((-y / dy, "S"))
    side = min(hits)[1]
    if side in space.walls:
        return {"side": side, "kind": "wall", "desc": space.walls[side]}
    return {"side": side, "kind": "open", "desc": space.open.get(side)}


def _subject_pts(sx: float, sy: float, face: float, h: float, base: float = 0.0) -> dict:
    fr = math.radians(face)
    rx, ry = math.sin(fr) * BODY_W / 2, -math.cos(fr) * BODY_W / 2  # her right side
    b, top, mid = base, base + h, base + h * 0.55
    return {"body": [(sx + rx, sy + ry, b), (sx - rx, sy - ry, b), (sx + rx, sy + ry, top), (sx - rx, sy - ry, top), (sx, sy, b + h / 2)],
            "right": (sx + rx, sy + ry, mid), "left": (sx - rx, sy - ry, mid), "center": (sx, sy, mid)}


def _orientation(cam: Camera, sx: float, sy: float, face: float) -> str:
    to_cam = math.degrees(math.atan2(cam.y - sy, cam.x - sx))
    a = (face - to_cam + 180) % 360 - 180
    if abs(a) <= 45:
        return "front"
    if abs(a) >= 135:
        return "back"
    return "profile"


def _sides(cam: Camera, pts: dict) -> dict:
    pr, pl, pc = cam.project(pts["right"]), cam.project(pts["left"]), cam.project(pts["center"])
    if not (pr and pl and pc):
        return {}
    right_side = "frame-right" if pr[0] > pl[0] else "frame-left"
    return {"her_right_side": right_side, "her_left_side": "frame-left" if right_side == "frame-right" else "frame-right"}


def _subject(cam: Camera, space: Space, s: dict) -> dict:
    sx, sy = space.point(s["at"])
    h = float(s.get("height", BODY_H))
    face = heading(s.get("facing", "camera"), (sx, sy), space, toward=(cam.x, cam.y))
    base = space.objects[s["on"]].z1 if s.get("on") in space.objects else 0.0
    pts = _subject_pts(sx, sy, face, h, base)
    out = {"name": s.get("name", "subject"), "at": [sx, sy], "facing_deg": round(face, 1), "on": s.get("on"), "base": base,
           "view": _orientation(cam, sx, sy, face), **_place(cam, pts["body"]), **_sides(cam, pts)}
    if out["view"] == "profile":
        fr = math.radians(face)
        tip = cam.project((sx + math.cos(fr), sy + math.sin(fr), base + h * 0.55))
        mid = cam.project(pts["center"])
        if tip and mid:
            out["looking_toward"] = "frame-right" if tip[0] > mid[0] else "frame-left"
    return out


def _reflect(o: Obj, space: Space):
    """Mirror plane of a wall object -> a function reflecting a world point through it."""
    return {"N": lambda p: (p[0], 2 * space.d - p[1], p[2]), "S": lambda p: (p[0], -p[1], p[2]),
            "E": lambda p: (2 * space.w - p[0], p[1], p[2]), "W": lambda p: (-p[0], p[1], p[2])}[o.wall]


def _through(cam: Camera, m: Obj, p) -> bool:
    """Does the line from the camera to the reflected point p cross the mirror's rectangle?"""
    ax = {"N": 1, "S": 1, "E": 0, "W": 0}[m.wall]  # axis normal to the wall: 1 = y, 0 = x
    plane = (m.y1 if m.wall == "N" else m.y0) if ax else (m.x1 if m.wall == "E" else m.x0)
    c = (cam.x, cam.y, cam.z)
    if abs(p[ax] - c[ax]) < 1e-9:
        return False
    t = (plane - c[ax]) / (p[ax] - c[ax])
    if not 0 < t < 1:
        return False
    hit = [c[i] + t * (p[i] - c[i]) for i in range(3)]
    lo, hi = (m.x0, m.x1) if ax else (m.y0, m.y1)
    return lo <= hit[1 - ax] <= hi and m.z0 <= hit[2] <= m.z1


def _self_visible(cam: Camera, m: Obj, ref) -> bool:
    """Would the camera see its own reflection: through the mirror and inside the frame."""
    p = ref((cam.x, cam.y, cam.z))
    q = cam.project(p)
    return _through(cam, m, p) and q is not None and abs(q[0]) <= 1 and abs(q[1]) <= 1


def _mirror(cam: Camera, space: Space, m: Obj, subject: dict | None) -> dict:
    ref = _reflect(m, space)
    seen = []
    for o in space.objects.values():
        if o.id == m.id:
            continue
        rp = [ref(p) for p in o.points()]
        vis = [p for p in rp if _through(cam, m, p)]
        pl = _place(cam, vis) if vis else {}
        if pl.get("h"):  # visible through the mirror and inside the frame
            seen.append({"id": o.id, "desc": o.desc, "h": pl.get("h"), "v": pl.get("v"), "share": round(len(vis) / len(rp), 2)})
    out = {"id": m.id, "desc": m.desc, "shows": seen,
           "camera_visible": _self_visible(cam, m, ref)}
    if subject:
        sx, sy = subject["at"]
        pts = _subject_pts(sx, sy, subject["facing_deg"], float(subject.get("height", BODY_H)), subject.get("base", 0.0))
        rpts = {k: ([ref(p) for p in v] if k == "body" else ref(v)) for k, v in pts.items()}
        vis = [p for p in rpts["body"] if _through(cam, m, p)]
        if vis and _place(cam, vis).get("h"):
            rs = _sides(cam, rpts)
            cx, cy = rpts["center"][:2]
            fr = math.radians(subject["facing_deg"])
            fx, fy = math.cos(fr), math.sin(fr)
            fx, fy = (fx, -fy) if m.wall in "NS" else (-fx, fy)  # a mirror flips the facing across its plane
            rface = math.degrees(math.atan2(fy, fx))
            out["subject"] = {"view": _orientation(cam, cx, cy, rface), "h": _place(cam, vis).get("h"),
                              "share": round(len(vis) / len(rpts["body"]), 2), **{f"reflected_{k}": v for k, v in rs.items()}}
    return out


def shot_problems(space: Space, cam: Camera, subject: dict | None) -> list[str]:
    """A shot that can't exist: the camera inside furniture or outside the walls, the subject inside furniture
    (unless the shot says she is `on` it) or off what she is `on`."""
    errs = []
    if [k for k in ("W", "E", "S", "N") if k in space.walls and ((k == "W" and cam.x < 0) or (k == "E" and cam.x > space.w)
                                                                 or (k == "S" and cam.y < 0) or (k == "N" and cam.y > space.d))]:
        errs.append(f"the camera at ({cam.x:g}, {cam.y:g}) is outside the walls")
    if space.height and cam.z > space.height:
        errs.append(f"the camera is above the ceiling ({cam.z} m)")
    hit = space.inside(cam.x, cam.y, cam.z)
    if hit:
        errs.append(f"the camera is inside '{hit[0]}'")
    if subject:
        sx, sy = space.point(subject["at"])
        on = subject.get("on")
        if on and on not in space.objects:
            errs.append(f"the subject is on '{on}', which is not in the space")
        elif on and on not in space.inside(sx, sy):
            errs.append(f"the subject is on '{on}' but stands outside its footprint")
        inside = [k for k in space.inside(sx, sy) if k != on]
        if inside:
            errs.append(f"the subject stands inside '{inside[0]}'" + ("" if on else f" (add \"on\": \"{inside[0]}\" if she is on it)"))
    return errs


def view(space: Space, cam: Camera, subject: dict | None = None) -> dict:
    errs = shot_problems(space, cam, subject)
    if errs:
        raise SceneError("shot rejected:\n  - " + "\n  - ".join(errs))
    left, right = cam.yaw + cam.hfov / 2, cam.yaw - cam.hfov / 2
    bounds = {"left_edge": _ray_side(space, cam.x, cam.y, left), "centre": _ray_side(space, cam.x, cam.y, cam.yaw),
              "right_edge": _ray_side(space, cam.x, cam.y, right)}
    subj = _subject(cam, space, subject) if subject else None
    objects = []
    for o in space.objects.values():
        pl = _place(cam, o.points())
        if subj and pl.get("in_frame") and subj.get("in_frame") and pl["distance"] > subj["distance"]:
            a0, a1 = pl["u"]
            b0, b1 = subj["u"]
            if a0 < b1 and b0 < a1:
                pl["behind_subject"] = True
        objects.append({"id": o.id, "desc": o.desc, "wall": o.wall, "parent": o.parent, "children": o.children, **pl})
    mirrors = [_mirror(cam, space, space.objects[o["id"]], subj) for o in objects
               if space.objects[o["id"]].mirror and o.get("in_frame")]
    return {"space": space.name,
            "camera": {"at": [cam.x, cam.y, cam.z], "heading": _compass(cam.yaw), "yaw": round(cam.yaw, 1),
                       "hfov": cam.hfov, "vfov": round(cam.vfov, 1), "aspect": round(cam.aspect, 3)},
            "bounds": bounds, "subject": subj, "objects": objects, "mirrors": mirrors}


def _compass(deg: float) -> str:
    names = ["E", "NE", "N", "NW", "W", "SW", "S", "SE"]
    return names[round((deg % 360) / 45) % 8]


def camera_for(space: Space, shot: dict) -> Camera:
    """A shot dict ({cam: [x, y, z] or a relation dict with "z", look: id | [x, y] | compass | degrees, fov, aspect}) -> Camera."""
    c = shot["cam"]
    if isinstance(c, dict):  # a relation: {"in_front_of": "bed", "gap": 2.5, "z": 1.5}
        (x, y), z = space.point(c), float(c.get("z", 1.5))
    else:
        x, y, z = (float(v) for v in c)
    yaw = heading(shot.get("look", "N"), (x, y), space)
    return Camera(x, y, z, yaw, float(shot.get("fov", 60)), float(shot.get("aspect", 2 / 3)))
