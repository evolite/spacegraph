# spacegraph

Spaces as data. Describe a place once (a bedroom, a street, a beach), place a virtual camera in it, and get back what
is in frame, where it sits (left / centre / right, low / high, foreground / background), which side of a person faces
which frame edge, and what a mirror shows, with no 3D engine and no dependencies.

It is built for keeping a series of generated images (or a storyboard) consistent: a director writes the space once,
every shot names a camera, and whoever writes the image prompt reads the space through spacegraph instead of
re-imagining it.

```
$ spacegraph view examples/bedroom.json --shot mirror_from_behind
SPACE    bedroom
CAMERA   at (2.6, 1.3, 1.1), facing E (342.5 deg), hfov 55.0 / vfov 76.0, aspect 0.667
BOUNDS   left edge -> E wall (warm white) · centre -> E wall (warm white) · right edge -> S wall (warm white)
SUBJECT  her: back view, centre, foreground, 1.0 m; her right side is frame-right
IN FRAME (left -> right)
  mirror         centre, mid, midground, 1.78 m, behind the subject  | a tall arched floor mirror
IN THE MIRROR 'mirror'  !! the camera itself is visible in it
  subject        front view, left of the frame, 100% visible; her reflected right side appears frame-right
  rail           left, mid, 44% visible  | a black metal clothing rail hung with colourful outfits
OUT OF FRAME (leave out of the prompt)
  bed            off the left edge
  nightstand     behind the camera
  ...
DRAFT
  The far wall is warm white. Behind her, a tall arched floor mirror is in the centre of the frame. ...
```

Outdoors (`examples/beach.json`), open sides become the backdrop:

```
$ spacegraph view examples/beach.json --shot towel_seaward
BOUNDS   left edge -> E open (the sea, calm and turquoise, running to the horizon) · centre -> E open (...) · right edge -> S open (rocky headland)
SUBJECT  her: front view, centre, background, 4.0 m; her right side is frame-left
IN FRAME (left -> right)
  boat           centre, mid, background, 28.0 m  | a small white sailing boat
  pier           right, mid, background, 8.0 m, cut by the right edge  | a weathered wooden pier
OUT OF FRAME (leave out of the prompt)
  tower          behind the camera
DRAFT
  In the distance, the sea, calm and turquoise, running to the horizon. Above it is a clear late-afternoon sky. ...
```

## Install

```
pip install git+https://github.com/evolite/spacegraph
```

Python 3.10+, standard library only.

## Commands

| Command | Does |
|-|-|
| `spacegraph view SCENE --shot NAME` | the report above, plus a draft background paragraph; `--json` for the raw data |
| `spacegraph view SCENE --cam X,Y,Z --look TARGET [--subject X,Y --facing camera]` | an ad-hoc camera |
| `spacegraph view SCENE --shot-json '{...}'` (or `@file`) | a shot kept outside the scene file, e.g. in a storyboard |
| `spacegraph check SCENE --shot NAME --text TEXT` (or `@file`, `-` for stdin) | warnings where the prose contradicts the view; exit 1 when there are any |
| `spacegraph map SCENE [--shot NAME]` | a top-down ASCII map (walls `#`, open sides `~`) with the view cone and the subject |
| `spacegraph list SCENE` | spaces, objects, shots |

Flags override the shot: `--space`, `--fov` (horizontal, default 60), `--aspect` (width / height, default 0.667 = a
vertical frame), `--hide id,id` (objects absent from this shot).

## Scene file

```json
{
  "spaces": {
    "bedroom": {
      "size": [4.5, 4.0], "height": 2.6,
      "walls": {"N": "warm white", "E": "warm white", "S": "warm white", "W": "warm white"},
      "ground": "pale oak with a cream rug",
      "objects": [
        {"id": "bed", "at": [2.25, 2.95], "size": [1.6, 2.1], "h": 0.5, "against": "N", "desc": "a low upholstered bed"},
        {"id": "lamp", "on": "nightstand", "h": 0.4, "desc": "a pink glass lamp"},
        {"id": "window", "wall": "E", "span": [2.2, 3.6], "z": [0.5, 2.3], "desc": "a tall window"},
        {"id": "mirror", "wall": "E", "span": [0.5, 1.3], "z": [0, 1.9], "mirror": true, "desc": "a tall floor mirror"}
      ]
    },
    "beach": {
      "size": [30, 20],
      "open": {"E": "the sea to the horizon", "W": "low grassy dunes"},
      "ground": "fine pale sand", "sky": "a clear late-afternoon sky",
      "objects": [{"id": "boat", "at": [45, 12], "size": [6, 2], "h": 3, "desc": "a small white sailing boat"}]
    }
  },
  "shots": {
    "foot_of_bed": {"space": "bedroom", "cam": [2.25, 0.5, 0.6], "look": "N", "fov": 60,
                    "subject": {"name": "her", "at": [2.25, 2.8], "facing": "N"}, "hide": []}
  }
}
```

- **Coordinates** are metres: x runs west to east, y south to north, z is height. A space is the area `size` wide (x)
  and deep (y), with four sides N, E, S, W.
- **Sides**: a side listed in `walls` is solid (the value describes it); any other side is open, and `open` gives the
  backdrop seen beyond it. Indoors set `height` (the ceiling); outdoors leave it out and add `sky`. `ground` describes
  the floor or terrain. Objects may stand outside the area (a boat out at sea, a distant tower).
- **Objects**: free-standing (`at` = footprint centre, `size`, `h` or `z`, optional `against` to snap to a side), on a
  side (`wall`, `span` along it from its west/south end, `z`; a window, a fence, a shop front), or on another object
  (`on`; at the parent's centre unless `at` is given). `mirror: true` makes a side-mounted object reflective. `desc` is
  the noun phrase used in drafts.
- **Shots**: `space`, `cam` [x, y, z], `look` (object id, [x, y], compass or degrees), `fov`, `aspect`, an optional
  `subject` (`at` [x, y] or an object id, `facing`: `camera`, compass, degrees or an object id) and `hide`.

## What the view reports

- **bounds**: which side the left edge, centre and right edge of the frame land on, and whether it is a wall or open.
- **subject**: front / back / profile, where in the frame, and which frame side her right side is on (front view:
  her right is frame-left).
- **objects**: horizontal third, vertical band, depth band (foreground < 1.5 m < midground < 3.5 m < background), the
  share in frame, which frame edges cut it, and whether it stands behind the subject.
- **mirrors**: the scene reflected through each mirror in frame, so the reflection's contents and sides are exact,
  plus a warning when the camera would see itself.
- **out of frame**: objects behind the camera or off an edge, which a prompt should leave out.

## Checking prose against the view

`check` reads a prompt (or any description) against the shot's view and warns, without rewriting anything:

- an object named in the text that is out of frame (unless a mirror in frame shows it);
- a sentence putting a single named object on the left or right when the view has it on the other side;
- the subject's view contradicted ("facing the camera" in a back view, "in profile" in a front view);
- her right or left side put on the wrong frame side;
- a mirror in frame that the text never mentions.

Objects are matched by their `names` list if the scene gives one (`"names": ["window", "curtains"]`), else by their id
and the head noun of `desc`. It is a heuristic net for drift, not a parser: keep the warnings advisory.

Not modelled: occlusion between objects (only "behind the subject"), lens distortion, non-rectangular spaces, terrain
height.

## Python

```python
import spacegraph as sg

scene = sg.load("examples/bedroom.json")
shot = scene.shots["foot_of_bed"]
space = scene.space(shot["space"], shot.get("hide", ()))
cam = sg.camera_for(space, shot)
v = sg.view(space, cam, shot.get("subject"))
print(sg.report(v))
print(sg.draft(v, space.ground, space.sky))
print(sg.topmap(space, cam, v["subject"]))
```

## License

MIT
