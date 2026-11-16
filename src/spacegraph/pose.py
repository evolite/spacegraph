"""A free-text pose read into claims, and where on the body each claim sits, so a view can tell what the camera and
each mirror can actually see of it.

    parse_pose("standing straight, both hands spread her buttocks behind her back, her left hand later on her knee")
    -> [Claim(limb="hand", side="both", location="buttocks", region="back"),
        Claim(limb="hand", side="left", location="knees", region="any")]   (unknown locations are skipped)

A claim is (limb, side, location, region): side is left / right / both, region is the part of the body the location
sits on (front, back, side, any). `visible(region, view)` says whether a front / back / profile view shows it.
Deliberately a small vocabulary: a heuristic net for prompts, not a parser.
"""
from __future__ import annotations

import re
from typing import NamedTuple

# hands and arms: what a pose puts on her body, and what mirrors get wrong ("two fingers" stays part of its hand)
LIMBS = {"hand": "hand", "hands": "hand", "palm": "hand", "palms": "hand", "arm": "arm", "arms": "arm", "elbow": "arm", "elbows": "arm"}
# location phrase -> (canonical location, body region); longest first when matching
LOCATIONS = {
    "behind her back": ("behind her back", "back"), "behind her hips": ("behind her back", "back"),
    "behind her": ("behind her back", "back"), "out of sight": ("behind her back", "back"), "hidden": ("behind her back", "back"),
    "buttocks": ("buttocks", "back"), "buttock": ("buttocks", "back"), "ass": ("buttocks", "back"), "butt": ("buttocks", "back"),
    "cheeks": ("buttocks", "back"), "cheek": ("buttocks", "back"), "lower back": ("buttocks", "back"),
    "hips": ("hips", "side"), "hip": ("hips", "side"), "waist": ("hips", "side"),
    "breasts": ("breasts", "front"), "breast": ("breasts", "front"), "chest": ("breasts", "front"), "nipples": ("breasts", "front"),
    "belly": ("belly", "front"), "stomach": ("belly", "front"),
    "between her thighs": ("between her thighs", "front"), "pussy": ("between her thighs", "front"),
    "clit": ("between her thighs", "front"), "crotch": ("between her thighs", "front"),
    "thighs": ("thighs", "front"), "thigh": ("thighs", "front"),
    "knees": ("knees", "any"), "knee": ("knees", "any"),  # hands on knees show from behind too (arms down at her sides)
    "hair": ("hair", "any"), "head": ("head", "any"), "shoulder": ("shoulders", "any"), "shoulders": ("shoulders", "any"),
}
_LOC_RE = re.compile(r"\b(" + "|".join(sorted(map(re.escape, LOCATIONS), key=len, reverse=True)) + r")\b")
_LIMB_RE = re.compile(r"\b(?:(both|her left|her right|left|right)\s+)?(" + "|".join(LIMBS) + r")\b")
_SPLIT = re.compile(r"[,;]|\band\b(?!\s+(?:spread|spreading|squeez|grip|pull|rub|hold))|\bwhile\b")


class Claim(NamedTuple):
    limb: str
    side: str
    location: str
    region: str


def parse_pose(text: str) -> list[Claim]:
    """Limb + location pairs, clause by clause; a limb takes the location nearest after it, else before it."""
    out: list[Claim] = []
    for clause in _SPLIT.split(text.lower().replace("her face", "")):
        limbs = list(_LIMB_RE.finditer(clause))
        locs = list(_LOC_RE.finditer(clause))
        if not limbs or not locs:
            continue
        for lm in limbs:
            after = [m for m in locs if m.start() > lm.end()]
            loc = after[0] if after else locs[-1]
            if loc.start() < lm.start() and after == [] and any(l.start() > loc.end() and l is not lm for l in limbs):
                continue  # the location before belongs to an earlier limb
            word, limb = lm.group(1) or "", LIMBS[lm.group(2)]
            side = "left" if "left" in word else "right" if "right" in word else "both"
            if side == "both" and lm.group(2) in ("hand", "arm", "elbow", "palm"):
                side = "one"  # singular, side unstated
            location, region = LOCATIONS[loc.group(1)]
            out.append(Claim(limb, side, location, region))
    return out



def visible(region: str, view: str) -> str:
    """'visible', 'hidden' or 'edge-on': can a front / back / profile view of her see this body region?"""
    if region in ("side", "any"):
        return "visible"
    if view == "profile":
        return "edge-on"
    hidden = {"front": "back", "back": "front"}.get(view)
    return "hidden" if region == hidden else "visible"


def same_limb(a: Claim, b: Claim) -> bool:
    """The same limb (and the same side, when both name one)."""
    return a.limb == b.limb and (a.side == b.side or "both" in (a.side, b.side) or "one" in (a.side, b.side))
