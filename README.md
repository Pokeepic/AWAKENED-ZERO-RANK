# AWAKENED: ZERO RANK

[![CI](https://github.com/Pokeepic/AWAKENED-ZERO-RANK/actions/workflows/ci.yml/badge.svg)](https://github.com/Pokeepic/AWAKENED-ZERO-RANK/actions/workflows/ci.yml)

A deterministic autonomous-life simulation and a separate private time-management RPG set in an awakened Tokyo.

The project has two distinct modes. In **Observer**, autonomous Ren decides how to live and survive. In **Game**, you play as Ren: your actions move a local four-slot calendar and change his RPG resources without rewriting the Observer timeline.

| Status | Value |
|---|---|
| Release | `0.1460.0` |
| Python | 3.11+; CI-tested through 3.14 |
| Production controller | Transparent utility policy |
| RL adoption verdict | **Baseline remains better** |
| Automated tests | 339 Python + 155 browser |
| Website access | Private, owner-only |

## Play the private web game

[Open AWAKENED: ZERO RANK](https://awakened-zero-rank-observer.pokeepic.chatgpt.site/game)

The game now opens on a restrained cinematic title screen set inside Ren's apartment. It supports mouse, touch, and game-style keyboard navigation: focus begins on Continue, Up/Down moves through choices, Enter activates, Escape backs out, and M toggles rain audio. Ambience fades around play and tab visibility while persistent settings retain sound, motion, and text choices.

Tokyo locations now keep their playable scene visible while work, training, and shopping sit in compact in-world activity drawers. The native controls work with keyboard, touch, and screen readers; the most immediately useful action opens by default while optional activities stay out of Ren's way.

Food is now part of Ren's survival budget. Once per day he can spend ¥650 and one apartment time slot on a proper meal, restoring 18 energy and 3 health. Recovery remains capped by the core state engine, and the action cannot be repeated to farm health in the same day.

Outbound Tokyo travel now costs ¥220 alongside its six-energy and one-slot commitment. Every route shows the complete cost before selection and unaffordable trips are blocked, while Ren can always return home without a cash charge so the economy cannot strand a save away from the apartment.

Haruto's Akihabara counter now sells individual field consumables after Ren arrives: ¥350 bandages, ¥500 energy drinks, and ¥900 ward charms. Purchases respect the existing three-item and one-ward pack limits, equip immediately, and do not spend another time slot after travel.

The Tokyo Hunter Guild now includes a licensed medical wing. Once per day Ren can pay ¥1,800 and spend one time slot to restore up to 25 HP. The clinic refuses unnecessary full-health treatment and unaffordable care, while all recovery remains capped by the core state engine.

The campaign journal now opens with a four-period day ledger. Morning, Afternoon, Evening, and Late Night are marked as spent, current, or still open, making the Persona-style clock readable without adding interface tabs or changing the underlying save format.

The title menu and playable campaign now share one release label. This removes the stale pre-arc version that remained on the live title screen and prevents those two player-facing surfaces from drifting apart in later releases.

The private title screen now disables speculative RSC prefetch on its Observer links. Normal navigation is unchanged, while the workaround avoids a confirmed vinext beta runtime fault that previously filled the deployed browser console during title initialization.

That safeguard now covers every RPG chapter through one shared game-link component. Apartment, city, caseboard, field, bond, awakening, deadline, debrief, and relay navigation retain normal clicks while avoiding the faulty speculative prefetch path.

The title screen now includes a dedicated Save Data panel. Players can download a portable JSON backup of Ren's local campaign and restore it later; restore files are size-limited and must pass the complete current save-schema validation before they can replace the active run. The authenticated Observer remains separate and unchanged.

Verified backups are now staged instead of loading immediately. The title screen compares the active campaign with the incoming timeline, day, slot, and action count, then requires an explicit confirmation; canceling leaves the current save untouched.

Ren's apartment now follows the local RPG calendar. Morning, afternoon, evening, and late night use distinct lighting; deterministic daily weather adds rain or snow beyond the closed window; and recent winter snowfall leaves visible outdoor accumulation that can build across several days. New illustrated night and snowbound apartment variants preserve the established pixel-art layout.

Tokyo's three district maps now share that same living calendar. Central Tokyo, the East Loop, and the Adachi Fringe use dedicated illustrated morning and late-night variants, keep the established dusk art for afternoon and evening, display the current season and weather, animate outdoor rain or snow across the full map, and retain the current winter snowpack while every route and contact remains usable.

Adachi now keeps that atmosphere after Ren leaves the route board. The investigation caseboard and Gate battle select the same morning, dusk, or late-night district illustration from the local RPG clock, carry rain or snow into the scene, and preserve recent winter accumulation so field continuity no longer resets between chapters.

The caseboard has received a focused visual QA pass. Ren's field marker is once again anchored inside the map instead of being clipped by a stronger generic text rule, and the opening copy is compact enough to bring the investigation board into a normal laptop viewport while preserving full-size evidence cards.

The Gate battle now opens closer to its tactical controls on laptop-height screens. The compact field introduction brings the first exact move preview into the initial viewport without shrinking the encounter artwork, compressing combat information, or changing any battle calculation.

Tokyo's route board now behaves like the game's main working hub from the first screen. A compact introduction removes the oversized empty band between Ren's status and the district controls, revealing substantially more of the active map without shrinking its artwork or changing travel flow.

The RPG is being rebuilt around three possible one-year timelines. Ordinary death is a real Game Over; retrying begins a new run of the same timeline and grants no transmigration benefit. On Day 365, an explicit ledger checks survival, mastery, evidence, bonds, health, location, and the final choice before a residual path can open. The first timeline begins with Ren's mocked Zero-Rank skill, Residual Read, and four unequal arc deadlines at Days 45, 120, 240, and 365.

Each successful transmigration now produces another awakening scene. Timeline 2 begins with Vector Step; the second and final transmigration begins Timeline 3 with a third skill, Causal Sever. Causal Sever can break one selected causal link, but begins at zero mastery and cannot create a fourth timeline.

Timeline 3 now has a complete playable year rather than ending after its awakening. The four fixed deadlines recur, Haneda switches to final-timeline training for Causal Sever, and Ren can map the Black Gate's causal spine at 40% mastery before forging a severance key at 100% mastery with a trusted bond. The final Black Gate ledger recognizes those preparations, but still offers no fourth transmigration.

A fully prepared Timeline 3 Ren can now choose a true ending at the Black Gate. Residual Read identifies the founding wound, Vector Step reaches it through the collapse, and Causal Sever removes the Gate's sustaining cause without erasing Tokyo or Ren's relationships. This completes the campaign permanently for that local chronicle; an unprepared attempt remains unavailable and ordinary lethal choices still end the run.

Timeline 3 begins differentiating its repeated crises at the Day 45 deadline. With 25% Causal Sever mastery, Ren can remove the initiating cause of Route C's collapse while preserving both the evacuation and its authenticated trace. Timeline 1 and Timeline 2 retain their original choices.

The Day 120 crisis now has a Timeline 3 solution at 55% Causal Sever mastery. Ren can remove the common trigger synchronizing all seven breaches, preserving the district, witnesses, evidence, and Aiko's trust without replaying Vector Step's route-by-route rescue.

The Day 240 command purge completes the Timeline 3 deadline set. At 85% Causal Sever mastery, Ren can cut the forged orders away from emergency command itself, restoring the authentic response network while Daichi preserves the proof and publishes the conspiracy.

The Black Gate true ending now requires the distinct Causal Sever resolution from all three earlier Timeline 3 deadlines. Mastery and final preparation alone are insufficient: Ren must demonstrate that he can remove a destructive cause without erasing the people, evidence, and trust surrounding it.

Timeline 2 now unlocks the hidden Haneda Residual Relay. Ren can train Vector Step, redeem earned loop lottery tickets through reproducible draws, decode the Busan residual signal at 40% mastery, and construct the second-loop anchor after mastering Vector Step and building a bond of 6. The relay and its objectives remain invisible in Timeline 1.

Timeline 2 now replays all four yearly deadlines instead of bypassing the arc structure. Remembered routes add Vector Step alternatives at 20%, 50%, and 80% mastery on Days 45, 120, and 240, while the original Timeline 1 solutions remain available. The Day 365 residual path additionally requires 100% Vector Step, the decoded Busan signal, and a completed anchor before the second transmigration can open.

Arc I now ends automatically on Day 45 at Adachi Evacuation Route C. Ren's available choices and survival odds reflect whether he secured the causal trace earlier and whether Residual Read has reached 20% mastery. The resolution consumes the remainder of the day and commits either authenticated evidence, a changed Aiko bond, a persistent arc failure, or an ordinary Game Over.

Arc II resolves automatically on Day 120 during a district-wide synchronized breach. Arc I proof reduces the physical cost, an Aiko bond of at least 2 enables a coordinated evacuation success, and 40% Residual Read mastery makes the dangerous live-network read survivable. Arriving without those preparations can permanently lose evidence or end the run.

Arc III resolves automatically on Day 240 inside Tokyo's compromised emergency command network. Arc II evidence exposes the forged dispatch chain, Daichi bond 2 lets the Guild publish it without Ren, and 65% Residual Read mastery makes a direct command-core read survivable. Failure can bury the evidence or kill Ren before the Black Gate arc.

The first year now reaches its automatic Day 365 Black Gate finale. Fighting the impossible Gate ends the run; reading its collapse can preserve temporal residue and open the ending ledger, but only a fully prepared Ren can satisfy every condition for the optional first transmigration. The Gate is not defeated in Timeline 1.

The current playable opening contains seven connected, authenticated chapters:

1. **Worthless Awakening** — begin a new game with a shot-directed Bureau assessment cinematic and receive Residual Read at Rank Zero.
2. **Apartment prologue** — explore Ren's pixel-art apartment and take his next action.
3. **Tokyo district maps** — move through Central Tokyo, the East Loop, and Adachi Fringe as Ren.
4. **Adachi Gate field** — inspect illustrated case files and choose Ren's risk response.
5. **First Contact** — fight a deterministic Gate sentinel with visible damage, energy costs, and a safe retreat.
6. **After the Gate** — choose how Ren answers Aiko and build a persistent local RPG bond.
7. **The Patrol Record** — debrief the mission with Daichi and decide whether the Guild receives rank or truth.

Exploration uses tiny transparent pixel chibi sprites, while canon and bond scenes switch into a visual-novel presentation with full-size illustrated characters and location-specific backgrounds. After the Gate at Adachi Station now leads into Daichi's patrol debrief inside the Tokyo Hunter Guild. Dialogue advances by click, Enter, or Space, numbered choices support keys 1–3, and an expandable history preserves each scene's lines. Canon events unlock in sequence and cannot be replayed for duplicate rewards. Local bonds and campaign state remain separate from the authenticated autonomous Observer save.

Optional contacts now follow deterministic local schedules. Tokyo's map shows who is available, who is away, and their normal hours; Ren may still travel to an empty location, but spending time and gaining a bond point requires the person to be present and is limited to once per day. Mandatory canon meetings bypass optional schedules so story progress cannot soft-lock.

Tokyo now supports a complete location-based work loop. After traveling, Ren can take a Guild patrol, market courier run, library indexing shift, or hazardous Gate perimeter watch. Every job declares its pay, energy cost, and any health or mastery consequence before confirmation, spends one time slot, and can be completed only once per location each day. This gives the permanent equipment and supply economy a sustainable deterministic income source.

Ren's apartment now has its own persistent monthly rent ledger. The ¥8,000 payment covers 30 campaign days; missed periods become cumulative arrears when the calendar crosses a due date. The envelope shows the exact balance and paid-through date, and transferring rent does not consume a time slot. Existing local saves migrate as current through their present billing period instead of receiving retroactive debt.

Housing pressure now remains visible after Ren leaves home. The shared RPG HUD shows his paid-through day or exact arrears on every chapter, turns amber during the final five days of a billing period, and raises an accessible red alert when rent is overdue. The compact housing row collapses cleanly beneath the other survival resources on narrow screens.

Residual Read now has a deliberate city training loop. After traveling to the Hunter Guild, Ren can run a controlled drill for 6% mastery at a cost of 20 energy. At the Adachi Gate perimeter, he can risk a live boundary read for 10% mastery, 28 energy, and 6 HP. Each option previews its exact outcome, consumes one time slot, is limited to once per location per day, and stops cleanly at 100% mastery.

Tokyo travel now respects the same fixed-slot economy on the way home. Opening the route map from Ren's apartment and cancelling it remains free, but once Ren has actually traveled elsewhere, returning home consumes one slot and four energy. The transition is recorded in the campaign journal and can trigger the same deterministic deadline and rent processing as every other committed action.

Gate combat now telegraphs the sentinel's next attack before every turn. Strike, barrier, and guard choices show exact outgoing damage, energy cost, and incoming damage; exposed-core rounds reward aggression, while pressure surges reward defense. Later timelines add mastery-gated Vector Step and Causal Sever moves, and number keys plus R provide complete keyboard control. Combat remains fully deterministic and advances the campaign clock only when Ren wins, retreats, or dies.

The caseboard now carries Ren's selected Gate and approach into the field. The Glass Office Labyrinth contains the faster Fracture Sentinel, while the harder Sunken Courtyard contains a Drowned Archivist with its own health, telegraphs, exposed phase, visual treatment, and reward. Preparing adds mitigation, investigating marks a damage weakness, and rushing accepts extra incoming damage; every modifier is shown before Ren commits to a move.

Ren's apartment field bag now holds a persistent, bounded combat kit. A ¥900 restock consumes one time slot and provides two bandages, two energy drinks, and a ward charm. In battle, bandages restore 18 HP and energy drinks restore 22 energy while still allowing the telegraphed enemy attack; the ward reduces every incoming hit by two. Supply use and mid-encounter health and energy are saved immediately, preventing refresh-based item duplication.

Haruto's Akihabara Market now sells permanent equipment after Ren travels there. The ¥4,500 Resonance Blade adds three damage to every combat move, while the ¥3,500 Guildweave Coat removes two damage from every enemy attack. Buying equips the item immediately without charging another time slot, owned gear is disabled at the counter, and exact combat previews include both bonuses. New runs begin with a Utility Knife and Street Jacket.

Optional meetings now reveal authored bond moments instead of only increasing a number. Aiko, Daichi, Haruto, and Mei each have four relationship chapters spanning distant, familiar, trusted, and unbreakable ranks; final-rank scenes in later timelines acknowledge Ren's sense of a remembered life. Rank 10 closes the optional progression cleanly instead of consuming more time for no reward.

Those optional meetings now play as full-screen visual-novel encounters rather than city result cards. Each contact has a location-specific stage, full-size character presentation, two authored lead-in beats, three role-play choices with distinct energy costs and replies, keyboard progression, and an explicit relationship/time result before returning to Tokyo. New production art completes Haruto's Akihabara night market scene and Mei's restricted Ueno archive scene.

Long campaign stretches now support an ordinary-routine action that advances up to seven days at once. It always stops at the current arc deadline, returns Ren home on the following morning, records the passage in his journal, and gives only modest work income and energy recovery; the skipped social, training, and investigation opportunities remain permanently spent.

Routine passage now requires an explicit in-world confirmation. Before committing, the apartment panel names the approaching arc and deadline, the maximum number of surrendered time slots, the modest routine return, and the irreversible loss of meetings, investigations, and training; cancelling leaves Ren's save untouched.

Canon scenes now flow out of normal RPG play instead of a chapter menu. Resolving the first Gate automatically triggers Aiko's station scene and consumes the rest of that day; later, traveling to the Hunter Guild after that scene automatically triggers Daichi's one-slot debrief. Each event remains one-time and criteria-driven.

The RPG no longer uses a persistent destination bar or apartment workspace tabs. Ren leaves home by clicking the apartment door, then navigates through locations and scene exits inside the world.

Apartment interactions are aligned to the illustrated room: the exit sits on the actual entry door, Ren stands in the open floor, and clue prompts sit beside their matching furniture or object.

Ren's apartment is framed as a first-person point-and-click scene, so Ren does not stand inside his own viewpoint. His illustrated portrait appears only when he speaks after an action, while small pixel sprites remain reserved for outdoor maps, travel, and field scenes.

The campaign journal now shows the active local autosave and its current day, slot, and location. Starting a new game requires a clear confirmation that displays existing progress and can be cancelled with Escape; the autonomous Observer save is never touched.

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
