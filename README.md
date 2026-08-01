# AWAKENED: ZERO RANK

An observer-only life simulation set in Japan after portals and Awakened hunters become part of everyday society.

Ren Takahashi begins poor, unranked, and unknown. He chooses how to work, recover, train, build relationships, investigate Gates, and survive. The player watches; Ren remains autonomous.

Current release: **0.36.0** · **98 automated tests**

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
- Work, meals, rest, study, physical training, commuting, rent, arrears, and partial debt repayment that preserves emergency cash.
- Seeded weather, daily wage and meal variation, Tanabata, and Gate alerts.
- Health, energy, hunger, stress, morale, injury severity, clinic treatment with explicit emergency assistance, money, equipment, and inventory.

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

- Gymnasium-compatible fixed-horizon episodes with 12 integer actions and valid-action masks.
- A 22-value observation interface and compact 16-feature strategic state abstraction.
- Utility, heuristic, masked-random, and tabular Q-learning policies.
- Count-based exploration, phased curriculum rewards, deterministic multi-condition training schedules, per-condition state-coverage summaries, and held-out seed enforcement.
- Reward decomposition, action/mask frequencies, low-need recovery and social-action rates, safety metrics, preparation coverage and success, exploit indicators, and worst-seed traces.
- Deterministic Q-table checkpoints with action/condition schema validation, SHA-256 tamper detection, and authenticated version migration.
- Repeated independent trials with pooled confidence and an adoption gate that requires at least two recorded training episodes for every evaluation condition.
- Named, multi-horizon scenario suites with isolated held-out seeds and per-scenario safety metrics.
- Deterministic evaluation starts for standard life, financial pressure, injury recovery, Gate crises, and a compound medical/debt/Gate crisis.
- Versioned scenario-suite JSON reports with stable policy binding, SHA-256 identity, exact reload, tamper rejection, and backward-compatible schema loading.
- Explainable offline adoption decisions with checkpoint verification and explicit confidence, safety, progression, rent-recovery, action-dominance, and exploit blockers.

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

Unless marked resolved, these are hypotheses rather than scheduled changes. Each patch should be isolated, evaluated on held-out seeds across all stress conditions, and rejected if it improves reward while weakening survival, rent recovery, mission coherence, or behavioral variety.

Update 0.24 — Adoption Metrics now records rent payment, average dominant-action share, and RL exploit flags in every scenario report. These measurements are adoption gates; they do not tune the simulator by themselves.

Update 0.25 — Rent Recovery addressed the first measured soft-lock by adding a masked **Pay rent arrears** action that keeps a ¥600 emergency reserve. In the bounded four-seed, 40-step utility audit, financial-pressure rent recovery improved from 0/4 to 4/4, survival remained 4/4, dominant-action share fell from 47.5% to 24.4%, and no exploit flags appeared. Standard and Gate-crisis results were unchanged. The Q-table checkpoint schema advanced because the policy action set changed from 11 to 12.

Update 0.26 — Crisis Preparation made utility decisions plan-aware only at maximum Gate alert. In the same bounded audit, Gate-crisis preparation increased from 0 to 5 actions, completed missions increased from 7 to 8, survival and rent recovery remained 4/4, and no exploit flags appeared. Standard, financial-pressure, and injury-recovery behavior remained unchanged. The first Gate-crisis mission is now preceded by preparation without forcing every low-alert mission into the same pattern.

Update 0.27 — Prepared Mission Evidence replaced action-count inference with persistent prepared-mission counters. The four-seed Gate-crisis audit recorded nine attempts, eight completions, four consumed plans, and three prepared completions: 44.4% preparation coverage, 75% prepared success, and 88.9% overall success. This small sample measures behavior but does not establish that preparation causes a higher success rate. Schema-4 reports expose both rates, and older saves/reports default the new fields safely.

Update 0.28 — Compound Crisis Balance added a compound crisis combining severe injury, low energy, rent arrears, limited cash, and maximum Gate alert. It exposed rent repayment outranking urgent treatment, so repayment utility now decreases with injury severity and low health. Across four 60-step seeds, utility and heuristic both chose treatment first in 4/4 runs, survived 4/4, cleared arrears 4/4, and produced no exploit flags. Existing condition audits retained 4/4 survival and rent recovery.

Update 0.29 — Condition-Aware Training made fixed-horizon training condition-aware without changing the default. Gymnasium resets accept a named condition through options, Q-learning cycles a validated condition tuple deterministically, and every episode records its condition. Checkpoint schema 3 preserves the schedule and loads authenticated schema-2 checkpoints as all-standard training. Only tiny reproducibility tests were run; there is no new RL verdict.

Update 0.30 — Condition Summaries added deterministic per-condition training summaries without changing checkpoints or policy behavior. Each observed condition now reports its episode count, average environment and shaped reward, and worst episode reward, while incomplete diagnostic records fail explicitly. This is coverage evidence only; no larger RL experiment or new verdict was produced.

Update 0.31 — State Coverage records unique strategic states visited in every training episode and aggregates average and minimum coverage for each observed condition. Checkpoint schema 4 authenticates these diagnostics; schema-2/3 policies remain loadable with coverage explicitly unavailable. Training behavior is unchanged, and no large RL experiment or new verdict was produced.

Update 0.32 — Condition Alignment prevents a policy from being adoption-ready when an evaluation scenario uses a condition absent from its recorded training episodes. Scenario-report schema 5 authenticates covered, absent, or legacy-unknown evidence, and both absent and unknown coverage become explicit blockers. Policy behavior is unchanged, and no large RL experiment or new verdict was produced.

Update 0.33 — Exposure Thresholds records the exact number of training episodes for every evaluation condition and requires at least two before adoption can be considered. Scenario-report schema 6 authenticates the count, while legacy reports retain unknown exposure rather than fabricated evidence. The threshold changes only adoption diagnostics; no policy behavior, large RL experiment, or verdict changed.

Update 0.34 — Recovery Necessity Audit distinguishes all recovery from conservatively low-need eating and resting. Across four 40-step seeds in standard, injury-recovery, and compound-crisis conditions, low-need recovery ranged from 2.6% to 16.1% of decision steps and survival remained 4/4 in every condition. The evidence did not justify a utility nerf, so this update adds diagnostics only.

Update 0.35 — Treatment Access makes the existing clinic safety net explicit. Ren already received full treatment when unable to pay the calculated price; outcomes now separate his payment from the emergency assistance covering the balance. A severe-injury test at ¥0 confirms the full treatment effect remains available without negative money. Pricing and healing behavior are unchanged.

Update 0.36 — Social Frequency Audit adds explicit social-action counts and shares to episode and batch diagnostics. Across four 60-step seeds in standard, Gate-crisis, and compound-crisis conditions, utility chose 0–3 Aiko conversations, produced no exploit flags, kept dominant-action share below 31%, and survived 4/4 in every condition. The evidence did not justify a dialogue cooldown, so social behavior remains unchanged.

| Area | Evidence or risk | Candidate patch | Acceptance check |
|---|---|---|---|
| Passive repetition — monitored in Update 0.34 | Recovery occupied a visible share of utility decisions, but the new conservative low-need metric measured only 2.6%–16.1% across the bounded audit | Defer utility penalties unless repeated audits show low-need recovery dominance; never discourage food, sleep, or treatment under genuine need | Low-need recovery stays bounded without worse survival or injury recovery |
| Debt behavior — resolved in Update 0.25 | Rent arrears were impossible to repay after the deadline, making paid patrols dominate | Added partial repayment while preserving ¥600 emergency cash; no patrol nerf was needed | Recovery improved from 0/4 to 4/4, survival stayed 4/4, and dominant share fell from 47.5% to 24.4% |
| Gate pacing — resolved for utility in Update 0.26 | Maximum-alert utility runs attempted missions without preparation | Added plan-aware scoring only at alert 3/3; normal and lower-alert routines retain prior scores | Preparation rose from 0 to 5, completed missions rose from 7 to 8, and survival stayed 4/4 |
| Recovery access — resolved in Update 0.35 | Compound injury and debt made repayment outrank urgent treatment, while cash-limited clinic assistance was implicit | Repayment defers under severe injury or low health, and treatment outcomes now disclose the emergency subsidy when Ren cannot pay the full price | Utility and heuristic treated first in 4/4 runs; ¥0 treatment retains the full treatment effect and reports assistance explicitly |
| Social frequency — monitored in Update 0.36 | Utility chose 0–3 Aiko conversations per 60-step episode across standard and crisis audits, with no exploit flags and below-31% dominant-action share | Defer cooldowns unless repeated audits show social-action dominance; preserve crisis support and autonomous relationship growth | Social-action share remains bounded and relationship behavior stays varied |
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

## Update History & Roadmap

Completed updates are grouped for readability:

| Updates | Focus |
|---|---|
| 0.01–0.06 | Deterministic life simulation, Tokyo economy, hunter progression, relationships, equipment, and persistence |
| 0.07–0.09 | Weather, calendar events, expanded attributes, mood, and dialogue consequences |
| 0.10–0.13 | Learning interface, scalable content, NPC networks, investigations, preparation, and cooperation |
| 0.14–0.15 | Gymnasium episodes, reproducible Q-learning, held-out comparison, and failure diagnostics |
| 0.16–0.17 | Broader economic/recovery scenarios and stronger utility, heuristic, and random baselines |
| 0.18–0.19 | Improved tabular training, checkpoint integrity, repeated trials, and neural-readiness auditing |
| 0.20 | Multi-horizon held-out scenario suites, pooled verdicts, and conservative adoption checks |
| 0.21 | Canonical scenario reports, checkpoint binding, deterministic export, and integrity verification |
| 0.22 | Explainable policy-adoption decisions with identity, confidence, safety, and progression gates |
| 0.23 | Deterministic financial, injury, and Gate-crisis evaluation conditions with versioned reporting |
| 0.24 | Rent recovery, action dominance, and exploit metrics integrated into reports and adoption gates |
| 0.25 | Partial rent-arrears repayment, emergency-cash protection, and a measured financial soft-lock fix |
| 0.26 | Maximum-alert plan-aware utility scoring with preserved lower-alert behavior |
| 0.27 | Persistent prepared-mission counters, effectiveness rates, and backward-compatible schema-4 reports |
| 0.28 | Compound medical/debt/Gate stress testing and injury-aware repayment priorities |
| 0.29 | Gym reset conditions, deterministic multi-condition training schedules, and checkpoint schema 3 |
| 0.30 | Auditable per-condition training reward and coverage summaries |
| 0.31 | Per-episode strategic state coverage and authenticated schema-4 diagnostics |
| 0.32 | Training/evaluation condition alignment and schema-5 adoption evidence |
| 0.33 | Minimum condition-exposure thresholds and authenticated schema-6 counts |
| 0.34 | Low-need recovery diagnostics and an evidence-based no-nerf decision |
| 0.35 | Explicit emergency clinic assistance with preserved treatment access |
| 0.36 | Social-action frequency diagnostics and an evidence-based no-cooldown decision |

Near-term work should use the expanded scenario suite to measure and improve tabular consistency across different horizons and stress conditions. Neural RL remains deferred while the readiness gate is closed.

### Future international expansion

On timelines spanning roughly three or four in-world years, major portal disasters and other consequential events can emerge outside Japan. Different countries can develop their own Awakened institutions, regulations, economies, Gate responses, recurring characters, and recovery arcs. These events should affect news, markets, guild priorities, relationships, migration, and humanitarian needs rather than existing only as spectacle.

International travel should remain grounded: passports or clearance, airfare, lodging, travel time, language and local contacts, mission invitations, personal risk, and whether Ren can responsibly afford the trip. Ren should decide autonomously whether to travel, remain in Japan, contribute remotely, or decline. All global events and decisions must remain seeded, persistent, and reproducible.

### Future observer website

A later presentation update can add a read-only web dashboard showing time, weather, Ren's condition, current concern, decision journal, relationships, finances, inventory, Gate investigations, and chronicles. Lightweight sprite animation can visualize travel, work, rest, training, conversations, and Gate activity. Versioned evaluation reports can feed a separate developer-facing experiment view without coupling the website to training code.

The website must remain a view of the authoritative deterministic simulator. Pause, speed, seed, save, reset, and diagnostics are developer controls—not ways to choose Ren's life for him.
