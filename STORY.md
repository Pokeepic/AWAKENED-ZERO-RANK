# AWAKENED: ZERO RANK — Campaign canon

## Premise

Ren Takahashi awakens with **Residual Read**, a Zero-Rank skill that can perceive traces left by abilities, Gates, emotions, and deaths but grants no obvious combat power. The Guild treats it as worthless. Over one year, Ren discovers that minor Gate incidents are preparations for the Black Gate that will consume Tokyo on Day 365.

The campaign has at most three timelines. Every timeline lasts one year. Death before the final day is Game Over and never causes transmigration. Reaching Day 365 alive only creates a *chance* to transmigrate: Ren must satisfy that timeline's evidence, bond, mastery, location, and final-choice conditions.

## Hell-difficulty rules

- Four time slots pass each day: Morning, Afternoon, Evening, and Late Night.
- Actions consume time and can permanently miss people, evidence, rescues, or arc deadlines.
- Retreat is a legitimate survival decision; zero health ends the run.
- A failed deadline changes the surviving cast and later routes instead of simply rewinding time.
- Transmigration is never automatic and never rescues an ordinary death.
- The first Black Gate cannot be defeated. Its real objective is to discover and activate the residual path.
- The third timeline is final. No fourth path exists.

## One-year arc clock

### Arc I — Worthless Awakening (Days 1–45)

Ren struggles with rent, registration, and low-rank work while learning that Residual Read records causal traces others cannot see. The deadline is the first abnormal Gate report. Ren must survive long enough to authenticate a trace before the Guild destroys the evidence.

### Arc II — The Adachi Countdown (Days 46–120)

Synchronized pulses target neglected districts. Aiko maps civilians and Daichi challenges abandoned patrol routes. Ren can reduce the collapse, but limited time forces him to choose whom and what to save.

### Arc III — Tokyo's False Orders (Days 121–240)

Forged Guild commands split Tokyo's responders. Mei identifies a portal signature inside their timestamps while Haruto builds an independent supply route. Ren must connect evidence, people, and surviving districts before the conspiracy isolates them.

### Arc IV — The Black Gate (Days 241–365)

Every recorded anomaly converges on a city-ending Gate. In the first timeline victory is impossible. Ren's only path forward is to reach its residual core alive, understand what it is doing, and fulfill the hidden conditions for transmigration.

## Timeline I — The Doomed Year

Ren has Residual Read, few choices, no reputation, and almost no resources. The year teaches the player the deadlines and the cost of the catastrophe. On Day 365, an eligible Ren may choose to read the collapsing Gate instead of fighting it and return to Day 1. Otherwise the run ends.

## Timeline II — The Defiant Year

Ren retains selected legacy knowledge and awakens **Vector Step**, a respectable short-range displacement skill. Residual Read reveals a threat's path; Vector Step lets him move through its weakest point. New locations, earlier meetings, alternate rescues, and achievement-earned lottery tickets become available. The Black Gate now recognizes Ren, and the second transmigration requires a constructed anchor, multiple survivors, decoded overseas evidence, and a willing ally.

## Timeline III — The Last Year

The second and last transmigration triggers Ren's third awakening: **Causal Sever**. Residual Read sees a causal chain, Vector Step moves between its links, and Causal Sever can break one chosen link so its consequence never arrives. It is powerful but tightly limited and begins at zero mastery. The final year opens the widest set of people, places, overseas routes, and lottery outcomes. Some characters experience déjà vu around Ren. There is no further transmigration: Day 365 must permanently resolve the Black Gate, and ordinary death remains final.

## End states

- **Run Terminated:** Ren dies before Day 365.
- **Ashes Again:** the final timeline reaches the catastrophe without enough preparation.
- **Tokyo Survives:** the city is saved, but the conspiracy or cycle remains.
- **The Lone Hunter:** Ren ends the loop by erasing himself and every retained memory.
- **Open Future:** Ren destroys the loop and reveals the origin of the Gates.
- **Zero Rank:** Ren survives with a trusted network; the skill dismissed as worthless connects the evidence and people required to end the Black Gate without erasing the lives built across the three years.

The campaign's dramatic progression is: **the first year teaches Ren what will happen; the second teaches him what he can change; the third asks what he is willing to lose.**

## Cutscene roadmap

Authored cutscenes belong at irreversible transitions rather than routine travel: the initial awakening, each arc deadline, ordinary death, the Black Gate reveal, successful transmigration, the second awakening, and each final ending. They should use the established visual-novel character art and location backgrounds, with bespoke animation added only after the underlying trigger and consequence are playable.

### Cutscene visual contract

- Every major scene receives a purpose-made 16:9 illustrated background for its actual location and time of day. Gameplay screenshots, enlarged pixel maps, and generic abstract backdrops are not acceptable substitutes.
- Speaking characters use clean full or three-quarter-body illustrations with consistent faces, clothing, proportions, and transparent edges across scenes. Pixel chibi sprites remain exclusive to exploration and field navigation.
- Motion stays restrained and authored: slow camera push or lateral drift, layered rain or dust, practical light flicker, foreground parallax, brief character entrances, subtle breathing, and controlled impact shake.
- Cutscenes must retain readable dialogue, keyboard/touch advancement, a history log, reduced-motion behavior, and a skip option after the scene has been viewed once.
- Death scenes avoid gore spectacle. Their image should communicate the failed location, the lost objective, and the absence of a residual path.
- Transmigration scenes visually reuse matching Day 365 and Day 1 compositions so the reset is understood through framing before exposition explains it.
- Generated art must be inspected for inconsistent anatomy, invented text, costume drift, and mismatched character identity before it enters the game. Unusable generations are rejected rather than hidden behind effects.

### In-engine cinematic direction

Cutscenes are authored as timed game sequences, not galleries of still images. Each sequence must define an establishing shot, character staging, shot changes, dialogue beats, sound cues, and the exact gameplay state it returns to.

- **Shot grammar:** begin with location and danger, move to the character affected by it, then reveal the information or choice that changes play. Avoid cutting simply because a dialogue line changed.
- **Character blocking:** characters enter, turn, step, recoil, or leave with clear screen direction. Their placement must remain geographically consistent between wide shots and dialogue framing.
- **Camera:** use slow pushes for realization, restrained lateral tracking for movement, brief handheld shake for Gate impacts, and hard cuts only for shocks or timeline discontinuity.
- **Animation:** layer separate character, foreground, weather, light, and background elements. Use short authored poses or crossfades for reactions; do not rubber-warp a single illustration to imitate full animation.
- **Timing:** important visual information receives a readable hold before dialogue advances. Automatic beats pause when the browser loses focus and never skip player choices.
- **Audio:** every scene has a cue sheet for ambience, music entry and exit, Gate pressure, footsteps, clothing movement, impacts, and intentional silence. Dialogue remains readable without audio.
- **Gameplay handoff:** the final shot must point toward the next controllable objective. Control returns only after the scene commits its event, time cost, consequences, and autosave.
- **Failure safety:** reloading during a cinematic resumes from its last committed beat or safely restarts the scene; it never duplicates rewards, bonds, evidence, or time costs.
- **Skip rules:** first viewing may skip only to the next mandatory choice; completed scenes may be skipped entirely. Skipping always commits the same deterministic consequences.
- **Presentation:** cinematic letterboxing is allowed when it improves composition, but subtitles, choices, and accessibility controls remain inside the safe area on desktop and mobile.

Every cinematic should ship with a small shot manifest containing shot ID, duration, background, character layers, camera motion, effects, audio cues, dialogue, skippability, and completion event. This keeps the scene testable as game logic rather than an unstructured animation.

### Required illustrated scenes

1. **Worthless Awakening:** clinical Bureau assessment room, fluorescent morning light, Ren isolated beneath a Zero-Rank result display.
2. **Arc I deadline:** Adachi evacuation route under the first synchronized pulse.
3. **Arc II deadline:** a district-wide breach seen from street level among civilians and patrol barriers.
4. **Arc III deadline:** the Guild operations room splitting over contradictory orders.
5. **Black Gate reveal:** Tokyo skyline folding toward the Gate on Day 365.
6. **Run Terminated:** location-aware defeat composition with no transmigration imagery.
7. **Residual Path:** Ren reading the core while fragments of Day 1 appear inside it.
8. **Second Awakening:** Vector Step manifesting as a precise displacement rather than a generic power aura.
9. **Final endings:** separate compositions for Ashes Again, Tokyo Survives, The Lone Hunter, Open Future, and Zero Rank.
