# View

`spacegraph view` places a camera in a space and reports what is in frame, partly in frame and out of frame. For each object it gives the frame third, height band, depth band and distance. It also reports the subject's orientation, what fills each third and what each mirror shows, and ends with a draft background paragraph.

## Sub-features

- `view-shot` views a named shot from the scene file.
- `view-adhoc` views from `--cam X,Y,Z --look TARGET`, with optional `--subject` and `--facing`.
- `view-shot-json` views a shot passed inline or from `@file`.
- `view-json` prints the raw view as JSON with `--json`.
- `view-mirror` lists what a mirror in frame reflects, under `IN THE MIRROR`.
- `view-outdoor` reports open sides as the backdrop.
- `view-override` lets flags (`--fov`, `--hide`, `--aspect`) override a named shot.

## How to get to it (user POV)

- `spacegraph view SCENE --shot NAME`
- `spacegraph view SCENE --cam X,Y,Z --look TARGET [--subject X,Y] [--facing camera]`
- `spacegraph view SCENE --shot-json '{...}'` or `--shot-json @file`
- Any of the above with `--json`.

## Driving it with sgv

Preconditions:

- Baseline preconditions from the README hold.

- **Named shot.** Run `sgv run "$RUN" view-shot -- spacegraph view examples/bedroom.json --shot doorway_wide`. Exit `0`. `.out` starts with `SPACE    bedroom`. Under `IN FRAME` there is a `bed` row containing `centre, low, midground`. Under `OUT OF FRAME`, `door` reads `behind the camera`. The output ends with a `DRAFT` paragraph.
- **Ad-hoc camera.** Run `sgv run "$RUN" view-adhoc -- spacegraph view examples/bedroom.json --cam 2.25,0.5,1.5 --look N`. Exit `0`. The `CAMERA` line reads `at (2.25, 0.5, 1.5), facing N`, and `bed` is under `IN FRAME`.
- **Shot JSON.** Run `sgv run "$RUN" view-shot-json -- spacegraph view examples/bedroom.json --shot-json '{"space":"bedroom","cam":[2.25,0.5,1.5],"look":"N"}'`. Exit `0`, and the `CAMERA` line matches the ad-hoc step.
- **JSON output.** Run `sgv run "$RUN" view-json -- spacegraph view examples/bedroom.json --shot doorway_wide --json`. Exit `0`, and `.out` parses as JSON (`python3 -m json.tool "$RUN/view-json.out"`).
- **Mirror.** Run `sgv run "$RUN" view-mirror -- spacegraph view examples/bedroom.json --shot mirror_from_behind`. Exit `0`. `.out` has a section starting `IN THE MIRROR 'mirror'` with a `subject` row reading `front view`, and the `SUBJECT` line reads `back view`.
- **Outdoor.** Run `sgv run "$RUN" view-outdoor -- spacegraph view examples/beach.json --shot towel_seaward`. Exit `0`. The `BOUNDS` line names `E open (the sea`, and `boat` is under `IN FRAME`.
- **Override.** Run `sgv run "$RUN" view-override -- spacegraph view examples/bedroom.json --shot doorway_wide --hide bench`. Exit `0`, and `bench` appears in none of the sections.

## Gotchas

- Facing degrees are compass-style: 0 = east, 90 = north. A `--look` of `N` faces 90 deg.
- `--shot-json` replaces the named shot entirely. Other flags still override it.
- Distances print rounded, so assert on the band words (`foreground`, `midground`, `background`) rather than exact metres unless the change is about distance.
- The subject is always called `her` in reports unless the shot gives a `subject.name`.
