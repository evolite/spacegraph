"""Scene model: spaces, objects and shots loaded from a JSON scene file.

Coordinates are metres. x runs west -> east, y runs south -> north, z is height above the ground.
A space is an axis-aligned area `size: [width_x, depth_y]` with four sides, N, E, S, W. Each side is either a wall
(`walls: {"N": "warm white"}`) or open (`open: {"E": "the sea to the horizon"}`, a backdrop seen beyond it); a side
listed in neither is open with no backdrop. `height` is the ceiling (omit it outdoors); `ground` and
`sky` describe the surfaces. Objects may stand outside the area too (a distant landmark).

An object is placed one of three ways:
  - free-standing: `at: [x, y]` (footprint centre) + `size: [sx, sy]`, optional `against: "N"` to snap it to a wall;
  - on a wall: `wall: "E"` + `span: [a, b]` (metres along the wall, from its west/south end);
  - on another object: `on: "<id>"` (sits on the parent's top, at its centre unless `at` is given).
Height is `h` (top above the ground or above the parent) or `z: [z0, z1]`. `mirror: true` makes a wall object reflective.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

COMPASS = {"E": 0.0, "N": 90.0, "W": 180.0, "S": 270.0, "NE": 45.0, "NW": 135.0, "SW": 225.0, "SE": 315.0}
THIN = 0.03  # depth of a wall-mounted object


@dataclass
class Obj:
    id: str
    desc: str
    x0: float
    y0: float
    x1: float
    y1: float
    z0: float
    z1: float
    wall: str | None = None
    parent: str | None = None
    mirror: bool = False
    children: list[str] = field(default_factory=list)

    @property
    def center(self) -> tuple[float, float, float]:
        return ((self.x0 + self.x1) / 2, (self.y0 + self.y1) / 2, (self.z0 + self.z1) / 2)

    def points(self) -> list[tuple[float, float, float]]:
        """Corners of the bounding box plus its centre: enough samples for frame placement."""
        pts = [(x, y, z) for x in (self.x0, self.x1) for y in (self.y0, self.y1) for z in (self.z0, self.z1)]
        return pts + [self.center]


class Space:
    def __init__(self, name: str, d: dict, hide: set[str] = frozenset()):
        self.name = name
        self.w, self.d = (float(v) for v in d["size"])
        self.height: float | None = float(d["height"]) if "height" in d else None
        self.h = self.height or 3.0  # default top for wall-mounted objects
        self.walls: dict[str, str] = d.get("walls", {})
        self.open: dict[str, str] = d.get("open", {})
        self.ground: str | None = d.get("ground")
        self.sky: str | None = d.get("sky")
        self._raw = {o["id"]: o for o in d.get("objects", []) if o["id"] not in hide}
        self.objects: dict[str, Obj] = {}
        for oid in self._raw:
            self._resolve(oid, ())
        for o in self.objects.values():
            if o.parent in self.objects:
                self.objects[o.parent].children.append(o.id)

    def _resolve(self, oid: str, chain: tuple) -> Obj:
        if oid in self.objects:
            return self.objects[oid]
        if oid in chain:
            raise ValueError(f"circular 'on' chain: {' -> '.join(chain + (oid,))}")
        if oid not in self._raw:
            raise ValueError(f"unknown object '{oid}'")
        r = self._raw[oid]
        desc = r.get("desc", oid)
        if "on" in r:
            p = self._resolve(r["on"], chain + (oid,))
            sx, sy = r.get("size", [0.15, 0.15])
            cx, cy = r.get("at", [(p.x0 + p.x1) / 2, (p.y0 + p.y1) / 2])
            z0 = p.z1
            o = Obj(oid, desc, cx - sx / 2, cy - sy / 2, cx + sx / 2, cy + sy / 2, z0, z0 + float(r.get("h", 0.3)), parent=p.id)
        elif "wall" in r:
            wall = r["wall"]
            a, b = r.get("span", [0, self.w if wall in "NS" else self.d])
            z0, z1 = r.get("z", [0, self.h])
            box = {"N": (a, self.d - THIN, b, self.d), "S": (a, 0, b, THIN),
                   "E": (self.w - THIN, a, self.w, b), "W": (0, a, THIN, b)}[wall]
            o = Obj(oid, desc, *box, z0, z1, wall=wall, mirror=bool(r.get("mirror")))
        else:
            sx, sy = r.get("size", [0.5, 0.5])
            cx, cy = r.get("at", [self.w / 2, self.d / 2])
            snap = r.get("against")
            if snap == "N":
                cy = self.d - sy / 2
            elif snap == "S":
                cy = sy / 2
            elif snap == "E":
                cx = self.w - sx / 2
            elif snap == "W":
                cx = sx / 2
            z0, z1 = r.get("z", [0, r.get("h", 0.5)])
            o = Obj(oid, desc, cx - sx / 2, cy - sy / 2, cx + sx / 2, cy + sy / 2, z0, z1)
        self.objects[oid] = o
        return o

    def point(self, target) -> tuple[float, float]:
        """An object id or an [x, y] pair -> a ground point."""
        if isinstance(target, str):
            if target not in self.objects:
                raise ValueError(f"unknown object '{target}' in space '{self.name}'")
            return self.objects[target].center[:2]
        return float(target[0]), float(target[1])



def heading(spec, origin: tuple[float, float], space: "Space", toward: tuple[float, float] | None = None) -> float:
    """A direction spec -> degrees (0 = east, 90 = north). Spec: compass ("N", "SW"), degrees, "camera"
    (needs `toward`), an object id, or an [x, y] point."""
    if isinstance(spec, (int, float)):
        return float(spec) % 360
    if isinstance(spec, str) and spec.upper() in COMPASS:
        return COMPASS[spec.upper()]
    if spec == "camera":
        if toward is None:
            raise ValueError("'camera' facing needs a camera")
        tx, ty = toward
    else:
        tx, ty = space.point(spec)
    return math.degrees(math.atan2(ty - origin[1], tx - origin[0])) % 360


class Scene:
    def __init__(self, data: dict):
        self.data = data
        self.shots: dict[str, dict] = data.get("shots", {})

    @property
    def spaces(self) -> dict:
        return self.data.get("spaces", {})

    def space(self, name: str | None = None, hide=()) -> Space:
        spaces = self.spaces
        name = name or next(iter(spaces))
        if name not in spaces:
            raise ValueError(f"unknown space '{name}' (have: {', '.join(spaces)})")
        return Space(name, spaces[name], set(hide))


def load(path: str | Path) -> Scene:
    return Scene(json.loads(Path(path).read_text()))
