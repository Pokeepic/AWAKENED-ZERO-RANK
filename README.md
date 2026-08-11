# AWAKENED: ZERO RANK

[![CI](https://github.com/Pokeepic/AWAKENED-ZERO-RANK/actions/workflows/ci.yml/badge.svg)](https://github.com/Pokeepic/AWAKENED-ZERO-RANK/actions/workflows/ci.yml)

An observer-only autonomous life simulation set in Japan after portals and Awakened hunters become part of everyday society.

Ren Takahashi begins poor, unranked, and unknown. He decides how to work, recover, train, form relationships, investigate Gates, and survive. The player watches rather than choosing his actions.

| Project status | Current value |
|---|---|
| Release | `0.162.0` |
| Python | 3.11+; CI-tested through 3.14 |
| Production controller | Transparent utility policy |
| Tabular RL verdict | **Baseline remains better** |
| Corrected ensemble verdict | **Inconclusive** |
| Automated tests | 174 |

## Why this project exists

AWAKENED: ZERO RANK explores whether a deterministic agent can live a coherent, persistent life without direct player control. Everyday needs and long-term ambitions share the same simulation: rent can delay training, injuries can alter social choices, relationships can affect preparation, and Gate decisions can create consequences that return days later.

The project follows six rules:

- Life comes before power progression.
- Ren remains autonomous and every decision is explainable.
- State and consequences survive integrity-checked, atomic save and resume.
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

Verify a save without advancing its timeline:

```bash
awakened-zero-rank --verify-save saves/ren.json
```

Inspect its structured story progress without advancing or rewriting it:

```bash
awakened-zero-rank --story-progress saves/ren.json
```

The JSON result reports `integrity: verified` for schema-2 saves. Compatible schema-1 saves report `integrity: legacy-unavailable` instead of claiming evidence they do not contain. Both formats must also satisfy critical clock, resource, progression, mission, injury, economy, inventory, chronology, social-reference, and portal invariants before the verifier reports `status: valid`. The same validation runs before every write, so an impossible current state cannot replace an existing save. Runtime-critical protagonist locations, equipped items, NPC relationships and collaborators, portal investigations, and active plans must also resolve coherently against the current world catalog; extensible unequipped inventory names remain allowed.

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

Run critical static checks and the complete suite with conservative resource usage:

```bash
python -m pip install -e ".[dev]"
python -m ruff check src tests
python -m unittest discover -s tests -v
```

The tests cover deterministic simulation, persistence, action masks, fixed horizons, held-out evaluation, honest verdicts, authenticated checkpoints and reports, bundle publication, comparison artifacts, and CLI behavior.

## Roadmap

### Three-year story arc

Six fixed story anchors arrive at roughly six-month intervals from day 183 through day 1,095. They cannot be avoided or moved, but each resolution reflects Ren's accumulated hunter rank, trusted relationships, and discovered portals. The final anchor closes the three-year chronicle with an ending shaped by that history. Every anchor has distinct authored outcomes for `isolated`, `resilient`, and `prepared` resolutions. Event prose names relevant trusted characters and the latest discovered portal when that evidence exists. The resolved tier is saved in world state, and the observer summary reports current arc progress plus the latest result. `story_progress(state)` exposes the same chronology through schema-3 mutation-free JSON with completed entries, next-anchor timing, and ending status for dashboards and tools. Saves from the brief pre-ledger story release migrate completed anchors as `legacy-unavailable` rather than inventing a readiness result, and resolved anchors must remain a chronological prefix. Completed arcs receive one deterministic named ending—`The Unfinished Warning`, `Tokyo's Quiet Guardian`, or `The Zero-Rank Horizon`—while legacy histories remain explicitly unavailable.

### Story and content growth

Expand the catalog through authored dialogue, recurring characters, portals, encounters, equipment, locations, and consequences. New content should deepen character identity and world continuity rather than only multiplying random combinations.

Deepen each anchor with recurring-character scenes, portal-specific consequences, international links, and more varied endings without turning the observer-only simulation into a scripted choice game.

### Advanced learning research

More expressive RL can be explored after the world and story state are represented safely. Candidate approaches must remain reproducible, train only on separated seeds, pass small pilots before larger runs, and beat the utility controller on held-out reward, survival, progression, and exploit checks before adoption.

### International expansion

On timelines spanning roughly three or four in-world years, major portal disasters and other consequential events can emerge outside Japan. Countries can develop distinct Awakened institutions, regulations, economies, Gate responses, recurring characters, and recovery arcs.

International travel should remain grounded in passports or clearance, airfare, lodging, travel time, language, local contacts, mission invitations, personal risk, and whether Ren can responsibly afford the trip. Ren should autonomously decide whether to travel, remain in Japan, contribute remotely, or decline.

### Observer website

A later release can add a read-only dashboard for time, weather, Ren's condition, current concerns, decisions, relationships, finances, inventory, investigations, and chronicles. Lightweight sprite animation can visualize travel, work, rest, training, conversations, and Gate activity.

The website must remain a view of the deterministic simulator. Pause, speed, seed, save, reset, and diagnostics are developer controls—not ways to choose Ren's life for him. Published experiment bundles and comparison artifacts can power a separate developer view without coupling presentation code to training. `observer_snapshot(simulation)` now provides the schema-1, mutation-free JSON boundary for current world, protagonist, relationship, portal, and story state; it exposes no control hooks.

### Future game adaptation

After the deterministic simulator, complete story content, balance evidence, and observer website are mature, a separate game adaptation can add presentation, exploration, and player interaction. The simulator should remain the canonical world model, while the game consumes stable story, save, and dashboard APIs instead of rewriting proven simulation rules.

A playable version should define its own choice design, failure handling, accessibility, pacing, controls, art, audio, and save experience. Player-directed outcomes must be evaluated separately from autonomous-agent and RL evidence so the research verdicts remain honest.

An optional future "echo advisor" can turn a separately evaluated, frozen RL policy into a split-personality-style companion that offers contextual tips and commentary. It should never silently choose for the player, must be clearly optional and can be muted or disabled, and should communicate uncertainty. The current tabular policy is not ready for that role: the held-out verdict remains that the utility baseline performs better.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for deterministic-development rules, test expectations, held-out evaluation requirements, and pull-request guidance.

## Project history

See [CHANGELOG.md](CHANGELOG.md) for the complete update record, balance evidence, rejected experiments, schema migrations, and reporting-tool history.
