# Contributing

Contributions should preserve AWAKENED: ZERO RANK's deterministic, observer-only design.

## Development setup

```bash
python -m pip install -e ".[training,dev]"
python -m ruff check src tests
python -m unittest discover -s tests -v
```

The core package remains dependency-free. Use the `training` extra only when exercising the official Gymnasium integration.

## Change guidelines

- Keep Ren autonomous; new controls may observe or configure a run but must not choose his in-world actions.
- Preserve seeded reproducibility and exact save continuation.
- Add focused tests before running larger training or evaluation batches.
- Use separate training and held-out evaluation seeds.
- Report learned-policy results as **promising**, **inconclusive**, or **baseline remains better** from held-out evidence.
- Reject policy changes that improve reward while weakening survival, rent recovery, mission coherence, or behavioral variety.
- Keep checkpoint and report migrations explicit, deterministic, and tamper-evident.
- Update the README for current behavior and the changelog for release history.

## Pull requests

A pull request should state what changed, why it is safe, which commands were run, and whether simulation behavior, checkpoint schemas, report schemas, or RL verdicts changed. Do not include generated saves, build artifacts, large experiment outputs, or unrelated formatting changes.