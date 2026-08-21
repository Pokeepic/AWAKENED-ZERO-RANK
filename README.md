# AWAKENED: ZERO RANK

[![CI](https://github.com/Pokeepic/AWAKENED-ZERO-RANK/actions/workflows/ci.yml/badge.svg)](https://github.com/Pokeepic/AWAKENED-ZERO-RANK/actions/workflows/ci.yml)

An observer-only autonomous life simulation set in Japan after portals and Awakened hunters become part of everyday society.

Ren Takahashi begins poor, unranked, and unknown. He decides how to work, recover, train, form relationships, investigate Gates, and survive. The player watches rather than choosing his actions.

| Project status | Current value |
|---|---|
| Release | `0.273.0` |
| Python | 3.11+; CI-tested through 3.14 |
| Production controller | Transparent utility policy |
| Tabular RL verdict | **Baseline remains better** |
| Corrected ensemble verdict | **Inconclusive** |
| Automated tests | 293 |

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

Export the complete observer snapshot from an authenticated save without advancing or rewriting it:

```bash
awakened-zero-rank --observer-snapshot saves/ren.json
awakened-zero-rank --observer-snapshot saves/ren.json --snapshot-output snapshots/ren.json
```

Direct publication validates and stages canonical UTF-8 JSON before an atomic rename, creates parent directories, and refuses to overwrite an existing artifact. The presentation contract supports the same deployment-safe path:

```bash
awakened-zero-rank --observer-presentation-contract
awakened-zero-rank --observer-presentation-contract --presentation-contract-output public/observer-contract.json
awakened-zero-rank --verify-observer-presentation-contract public/observer-contract.json
```

Publish both verified files as one non-overwriting, directory-level transaction from an authenticated save:

```bash
awakened-zero-rank --publish-observer-site-data saves/ren.json public/data
awakened-zero-rank --verify-observer-site-data public/data
```

The publish command creates `observer-contract.json` and `observer-snapshot.json` together and prints their paths, schemas, and SHA-256 identities for deployment logs. Verification requires exactly those two files, validates both identities and their shared observer schema, rejects directory drift, and never rewrites the artifact.

Verify a previously exported observer snapshot without rewriting it:

```bash
awakened-zero-rank --verify-observer-snapshot snapshot.json
```

Compare two verified observer snapshots without rewriting either file:

Comparison schema 8 reports sorted changed sections, signed clock movement, recent-activity relationships, copied appended-event data, stable animation cues, whether seeds match, a directional clock relation, and a conservative presentation mode. The modes are `unchanged`, `animate`, `refresh`, or `replace`. Seed equality is useful continuity metadata but does not claim that two saves are an unbranched timeline; animate only means the verified clock moved forward on the same seed.

```bash
awakened-zero-rank --compare-observer-snapshots before.json after.json
awakened-zero-rank --compare-observer-snapshots before.json after.json --require-identical
awakened-zero-rank --compare-observer-site-data previous/data current/data
awakened-zero-rank --compare-observer-site-data previous/data current/data --require-identical
awakened-zero-rank --compare-observer-site-data previous/data current/data --observer-site-comparison-output artifacts/deployment-comparison.json
awakened-zero-rank --inspect-observer-site-comparison artifacts/deployment-comparison.json
```

Snapshot verification detects accidental corruption and unchanged-digest tampering. It also rejects re-digested impossible values throughout the schema-4 world projection and inconsistent activity, clock, portal, progression, social, and story relationships. It does not prove authorship because anyone who changes valid content can calculate a new digest.

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
| `src/awakened_zero_rank/observer.py` | Stable read-only application snapshot |
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

Six fixed story anchors arrive at roughly six-month intervals from day 183 through day 1,095. They cannot be avoided or moved, but each resolution reflects Ren's accumulated hunter rank, trusted relationships, and discovered portals. The final anchor closes the three-year chronicle with an ending shaped by that history. Every anchor has distinct authored outcomes for `isolated`, `resilient`, and `prepared` resolutions, plus a recurring-character scene and a portal-specific consequence. From the Tokyo Fracture onward, international continuity links the forged signal, a Busan response corridor, the guild hearing, and the final civilian warning network. Event prose names relevant trusted characters and the latest discovered portal when that evidence exists. The resolved tier is saved in world state, and the observer summary reports current arc progress plus the latest result. `story_progress(state)` exposes the same chronology through schema-4 mutation-free JSON with authenticated premise, scene, portal consequence, international link, completed entries, next-anchor timing, and ending status for dashboards and tools. Saves from the brief pre-ledger story release migrate completed anchors as `legacy-unavailable` rather than inventing a readiness result, and resolved anchors must remain a chronological prefix. Completed arcs now resolve into one of five deterministic named endings—`The Unfinished Warning`, `The Scarred Watch`, `Tokyo's Quiet Guardian`, `The Open Corridor`, or `The Zero-Rank Horizon`—while legacy histories remain explicitly unavailable.

### Story and content growth

Expand the catalog through authored dialogue, recurring characters, portals, encounters, equipment, locations, and consequences. New content should deepen character identity and world continuity rather than only multiplying random combinations. Delayed investigation consequences resolve as background effects alongside Ren's real decision, so they can change relationships and the world without consuming one of his four daily action slots.

Deepen each anchor with recurring-character scenes, portal-specific consequences, international links, and more varied endings without turning the observer-only simulation into a scripted choice game.

### Advanced learning research

More expressive RL can be explored after the world and story state are represented safely. Candidate approaches must remain reproducible, train only on separated seeds, pass small pilots before larger runs, and beat the utility controller on held-out reward, survival, progression, and exploit checks before adoption.

### International expansion

On timelines spanning roughly three or four in-world years, major portal disasters and other consequential events can emerge outside Japan. Countries can develop distinct Awakened institutions, regulations, economies, Gate responses, recurring characters, and recovery arcs.

International travel should remain grounded in passports or clearance, airfare, lodging, travel time, language, local contacts, mission invitations, personal risk, and whether Ren can responsibly afford the trip. Ren should autonomously decide whether to travel, remain in Japan, contribute remotely, or decline.

### Observer website

Version 0.228.0 provides the first production-shaped observer surface in `site/`: a responsive, control-free chronicle that verifies both the presentation contract and snapshot identities in the browser before rendering Ren's current condition, goal, recent decisions, hunter record, story countdown, relationships, portals, and content identities. After the first trusted load it refreshes the artifact pair every 60 seconds without cache reuse, keeps the last verified chronicle visible through transient refresh failures, pauses network work in hidden tabs, refreshes immediately when the page becomes visible, and never exposes simulation controls. The client treats downloaded JSON as unknown and applies executable runtime guards to every field it renders before canonical SHA-256 verification. Explicit contract, snapshot, resource, activity, relationship, and story types are returned only after that boundary passes. When a later verified snapshot identity changes, the page announces the advance and applies one brief visual pulse; initial and unchanged loads stay quiet, and reduced-motion preferences disable the animation. Section titles use real heading semantics, world conditions have a named navigation landmark, verification changes use an atomic live status, and Ren's five condition meters expose labeled 0–100 progress values. Version 0.200.0 corrects canonical share metadata and adds a keyboard-visible skip link to the chronicle landmark. Version 0.201.0 keeps that landmark valid while authenticating or offline, announces verification as a polite busy status, and reports terminal first-load verification failure as an alert. Version 0.202.0 replaces the remaining generic site manual with production observer guidance and removes three unreferenced starter assets. Version 0.203.0 displays the UTC time of the latest successfully authenticated artifact pair outside the live status region, making data freshness visible without noisy routine announcements. Version 0.204.0 adds matching document and robots.txt no-crawl policies for the current private deployment; those policies should be deliberately revisited before any approved public launch. Version 0.205.0 marks trusted data delayed immediately when the browser goes offline and reauthenticates the artifact pair as soon as connectivity returns. Version 0.206.0 validates the authenticated named-ending projection and renders completed three-year arcs without undefined anchor or countdown values. Version 0.207.0 gives valid empty decision, relationship, and portal collections explicit observational states rather than blank panels. Version 0.208.0 rejects browser-side story chronology contradictions, including altered countdowns, premature completion, and ending outcome counts that do not cover every anchor. Version 0.209.0 also rejects unsupported, duplicated, out-of-order, or future recent-activity positions before rendering. Version 0.210.0 accepts valid signed integer trust from -100 through 100 while rejecting fractional, out-of-range, duplicated, or non-canonical relationship data. Version 0.211.0 requires the browser-rendered environment to match the simulator's five canonical Summer weather/temperature pairs and Gate alert range. Version 0.212.0 permits only unique names from the simulator's six authored portal profiles in the browser-rendered discovery ledger. Version 0.213.0 restricts rendered ranks and locations to the simulator domain and requires integer condition, money, and progression values within their authenticated bounds. Version 0.214.0 binds the browser-rendered story countdown to the simulator's exact six authored anchors and fixed three-year schedule. Version 0.215.0 validates the exact three named endings while correctly accepting honest legacy-unavailable histories whose unknown tiers are not counted as invented outcomes. Version 0.216.0 rejects unsupported or missing observer and story schema versions before rendering. Version 0.217.0 restricts browser-rendered relationships to the four authored recurring characters and their canonical roles. Version 0.218.0 rejects integer values that cannot be represented exactly by the browser. Version 0.219.0 prevents completed story anchors or endings from appearing before their fixed authored day. Version 0.220.0 restricts the browser-rendered protagonist identity, ability, and mood to simulator-authored values. Version 0.221.0 requires rank and ability to form a possible protagonist lifecycle. Version 0.222.0 requires exact rendered record shapes and authenticates each upcoming story anchor key. Version 0.223.0 requires the complete authored read-only presentation contract and vocabulary. Version 0.224.0 requires the complete schema-4 snapshot envelope and structural projections. Version 0.225.0 validates authored economy values and bounds before trusting the snapshot. Version 0.226.0 validates the full hunter progression record and mission-counter consistency. Version 0.227.0 validates canonical inventory and equipped item kinds while preserving future item names. Version 0.228.0 validates all five authenticated relationship metrics and their signed or unsigned bounds. The checked-in seed-42 day-11 dataset is deterministic demonstration content and can be replaced atomically with `--publish-observer-site-data`.


Version 0.229.0 validates complete authenticated portal investigations, including metric bounds, collaborators, canonical ordering, and active-plan consistency. Version 0.230.0 validates the complete key-memory ledger and its canonical priority order. Version 0.231.0 binds completed story records to their declared count and canonical anchor prefix. Version 0.232.0 authenticates every completed anchor's focus characters and authored outcome prose. Version 0.233.0 reconciles ending counts, final tier, legacy status, and named ending with that authenticated ledger. Version 0.234.0 accepts portable string path provenance without including it in authenticated content identity. Version 0.235.0 accepts signed, exactly representable deterministic simulation seeds. Version 0.236.0 requires every investigated portal to appear in the discovery ledger. Version 0.237.0 enforces the same hunter rank and ability lifecycle across browser artifacts, Python verification, and saves. Version 0.238.0 reconciles hunter rank with the simulator's immediate promotion thresholds. Version 0.239.0 requires completed-mission evidence for every accumulated rank point. Version 0.240.0 requires those points to be an exact composition of the authored 10, 13, and 17-point mission awards. Version 0.241.0 authenticates the fixed day-8, ¥8,000 rent contract and rejects contradictory payment and arrears ledgers. Version 0.242.0 prevents rent payments or arrears from appearing before the day-8 Morning deadline has been processed. Version 0.243.0 binds Unranked and awakened hunter states to the fixed day-3 Afternoon Awakening event. Version 0.244.0 requires Ren's displayed goal to match his authored lifecycle, arrears, and current rank. Version 0.245.0 binds Guild registration and Aiko Sato's relationship record to the fixed day-4 Morning event. Version 0.246.0 authenticates the fixed introduction chronology for Daichi Mori, Mei Kuroda, and Haruto Ishikawa. Version 0.247.0 verifies each recurring character's authored starting relationship evidence at the exact introduction boundary. Version 0.248.0 binds the Awakening assessment and Guild registration boundaries to their authored locations. Version 0.249.0 authenticates initial ability mastery and Gate alert evidence at those boundaries. Version 0.250.0 requires an empty hunter mission record at both fixed lifecycle boundaries. Version 0.251.0 requires an empty hunter loadout at both boundaries. Version 0.252.0 requires an empty portal ledger at both boundaries. Version 0.253.0 authenticates the latest fixed-event record at both boundaries. Version 0.254.0 authenticates their fixed-event memories. Version 0.255.0 prevents hunter-shop visits from predating Guild registration. Version 0.256.0 prevents hunter equipment from predating the Guild shop unlock. Version 0.257.0 prevents portal evidence from predating Guild registration. Version 0.258.0 prevents hunter mission progress from predating Guild registration. Version 0.259.0 prevents ability mastery from predating Awakening.

Version 0.260.0 completes the ability-mastery lifecycle by preventing awakened timelines from reverting mastery to zero. Version 0.261.0 authenticates fixed-event memory presence across their complete lifecycles. Version 0.262.0 brings save-event clock validation into parity with observer snapshots. Version 0.263.0 requires saved event positions to be strictly chronological. Version 0.264.0 requires complete action, reason, and outcome text in every saved event. Version 0.265.0 prevents blank memory summaries from entering saved chronicles. Version 0.266.0 requires complete text in every dialogue exchange. Version 0.267.0 requires saved dialogue history to remain chronological. Version 0.268.0 requires complete source and description text for delayed consequences. Version 0.269.0 requires every saved portal investigation to name its preparation strategy. Version 0.270.0 completes the production observer surface and its responsive, accessibility, integrity, and delivery hardening. Version 0.271.0 deepens the fixed arc with recurring-character scenes, portal consequences, international continuity, and authenticated observer rendering. Version 0.272.0 expands the evidence-derived ending catalogue from three to five named outcomes. Version 0.273.0 prevents delayed investigation consequences from consuming autonomous action slots.

The production observer now covers time, weather, Ren's condition and intent, explained decisions, finances, inventory, hunter progression, story history, relationships, portal investigations, memories, and authenticated artifact identity. Lightweight sprite animation remains an optional future presentation layer rather than a requirement for the completed read-only web checkpoint.

The observer is a real managed website rather than a local-only developer demo. It includes responsive phone, tablet, and desktop layouts, reduced-motion and increased-contrast support, secure read-only data delivery, visible freshness and failure states, and managed version rollback. Access remains deliberately private; a future public launch is an access-policy decision, not unfinished web development.

The website must remain a view of the deterministic simulator. Pause, speed, seed, save, reset, and diagnostics are developer controls—not ways to choose Ren's life for him. Published experiment bundles and comparison artifacts can power a separate developer view without coupling presentation code to training. `observer_snapshot(simulation)` now provides the schema-4, mutation-free, SHA-256-identified JSON boundary for current world, economy, protagonist, relationship, portal, story, and bounded recent-activity state; it exposes no control hooks. Comparison schema 8 adds a stable `animation_cue` beside the copied `appended_event`, so public clients can select accessible motion or sprite treatments without parsing prose or duplicating simulator rules. `observer_presentation_contract()` and `--observer-presentation-contract` expose the versioned cue, update-mode, and activity-relation vocabularies as read-only JSON with no control capabilities. Contract schema 2 adds canonical `contract_sha256` cache identity; it is not a signature or authority token. `verify_observer_presentation_contract()` and `--verify-observer-presentation-contract FILE` authenticate downloaded contract structure, content, and supported vocabulary without rewriting it. `save_observer_presentation_contract()` and `--presentation-contract-output FILE` publish the exact canonical contract through a verified, atomic, non-overwriting path suitable for a static public-site build. `publish_observer_site_data()` and `--publish-observer-site-data SAVE DIR` stage, reread, cross-check, and atomically publish the contract and authenticated snapshot as one non-overwriting static-site data directory. `verify_observer_site_data()` and `--verify-observer-site-data DIR` enforce the exact two-file boundary, both content identities, and schema compatibility through a read-only deployment check. `compare_observer_site_data()` and `--compare-observer-site-data LEFT RIGHT` verify both deployments before reporting contract continuity and the complete schema-8 snapshot update, animation, activity, and clock semantics; `--require-identical` makes this usable as a CI deployment-drift gate. `save_observer_site_comparison()`, `--observer-site-comparison-output FILE`, and `--inspect-observer-site-comparison FILE` preserve that decision as a schema-1, content-addressed, strictly validated, non-overwriting artifact without embedding machine-specific deployment paths. Compatible historical actions use `other`, while non-append comparisons return `null` and never imply shared lineage.

### Future game adaptation

After the deterministic simulator, complete story content, balance evidence, and observer website are mature, a separate game adaptation can add presentation, exploration, and player interaction. The simulator should remain the canonical world model, while the game consumes stable story, save, and dashboard APIs instead of rewriting proven simulation rules.

A playable version should favor an approachable point-and-click structure: inspect locations, objects, evidence, and conversations; choose what the player notices or suggests; and let the canonical simulation resolve Ren's autonomous response and consequences. It should define its own failure handling, accessibility, pacing, controls, art, audio, and save experience. Player-directed outcomes must be evaluated separately from autonomous-agent and RL evidence so the research verdicts remain honest.

An optional future "echo advisor" can turn a separately evaluated, frozen RL policy into a split-personality-style companion that offers contextual tips and commentary. It should never silently choose for the player, must be clearly optional and can be muted or disabled, and should communicate uncertainty. The current tabular policy is not ready for that role: the held-out verdict remains that the utility baseline performs better.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for deterministic-development rules, test expectations, held-out evaluation requirements, and pull-request guidance.

## Project history

See [CHANGELOG.md](CHANGELOG.md) for the complete update record, balance evidence, rejected experiments, schema migrations, and reporting-tool history.
