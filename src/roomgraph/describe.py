"""Turn a view() dict into text: a compact report for a prompt-writing agent and a draft background paragraph.

The draft only uses the scene's own `desc` strings and frame placements; it is a starting point to adapt, written
positively (it names what is in frame and never lists what is missing).
"""
from __future__ import annotations

H = {"left": "on the left of the frame", "centre": "in the centre of the frame", "right": "on the right of the frame"}
V = {"low": "low in the frame", "mid": "", "high": "high in the frame"}


def _where(o: dict) -> str:
    bits = [o["h"], o["v"], o["depth"], f"{o['distance']} m"]
    if o.get("cut_by"):
        bits.append("cut by the " + " and ".join(o["cut_by"]))
    if o.get("behind_subject"):
        bits.append("behind the subject")
    return ", ".join(bits)


def report(v: dict) -> str:
    c = v["camera"]
    lines = [f"ROOM     {v['room']}",
             f"CAMERA   at {tuple(c['at'])}, facing {c['heading']} ({c['yaw']} deg), hfov {c['hfov']} / vfov {c['vfov']}, aspect {c['aspect']}",
             f"WALLS    left edge -> {v['walls']['left_edge']} wall · centre -> {v['walls']['centre']} wall · right edge -> {v['walls']['right_edge']} wall"]
    s = v.get("subject")
    if s:
        if s.get("in_frame"):
            pos = f"{s['h']}, {s['depth']}, {s['distance']} m"
            sides = f"; her right side is {s['her_right_side']}" if s.get("her_right_side") else ""
            look = f", looking toward {s['looking_toward']}" if s.get("looking_toward") else ""
            lines.append(f"SUBJECT  {s['name']}: {s['view']} view{look}, {pos}{sides}")
        else:
            lines.append(f"SUBJECT  {s['name']}: NOT IN FRAME ({s.get('where')})")
    inf = sorted([o for o in v["objects"] if o.get("in_frame")], key=lambda o: o["u"][0])
    full = [o for o in inf if o["in_frame"] >= 0.7]
    part = [o for o in inf if o["in_frame"] < 0.7]
    out = [o for o in v["objects"] if not o.get("in_frame")]
    if full:
        lines.append("IN FRAME (left -> right)")
        lines += [f"  {o['id']:<14} {_where(o)}  | {o['desc']}" for o in full]
    if part:
        lines.append("PARTLY IN FRAME")
        lines += [f"  {o['id']:<14} {int(o['in_frame'] * 100)}% · {_where(o)}  | {o['desc']}" for o in part]
    for m in v["mirrors"]:
        lines.append(f"IN THE MIRROR '{m['id']}'" + ("  !! the camera itself is visible in it" if m["camera_visible"] else ""))
        ms = m.get("subject")
        if ms:
            sides = f"; her reflected right side appears {ms['reflected_her_right_side']}" if ms.get("reflected_her_right_side") else ""
            lines.append(f"  subject        {ms['view']} view, {ms['h']} of the frame, {int(ms['share'] * 100)}% visible{sides}")
        lines += [f"  {o['id']:<14} {o['h']}, {o['v']}, {int(o['share'] * 100)}% visible  | {o['desc']}" for o in m["shows"]]
        if not ms and not m["shows"]:
            lines.append("  (only bare wall)")
    if out:
        lines.append("OUT OF FRAME (leave out of the prompt)")
        lines += [f"  {o['id']:<14} {o['where']}" for o in out]
    return "\n".join(lines)


def draft(v: dict, room_floor: str | None = None, walls: dict | None = None) -> str:
    """A background paragraph from the in-frame objects, far to near, children folded into their parent."""
    inf = {o["id"]: o for o in v["objects"] if o.get("in_frame")}
    sents = []
    far = v["walls"]["centre"]
    if walls and walls.get(far):
        sents.append(f"The far wall is {walls[far]}.")
    for o in sorted(inf.values(), key=lambda o: -o["distance"]):
        if o.get("parent") in inf:
            continue
        kids = [inf[k]["desc"] for k in o.get("children", []) if k in inf]
        thing = o["desc"] + (f", with {', '.join(kids[:-1]) + ' and ' if len(kids) > 1 else ''}{kids[-1]} on it," if kids else "")
        place = H[o["h"]]
        if V[o["v"]]:
            place += f", {V[o['v']]}"
        if o.get("cut_by"):
            place += f", running off the {' and '.join(o['cut_by'])}"
        lead = "Behind her, " if o.get("behind_subject") else ""
        sents.append(f"{lead}{thing[0].upper() + thing[1:] if not lead else thing} is {place}.")
    for m in v["mirrors"]:
        shown = [o["desc"] for o in m["shows"]]
        if m.get("subject"):
            shown.insert(0, f"her {m['subject']['view']}, on the {m['subject']['h']} side of the reflection")
        if shown:
            d = m["desc"]
            sents.append(f"{d[0].upper() + d[1:]} reflects {', '.join(shown[:-1]) + ' and ' if len(shown) > 1 else ''}{shown[-1]}.")
    if room_floor:
        sents.append(f"The floor is {room_floor}.")
    return " ".join(sents)
