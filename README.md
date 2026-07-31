# AWAKENED ZERO RANK

An observer-only life simulation set in modern Japan after portals and awakenings become part of everyday society.

The protagonist begins poor, unranked, and unknown. They act autonomously while the player watches their daily routine, work, study, training, awakening, hunter career, failures, and long-term growth.

## Core vision

- **Observer simulation:** the protagonist chooses; the user watches.
- **Zero-to-hero progression:** begin with little money, weak stats, and no hunter rank.
- **Persona-style time:** each meaningful action advances Morning → Afternoon → Evening → Late Night.
- **Living Japan setting:** rent, part-time work, transport, guilds, gates, and social pressure matter.
- **Protagonist-focused observation:** the main chronicle follows what Ren experiences, notices, and feels.
- **Explainable autonomy:** technical decision reasons remain available for development and balancing.
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
- a protagonist-focused chronicle that presents Ren's days as compact scenes;
- a changing personal goal that follows Ren's current life stage;
- bounded, importance-ranked memories of awakenings, missions, rent, and social moments;
- recurring guild clerk Aiko Sato, with trust, familiarity, and meeting history;
- autonomous social time that can reduce stress and deepen relationships.
- a Kita-Senju hunter supply shop with autonomous, budget-aware purchases;
- inventory, equipped weapons and armor, and automatic consumable use;
- equipment bonuses that affect combat readiness and incoming damage;
- named gate encounters with distinct difficulty, rewards, rank points, and danger.
- versioned JSON saves that preserve the exact clock, world, character, and random state;
- deterministic continuation: a resumed timeline has the same future as an uninterrupted run;
- an optional technical log for debugging without cluttering the main experience.
- deterministic daily Tokyo summer weather: clear, cloudy, rain, heatwaves, and thunderstorms;
- weather-aware choices, fatigue, shop closures, and gate danger;
- season and temperature shown through Ren's immediate experience;
- a calendar event framework, beginning with a one-time Tanabata evening.
- hunter attributes: strength, agility, endurance, perception, mana, and luck;
- rotating physical training whose gains depend on Ren's health and energy;
- gradual Threat Sense mastery through patrols and dangerous gate experience;
- latent **Echo Fragment** growth from meaningful survival exposure rather than repetitive kills;
- all new development state preserved exactly across saves.
- a dynamic mood and morale state shaped by Ren's health, exhaustion, stress, and outcomes;
- transparent dialogue intentions such as asking for guidance, expressing gratitude, offering help,
  concealing worry, and apologizing;
- spoken exchanges with Aiko shown directly in Ren's chronicle, including her visible emotional reaction;
- lasting social consequences through trust, familiarity, affection, tension, and social confidence;
- bounded dialogue history preserved across save and resume.

The calendar roadmap also reserves space for Japanese public holidays, seasonal festivals, shops, scheduled auction days, random/story events, and expanded hunter and social stats.

## Project layout

```text
src/awakened_zero_rank/
  models.py       # Character, clock, progression, and event state
  world.py        # Tokyo locations, jobs, and transport costs
  actions.py      # Civilian and hunter actions
  agent.py        # Explainable utility-based decision policy
  simulation.py   # Deterministic world, memory, relationship, and progression engine
  journal.py      # Ren-centered scene presentation
  persistence.py  # Versioned save/load system
  environment.py  # Seasons, weather conditions, and environmental effects
  dialogue.py     # Dialogue intentions, NPC reactions, and social consequences
  cli.py          # Protagonist chronicle interface
tests/             # Determinism, world, and progression tests
```

## Run the simulation

Requires Python 3.11 or newer. From the repository root:

```bash
python -m pip install -e .
python -m awakened_zero_rank --days 12 --seed 42
```

The main output reads as Ren's chronicle. Reusing the same seed reproduces the same story. Save and resume a timeline with:

```bash
python -m awakened_zero_rank --days 7 --seed 42 --save saves/ren.json
python -m awakened_zero_rank --days 7 --load saves/ren.json --save saves/ren.json
```

Developers can add `--technical-log` to inspect decision reasons and utility scores.

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

✅ Milestone 6: exact save/load continuation and a protagonist-focused chronicle.

✅ Milestone 7: weather, seasons, calendar events, and environment-aware decisions.

✅ Milestone 8: expanded protagonist stats, ability growth, rotating training, and condition-sensitive progression.

✅ Milestone 9: mood, dialogue intentions, visible NPC reactions, and lasting social consequences.

Next: additional recurring characters, relationship networks, and dialogue shaped by conflicting loyalties.
