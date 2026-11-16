# Map

`spacegraph map` draws a top-down ASCII map with north up, walls as `#` and open sides as `~`. Each object is drawn as a letter with a legend. When a camera is given, the map adds the camera `C`, its view-cone edges (`.`), its centre line (`:`) and the subject `@`.

## Sub-features

- `map-bare` draws the space alone when no camera is given.
- `map-shot` adds the camera, view cone and subject for a shot.
- `map-outdoor` shows open sides as `~`.

## How to get to it (user POV)

- `spacegraph map SCENE [--space S]`
- `spacegraph map SCENE --shot NAME` or `--cam X,Y,Z --look TARGET`

## Driving it with sgv

Preconditions:

- Baseline preconditions from the README hold.

- **Bare map.** Run `sgv run "$RUN" map-bare -- spacegraph map examples/bedroom.json`. Exit `0`. The first line starts `bedroom  4.5 x 4.0 m   N up`, the legend lists `A  bed (on it: cushions)`, and the grid contains no `C`.
- **With a shot.** Run `sgv run "$RUN" map-shot -- spacegraph map examples/bedroom.json --shot doorway_wide`. Exit `0`. The legend has `C  camera, facing 117 deg` and `@  her`, and the grid contains `C`, `@` and `.` cone marks.
- **Outdoor.** Run `sgv run "$RUN" map-outdoor -- spacegraph map examples/beach.json --shot towel_seaward`. Exit `0`, and the grid border contains `~` for the open sides.

## Gotchas

- One map character is 0.125 m wide (the header gives `1 char = ...`), so small objects can be a single letter.
- On a scene with several spaces, `--space` picks which one to draw when there is no shot.
