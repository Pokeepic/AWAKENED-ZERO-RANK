# AWAKENED: ZERO RANK

[![CI](https://github.com/Pokeepic/AWAKENED-ZERO-RANK/actions/workflows/ci.yml/badge.svg)](https://github.com/Pokeepic/AWAKENED-ZERO-RANK/actions/workflows/ci.yml)

A deterministic autonomous-life simulation and a separate private time-management RPG set in an awakened Tokyo.

The project has two distinct modes. In **Observer**, autonomous Ren decides how to live and survive. In **Game**, you play as Ren: your actions move a local four-slot calendar and change his RPG resources without rewriting the Observer timeline.

| Status | Value |
|---|---|
| Release | `0.650.0` |
| Python | 3.11+; CI-tested through 3.14 |
| Production controller | Transparent utility policy |
| RL adoption verdict | **Baseline remains better** |
| Automated tests | 339 Python + 105 browser |
| Website access | Private, owner-only |

## Play the private web game

[Open AWAKENED: ZERO RANK](https://awakened-zero-rank-observer.pokeepic.chatgpt.site/game)

The current game contains three connected, authenticated chapters:

1. **Apartment prologue** — explore Ren's pixel-art apartment and take his next action.
2. **Tokyo district maps** — move through Central Tokyo, the East Loop, and Adachi Fringe as Ren.
3. **Adachi Gate field** — inspect illustrated case files and choose Ren's risk response.

The game uses tiny transparent pixel chibi sprites, original district maps, location art, and illustrated Gate files inside an angular, dialogue-first interface. A persistent HUD follows Ren across chapters, and New Game safely resets only the local RPG campaign. Every committed action advances Morning → Afternoon → Evening → Late Night, updates Ren's RPG resources, and remains separate from the authenticated autonomous Observer save.

## What the simulation models

- Four daily periods: Morning, Afternoon, Evening, and Late Night.
- Work, meals, recovery, training, rent, arrears, equipment, and injuries.
- Hunter registration, rank progression, Gate missions, and persistent portal investigations.
- Seeded weather and a repeating four-season calendar.
- Recurring characters with schedules, relationships, contextual dialogue, and memories.
- Six fixed story anchors across a three-year arc with five deterministic endings.
- Integrity-checked saves, observer snapshots, experiment bundles, and comparisons.

Core principles:

- Life comes before power progression.
- Observer Ren remains autonomous; Game Ren is directly player-controlled.
- Identical seeds and state produce identical futures.
- Progression is earned through preparation and experience.
- Learned policies stay offline until held-out evidence supports adoption.

## Quick start

```bash
python -m pip install -e .
awakened-zero-rank --days 12 --seed 42
```

Save, resume, and verify an exact timeline:

```bash
awakened-zero-rank --days 7 --seed 42 --save saves/ren.json
awakened-zero-rank --days 7 --load saves/ren.json --save saves/ren.json
awakened-zero-rank --verify-save saves/ren.json
```

Publish the authenticated observer data pair:

```bash
awakened-zero-rank --publish-observer-site-data saves/ren.json public/data
awakened-zero-rank --verify-observer-site-data public/data
```

Use `awakened-zero-rank --help` for snapshot, story, comparison, checkpoint, and experiment commands.

## Architecture

| Path | Responsibility |
|---|---|
| `src/awakened_zero_rank/simulation.py` | Deterministic simulation loop |
| `src/awakened_zero_rank/agent.py` | Autonomous utility decisions |
| `src/awakened_zero_rank/actions.py` | Valid actions and outcomes |
| `src/awakened_zero_rank/models.py` | Persistent state models |
| `src/awakened_zero_rank/content.py` | Story, characters, Gates, and equipment |
| `src/awakened_zero_rank/dialogue.py` | Contextual dialogue and intentions |
| `src/awakened_zero_rank/learning.py` | Training, evaluation, and artifacts |
| `src/awakened_zero_rank/persistence.py` | Verified save and load behavior |
| `src/awakened_zero_rank/observer.py` | Mutation-free observer boundary |
| `site/app` | Observer routes and the separate Ren-controlled RPG |
| `tests` / `site/tests` | Python and browser regression suites |

## Learning and evaluation

The offline stack includes Gymnasium-compatible fixed-horizon episodes, twelve integer actions, valid-action masks, reproducible tabular Q-learning, and separate training and held-out seeds.

| Experiment | Training budget | Held-out evaluation | RL vs utility | Verdict |
|---|---:|---:|---:|---|
| First tabular reference | 24 × 60 steps | 8 seeds | −33.894 | Baseline remains better |
| Improved tabular policy | 120 × 80 steps | 12 seeds | −8.493 | Inconclusive |
| Repeated-trial audit | 3 × 120 × 80 steps | 3 groups × 8 seeds | −6.196 pooled | Inconclusive |

The utility agent remains the production controller. Neural RL and an optional future in-game “echo advisor” remain deferred until stronger held-out evidence exists.

## Tests

```bash
python -m pip install -e ".[dev]"
python -m ruff check src tests
python -m unittest discover -s tests -q

cd site
npm test
npm run lint
```

## Roadmap

- Expand the RPG chapters, location backdrops, chibi expressions, combat, and dialogue presentation.
- Add more dialogue, characters, portals, equipment, and authored story variations.
- Improve accessibility, controls, pacing, sound, and local save UX for the game layer.
- Preserve the autonomous Observer while growing the player-directed RPG as a separate campaign.
- Revisit advanced RL only after representation and held-out coverage improve.
- Consider international travel and disaster arcs after Tokyo's core game is mature.

See [CHANGELOG.md](CHANGELOG.md) for the full release and evaluation history and [CONTRIBUTING.md](CONTRIBUTING.md) for deterministic-development rules.
