# Check

`spacegraph check` reads prompt text against a shot's view and prints one `WARN` line per contradiction. Contradictions include an object that is named but out of frame, an object in frame that is never mentioned, the subject's view contradicted, and an unmentioned mirror. It exits `1` when there are warnings and `0` with `OK  the text agrees with the view` when there are none.

## Sub-features

- `check-warn` warns for out-of-frame and unmentioned objects.
- `check-ok` passes text that matches the view.
- `check-file` reads the text from `@file`.
- `check-stdin` reads the text from `-` (stdin).

## How to get to it (user POV)

- `spacegraph check SCENE --shot NAME --text "TEXT"`
- `spacegraph check SCENE --shot NAME --text @prompt.txt`
- `... --text -` with the prompt on stdin.

## Driving it with sgv

Preconditions:

- Baseline preconditions from the README hold.

- **Contradiction.** Run `sgv run "$RUN" check-warn -- spacegraph check examples/bedroom.json --shot doorway_wide --text "the window is behind her"`. Exit `1`. `.out` has `WARN  'window' (window) is named but out of frame: off the right edge` and a `WARN` line saying `'bed' is in frame ... but the text never mentions it`.
- **Agreeing text.** Write the `DRAFT` paragraph of the `view-shot` run to `"$RUN/scratch/ok.txt"` (`sed -n '/^DRAFT/{n;p}' "$RUN/view-shot.out" > "$RUN/scratch/ok.txt"`). Run `sgv run "$RUN" check-file -- spacegraph check examples/bedroom.json --shot doorway_wide --text @"$RUN/scratch/ok.txt"`. Exit `0` and `.out` is `OK  the text agrees with the view`. A warning against spacegraph's own draft is a finding to report.
- **Stdin.** Run `echo "the window is behind her" | .claude/skills/verify-spacegraph/sgv run "$RUN" check-stdin -- spacegraph check examples/bedroom.json --shot doorway_wide --text -`. Exit `1`, with the same `window` warning as the contradiction step.

## Gotchas

- Exit `1` is the success path for a contradiction. Do not read it as a crash; confirm `.err` is empty.
- `@file` paths are read relative to the repo root, because `sgv` runs from there. Use absolute paths into `"$RUN/scratch/"`.
