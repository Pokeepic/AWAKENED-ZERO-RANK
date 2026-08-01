# AWAKENED: ZERO RANK

An observer-only life simulation set in Japan after portals and Awakened hunters become part of everyday society.

Ren Takahashi begins poor, unranked, and unknown. He chooses how to work, recover, train, build relationships, investigate Gates, and survive. The player watches; Ren remains autonomous.

Current release: **0.23.0** · **87 automated tests**

## Design principles

- **A believable life first:** rent, travel, food, fatigue, injury, weather, and social pressure matter.
- **Autonomy:** the observer does not select Ren's actions or dialogue.
- **Explainability:** decisions have recorded options and structured reasons.
- **Persistence:** people, memories, investigations, plans, and consequences survive save and resume.
- **Earned progression:** power grows through preparation, varied experience, knowledge, and relationships.
- **Reproducibility:** the same seed, state, and policy produce the same future.

## What is implemented

### Life in Tokyo

- Four daily periods: Morning → Afternoon → Evening → Late Night.
- Work, meals, rest, study, physical training, commuting, rent, and arrears.
- Seeded weather, daily wage and meal variation, Tanabata, and Gate alerts.
- Health, energy, hunger, stress, morale, injury severity, clinic treatment, money, equipment, and inventory.

### Hunter progression

- Day 3 awakening, Rank F registration, Threat Sense mastery, and latent Echo Fragment growth.
- Guild patrols, named Gate encounters, deterministic combat, injuries, rewards, rank points, and promotion.
- Persistent portal discoveries, clues, risk, delayed consequences, and three-stage hazard-aware preparation.
- Multi-step financial, recovery, and portal-readiness objectives.

### Characters and narrative

- Recurring characters Aiko Sato, Daichi Mori, Mei Kuroda, and Haruto Ishikawa.
- NPC schedules, autonomous encounters, relationship networks, trust, affection, tension, and loyalty.
- Structured dialogue with more than 4,200 NPC-specific contexts.
- Bounded memories, changing personal goals, contextual chronicles, and exact save continuation.

### Learning and evaluation

- Gymnasium-compatible fixed-horizon episodes with 11 integer actions and valid-action masks.
- A 22-value observation interface and compact 16-feature strategic state abstraction.
- Utility, heuristic, masked-random, and tabular Q-learning policies.
- Count-based exploration, phased curriculum rewards, and held-out seed enforcement.
- Reward decomposition, action/mask frequencies, safety metrics, exploit indicators, and worst-seed traces.
- Deterministic Q-table checkpoints with schema validation and SHA-256 tamper detection.
- Repeated independent trials with pooled confidence and a conservative adoption gate.
- Named, multi-horizon scenario suites with isolated held-out seeds and per-scenario safety metrics.
- Deterministic evaluation starts for standard life, financial pressure, injury recovery, and Gate crises.
- Versioned scenario-suite JSON reports with stable policy binding, SHA-256 identity, exact reload, tamper rejection, and backward-compatible schema loading.
- Explainable offline adoption decisions with checkpoint verification and explicit confidence, safety, and progression blockers.

The production controller remains the transparent utility policy. Learned policies stay offline until they demonstrate a clear, repeatable held-out advantage without safety or progression regressions; every failed gate now returns explicit blocker reasons.

## Run the simulation

Requires Python 3.11 or newer.

```bash
python -m pip install -e .
python -m awakened_zero_rank --days 12 --seed 42
```

Install the optional official Gymnasium integration with:

```bash
python -m pip install -e ".[training]"
```

Save and resume an exact timeline:

```bash
python -m awakened_zero_rank --days 7 --seed 42 --save saves/ren.json
python -m awakened_zero_rank --days 7 --load saves/ren.json --save saves/ren.json
```

Add `--technical-log` to show decision reasons and utility scores.

Run the tests:

```bash
python -m unittest discover -s tests -v
```

## Learning results

All scores below are environment rewards measured on held-out seeds. Training-only curriculum rewards never enter evaluation.

| Experiment | Training | Evaluation | RL vs utility | Verdict |
|---|---:|---:|---:|---|
| First tabular reference | 24 × 60 steps | 8 seeds | −33.894 | Baseline remains better |
| Improved tabular policy | 120 × 80 steps | 12 seeds | −8.493 | Inconclusive |
| Repeated-trial audit | 3 × 120 × 80 steps | 3 groups × 8 seeds | −6.196 pooled | Inconclusive |

In the improved-policy experiment, RL averaged `80.088` reward versus utility's `88.581`, completed more missions (`4.667` versus `3.750`), and matched utility's 100% survival and rent payment. The difference was not statistically decisive.

The repeated audit produced trial differences of `−19.965`, `+8.436`, and `−7.059`. All three trials were inconclusive, so neural-policy readiness remains **false**.

## Suggested balance backlog

These are hypotheses, not scheduled changes. Each patch should be isolated, evaluated on held-out seeds across all stress conditions, and rejected if it improves reward while weakening survival, rent recovery, mission coherence, or behavioral variety.

| Area | Evidence or risk | Candidate patch | Acceptance check |
|---|---|---|---|
| Passive repetition | Earlier RL diagnostics showed excessive eating and resting with weak progression | Add diminishing decision value only when recovery is unnecessary; never discourage food, sleep, or treatment under genuine need | Lower dominant-action share without worse survival or injury recovery |
| Debt behavior | Rent arrears can make paid patrols dominate utility choices | Cap the arrears-derived patrol bonus or compare patrol income against health, energy, and Gate risk before increasing it | Financial-pressure runs recover reliably without patrol loops or reduced survival |
| Gate pacing | RL completed more missions without establishing a reward advantage | Strengthen the value of preparation, retreat, and information while keeping unprepared mission failure costly | More prepared completions, not simply more attempts; no survival regression |
| Recovery access | Severe injury plus low cash can create a long recovery spiral | Review minimum clinic access, consumable availability, and safe income options rather than granting free healing | Injury scenarios return to stable health without erasing economic consequences |
| Social frequency | Dialogue should matter without becoming a low-risk reward farm | Add context-sensitive cooldowns or diminishing utility for repeated conversations while preserving crisis support | Relationship growth remains varied and passive-policy flags do not increase |
| Policy consistency | Repeated tabular trials remain inconclusive and vary by training seed | Improve state coverage and condition-aware diagnostics before increasing episode counts or trying neural RL | A frozen policy is promising in every scenario, matches safety and mission metrics, and passes the existing adoption gate |

Random-policy mission counts must never be used as a tuning target by themselves: prior evaluation showed that a controller can attempt missions while surviving only 12.5% of episodes. Safety and coherent preparation remain first-class balance constraints.

## Project layout

```text
src/awakened_zero_rank/
  models.py       # Persistent character and world state
  world.py        # Locations, jobs, items, and Gate encounters
  actions.py      # Civilian, hunter, preparation, and recovery actions
  agent.py        # Explainable production utility policy
  simulation.py   # Deterministic world and consequence engine
  journal.py      # Ren-centered chronicle presentation
  persistence.py  # Exact save/load continuation
  environment.py  # Weather and seasonal effects
  dialogue.py     # Dialogue intentions and social consequences
  content.py      # Tokyo, NPC, dialogue, and portal catalogues
  learning.py     # Episodes, policies, training, diagnostics, and checkpoints
  cli.py          # Chronicle command-line interface
tests/
  test_simulation.py
```

## Roadmap

Completed milestones are grouped for readability:

| Milestones | Focus |
|---|---|
| 1–6 | Deterministic life simulation, Tokyo economy, hunter progression, relationships, equipment, and persistence |
| 7–9 | Weather, calendar events, expanded attributes, mood, and dialogue consequences |
| 10–13 | Learning interface, scalable content, NPC networks, investigations, preparation, and cooperation |
| 14–15 | Gymnasium episodes, reproducible Q-learning, held-out comparison, and failure diagnostics |
| 16–17 | Broader economic/recovery scenarios and stronger utility, heuristic, and random baselines |
| 18–19 | Improved tabular training, checkpoint integrity, repeated trials, and neural-readiness auditing |
| 20 | Multi-horizon held-out scenario suites, pooled verdicts, and conservative adoption checks |
| 21 | Canonical scenario reports, checkpoint binding, deterministic export, and integrity verification |
| 22 | Explainable policy-adoption decisions with identity, confidence, safety, and progression gates |
| 23 | Deterministic financial, injury, and Gate-crisis evaluation conditions with versioned reporting |

Near-term work should use the expanded scenario suite to measure and improve tabular consistency across different horizons and stress conditions. Neural RL remains deferred while the readiness gate is closed.

### Future international expansion

On timelines spanning roughly three or four in-world years, major portal disasters and other consequential events can emerge outside Japan. Different countries can develop their own Awakened institutions, regulations, economies, Gate responses, recurring characters, and recovery arcs. These events should affect news, markets, guild priorities, relationships, migration, and humanitarian needs rather than existing only as spectacle.

International travel should remain grounded: passports or clearance, airfare, lodging, travel time, language and local contacts, mission invitations, personal risk, and whether Ren can responsibly afford the trip. Ren should decide autonomously whether to travel, remain in Japan, contribute remotely, or decline. All global events and decisions must remain seeded, persistent, and reproducible.

### Future observer website

A later presentation milestone can add a read-only web dashboard showing time, weather, Ren's condition, current concern, decision journal, relationships, finances, inventory, Gate investigations, and chronicles. Lightweight sprite animation can visualize travel, work, rest, training, conversations, and Gate activity. Versioned evaluation reports can feed a separate developer-facing experiment view without coupling the website to training code.

The website must remain a view of the authoritative deterministic simulator. Pause, speed, seed, save, reset, and diagnostics are developer controls—not ways to choose Ren's life for him.
