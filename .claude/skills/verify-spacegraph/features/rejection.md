# Rejection

spacegraph refuses impossible input. A camera outside the walls, a subject inside furniture, overlapping furniture or an object through a wall each print `REJECTED` followed by every problem as a `  - ` line, and the command exits `2`. Spaces are checked when they load, and shots when they are viewed.

## Sub-features

- `reject-camera` rejects a camera outside the walls.
- `reject-scene` rejects a scene whose furniture overlaps.
- `reject-unknown-shot` reports an unknown shot name (exit 1, not `REJECTED`).

## How to get to it (user POV)

- Any `view`, `check` or `map` with an impossible camera or subject.
- Any command on a scene file with an impossible layout.

## Driving it with sgv

Preconditions:

- Baseline preconditions from the README hold.

- **Camera outside.** Run `sgv run "$RUN" reject-camera -- spacegraph view examples/bedroom.json --cam 99,99,1.5 --look bed`. Exit `2`. `.out` is `REJECTED  shot rejected:` followed by `  - the camera at (99, 99) is outside the walls`.
- **Overlapping furniture.** Write `"$RUN/scratch/overlap.json"` containing `{"spaces":{"r":{"size":[3,3],"height":2.5,"walls":{"N":"white","E":"white","S":"white","W":"white"},"ground":"wood","objects":[{"id":"a","at":[1.5,1.5],"size":[1,1],"h":0.5,"desc":"a box"},{"id":"b","at":[1.6,1.6],"size":[1,1],"h":0.5,"desc":"a crate"}]}},"shots":{}}`. Run `sgv run "$RUN" reject-scene -- spacegraph map "$RUN/scratch/overlap.json"`. Exit `2`. `.out` is `REJECTED  space 'r' rejected:` followed by `  - 'a' and 'b' overlap by 0.90 x 0.90 m`.
- **Rejected on load.** Run `sgv run "$RUN" reject-list -- spacegraph list "$RUN/scratch/overlap.json"`. Exit `2`, with the same `REJECTED` output as the previous step.
- **Unknown shot.** Run `sgv run "$RUN" reject-unknown-shot -- spacegraph view examples/bedroom.json --shot nope`. Exit `1`, and `.err` is `unknown shot 'nope'`.

## Gotchas

- `REJECTED` goes to stdout, not stderr. Assert on `.out`.
- Every space is checked when the scene loads, so all four commands, `list` included, reject a scene with any impossible space, even one the command doesn't use. Before 0.6.1, `list` skipped this check.
- Flat objects (5 cm tall or less, such as rugs and towels) never collide, so build an overlap from objects taller than that.
- If the scratch scene's schema drifts from `docs/REFERENCE.md`, the rejection reason changes. Read the reason before counting the step as proven.
