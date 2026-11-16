---
name: verify-spacegraph
description: Drive the real spacegraph CLI (view, map, check, list) on the example scenes the way a user does, and capture the command, stdout, stderr and exit code as proof. Use to prove that a change to spacegraph works end to end, beyond the unit tests.
---

# Verify spacegraph

spacegraph is a short-lived, stateless command-line tool. Its main surface is the `spacegraph` CLI, and the Python API (`import spacegraph`) is secondary. Each command reads a scene JSON file, prints its result and exits, and nothing is written back. Because there is no server or data directory, any number of runs can go at once.

The helper is `.claude/skills/verify-spacegraph/sgv`. Run it from anywhere inside the repo; it `cd`s to the repo root itself.

## Launch

1. `uv` must be on `PATH`. `uv run` syncs `.venv` from `uv.lock` and installs spacegraph in editable mode from `src/`, so every run uses the working tree.
2. Start a run: `RUN=$(.claude/skills/verify-spacegraph/sgv new)`. This creates `~/.cache/spacegraph-verify/<timestamp>-<pid>/` with `revision.txt` (commit plus `git status --short`) and an empty `scratch/` for any scene files you write. Set `SGV_EVIDENCE` to put runs somewhere else.

The CLI is ready once `sgv doctor` prints `OK`. Each command is its own process, so there is nothing to keep running and nothing to tear down between drives.

## Doctor

`.claude/skills/verify-spacegraph/sgv doctor` is read-only. It checks that:

- `spacegraph` imports from this repo's `src/` and not from some other install;
- `spacegraph.__version__` equals the `version` in `pyproject.toml`;
- `spacegraph list examples/bedroom.json` exits 0.

It prints `OK  spacegraph <version> from <repo>/src at <sha>`, with ` +dirty` when the tree has uncommitted changes. Any `FAIL` line names the check that failed. Run doctor first, and again whenever output looks wrong.

## Drive

```
.claude/skills/verify-spacegraph/sgv run "$RUN" <label> -- spacegraph <args...>
```

This runs `uv run spacegraph <args...>` from the repo root and writes `<label>.cmd`, `<label>.out`, `<label>.err` and `<label>.exit` into the run dir. It echoes stdout, then any stderr, then `--- exit N`, and returns the CLI's own exit code. Exit codes: `0` ok, `1` from `check` when it warns, `2` with `REJECTED` for an impossible scene or shot. Other failures (unknown shot, missing `--cam`) exit 1 with a message on stderr.

The scenes are `examples/bedroom.json` (indoor, with a mirror and a subject) and `examples/beach.json` (outdoor, with open sides). For the commands that prove each feature, see [features/README.md](features/README.md).

## Evidence

Every proof is the four `<label>.*` files plus the run's `revision.txt`. Proof standards:

- Drive the real CLI through `sgv run`. Do not call internal functions or edit the example scenes to make a run pass.
- Capture the action and its result: the `.cmd` file holds the exact invocation, and `.out`/`.err`/`.exit` hold what came back.
- Assert on specific lines (an object's row under `IN FRAME`, a `WARN` line, a `REJECTED` reason), not only on the exit code.
- To prove a fix, run the same label against the old commit (`git stash` or a worktree) and the new one, and keep both run dirs.
- Put scenes you write in `"$RUN/scratch/"`, and copy any you want to keep as proof next to the label files before cleanup.

## Cleanup

`.claude/skills/verify-spacegraph/sgv cleanup "$RUN"` deletes only `"$RUN/scratch/"`. The label files and `revision.txt` stay in the run dir. The script refuses any path outside `~/.cache/spacegraph-verify/` (or `SGV_EVIDENCE`). No processes are left running, so there is nothing to kill.
