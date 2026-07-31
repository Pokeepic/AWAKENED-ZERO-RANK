# AWAKENED ZERO RANK

An observer-only life simulation set in modern Japan after portals and awakenings become part of everyday society.

The protagonist begins poor, unranked, and unknown. They act autonomously while the player watches their daily routine, work, study, training, awakening, hunter career, failures, and long-term growth.

## Core vision

- **Observer simulation:** the protagonist chooses; the user watches.
- **Zero-to-hero progression:** begin with little money, weak stats, and no hunter rank.
- **Persona-style time:** each meaningful action advances Morning → Afternoon → Evening → Late Night.
- **Living Japan setting:** rent, part-time work, transport, guilds, gates, and social pressure matter.
- **Explainable autonomy:** every decision is logged with its reason and utility score.
- **Learning-ready architecture:** start with a dependable utility agent, then add reinforcement learning as an experiment.
- **Reproducible worlds:** seeded runs make bugs and balance changes comparable.

## Current simulation

The simulation follows Ren Takahashi across a small Tokyo map and currently includes:

- autonomous work, meals, rest, study, and physical training;
- money, needs, knowledge, fitness, reputation, and combat readiness;
- Tokyo locations, rail fares, a konbini job, rent, arrears, and gate alerts;
- the Day 3 awakening assessment: Rank F with **Threat Sense**;
- mandatory Tokyo Hunter Guild registration and an F-rank license;
- safe guild patrol work and riskier low-rank gate missions;
- deterministic combat rolls, mission rewards, damage, injuries, and combat experience;
- rank points and promotion from F toward E, D, and C;
- observer logs explaining why every autonomous choice was made.
- a changing personal goal that follows Ren's current life stage;
- bounded, importance-ranked memories of awakenings, missions, rent, and social moments;
- recurring guild clerk Aiko Sato, with trust, familiarity, and meeting history;
- autonomous social time that can reduce stress and deepen relationships.
- a Kita-Senju hunter supply shop with autonomous, budget-aware purchases;
- inventory, equipped weapons and armor, and automatic consumable use;
- equipment bonuses that affect combat readiness and incoming damage;
- named gate encounters with distinct difficulty, rewards, rank points, and danger.

The calendar roadmap also reserves space for Japanese public holidays, seasonal festivals, shops, scheduled auction days, random/story events, and expanded hunter and social stats.

## Project layout

```text
src/awakened_zero_rank/
  models.py       # Character, clock, progression, and event state
  world.py        # Tokyo locations, jobs, and transport costs
  actions.py      # Civilian and hunter actions
  agent.py        # Explainable utility-based decision policy
  simulation.py   # Deterministic world, memory, relationship, and progression engine
  cli.py          # Observer command-line interface
tests/             # Determinism, world, and progression tests
```

## Run the simulation

Requires Python 3.11 or newer. From the repository root:

```bash
python -m pip install -e .
python -m awakened_zero_rank --days 12 --seed 42
```

The log prints every selected action, its outcome, and its reason. Reusing the same seed reproduces the same story.

Run the tests with:

```bash
python -m unittest discover -s tests -v
```

## V3 development workflow

1. **Deterministic simulation core** — clock, calendar, character state, needs, actions, and event log.
2. **Autonomous decision system** — utility scoring, goals, memory, and explainable choices.
3. **Japan world systems** — districts, economy, jobs, rent, gates, guilds, and hunter ranks.
4. **Dashboard** — observe time, status, decisions, relationships, and story events.
5. **Persistence and evaluation** — save/load, seeded batch runs, survival and progression metrics.
6. **Learning experiment** — train an RL policy separately and compare it with the baseline agent.
7. **Narrative layer** — turn important simulation events into readable scenes and chronicles.

## Learning strategy

Reinforcement learning is not the entire simulation. The simulation is the environment; an RL agent is one possible decision-maker inside it. We retain a transparent utility baseline so learned behavior can be measured against something stable, debuggable, and fun.

## Status

✅ Milestone 1: deterministic simulation core and explainable baseline agent.

✅ Milestone 2: Tokyo locations, transport, job economy, rent, gates, and awakening.

✅ Milestone 3: guild registration, hunter work, combat readiness, gate missions, injuries, rewards, and rank progression.

✅ Milestone 4: changing goals, important memories, relationships, and recurring characters.

✅ Milestone 5: equipment, inventory, shops, consumables, mission difficulty, and richer gate encounters.

Next: save/load persistence, batch evaluation, progression metrics, and balance reports.
