# AWAKENED: ZERO RANK

[![CI](https://github.com/Pokeepic/AWAKENED-ZERO-RANK/actions/workflows/ci.yml/badge.svg)](https://github.com/Pokeepic/AWAKENED-ZERO-RANK/actions/workflows/ci.yml)

An observer-only autonomous life simulation set in Japan after portals and Awakened hunters become part of everyday society.

Ren Takahashi begins poor, unranked, and unknown. He decides how to work, recover, train, form relationships, investigate Gates, and survive. The player watches rather than choosing his actions.

| Project status | Current value |
|---|---|
| Release | `0.138.0` |
| Python | 3.11+ |
| Production controller | Transparent utility policy |
| Tabular RL verdict | **Baseline remains better** |
| Corrected ensemble verdict | **Inconclusive** |
| Automated tests | 132 |

## Why this project exists

AWAKENED: ZERO RANK explores whether a deterministic agent can live a coherent, persistent life without direct player control. Everyday needs and long-term ambitions share the same simulation: rent can delay training, injuries can alter social choices, relationships can affect preparation, and Gate decisions can create consequences that return days later.

The project follows six rules:

- Life comes before power progression.
- Ren remains autonomous and every decision is explainable.
- State and consequences survive save and resume.
- Progression must be earned through preparation and experience.
- Identical seeds and state must produce identical futures.
- Learned policies stay offline until held-out evidence supports adoption.

## Current simulation

### Daily life

- Four daily periods: Morning, Afternoon, Evening, and Late Night.
- Work, meals, rest, study, training, commuting, rent, arrears, and debt recovery.
- Seeded weather, wages, meal costs, seasonal events, and Gate alerts.
- Persistent health, energy, hunger, stress, morale, injuries, money, equipment, and inventory.

### Hunter progression

- Day-three awakening, Rank F registration, Threat Sense mastery, and Echo Fragment growth.
- Guild patrols, named Gate encounters, deterministic combat, injuries, rewards, and promotion.
- Persistent portal discoveries, clues, risk, delayed consequences, and hazard-aware preparation.
- Financial, medical, social, and mission-readiness goals that compete for Ren's time.

### Characters and narrative

- Recurring characters Aiko Sato, Daichi Mori, Mei Kuroda, and Haruto Ishikawa.
- NPC schedules, autonomous encounters, relationship networks, and conflicting loyalties.
- More than 4,200 structured dialogue contexts.
- Bounded memories, changing personal goals, contextual chronicles, and exact timeline continuation.

## Quick start

Install the package in editable mode:

```bash
python -m pip install -e .
```

Confirm the installed release:

```bash
awakened-zero-rank --version
```

Run a deterministic twelve-day timeline:

```bash
awakened-zero-rank --days 12 --seed 42
```

The module entry point is equivalent:

```bash
python -m awakened_zero_rank --days 12 --seed 42
```

Save and resume an exact timeline:

```bash
awakened-zero-rank --days 7 --seed 42 --save saves/ren.json
awakened-zero-rank --days 7 --load saves/ren.json --save saves/ren.json
```

Add `--technical-log` to display decision reasons and utility scores.

## Learning and evaluation

The offline learning system provides:

- Gymnasium-compatible fixed-horizon episodes.
- Twelve integer actions with valid-action masks.
- A stable 22-value observation and compact 16-feature strategic state.
- Reproducible tabular Q-learning with separate training and held-out seeds.
- Utility, heuristic, masked-random, single-policy RL, and ensemble comparisons.
- Multi-condition and multi-horizon scenario suites with conservative verdicts.
- Deterministic checkpoints, SHA-256 identity, schema migration, and tamper rejection.
- Detailed safety, state coverage, action exposure, recurrence, fallback, reward, and mission diagnostics.

Install the official Gymnasium integration when working on training:

```bash
python -m pip install -e ".[training]"
```

### Current evidence

All figures below are environment rewards from held-out seeds. Training-only curriculum rewards are excluded.

| Experiment | Training budget | Held-out evaluation | RL vs utility | Verdict |
|---|---:|---:|---:|---|
| First tabular reference | 24 × 60 steps | 8 seeds | −33.894 | Baseline remains better |
| Improved tabular policy | 120 × 80 steps | 12 seeds | −8.493 | Inconclusive |
| Repeated-trial audit | 3 × 120 × 80 steps | 3 groups × 8 seeds | −6.196 pooled | Inconclusive |

The production controller remains the utility policy. The latest single-policy adoption decision is **baseline remains better**. The corrected return-evidence ensemble is **inconclusive** and is not production-ready.

Near-term learning work should not repeat episode-count scaling, seed replay, similarity fallback tuning, or similarity ensembling. A future learned representation must preserve explicit safety contexts and demonstrate balanced held-out coverage before policy evaluation. Neural RL remains deferred.

## Experiment artifacts

Experiment bundles are portable, authenticated, staged without overwriting, and verified before inspection or comparison.

```bash
# Verify a published bundle and print compact JSON metadata.
awakened-zero-rank --inspect-experiment-bundle reports/run-001

# Compare two verified bundles.
awakened-zero-rank --compare-experiment-bundles reports/run-001 reports/run-002

# Fail CI when the verified bundles differ.
awakened-zero-rank --compare-experiment-bundles reports/run-001 reports/run-002 --require-identical

# Publish and later inspect a content-addressed comparison artifact.
awakened-zero-rank --compare-experiment-bundles reports/run-001 reports/run-002 --comparison-output reports/comparison.json
awakened-zero-rank --inspect-comparison-artifact reports/comparison.json
```

Comparison artifacts include complete added and removed report records, field-level before/after snapshots, aggregate seed/condition/horizon changes, a stable SHA-256 identity, and semantic validation that rejects re-hashed impossible data.

## Repository layout

| Path | Responsibility |
|---|---|
| `src/awakened_zero_rank/simulation.py` | Deterministic simulation loop |
| `src/awakened_zero_rank/agent.py` | Autonomous utility decisions |
| `src/awakened_zero_rank/actions.py` | Available actions and outcomes |
| `src/awakened_zero_rank/models.py` | Persistent state models |
| `src/awakened_zero_rank/content.py` | Scalable narrative content |
| `src/awakened_zero_rank/dialogue.py` | Contextual dialogue and intentions |
| `src/awakened_zero_rank/learning.py` | Training, evaluation, diagnostics, and artifacts |
| `src/awakened_zero_rank/persistence.py` | Exact save and load behavior |
| `src/awakened_zero_rank/cli.py` | Simulation and artifact command line interface |
| `tests/test_simulation.py` | Deterministic regression suite |

## Tests

Run the complete suite with conservative resource usage:

```bash
python -m unittest discover -s tests -v
```

The tests cover deterministic simulation, persistence, action masks, fixed horizons, held-out evaluation, honest verdicts, authenticated checkpoints and reports, bundle publication, comparison artifacts, and CLI behavior.

## Roadmap

### International expansion

On timelines spanning roughly three or four in-world years, major portal disasters and other consequential events can emerge outside Japan. Countries can develop distinct Awakened institutions, regulations, economies, Gate responses, recurring characters, and recovery arcs.

International travel should remain grounded in passports or clearance, airfare, lodging, travel time, language, local contacts, mission invitations, personal risk, and whether Ren can responsibly afford the trip. Ren should autonomously decide whether to travel, remain in Japan, contribute remotely, or decline.

### Observer website

A later release can add a read-only dashboard for time, weather, Ren's condition, current concerns, decisions, relationships, finances, inventory, investigations, and chronicles. Lightweight sprite animation can visualize travel, work, rest, training, conversations, and Gate activity.

The website must remain a view of the deterministic simulator. Pause, speed, seed, save, reset, and diagnostics are developer controls—not ways to choose Ren's life for him. Published experiment bundles and comparison artifacts can power a separate developer view without coupling presentation code to training.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for deterministic-development rules, test expectations, held-out evaluation requirements, and pull-request guidance.

## Project history

See [CHANGELOG.md](CHANGELOG.md) for the complete update record, balance evidence, rejected experiments, schema migrations, and reporting-tool history.
