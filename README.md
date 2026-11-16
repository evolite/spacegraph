# roomgraph

Rooms as data. Describe a room once, place a virtual camera in it, and get back what is in frame, where it sits
(left / centre / right, low / high, foreground / background), which side of a person faces which frame edge, and what
a mirror shows, with no 3D engine and no dependencies.

It is built for keeping a series of generated images (or a storyboard) consistent: a director writes the room, every
shot names a camera, and whoever writes the image prompt reads the room through roomgraph instead of re-imagining it.

```
$ roomgraph view examples/bedroom.json --shot mirror_from_behind
CAMERA   at (2.6, 1.3, 1.1), facing E (342.5 deg), hfov 55.0 / vfov 76.0, aspect 0.667
WALLS    left edge -> E wall · centre -> E wall · right edge -> S wall
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

## Install

```
pip install git+https://github.com/evolite/roomgraph
```

Python 3.10+, standard library only.

## Commands

| Command | Does |
|-|-|
| `roomgraph view SCENE --shot NAME` | the report above, plus a draft background paragraph; `--json` for the raw data |
| `roomgraph view SCENE --cam X,Y,Z --look TARGET [--subject X,Y --facing camera]` | an ad-hoc camera |
| `roomgraph map SCENE [--shot NAME]` | a top-down ASCII map with the camera's view cone and the subject |
| `roomgraph list SCENE` | rooms, objects, shots |

Flags override the shot: `--room`, `--fov` (horizontal, default 60), `--aspect` (width / height, default 0.667 = a
vertical frame), `--hide id,id` (objects absent from this shot).

## Scene file

```json
{
  "rooms": {
    "bedroom": {
      "size": [4.5, 4.0], "height": 2.6,
      "walls": {"N": "warm white", "E": "warm white", "S": "warm white", "W": "warm white"},
      "floor": "pale oak with a cream rug",
      "objects": [
        {"id": "bed", "at": [2.25, 2.95], "size": [1.6, 2.1], "h": 0.5, "against": "N", "desc": "a low upholstered bed"},
        {"id": "lamp", "on": "nightstand", "h": 0.4, "desc": "a pink glass lamp"},
        {"id": "window", "wall": "E", "span": [2.2, 3.6], "z": [0.5, 2.3], "desc": "a tall window"},
        {"id": "mirror", "wall": "E", "span": [0.5, 1.3], "z": [0, 1.9], "mirror": true, "desc": "a tall floor mirror"}
      ]
    }
  },
  "shots": {
    "foot_of_bed": {"room": "bedroom", "cam": [2.25, 0.5, 0.6], "look": "N", "fov": 60,
                    "subject": {"name": "her", "at": [2.25, 2.8], "facing": "N"}, "hide": []}
  }
}
```

- **Coordinates** are metres: x runs west to east, y south to north, z is height. Walls are N, E, S, W.
- **Objects**: free-standing (`at` = footprint centre, `size`, `h` or `z`, optional `against` to snap to a wall), on a
  wall (`wall`, `span` along it from its west/south end, `z`), or on another object (`on`; at the parent's centre
  unless `at` is given). `mirror: true` makes a wall object reflective. `desc` is the noun phrase used in drafts.
- **Shots**: `cam` [x, y, z], `look` (object id, [x, y], compass or degrees), `fov`, `aspect`, an optional `subject`
  (`at` [x, y] or an object id, `facing`: `camera`, compass, degrees or an object id) and `hide`.

## What the view reports

- **walls**: which wall the left edge, centre and right edge of the frame land on.
- **subject**: front / back / profile, where in the frame, and which frame side her right side is on (front view:
  her right is frame-left).
- **objects**: horizontal third, vertical band, depth band (foreground < 1.5 m < midground < 3.5 m < background), the
  share in frame, which frame edges cut it, and whether it stands behind the subject.
- **mirrors**: the scene reflected through each mirror in frame, so the reflection's contents and sides are exact,
  plus a warning when the camera would see itself.
- **out of frame**: objects behind the camera or off an edge, which a prompt should leave out.

Not modelled: occlusion between objects (only "behind the subject"), lens distortion, non-rectangular rooms.

## Python

```python
import roomgraph as rg
scene = rg.load("examples/bedroom.json")
shot = scene.shots["foot_of_bed"]
room = scene.room(shot["room"], shot.get("hide", ()))
v = rg.view(room, rg.camera_for(room, shot), shot.get("subject"))
print(rg.report(v)); print(rg.draft(v, room.floor, room.walls)); print(rg.topmap(room, rg.camera_for(room, shot), v["subject"]))
```

## License

MIT
