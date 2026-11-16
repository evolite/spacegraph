# spacegraph verification map

This directory is the maintained source for verifying spacegraph's user-facing behavior. Read this index before driving the CLI, then follow the matching feature file as the recipe.

## Baseline preconditions

- `.claude/skills/verify-spacegraph/sgv doctor` prints `OK`.
- `RUN=$(.claude/skills/verify-spacegraph/sgv new)` has created a run dir.
- `examples/bedroom.json` and `examples/beach.json` are unmodified (`git diff --quiet examples/`), unless the change under test is to them.

## Driving conventions

- Run every command from the repo root through `sgv run "$RUN" <label> -- spacegraph ...`.
- Treat commands as literal. Keep quoting and flags as written.
- Name each label `<feature-id>-<step>`, for example `view-shot`.
- Write scratch scenes and prompt text into `"$RUN/scratch/"`, never into `examples/`.

## Proof and skip reporting

- CLI proof is the `.cmd`, `.out`, `.err` and `.exit` files for the label.
- Quote the line that proves the claim, and give its label.
- If a step's precondition is unmet, report the attempted command and the missing precondition. Do not count it as verified through a different path.

## Feature entry contract

Each feature file starts with an H1 and one paragraph on the user-visible behavior, followed by exactly four H2s in this order: `Sub-features`, `How to get to it (user POV)`, `Driving it with sgv`, `Gotchas`.

## Features

- [View](./view.md): what is in frame from a camera, given as a named shot, an ad-hoc camera or shot JSON, in report or JSON form.
- [Map](./map.md): a top-down ASCII map, with or without a camera.
- [Check](./check.md): warnings where prompt text contradicts the view.
- [List](./list.md): the spaces, objects and shots in a scene.
- [Rejection](./rejection.md): impossible cameras and scenes rejected with `REJECTED` and exit 2.
