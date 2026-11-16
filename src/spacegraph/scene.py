"""Scene model: spaces, objects and shots loaded from a JSON scene file.

Coordinates are metres. x runs west -> east, y runs south -> north, z is height above the ground.
A space is an axis-aligned area `size: [width_x, depth_y]` with four sides, N, E, S, W. Each side is either a wall
(`walls: {"N": "warm white"}`) or open (`open: {"E": "the sea to the horizon"}`, a backdrop seen beyond it); a side
listed in neither is open with no backdrop. `height` is the ceiling (omit it outdoors); `ground` and
`sky` describe the surfaces. Objects may stand outside the area too (a distant landmark).

An object is placed one of three ways, by relations to the space and to other objects (or by numbers, which win):
  - free-standing, `size: [sx, sy]` plus any of:
      `against: "N"`                     back to a side (it then faces into the space);
      `corner: "NE"`                     into a corner;
      `north_of` / `south_of` / `east_of` / `west_of`: "<id>"   beside another object, `gap` metres apart (default
                                         0.05), centred on it unless `align` names an edge ("N", "S", "E", "W");
      `in_front_of` / `behind`: "<id>"   the same, relative to the side that object stands against;
      `at: [x, y]`                       its footprint centre, in metres (overrides the above);
  - on a side: `wall: "E"` + `width` and `centred_on: "<id>"`, or `from: "N"` (the end it is measured from) +
    `offset`; or `span: [a, b]` in metres from the side's west/south end;
  - on another object: `on: "<id>"` (on the parent's top, at its centre, or against its `align` edge: "N", "SW", ...;
    `at` overrides).
Height is `h` (top above the ground or the parent) or `z: [z0, z1]`. `mirror: true` makes a side-mounted object reflective.
Compass relations are used instead of left/right, which depend on where the viewer stands.

Points (a shot's subject `at`, its `cam`) take the same relations as a dict, e.g. `{"in_front_of": "mirror", "gap": 0.6}`.

Every space validates itself on load and raises SceneError listing what is wrong: free-standing objects overlapping,
an object through a wall or the ceiling, a prop hanging off what it sits on, a side object longer than its side.
Flat things (5 cm or less: a rug, a towel) and `solid: false` ones (a canopy) never count as overlapping.
"""
from __future__ import annotations

import json
import math
from itertools import combinations
from dataclasses import dataclass, field
from pathlib import Path

REL = {"north_of": (0, 1), "south_of": (0, -1), "east_of": (1, 0), "west_of": (-1, 0)}
FRONT = {"N": "south_of", "S": "north_of", "E": "west_of", "W": "east_of"}
OPPOSITE = {"N": "S", "S": "N", "E": "W", "W": "E"}
COMPASS = {"E": 0.0, "N": 90.0, "W": 180.0, "S": 270.0, "NE": 45.0, "NW": 135.0, "SW": 225.0, "SE": 315.0}
THIN = 0.03
TOL = 0.01
CORNER = 0.6
FLAT = 0.05


class SceneError(ValueError):
    """A space or shot that is physically impossible; the message lists every problem."""


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
    against: str | None = None
    solid: bool = True
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
        self.h = self.height or 3.0
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
        errs = self.problems()
        if errs:
            raise SceneError(f"space '{name}' rejected:\n  - " + "\n  - ".join(errs))

    def floor_objects(self) -> list[Obj]:
        return [o for o in self.objects.values() if not o.wall and not o.parent]

    def solid_objects(self) -> list[Obj]:
        return [o for o in self.floor_objects() if o.solid]

    def problems(self) -> list[str]:
        errs = []
        for a, b in combinations(self.solid_objects(), 2):
            ox, oy = min(a.x1, b.x1) - max(a.x0, b.x0), min(a.y1, b.y1) - max(a.y0, b.y0)
            oz = min(a.z1, b.z1) - max(a.z0, b.z0)
            if ox > TOL and oy > TOL and oz > TOL:
                errs.append(f"'{a.id}' and '{b.id}' overlap by {ox:.2f} x {oy:.2f} m")
        for o in self.floor_objects():
            for side, out in (("W", o.x0 < -TOL), ("E", o.x1 > self.w + TOL), ("S", o.y0 < -TOL), ("N", o.y1 > self.d + TOL)):
                if out and side in self.walls:
                    errs.append(f"'{o.id}' goes through the {side} wall")
        for o in self.objects.values():
            if self.height and o.z1 > self.height + TOL:
                errs.append(f"'{o.id}' goes through the ceiling ({o.z1:.2f} m > {self.height} m)")
            if o.parent:
                p = self.objects[o.parent]
                if o.x0 < p.x0 - TOL or o.x1 > p.x1 + TOL or o.y0 < p.y0 - TOL or o.y1 > p.y1 + TOL:
                    errs.append(f"'{o.id}' hangs off the edge of '{p.id}' it sits on")
            if o.wall:
                length = self.w if o.wall in "NS" else self.d
                a, b = (o.x0, o.x1) if o.wall in "NS" else (o.y0, o.y1)
                if a < -TOL or b > length + TOL:
                    errs.append(f"'{o.id}' runs past the end of the {o.wall} side ({length} m)")
        return errs

    def placement(self, oid: str) -> str:
        """Where an object is in the space, in words: 'on the E wall, near the SE corner', 'in the NW corner',
        'against the N wall, in the middle', 'on the nightstand', 'in the middle of the space'."""
        o = self.objects[oid]
        if o.parent:
            return f"on the {o.parent}"
        near = {"W": o.x0 < CORNER, "E": o.x1 > self.w - CORNER, "S": o.y0 < CORNER, "N": o.y1 > self.d - CORNER}
        if o.wall:
            length = self.w if o.wall in "NS" else self.d
            a, b = (o.x0, o.x1) if o.wall in "NS" else (o.y0, o.y1)
            lo, hi = ("W", "E") if o.wall in "NS" else ("S", "N")
            corner = lambda end: "".join(sorted((o.wall, end), key="NSEW".index))
            if a < CORNER and length - b < CORNER:
                return f"filling the {o.wall} wall"
            if a < CORNER or (a + b) / 2 < length * 0.3:
                return f"on the {o.wall} wall, near the {corner(lo)} corner"
            if length - b < CORNER or (a + b) / 2 > length * 0.7:
                return f"on the {o.wall} wall, near the {corner(hi)} corner"
            return f"in the middle of the {o.wall} wall"
        ns = "N" if near["N"] else "S" if near["S"] else ""
        ew = "E" if near["E"] else "W" if near["W"] else ""
        if ns and ew:
            return f"in the {ns}{ew} corner"
        if ns or ew:
            return f"against the {ns or ew} wall"
        return "in the open floor"

    def inside(self, x: float, y: float, z: float | None = None) -> list[str]:
        """Floor objects whose footprint contains (x, y) (and, with z, whose height reaches z)."""
        return [o.id for o in self.solid_objects()
                if o.x0 + TOL < x < o.x1 - TOL and o.y0 + TOL < y < o.y1 - TOL and (z is None or z < o.z1)]

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
            edge = r.get("align", "")
            if "at" not in r:
                cx = p.x0 + sx / 2 if "W" in edge else p.x1 - sx / 2 if "E" in edge else cx
                cy = p.y0 + sy / 2 if "S" in edge else p.y1 - sy / 2 if "N" in edge else cy
            z0 = p.z1
            o = Obj(oid, desc, cx - sx / 2, cy - sy / 2, cx + sx / 2, cy + sy / 2, z0, z0 + float(r.get("h", 0.3)), parent=p.id)
        elif "wall" in r:
            wall = r["wall"]
            a, b = r["span"] if "span" in r else self._span(r, wall, chain + (oid,))
            z0, z1 = r.get("z", [0, self.h])
            box = {"N": (a, self.d - THIN, b, self.d), "S": (a, 0, b, THIN),
                   "E": (self.w - THIN, a, self.w, b), "W": (0, a, THIN, b)}[wall]
            o = Obj(oid, desc, *box, z0, z1, wall=wall, mirror=bool(r.get("mirror")), against=wall)
        else:
            sx, sy = r.get("size", [0.5, 0.5])
            cx, cy = self._xy(oid, r, sx, sy, chain + (oid,))
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
            o = Obj(oid, desc, cx - sx / 2, cy - sy / 2, cx + sx / 2, cy + sy / 2, z0, z1, against=snap,
                    solid=bool(r.get("solid", True)) and z1 - z0 > FLAT)
        self.objects[oid] = o
        return o

    def _xy(self, oid: str, r: dict, sx: float, sy: float, chain: tuple) -> tuple[float, float]:
        """Footprint centre from `at`, a relation to another object and/or a corner (`against` is applied after)."""
        if "at" in r:
            return float(r["at"][0]), float(r["at"][1])
        cx, cy = self.w / 2, self.d / 2
        rel = next((k for k in (*REL, "in_front_of", "behind") if k in r), None)
        if rel:
            t = self._resolve(r[rel], chain)
            if rel in ("in_front_of", "behind"):
                if not t.against:
                    raise ValueError(f"'{oid}': '{rel}' needs '{t.id}' to stand against a side or hang on one")
                rel = FRONT[t.against] if rel == "in_front_of" else FRONT[OPPOSITE[t.against]]
            dx, dy = REL[rel]
            gap, align = float(r.get("gap", 0.05)), r.get("align")
            if dx:
                cx = t.x1 + gap + sx / 2 if dx > 0 else t.x0 - gap - sx / 2
                cy = {"N": t.y1 - sy / 2, "S": t.y0 + sy / 2}.get(align, (t.y0 + t.y1) / 2)
            else:
                cy = t.y1 + gap + sy / 2 if dy > 0 else t.y0 - gap - sy / 2
                cx = {"W": t.x0 + sx / 2, "E": t.x1 - sx / 2}.get(align, (t.x0 + t.x1) / 2)
        corner = r.get("corner", "")
        if "W" in corner:
            cx = sx / 2
        if "E" in corner:
            cx = self.w - sx / 2
        if "S" in corner:
            cy = sy / 2
        if "N" in corner:
            cy = self.d - sy / 2
        return cx, cy

    def _span(self, r: dict, wall: str, chain: tuple) -> tuple[float, float]:
        """[a, b] along a side from `width` + `centred_on` / `from` + `offset` (default: centred on the side)."""
        length = self.w if wall in "NS" else self.d
        width = float(r.get("width", min(1.0, length)))
        if "centred_on" in r:
            t = self._resolve(r["centred_on"], chain)
            c = (t.x0 + t.x1) / 2 if wall in "NS" else (t.y0 + t.y1) / 2
        elif "from" in r:
            off = float(r.get("offset", 0.2))
            c = off + width / 2 if r["from"] in ("W", "S") else length - off - width / 2
        else:
            c = length / 2
        return c - width / 2, c + width / 2

    def point(self, target) -> tuple[float, float]:
        """An object id, an [x, y] pair or a relation dict ({"in_front_of": "mirror", "gap": 0.6}) -> a ground point."""
        if isinstance(target, dict):
            return self._xy("point", target, 0.4, 0.4, ())
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
