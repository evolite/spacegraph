"""spacegraph CLI.

  spacegraph view  SCENE (--shot NAME | --cam X,Y,Z --look TARGET) [--space S] [--fov 60] [--aspect 0.667]
                  [--subject X,Y | --subject OBJ] [--facing camera|N|deg|OBJ] [--hide id,id] [--json]
  spacegraph map   SCENE [--space S] [--shot NAME | --cam ... --look ...] [--subject ...]
  spacegraph list  SCENE        spaces, objects and shots

A shot in the scene file: {"space": S, "cam": [x, y, z], "look": target, "fov": 60, "aspect": 0.667,
"subject": {"at": [x, y] | id, "facing": spec, "name": str}, "hide": [ids]}. Command-line flags override it.
"""
from __future__ import annotations

import argparse
import json
import sys

from .describe import draft, report
from .scene import load
from .topmap import topmap
from .view import camera_for, view


def _floats(s: str) -> list[float]:
    return [float(v) for v in s.split(",")]


def _target(s: str):
    try:
        return _floats(s)
    except ValueError:
        try:
            return float(s)
        except ValueError:
            return s


def _shot(sc, a) -> dict:
    shot = dict(sc.shots[a.shot]) if a.shot else {}
    if a.shot and a.shot not in sc.shots:
        sys.exit(f"unknown shot '{a.shot}'")
    if a.space:
        shot["space"] = a.space
    if a.cam:
        shot["cam"] = _floats(a.cam)
    if a.look:
        shot["look"] = _target(a.look)
    if a.fov:
        shot["fov"] = a.fov
    if a.aspect:
        shot["aspect"] = a.aspect
    if a.subject:
        shot["subject"] = {**shot.get("subject", {}), "at": _target(a.subject)}
    if a.facing and "subject" in shot:
        shot["subject"]["facing"] = _target(a.facing)
    if a.hide:
        shot["hide"] = shot.get("hide", []) + a.hide.split(",")
    return shot


def main(argv=None) -> None:
    p = argparse.ArgumentParser(prog="spacegraph", description="Spaces as data; place a camera and see what is in frame.")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("view", "map", "list"):
        s = sub.add_parser(name)
        s.add_argument("scene")
        if name == "list":
            continue
        s.add_argument("--space")
        s.add_argument("--shot")
        s.add_argument("--cam", help="x,y,z in metres")
        s.add_argument("--look", help="object id, x,y point, compass (N, SW) or degrees")
        s.add_argument("--fov", type=float, help="horizontal field of view, degrees (default 60)")
        s.add_argument("--aspect", type=float, help="frame width / height (default 0.667, vertical)")
        s.add_argument("--subject", help="x,y or an object id the subject stands at")
        s.add_argument("--facing", help="camera, compass, degrees or object id (default camera)")
        s.add_argument("--hide", help="comma-separated object ids to leave out of this shot")
        if name == "view":
            s.add_argument("--json", action="store_true", help="the raw view as JSON")
    a = p.parse_args(argv)
    sc = load(a.scene)
    if a.cmd == "list":
        for rn, r in sc.spaces.items():
            print(f"space {rn}: {r['size'][0]} x {r['size'][1]} m, {len(r.get('objects', []))} objects")
            for o in r.get("objects", []):
                print(f"  {o['id']:<14} {o.get('desc', '')}")
        for sn, s in sc.shots.items():
            print(f"shot {sn}: space {s.get('space', '-')}, cam {s.get('cam')}, look {s.get('look')}")
        return
    shot = _shot(sc, a)
    space = sc.space(shot.get("space"), shot.get("hide", ()))
    if "cam" not in shot:
        if a.cmd == "map":
            print(topmap(space))
            return
        sys.exit("need --shot or --cam/--look")
    cam = camera_for(space, shot)
    v = view(space, cam, shot.get("subject"))
    if a.cmd == "map":
        print(topmap(space, cam, v["subject"]))
    elif a.json:
        print(json.dumps(v, indent=2))
    else:
        print(report(v))
        print("\nDRAFT\n  " + draft(v, space.ground, space.sky))


if __name__ == "__main__":
    main()
