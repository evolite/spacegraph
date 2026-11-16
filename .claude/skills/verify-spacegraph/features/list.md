# List

`spacegraph list` prints every space in a scene, with its size, object count and each object's id and description, followed by every shot with its space, camera and look target.

## Sub-features

- `list-indoor` lists the bedroom scene.
- `list-outdoor` lists the beach scene.

## How to get to it (user POV)

- `spacegraph list SCENE`

## Driving it with sgv

Preconditions:

- Baseline preconditions from the README hold.

- **Indoor.** Run `sgv run "$RUN" list-indoor -- spacegraph list examples/bedroom.json`. Exit `0`. The first line is `space bedroom: 4.5 x 4.0 m, 11 objects`, and there are four `shot` lines, including `shot doorway_wide: space bedroom, cam [3.6, 0.3, 1.5], look bed`.
- **Outdoor.** Run `sgv run "$RUN" list-outdoor -- spacegraph list examples/beach.json`. Exit `0`. The first line is `space beach: 30 x 20 m, 6 objects`, and there are shot lines for `towel_seaward` and `from_the_water`.

## Gotchas

- Object and shot counts change whenever the examples change. Check `git log examples/` before treating a count mismatch as a regression.
