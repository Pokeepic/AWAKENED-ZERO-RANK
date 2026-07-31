# AWAKENED ZERO RANK

An observer-only life simulation set in modern Japan after portals and awakenings become part of everyday society.

The protagonist begins poor, unranked, and unknown. They act autonomously while the player watches their daily routine, relationships, work, study, training, awakening opportunities, failures, and long-term growth.

## Core vision

- **Observer simulation:** the protagonist chooses; the user watches.
- **Zero-to-hero progression:** begin with little money, weak stats, and no hunter rank.
- **Persona-style time:** each meaningful action advances Morning → Afternoon → Evening → Late Night.
- **Living Japan setting:** rent, part-time work, school, transport, guilds, gates, and social pressure matter.
- **Explainable autonomy:** every decision is logged with its reason.
- **Learning-ready architecture:** start with a dependable rule/utility agent, then add reinforcement learning as an experiment.
- **Reproducible worlds:** seeded runs make bugs and balance changes comparable.

## V3 development workflow

1. **Deterministic simulation core** — clock, calendar, character state, needs, actions, and event log.
2. **Autonomous decision system** — utility scoring, goals, memory, and explainable choices.
3. **Japan world systems** — districts, economy, jobs, rent, gates, guilds, and hunter ranks.
4. **Dashboard** — observe time, status, decisions, relationships, and story events.
5. **Persistence and evaluation** — save/load, seeded batch runs, survival and progression metrics.
6. **Learning experiment** — train an RL policy in a separate environment and compare it with the baseline agent.
7. **Narrative layer** — turn important simulation events into readable scenes and chronicles.

## First playable milestone

The first milestone will let us run one autonomous protagonist for multiple days and inspect:

- current day and time slot;
- money, health, energy, hunger, stress, knowledge, fitness, and reputation;
- the selected action and the reason it was selected;
- part-time work, meals, rest, study, exercise, and early awakening events;
- a chronological event log;
- identical results when the same random seed is reused.

## Planned project layout

```text
src/awakened_zero_rank/
  domain/       # Character, time, actions, world state
  simulation/   # Engine and event processing
  agents/       # Utility baseline and later learning policies
  content/      # Japan locations, jobs, gates, events
  ui/           # Observer dashboard
tests/          # Deterministic and balance tests
docs/           # Design, workflow, and experiment notes
```

## Learning strategy

Reinforcement learning is not the entire simulation. The simulation is the environment; an RL agent is one possible decision-maker inside it. We will keep a transparent utility-based baseline so learned behavior can be measured against something stable, debuggable, and fun.

## Status

🚧 Foundation initialized. Next: implement and test the deterministic simulation core.
