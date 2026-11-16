"""Check a prompt's wording against a view: warnings for prose that drifted from the shot.

`check(view, text, space)` returns a list of warning strings (empty = consistent):
  - an object named in the text that is out of frame (and not shown in a mirror in frame);
  - a sentence placing a single named object on the left/right when the view has it on the other side;
  - the subject's view contradicted ("facing the camera" in a back view, "in profile" in a front view, ...);
  - her right/left side placed on the wrong frame side ("her right hand on the left of the frame" in a front view is right);
  - a mirror in frame that the text never mentions;
  - an object put "in the corner" that stands mid-wall, or "in the middle of the wall" when it stands near a corner;
  - furniture in frame (not a prop on something) that the text never mentions: half or more of it in frame, or a tenth
    of it in the foreground. Leaving it out lets the image model invent something else in its place.

Phrases like "captured from the doorway" or "light from the window" name a source, not something in frame, and are
skipped. Object names: an object's `names` list in the scene file if given, else its id and the head noun of its `desc`
("a walnut nightstand" -> nightstand). Phrases of in-frame objects (their full desc) are masked before matching, so
"a pink glass lamp" does not count as a mention of a glass. Heuristic by design: it warns, it never rewrites.
"""
from __future__ import annotations

import re

from .scene import Space

STOP = re.compile(r"\s+(?:with|in|of|on|from|and|that|which|hung|filled|ringed|crowded)\s+|,")
BODY = r"(?:hand|arm|leg|foot|knee|thigh|shoulder|hip|side|eye|ear|breast|cheek|elbow|wrist|palm|ankle|buttock|fingers?)"
SIDE_WORDS = re.compile(r"\b(?:on|to|at|in)\s+the\s+(left|right)\b|\bframe[- ](left|right)\b|\b(left|right)\s+(?:of|side of|edge of|third of)\s+the\s+(?:frame|image|picture|shot)\b|\b(left|right)\s+edge\b|\bthe\s+(left|right)(?:-hand)?\s+(?:wall|side)\b", re.I)
BODY_SIDE = re.compile(rf"\b(?:her|his|their)\s+(left|right)\s+{BODY}s?\b|\b(left|right)\s+{BODY}s?\b", re.I)
FRONT = re.compile(r"\b(?:facing|faces|turned toward|turns toward) the (?:camera|lens|viewer)\b", re.I)
BACK = re.compile(r"\b(?:back to the (?:camera|lens|viewer)|back is to the (?:camera|lens)|seen from behind|from behind her)\b", re.I)
PROFILE = re.compile(r"\bin profile\b", re.I)
FROM = re.compile(r"\bfrom\s+(?:near\s+|beside\s+|behind\s+|outside\s+|inside\s+|across\s+)?(?:the|a|an)\s+(?:(?!toward|towards|to|at|into|onto|across|with|and|looking|over|on)[\w-]+\s+){0,3}[\w-]+")


def names_for(space: Space, oid: str) -> list[str]:
    raw = space._raw.get(oid, {})
    if raw.get("names"):
        return [n.lower() for n in raw["names"]]
    desc = space.objects[oid].desc.lower()
    head = STOP.split(desc, maxsplit=1)[0].split()
    out = {oid.lower().replace("_", " ")}
    if head:
        out.add(head[-1])
    return sorted(out, key=len, reverse=True)


def _found(name: str, text: str, as_object: bool = False) -> bool:
    """A mention of name; as_object skips light-source uses ("lamp light", "window glow")."""
    tail = r"(?!\s*(?:light|lit|glow|shine))" if as_object else ""
    return re.search(rf"\b{re.escape(name)}(?:e?s)?\b{tail}", text) is not None


def _sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip()]


def check(v: dict, text: str, space: Space) -> list[str]:
    warns = []
    low = text.lower()
    objs = {o["id"]: o for o in v["objects"]}
    in_frame = {k for k, o in objs.items() if o.get("in_frame")}
    in_mirror = {o["id"] for m in v["mirrors"] for o in m["shows"]}
    masked = low
    for k in in_frame:  # an in-frame object's own phrase can't be a mention of something else
        masked = masked.replace(space.objects[k].desc.lower(), " ")
    masked = FROM.sub(" ", masked)  # "captured from the doorway", "light from the window": a source, not something in frame
    for k, o in objs.items():
        if k in in_frame or k in in_mirror:
            continue
        hit = next((n for n in names_for(space, k) if _found(n, masked, as_object=True)), None)
        if hit:
            warns.append(f"'{hit}' ({k}) is named but out of frame: {o.get('where')}")
    for s in _sentences(text):
        sl = s.lower()
        named = [k for k in in_frame if any(_found(n, sl) for n in names_for(space, k))]
        bare = BODY_SIDE.sub(" ", sl)
        sides = {next(g for g in m.groups() if g).lower() for m in SIDE_WORDS.finditer(bare)}
        if len(named) == 1 and len(sides) == 1:
            k, side = named[0], sides.pop()
            if objs[k]["h"] in ("left", "right") and objs[k]["h"] != side:
                warns.append(f"{k} is placed on the {side} in \"{s.strip()[:80]}\", but the view has it {objs[k]['h']}")
    subj = v.get("subject")
    if subj and subj.get("in_frame"):
        view = subj["view"]
        if view == "back" and FRONT.search(text):
            warns.append(f"the text has her facing the camera, but the view is a back view")
        if view == "front" and BACK.search(text):
            warns.append(f"the text has her back to the camera, but the view is a front view")
        if view != "profile" and PROFILE.search(text):
            warns.append(f"the text has her in profile, but the view is a {view} view")
        right = subj.get("her_right_side")
        if right:
            for s in _sentences(text):
                for m in re.finditer(rf"\bher\s+(left|right)\s+{BODY}s?\b", s, re.I):
                    rest = s[m.end():m.end() + 60]
                    sm = SIDE_WORDS.search(rest)
                    if not sm:
                        continue
                    claimed = next(g for g in sm.groups() if g).lower()
                    expect = right.split("-")[1] if m.group(1).lower() == "right" else ("left" if right == "frame-right" else "right")
                    if claimed != expect:
                        warns.append(f"her {m.group(1).lower()} side is put on the {claimed} in \"{s.strip()[:80]}\", "
                                     f"but in this {view} view it is frame-{expect}")
    for s in _sentences(text):  # "in the corner" vs. "in the middle of the wall"
        sl = s.lower()
        named = [k for k in in_frame | in_mirror if any(_found(n, sl) for n in names_for(space, k))]
        if len(named) != 1:
            continue
        k, where = named[0], space.placement(named[0])
        if re.search(r"\bcorner\b", sl) and "corner" not in where and "in the corner" not in where:
            warns.append(f"{k} is put in a corner in \"{s.strip()[:80]}\", but it stands {where}")
        if re.search(r"\b(?:middle|centre|center) of the (?:\w+ )?wall\b", sl) and "corner" in where:
            warns.append(f"{k} is put in the middle of a wall in \"{s.strip()[:80]}\", but it stands {where}")
    mirrors = {m["id"] for m in v["mirrors"]}
    for k in sorted(in_frame, key=lambda k: objs[k]["u"][0]):
        o = objs[k]
        if o.get("parent") or k in mirrors or not (o["in_frame"] >= 0.5 or (o["depth"] == "foreground" and o["in_frame"] >= 0.1)):
            continue
        if not any(_found(n, low) for n in names_for(space, k)):
            share = f"{int(o['in_frame'] * 100)}% in frame"
            warns.append(f"'{k}' is in frame ({o['h']}, {o['v']}, {o['depth']}, {share}) but the text never mentions it")
    for m in v["mirrors"]:
        if not any(_found(n, low) for n in names_for(space, m["id"]) + ["mirror", "reflection", "reflected"]):
            what = f"her {m['subject']['view']}" if m.get("subject") else ", ".join(o["id"] for o in m["shows"]) or "bare wall"
            warns.append(f"mirror '{m['id']}' is in frame (it shows {what}) but the text never mentions it")
    return warns
