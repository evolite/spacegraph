"""A top-down ASCII map of a space (north up), with a shot's camera, its view cone and the subject. Walls are #, open sides ~."""
from __future__ import annotations

import math
import string

from .scene import Space

MAX_COLS = 64
ARROW = {0: ">", 1: "^", 2: "<", 3: "v"}


def topmap(space: Space, cam=None, subject: dict | None = None) -> str:
    CELL_X = max(0.125, space.w / MAX_COLS)
    CELL_Y = CELL_X * 2
    cols, rows = int(space.w / CELL_X) + 1, int(space.d / CELL_Y) + 1
    grid = [[" "] * (cols + 2) for _ in range(rows + 2)]

    def cell(x, y):
        return min(max(int(round(rows - y / CELL_Y)) + 1, 0), rows + 1), min(max(int(round(x / CELL_X)) + 1, 0), cols + 1)

    edge = {s: ("#" if s in space.walls else "~") for s in "NESW"}
    for c in range(cols + 2):
        grid[0][c], grid[rows + 1][c] = edge["N"], edge["S"]
    for r in range(1, rows + 1):
        grid[r][0], grid[r][cols + 1] = edge["W"], edge["E"]
    legend = []
    labels = iter(c for c in string.ascii_uppercase + string.ascii_lowercase + string.digits if c != "C")
    for o in space.objects.values():
        if o.parent:
            continue
        ch = next(labels, "?")
        kids = f" (on it: {', '.join(o.children)})" if o.children else ""
        outside = o.x1 < 0 or o.x0 > space.w or o.y1 < 0 or o.y0 > space.d
        legend.append(f"  {ch}  {o.id}{kids}" + ("  (outside the map)" if outside else ""))
        if outside:
            continue
        r0, c0 = cell(o.x0, o.y1)
        r1, c1 = cell(o.x1, o.y0)
        if o.wall:
            r0, r1 = {"N": (0, 0), "S": (rows + 1, rows + 1)}.get(o.wall, (r0, r1))
            c0, c1 = {"W": (0, 0), "E": (cols + 1, cols + 1)}.get(o.wall, (c0, c1))
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                grid[r][c] = ch
    if cam is not None:
        for edge in (cam.yaw + cam.hfov / 2, cam.yaw - cam.hfov / 2, cam.yaw):
            dx, dy = math.cos(math.radians(edge)), math.sin(math.radians(edge))
            t = 0.0
            while True:
                t += CELL_X / 3
                x, y = cam.x + dx * t, cam.y + dy * t
                if not (0 < x < space.w and 0 < y < space.d):
                    break
                r, c = cell(x, y)
                if grid[r][c] == " ":
                    grid[r][c] = ":" if edge == cam.yaw else "."
        r, c = cell(cam.x, cam.y)
        grid[r][c] = "C"
        legend.append(f"  C  camera, facing {round(cam.yaw)} deg (. view edges, : centre line)")
    if subject:
        sx, sy = space.point(subject["at"])
        r, c = cell(sx, sy)
        grid[r][c] = "@"
        if "facing_deg" in subject:
            q = round((subject["facing_deg"] % 360) / 90) % 4
            dr, dc = {0: (0, 1), 1: (-1, 0), 2: (0, -1), 3: (1, 0)}[q]
            if 0 < r + dr <= rows and 0 < c + dc <= cols:
                grid[r + dr][c + dc] = ARROW[q]
        legend.append(f"  @  {subject.get('name', 'subject')} (arrow = facing)")
    head = f"{space.name}  {space.w} x {space.d} m   N up, E right   # wall  ~ open   1 char = {CELL_X:g} m"
    return "\n".join([head] + ["".join(row) for row in grid] + legend)
