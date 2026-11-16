"""A top-down ASCII map of a room (north up), with a shot's camera, its view cone and the subject."""
from __future__ import annotations

import math
import string

from .scene import Room

CELL_X, CELL_Y = 0.125, 0.25  # metres per character (characters are about twice as tall as wide)
ARROW = {0: ">", 1: "^", 2: "<", 3: "v"}


def topmap(room: Room, cam=None, subject: dict | None = None) -> str:
    cols, rows = int(room.w / CELL_X) + 1, int(room.d / CELL_Y) + 1
    grid = [[" "] * (cols + 2) for _ in range(rows + 2)]

    def cell(x, y):
        return min(max(int(round(rows - y / CELL_Y)) + 1, 0), rows + 1), min(max(int(round(x / CELL_X)) + 1, 0), cols + 1)

    for c in range(cols + 2):
        grid[0][c] = grid[rows + 1][c] = "#"
    for r in range(rows + 2):
        grid[r][0] = grid[r][cols + 1] = "#"
    legend = []
    labels = iter(c for c in string.ascii_uppercase + string.ascii_lowercase + string.digits if c != "C")
    for o in room.objects.values():
        if o.parent:
            continue  # sits on another object: listed under it
        ch = next(labels, "?")
        kids = f" (on it: {', '.join(o.children)})" if o.children else ""
        legend.append(f"  {ch}  {o.id}{kids}")
        r0, c0 = cell(o.x0, o.y1)
        r1, c1 = cell(o.x1, o.y0)
        if o.wall:  # drawn on the wall line itself
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
                t += 0.05
                x, y = cam.x + dx * t, cam.y + dy * t
                if not (0 < x < room.w and 0 < y < room.d):
                    break
                r, c = cell(x, y)
                if grid[r][c] == " ":
                    grid[r][c] = ":" if edge == cam.yaw else "."
        r, c = cell(cam.x, cam.y)
        grid[r][c] = "C"
        legend.append(f"  C  camera, facing {round(cam.yaw)} deg (. view edges, : centre line)")
    if subject:
        sx, sy = room.point(subject["at"])
        r, c = cell(sx, sy)
        grid[r][c] = "@"
        if "facing_deg" in subject:
            q = round((subject["facing_deg"] % 360) / 90) % 4
            dr, dc = {0: (0, 1), 1: (-1, 0), 2: (0, -1), 3: (1, 0)}[q]
            if 0 < r + dr <= rows and 0 < c + dc <= cols:
                grid[r + dr][c + dc] = ARROW[q]
        legend.append(f"  @  {subject.get('name', 'subject')} (arrow = facing)")
    head = f"{room.name}  {room.w} x {room.d} m   N up, E right"
    return "\n".join([head] + ["".join(row) for row in grid] + legend)
