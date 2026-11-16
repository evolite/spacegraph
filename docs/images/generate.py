"""Generate the README SVGs in docs/images from examples/bedroom.json. Run from the repo root: python docs/images/generate.py"""
import math, random, sys
from pathlib import Path

sys.path.insert(0, "src")
from spacegraph.scene import load

OUT = Path("docs/images")
OUT.mkdir(parents=True, exist_ok=True)
room = load("examples/bedroom.json").space("bedroom")
O = room.objects

BG0, BG1 = "#0b1020", "#141b33"
INK, MUTED, DIM = "#e8ecf4", "#8d97ad", "#3a4566"
CYAN, PINK, AMBER, RED, VIOLET = "#5eead4", "#f472b6", "#fbbf24", "#f87171", "#a78bfa"
SANS = "Inter, 'Segoe UI', -apple-system, Helvetica, Arial, sans-serif"
MONO = "'JetBrains Mono', 'SFMono-Regular', Menlo, Consolas, monospace"


def defs(extra=""):
    return f"""<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{BG0}"/><stop offset="1" stop-color="{BG1}"/></linearGradient>
  <pattern id="grid" width="24" height="24" patternUnits="userSpaceOnUse"><path d="M24 0H0V24" fill="none" stroke="#ffffff" stroke-opacity="0.04"/></pattern>
  <radialGradient id="cone" cx="0" cy="0.5" r="1"><stop offset="0" stop-color="{CYAN}" stop-opacity="0.45"/><stop offset="1" stop-color="{CYAN}" stop-opacity="0.02"/></radialGradient>
  <filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="4" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
  {extra}
</defs>"""


def frame(w, h, body, extra_defs="", rx=18):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" font-family="{SANS}">
{defs(extra_defs)}
<rect width="{w}" height="{h}" rx="{rx}" fill="url(#bg)"/>
<rect width="{w}" height="{h}" rx="{rx}" fill="url(#grid)"/>
{body}
</svg>
"""


class Plan:
    """Map room metres to SVG pixels (N up)."""

    def __init__(self, ox, oy, s, w=room.w, d=room.d):
        self.ox, self.oy, self.s, self.w, self.d = ox, oy, s, w, d

    def p(self, x, y):
        return self.ox + x * self.s, self.oy + (self.d - y) * self.s

    def rect(self, x0, y0, x1, y1, **kw):
        ax, ay = self.p(x0, y1)
        attrs = " ".join(f'{k.replace("_", "-")}="{v}"' for k, v in kw.items())
        return f'<rect x="{ax:.1f}" y="{ay:.1f}" width="{(x1-x0)*self.s:.1f}" height="{(y1-y0)*self.s:.1f}" {attrs}/>'

    def walls(self, stroke=INK, width=4, door=True, clip_id=None):
        x0, y0 = self.p(0, self.d)
        out = [f'<rect x="{x0}" y="{y0}" width="{self.w*self.s}" height="{self.d*self.s}" fill="#ffffff" fill-opacity="0.025" stroke="{stroke}" stroke-width="{width}" rx="2"/>']
        if clip_id:
            out.append(f'<clipPath id="{clip_id}"><rect x="{x0}" y="{y0}" width="{self.w*self.s}" height="{self.d*self.s}"/></clipPath>')
        return "\n".join(out)

    def cone(self, cam, yaw, fov, length, color=CYAN, clip=None, op=0.22, lines=True):
        cx, cy = self.p(*cam)
        pts = []
        for a in (yaw + fov / 2, yaw - fov / 2):
            r = math.radians(a)
            pts.append(self.p(cam[0] + length * math.cos(r), cam[1] + length * math.sin(r)))
        poly = f"{cx:.1f},{cy:.1f} " + " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        c = f' clip-path="url(#{clip})"' if clip else ""
        out = [f'<g{c}><polygon points="{poly}" fill="{color}" fill-opacity="{op}"/>']
        if lines:
            for x, y in pts:
                out.append(f'<line x1="{cx:.1f}" y1="{cy:.1f}" x2="{x:.1f}" y2="{y:.1f}" stroke="{color}" stroke-width="1.5" stroke-dasharray="5 4" stroke-opacity="0.8"/>')
        out.append("</g>")
        return "\n".join(out)

    def camera(self, cam, yaw, color=CYAN, label=None):
        cx, cy = self.p(*cam)
        r = math.radians(yaw)
        dx, dy = math.cos(r), -math.sin(r)
        tip = (cx + dx * 16, cy + dy * 16)
        out = [f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="9" fill="{BG0}" stroke="{color}" stroke-width="2.5" filter="url(#glow)"/>',
               f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="3.5" fill="{color}"/>',
               f'<line x1="{cx:.1f}" y1="{cy:.1f}" x2="{tip[0]:.1f}" y2="{tip[1]:.1f}" stroke="{color}" stroke-width="2.5" stroke-linecap="round"/>']
        if label:
            out.append(f'<text x="{cx:.1f}" y="{cy+26:.1f}" fill="{color}" font-size="12" font-weight="600" text-anchor="middle">{label}</text>')
        return "\n".join(out)


FURN = {
    "bed": ("#c7cbd6", "#e8ecf4"), "cushions": (PINK, PINK), "nightstand": ("#8b5e3c", "#b07a50"),
    "lamp": (PINK, "#fbcfe8"), "bottle": ("#fda4af", "#fecdd3"), "bench": (PINK, "#f9a8d4"),
    "rail": ("#475569", "#94a3b8"),
}


def furniture(pl, state=None, labels=True, fs=12):
    """state: id -> 'in' | 'part' | 'out' recolours by visibility."""
    out = []
    order = ["rail", "bed", "bench", "nightstand", "cushions", "lamp", "bottle"]
    for oid in order:
        o = O[oid]
        fill, stroke = FURN[oid]
        if state:
            st = state.get(oid, "out")
            fill, stroke, op = {"in": (CYAN, CYAN, 0.28), "part": (AMBER, AMBER, 0.28), "out": (DIM, "#56618a", 0.35)}[st]
        else:
            op = 0.85 if oid not in ("bed",) else 0.55
        out.append(pl.rect(o.x0, o.y0, o.x1, o.y1, fill=fill, fill_opacity=op, stroke=stroke, stroke_width=1.5, rx=3))
    for oid, col in (("print", PINK), ("window", "#7dd3fc"), ("mirror", VIOLET), ("door", AMBER)):
        o = O[oid]
        if state:
            col = {"in": CYAN, "part": AMBER, "out": "#56618a"}[state.get(oid, "out")]
        if o.wall in ("E", "W"):
            x = 0 if o.wall == "W" else pl.w
            a, b = pl.p(x, o.y0), pl.p(x, o.y1)
        else:
            y = 0 if o.wall == "S" else pl.d
            a, b = pl.p(o.x0, y), pl.p(o.x1, y)
        out.append(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" stroke="{col}" stroke-width="7" stroke-linecap="round"/>')
    if labels:
        lab = {"bed": (2.25, 2.75), "bench": (2.25, 1.65), "rail": (0.2, 2.0), "nightstand": (1.12, 3.35),
               "window": (4.3, 2.9), "mirror": (4.3, 0.9), "door": (3.65, -0.28), "print": (2.25, 4.15)}
        for oid, (x, y) in lab.items():
            px, py = pl.p(x, y)
            anchor = "end" if oid in ("window", "mirror") else "middle"
            rot = f' transform="rotate(-90 {px:.1f} {py:.1f})"' if oid == "rail" else ""
            col = INK if not state else {"in": CYAN, "part": AMBER, "out": MUTED}[state.get(oid, "out")]
            out.append(f'<text x="{px:.1f}" y="{py+4:.1f}" fill="{col}" font-size="{fs}" font-weight="600" text-anchor="{anchor}"{rot}>{oid}</text>')
    return "\n".join(out)


SHOTS = {
    "doorway_wide": ((3.6, 0.3), 117.0, 70),
    "foot_of_bed": ((2.25, 0.5), 90.0, 60),
    "rail_side": ((0.9, 2.6), 0.0, 65),
    "mirror_from_behind": ((2.6, 1.3), 342.5, 55),
}


def hero():
    W, H = 1280, 440
    pl = Plan(800, 52, 78)
    b = [pl.walls(clip_id="roomclip")]
    cols = [CYAN, PINK, AMBER, VIOLET]
    for (name, (cam, yaw, fov)), c in zip(SHOTS.items(), cols):
        b.append(pl.cone(cam, yaw, fov, 6, color=c, clip="roomclip", op=0.13, lines=False))
    b.append(furniture(pl, labels=False))
    for (name, (cam, yaw, fov)), c in zip(SHOTS.items(), cols):
        b.append(pl.camera(cam, yaw, color=c))
    b.append(f"""
<text x="80" y="150" fill="{INK}" font-size="72" font-weight="800" letter-spacing="-2">space<tspan fill="{CYAN}">graph</tspan></text>
<text x="84" y="196" fill="{MUTED}" font-size="24" font-weight="500">Spatial memory for AI agents.</text>
<text x="84" y="262" fill="{INK}" font-size="19">Describe a place once.</text>
<text x="84" y="290" fill="{INK}" font-size="19">See it right from <tspan fill="{CYAN}" font-weight="700">every angle</tspan>, for <tspan fill="{PINK}" font-weight="700">every agent</tspan>.</text>
<g font-family="{MONO}" font-size="13" font-weight="600">
  <rect x="84" y="336" width="150" height="30" rx="15" fill="{CYAN}" fill-opacity="0.12" stroke="{CYAN}" stroke-opacity="0.5"/>
  <text x="159" y="356" fill="{CYAN}" text-anchor="middle">zero dependencies</text>
  <rect x="246" y="336" width="104" height="30" rx="15" fill="{PINK}" fill-opacity="0.12" stroke="{PINK}" stroke-opacity="0.5"/>
  <text x="298" y="356" fill="{PINK}" text-anchor="middle">no GPU</text>
  <rect x="362" y="336" width="124" height="30" rx="15" fill="{AMBER}" fill-opacity="0.12" stroke="{AMBER}" stroke-opacity="0.5"/>
  <text x="424" y="356" fill="{AMBER}" text-anchor="middle">python 3.10+</text>
</g>
<text x="975" y="410" fill="{MUTED}" font-size="13" text-anchor="middle">one bedroom · four cameras · one truth</text>
""")
    (OUT / "hero.svg").write_text(frame(W, H, "\n".join(b)))


def mini_room(x, y, s, seed, bad):
    """A tiny room thumbnail; bad=True scrambles the layout."""
    rnd = random.Random(seed)
    w, d = 4.5 * s, 4.0 * s
    out = [f'<g transform="translate({x},{y})">',
           f'<rect width="{w:.1f}" height="{d:.1f}" rx="3" fill="#ffffff" fill-opacity="0.03" stroke="{RED if bad else CYAN}" stroke-opacity="0.7" stroke-width="2"/>']
    if bad:
        side = rnd.choice(["N", "S"])
        bx = rnd.uniform(0.3, 2.6) * s
        by = 0 if side == "N" else d - 2.1 * s
        out.append(f'<rect x="{bx:.1f}" y="{by:.1f}" width="{1.6*s:.1f}" height="{2.1*s:.1f}" rx="2" fill="#c7cbd6" fill-opacity="0.5"/>')
        nx = bx - 0.55 * s if rnd.random() < 0.5 else bx + 1.7 * s
        ny = by if side == "N" else d - 0.4 * s
        out.append(f'<rect x="{nx:.1f}" y="{ny:.1f}" width="{0.45*s:.1f}" height="{0.4*s:.1f}" rx="1" fill="#b07a50"/>')
        wall = rnd.choice(["E", "W", "S", "N"])
        pos = rnd.uniform(0.15, 0.6)
        if wall in "EW":
            wx = w if wall == "E" else 0
            out.append(f'<line x1="{wx:.1f}" y1="{pos*d:.1f}" x2="{wx:.1f}" y2="{(pos+0.35)*d:.1f}" stroke="#7dd3fc" stroke-width="5"/>')
        else:
            wy = 0 if wall == "N" else d
            out.append(f'<line x1="{pos*w:.1f}" y1="{wy:.1f}" x2="{(pos+0.3)*w:.1f}" y2="{wy:.1f}" stroke="#7dd3fc" stroke-width="5"/>')
        if rnd.random() < 0.6:
            mw = rnd.choice(["E", "W"])
            mx = w if mw == "E" else 0
            my = rnd.uniform(0.1, 0.7) * d
            out.append(f'<line x1="{mx:.1f}" y1="{my:.1f}" x2="{mx:.1f}" y2="{my+0.2*d:.1f}" stroke="{VIOLET}" stroke-width="5"/>')
    out.append("</g>")
    return "\n".join(out)


def drift():
    W, H = 1280, 400
    b = [f'<text x="60" y="62" fill="{RED}" font-size="15" font-weight="700" letter-spacing="2">WITHOUT</text>',
         f'<text x="60" y="90" fill="{INK}" font-size="22" font-weight="700">Twelve shots, twelve bedrooms.</text>']
    s = 19
    for i in range(12):
        r, c = divmod(i, 6)
        x, y = 60 + c * 98, 120 + r * 120
        b.append(mini_room(x, y, s, seed=i * 7 + 3, bad=True))
        b.append(f'<text x="{x + 2.25*s:.0f}" y="{y + 4*s + 18:.0f}" fill="{MUTED}" font-size="11" font-family="{MONO}" text-anchor="middle">shot {i+1:02d}</text>')
    b.append(f'''<g transform="translate(660,215)">
<path d="M0 0 H70" stroke="{CYAN}" stroke-width="3" stroke-linecap="round"/>
<path d="M60 -10 L74 0 L60 10" fill="none" stroke="{CYAN}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
</g>''')
    b.append(f'<text x="790" y="62" fill="{CYAN}" font-size="15" font-weight="700" letter-spacing="2">WITH SPACEGRAPH</text>')
    b.append(f'<text x="790" y="90" fill="{INK}" font-size="22" font-weight="700">One bedroom, every angle.</text>')
    pl = Plan(800, 120, 58)
    b.append(pl.walls(clip_id="dclip"))
    cols = [CYAN, PINK, AMBER, VIOLET]
    for (cam, yaw, fov), c in zip(SHOTS.values(), cols):
        b.append(pl.cone(cam, yaw, fov, 6, color=c, clip="dclip", op=0.12, lines=False))
    b.append(furniture(pl, labels=False))
    for (cam, yaw, fov), c in zip(SHOTS.values(), cols):
        b.append(pl.camera(cam, yaw, color=c))
    lx = 1085
    for i, (name, c) in enumerate(zip(SHOTS, cols)):
        y = 150 + i * 34
        b.append(f'<circle cx="{lx}" cy="{y}" r="6" fill="{c}"/><text x="{lx+16}" y="{y+5}" fill="{INK}" font-size="13" font-family="{MONO}">{name}</text>')
    b.append(f'<text x="{lx}" y="{150+4*34+14}" fill="{MUTED}" font-size="12"><tspan x="{lx}">the window never moves.</tspan><tspan x="{lx}" dy="18">the nightstand stays west.</tspan></text>')
    (OUT / "drift.svg").write_text(frame(W, H, "\n".join(b)))


def view():
    W, H = 1280, 560
    pl = Plan(70, 104, 92)
    state = {"bench": "in", "bed": "in", "nightstand": "in", "lamp": "in", "bottle": "in", "cushions": "in",
             "print": "in", "rail": "part", "window": "out", "mirror": "out", "door": "out"}
    cam, yaw, fov = SHOTS["doorway_wide"]
    b = [f'<text x="70" y="62" fill="{INK}" font-size="22" font-weight="700">Point a camera. Ask what it sees.</text>',
         pl.walls(clip_id="vclip"), pl.cone(cam, yaw, fov, 7, clip="vclip", op=0.16), furniture(pl, state=state, fs=13)]
    sx, sy = pl.p(0.75, 1.9)
    r = math.radians(330.7)
    b.append(f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="11" fill="{PINK}" filter="url(#glow)"/>'
             f'<line x1="{sx:.1f}" y1="{sy:.1f}" x2="{sx+22*math.cos(r):.1f}" y2="{sy-22*math.sin(r):.1f}" stroke="{PINK}" stroke-width="3" stroke-linecap="round"/>'
             f'<text x="{sx+16:.1f}" y="{sy-12:.1f}" fill="{PINK}" font-size="13" font-weight="700">her</text>')
    b.append(pl.camera(cam, yaw, label="camera"))
    ly = 110 + 4 * 92 + 40
    for i, (lab, c) in enumerate((("in frame", CYAN), ("partly in frame", AMBER), ("out of frame", "#56618a"))):
        x = 70 + i * 150
        b.append(f'<rect x="{x}" y="{ly-10}" width="14" height="14" rx="3" fill="{c}" fill-opacity="0.6"/><text x="{x+22}" y="{ly+2}" fill="{MUTED}" font-size="12">{lab}</text>')
    px, py, pw, ph = 560, 40, 680, 480
    b.append(f'<rect x="{px}" y="{py}" width="{pw}" height="{ph}" rx="14" fill="#060914" stroke="#ffffff" stroke-opacity="0.08"/>')
    for i, c in enumerate(("#ff5f57", "#febc2e", "#28c840")):
        b.append(f'<circle cx="{px+22+i*18}" cy="{py+20}" r="5.5" fill="{c}"/>')
    lines = [
        (CYAN, "$ ", MUTED, "spacegraph view bedroom.json --shot doorway_wide"),
        (None, "", None, ""),
        (MUTED, "SPACE    ", INK, "bedroom"),
        (MUTED, "CAMERA   ", INK, "at (3.6, 0.3, 1.5), facing NW, hfov 70"),
        (MUTED, "SUBJECT  ", PINK, "her: front view, left, midground, 2.59 m"),
        (None, "", MUTED, "         her right side is frame-left"),
        (None, "", None, ""),
        (CYAN, "IN FRAME (left → right)", None, ""),
        (None, "", INK, "  bench       left, low, foreground"),
        (None, "", INK, "  bed         centre, low, midground"),
        (None, "", INK, "  nightstand  centre, mid, background"),
                (None, "", INK, "  print       centre, mid, background"),
        (AMBER, "PARTLY IN FRAME", None, ""),
        (None, "", INK, "  rail        34% · cut by the left edge"),
        ("#7d89a8", "OUT OF FRAME (leave out of the prompt)", None, ""),
        (None, "", MUTED, "  window      off the right edge"),
        (None, "", MUTED, "  mirror      off the right edge"),
        (None, "", MUTED, "  door        behind the camera"),
        (None, "", None, ""),
        (VIOLET, "DRAFT", None, ""),
        (None, "", INK, "  The far wall is warm white. A walnut nightstand,"),
        (None, "", INK, "  with a pink glass lamp and a bottle of rosé on it,"),
        (None, "", INK, "  is in the centre of the frame. …"),
    ]
    y = py + 54
    out = [f'<g font-family="{MONO}" font-size="14">']
    for c1, t1, c2, t2 in lines:
        if t1 or t2:
            out.append(f'<text x="{px+26}" y="{y}" xml:space="preserve">'
                       + (f'<tspan fill="{c1}" font-weight="700">{t1}</tspan>' if t1 else "")
                       + (f'<tspan fill="{c2}">{t2}</tspan>' if t2 else "") + "</text>")
        y += 19.5
    out.append("</g>")
    b.extend(out)
    (OUT / "view.svg").write_text(frame(W, H, "\n".join(b)))


def mirror():
    W, H = 1280, 380
    b = [f'<text x="70" y="70" fill="{VIOLET}" font-size="15" font-weight="700" letter-spacing="2">MIRRORS, SOLVED</text>',
         f'<text x="70" y="104" fill="{INK}" font-size="26" font-weight="700">The thing AI imagery fumbles most.</text>',
         f'<text font-size="16" fill="{MUTED}"><tspan x="70" y="150">spacegraph reflects the room through the glass and</tspan>'
         f'<tspan x="70" dy="26">reports exactly what the mirror shows: which side</tspan>'
         f'<tspan x="70" dy="26">of her appears where, and what else the</tspan>'
         f'<tspan x="70" dy="26">glass picks up behind her.</tspan></text>',
         f'<g font-family="{MONO}" font-size="13"><rect x="70" y="270" width="470" height="80" rx="10" fill="#060914" stroke="#ffffff" stroke-opacity="0.08"/>'
         f'<text x="88" y="294" fill="{VIOLET}" font-weight="700">IN THE MIRROR \'mirror\'</text>'
         f'<text x="88" y="316" fill="{INK}" xml:space="preserve">subject  front view, reflected right → frame-right</text>'
         f'<text x="88" y="338" fill="{INK}" xml:space="preserve">rail     left, mid, 44% visible</text></g>']
    mx, top, bot = 1000, 60, 320
    b.append(f'<rect x="{mx}" y="{top}" width="230" height="{bot-top}" fill="{VIOLET}" fill-opacity="0.05"/>')
    b.append(f'<text x="{mx+115}" y="{bot+28}" fill="{VIOLET}" fill-opacity="0.8" font-size="12" text-anchor="middle">the reflected room</text>')
    b.append(f'<text x="{(620+mx)/2:.0f}" y="{bot+28}" fill="{MUTED}" font-size="12" text-anchor="middle">the real room</text>')
    b.append(f'<line x1="{mx}" y1="{top}" x2="{mx}" y2="{bot}" stroke="{VIOLET}" stroke-width="6" stroke-linecap="round"/>')
    cam = (800, 270)
    her = (890, 160)
    vher = (2 * mx - her[0], her[1])
    def hit(a, v):
        t = (mx - a[0]) / (v[0] - a[0])
        return (mx, a[1] + t * (v[1] - a[1]))
    h1 = hit(cam, vher)
    b.append(f'<path d="M{cam[0]} {cam[1]} L{her[0]} {her[1]}" stroke="{CYAN}" stroke-width="2" stroke-dasharray="6 5" opacity="0.7"/>')
    b.append(f'<path d="M{cam[0]} {cam[1]} L{h1[0]:.1f} {h1[1]:.1f} L{her[0]} {her[1]}" fill="none" stroke="{PINK}" stroke-width="2.5"/>')
    b.append(f'<path d="M{h1[0]:.1f} {h1[1]:.1f} L{vher[0]} {vher[1]}" stroke="{PINK}" stroke-width="2" stroke-dasharray="4 5" opacity="0.6"/>')
    for (x, y), op, lab in ((her, 1, "her"), (vher, 0.45, "her, reflected")):
        b.append(f'<circle cx="{x}" cy="{y}" r="13" fill="{PINK}" fill-opacity="{op}" filter="url(#glow)"/>')
        b.append(f'<text x="{x}" y="{y-24}" fill="{PINK}" fill-opacity="{max(op,0.7)}" font-size="13" font-weight="600" text-anchor="middle">{lab}</text>')
    b.append(f'<line x1="{her[0]}" y1="{her[1]}" x2="{her[0]+26}" y2="{her[1]}" stroke="{PINK}" stroke-width="3" stroke-linecap="round"/>')
    b.append(f'<line x1="{vher[0]}" y1="{vher[1]}" x2="{vher[0]-26}" y2="{vher[1]}" stroke="{PINK}" stroke-opacity="0.5" stroke-width="3" stroke-linecap="round"/>')
    b.append(f'<circle cx="{cam[0]}" cy="{cam[1]}" r="10" fill="{BG0}" stroke="{CYAN}" stroke-width="2.5" filter="url(#glow)"/><circle cx="{cam[0]}" cy="{cam[1]}" r="4" fill="{CYAN}"/>')
    b.append(f'<text x="{cam[0]}" y="{cam[1]+30}" fill="{CYAN}" font-size="13" font-weight="600" text-anchor="middle">camera</text>')
    b.append(f'<text x="{mx}" y="{top-14}" fill="{VIOLET}" font-size="13" font-weight="700" text-anchor="middle">mirror</text>')
    (OUT / "mirror.svg").write_text(frame(W, H, "\n".join(b)))


def pipeline():
    W, H = 1280, 470

    def card(x, y, w, h, color, kicker, title, lines, mono=False):
        out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="16" fill="#ffffff" fill-opacity="0.035" stroke="{color}" stroke-opacity="0.55" stroke-width="1.5"/>',
               f'<rect x="{x+18}" y="{y}" width="{w-36}" height="4" rx="2" fill="{color}"/>',
               f'<text x="{x+22}" y="{y+38}" fill="{color}" font-size="12" font-weight="700" letter-spacing="2">{kicker}</text>',
               f'<text x="{x+22}" y="{y+66}" fill="{INK}" font-size="20" font-weight="700">{title}</text>']
        ff = f' font-family="{MONO}"' if mono else ""
        for i, (c, t) in enumerate(lines):
            out.append(f'<text x="{x+22}" y="{y+100+i*22}" fill="{c}" font-size="13"{ff} xml:space="preserve">{t}</text>')
        return "\n".join(out)

    def arrow(x1, y1, x2, y2, c=MUTED):
        return (f'<line x1="{x1}" y1="{y1}" x2="{x2-8}" y2="{y2}" stroke="{c}" stroke-width="2.5" stroke-dasharray="6 6"/>'
                f'<path d="M{x2-12} {y2-8} L{x2} {y2} L{x2-12} {y2+8}" fill="none" stroke="{c}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>')

    b = [f'<text x="640" y="56" fill="{INK}" font-size="24" font-weight="700" text-anchor="middle">One shared world. Every agent in agreement.</text>']
    b.append(card(40, 100, 360, 320, PINK, "01 · DIRECTOR AGENT", "Writes the world once", [
        (MUTED, '{"id": "nightstand",'), (INK, ' "west_of": "bed",'), (INK, ' "against": "N"}'), (MUTED, ""),
        (MUTED, '{"id": "mirror",'), (INK, ' "wall": "E", "mirror": true}'), (MUTED, ""),
        (CYAN, "✓ impossible rooms rejected"),
    ], mono=True))
    b.append(arrow(410, 260, 460, 260, PINK))
    for i, (c, shot) in enumerate(((CYAN, "doorway_wide"), (AMBER, "foot_of_bed"), (VIOLET, "mirror_from_behind"))):
        y = 110 + i * 104
        b.append(f'<rect x="470" y="{y}" width="340" height="88" rx="14" fill="#ffffff" fill-opacity="0.035" stroke="{c}" stroke-opacity="0.55" stroke-width="1.5"/>')
        b.append(f'<circle cx="502" cy="{y+44}" r="10" fill="{BG0}" stroke="{c}" stroke-width="2.5"/><circle cx="502" cy="{y+44}" r="4" fill="{c}"/>')
        b.append(f'<text x="526" y="{y+38}" fill="{c}" font-size="12" font-weight="700" letter-spacing="2">02 · SCENE AGENT</text>')
        b.append(f'<text x="526" y="{y+62}" fill="{INK}" font-size="14" font-family="{MONO}">view --shot {shot}</text>')
    b.append(arrow(820, 260, 870, 260, CYAN))
    b.append(card(880, 100, 360, 320, AMBER, "03 · REVIEW PASS", "Catches drift", [
        (MUTED, "$ spacegraph check … --text @prompt"), (MUTED, ""),
        (RED, "WARN 'window' is named but"), (RED, "     out of frame: off the right edge"),
        (RED, "WARN 'print' is in frame but the"), (RED, "     text never mentions it"), (MUTED, ""),
        (AMBER, "exit 1 → fix before the render"),
    ], mono=True))
    (OUT / "pipeline.svg").write_text(frame(W, H, "\n".join(b)))


def tiles():
    W, H = 1280, 300
    items = [
        (CYAN, "RELATIONS", "not coordinates", ['"west_of": "bed"', '"in_front_of": "bed"', '"on": "nightstand"']),
        (PINK, "PLAIN LANGUAGE", "or JSON", ["left, low, foreground", "her right side is", "frame-left"]),
        (AMBER, "DRIFT CHECK", "before the render", ["WARN named but", "out of frame", "exit 1"]),
        (RED, "NO IMPOSSIBLE", "spaces or shots", ["camera inside the bed?", "bench inside the rail?", "→ rejected"]),
    ]
    b = []
    w = 280
    for i, (c, k, sub, lines) in enumerate(items):
        x = 40 + i * (w + 20)
        b.append(f'<rect x="{x}" y="40" width="{w}" height="220" rx="16" fill="#ffffff" fill-opacity="0.035" stroke="{c}" stroke-opacity="0.45"/>')
        b.append(f'<text x="{x+24}" y="82" fill="{c}" font-size="17" font-weight="800" letter-spacing="1.5">{k}</text>')
        b.append(f'<text x="{x+24}" y="106" fill="{MUTED}" font-size="14">{sub}</text>')
        b.append(f'<rect x="{x+20}" y="128" width="{w-40}" height="108" rx="10" fill="#060914"/>')
        for j, t in enumerate(lines):
            b.append(f'<text x="{x+36}" y="{160+j*26}" fill="{INK}" font-size="14" font-family="{MONO}">{t}</text>')
    (OUT / "features.svg").write_text(frame(W, H, "\n".join(b)))


hero(); drift(); view(); mirror(); pipeline(); tiles()
print(sorted(p.name for p in OUT.glob("*.svg")))
