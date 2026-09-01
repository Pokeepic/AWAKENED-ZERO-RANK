import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { access, readFile } from "node:fs/promises";
import test from "node:test";
import {
  canonical,
  isObserverSnapshot,
  verifyArtifacts,
} from "../app/observer-data.ts";
const root = new URL("../", import.meta.url);
test("ships a separate Ren-controlled local RPG prologue", async () => {
  const [game, observer] = await Promise.all([
    readFile(new URL("app/game/page.tsx", root), "utf8"),
    readFile(new URL("app/page.tsx", root), "utf8"),
  ]);
  assert.match(game, /verifyArtifacts/);
  assert.match(game, /HOTSPOTS\.map/);
  assert.match(game, /clues\.length >= 2/);
  assert.match(game, /loadRpgState/);
  assert.match(game, /takeRpgAction/);
  assert.doesNotMatch(game, /fetch\([^)]*method\s*:/);
  assert.match(observer, /href="\/game"/);
});
test("opens a one-time shot-directed Day One awakening cinematic", async () => {
  const [awakening, state, styles] = await Promise.all([
    readFile(new URL("app/game/awakening/page.tsx", root), "utf8"),
    readFile(new URL("app/game/game-state.ts", root), "utf8"),
    readFile(new URL("app/globals.css", root), "utf8"),
  ]);
  assert.match(awakening, /SHOT_MANIFEST/);
  assert.match(awakening, /worthless-awakening-intro/);
  assert.match(awakening, /awakening-bureau-establishing-v1\.png/);
  assert.match(awakening, /ren-full\.png/);
  assert.match(awakening, /saveRpgState/);
  assert.match(awakening, /Enter/);
  assert.match(awakening, /Escape/);
  assert.match(state, /return "\/game\/awakening"/);
  assert.match(styles, /\.awakening-cutscene/);
  assert.match(styles, /awakening-scan/);
  assert.match(styles, /data-game-motion="reduced".*awakening-cutscene/);
  await access(
    new URL("public/game/cutscenes/awakening-bureau-establishing-v1.png", root),
  );
});
test("resolves the first arc deadline through evidence and mastery consequences", async () => {
  const [deadline, state, styles] = await Promise.all([
    readFile(new URL("app/game/deadline/arc-one/page.tsx", root), "utf8"),
    readFile(new URL("app/game/game-state.ts", root), "utf8"),
    readFile(new URL("app/globals.css", root), "utf8"),
  ]);
  assert.match(state, /state\.day >= 45/);
  assert.match(state, /return "\/game\/deadline\/arc-one"/);
  assert.match(deadline, /arc-i-deadline-resolved/);
  assert.match(deadline, /arc-i-authenticated-trace/);
  assert.match(deadline, /mastery >= 20/);
  assert.match(deadline, /remainingDaySlots/);
  assert.match(deadline, /takeRpgAction/);
  assert.match(deadline, /SKIP TO DECISION/);
  assert.match(deadline, /adachi-day45-pulse-v1\.png/);
  assert.match(styles, /\.deadline-cutscene/);
  assert.match(styles, /data-game-motion="reduced".*deadline-cutscene/);
  await access(
    new URL("public/game/cutscenes/adachi-day45-pulse-v1.png", root),
  );
});
test("grants and stages a third awakening after the second transmigration", async () => {
  const [awakening, state, hud, story, styles] = await Promise.all([
    readFile(new URL("app/game/awakening/final/page.tsx", root), "utf8"),
    readFile(new URL("app/game/game-state.ts", root), "utf8"),
    readFile(new URL("app/game/game-hud.tsx", root), "utf8"),
    readFile(new URL("../STORY.md", root), "utf8"),
    readFile(new URL("app/globals.css", root), "utf8"),
  ]);
  assert.match(state, /\["Residual Read", "Vector Step", "Causal Sever"\]/);
  assert.match(state, /"Causal Sever": 0/);
  assert.match(state, /return "\/game\/awakening\/final"/);
  assert.match(awakening, /FINAL_AWAKENING_SHOTS/);
  assert.match(awakening, /third-awakening-intro/);
  assert.match(awakening, /THIRD AWAKENING CONFIRMED/);
  assert.match(hud, /Causal Sever[\s\S]*CS/);
  assert.match(
    story,
    /second and last transmigration triggers Ren's third awakening/,
  );
  assert.match(styles, /\.final-awakening/);
  assert.match(styles, /causal-sever-flash/);
});
test("stages Vector Step after the first transmigration", async () => {
  const [awakening, state, styles] = await Promise.all([
    readFile(new URL("app/game/awakening/second/page.tsx", root), "utf8"),
    readFile(new URL("app/game/game-state.ts", root), "utf8"),
    readFile(new URL("app/globals.css", root), "utf8"),
  ]);
  assert.match(state, /state\.timeline === 2/);
  assert.match(state, /return "\/game\/awakening\/second"/);
  assert.match(awakening, /SECOND_AWAKENING_SHOTS/);
  assert.match(awakening, /second-awakening-intro/);
  assert.match(awakening, /SECOND AWAKENING CONFIRMED/);
  assert.match(awakening, /NEW ABILITY: VECTOR STEP/);
  assert.match(awakening, /saveRpgState/);
  assert.match(styles, /\.second-awakening/);
  assert.match(styles, /vector-step-reveal/);
});
test("resolves the Arc II district breach from prior proof bond and mastery", async () => {
  const [deadline, state, styles] = await Promise.all([
    readFile(new URL("app/game/deadline/arc-two/page.tsx", root), "utf8"),
    readFile(new URL("app/game/game-state.ts", root), "utf8"),
    readFile(new URL("app/globals.css", root), "utf8"),
  ]);
  assert.match(state, /state\.day >= 120/);
  assert.match(state, /return "\/game\/deadline\/arc-two"/);
  assert.match(deadline, /arc-ii-deadline-resolved/);
  assert.match(deadline, /arc-i-authenticated-trace/);
  assert.match(deadline, /Aiko Sato.*>= 2/);
  assert.match(deadline, /mastery >= 40/);
  assert.match(deadline, /arc-ii-evidence/);
  assert.match(deadline, /remainingDaySlots/);
  assert.match(deadline, /adachi-day120-breach-v1\.png/);
  assert.match(styles, /\.arc-two-deadline/);
  await access(
    new URL("public/game/cutscenes/adachi-day120-breach-v1.png", root),
  );
});
test("resolves the Arc III false-orders conspiracy from evidence trust and mastery", async () => {
  const [deadline, state, styles] = await Promise.all([
    readFile(new URL("app/game/deadline/arc-three/page.tsx", root), "utf8"),
    readFile(new URL("app/game/game-state.ts", root), "utf8"),
    readFile(new URL("app/globals.css", root), "utf8"),
  ]);
  assert.match(state, /state\.day >= 240/);
  assert.match(state, /return "\/game\/deadline\/arc-three"/);
  assert.match(deadline, /arc-iii-deadline-resolved/);
  assert.match(deadline, /arc-ii-evidence/);
  assert.match(deadline, /Daichi Mori.*>= 2/);
  assert.match(deadline, /mastery >= 65/);
  assert.match(deadline, /arc-iii-evidence/);
  assert.match(deadline, /remainingDaySlots/);
  assert.match(deadline, /tokyo-day240-false-orders-v1\.png/);
  assert.match(styles, /\.arc-three-deadline/);
  await access(
    new URL("public/game/cutscenes/tokyo-day240-false-orders-v1.png", root),
  );
});
test("ends the first year at an impossible Black Gate with conditional transmigration", async () => {
  const [finale, state, styles] = await Promise.all([
    readFile(new URL("app/game/deadline/black-gate/page.tsx", root), "utf8"),
    readFile(new URL("app/game/game-state.ts", root), "utf8"),
    readFile(new URL("app/globals.css", root), "utf8"),
  ]);
  assert.match(state, /state\.day === 365/);
  assert.match(state, /return "\/game\/deadline\/black-gate"/);
  assert.match(finale, /black-gate-deadline-resolved/);
  assert.match(finale, /black-gate-temporal-residue/);
  assert.match(finale, /read-the-collapsing-gate/);
  assert.match(finale, /mastery === 100/);
  assert.match(finale, /strongestBond >= 4/);
  assert.match(finale, /health >= 38/);
  assert.match(finale, /remainingDaySlots/);
  assert.match(finale, /black-gate-day365-core-v1\.png/);
  assert.match(styles, /\.black-gate-deadline/);
  await access(
    new URL("public/game/cutscenes/black-gate-day365-core-v1.png", root),
  );
});
test("opens the RPG through a persistent title menu without interrupting return travel", async () => {
  const [game, title, preferences, styles] = await Promise.all([
    readFile(new URL("app/game/page.tsx", root), "utf8"),
    readFile(new URL("app/game/title-screen.tsx", root), "utf8"),
    readFile(new URL("app/game/game-preferences.ts", root), "utf8"),
    readFile(new URL("app/globals.css", root), "utf8"),
  ]);
  assert.match(game, /RPG_SESSION_KEY/);
  assert.match(game, /sessionStorage\.getItem/);
  assert.doesNotMatch(game, /window\.confirm/);
  assert.match(title, /CONTINUE/);
  assert.match(title, /NEW GAME/);
  assert.match(title, /SETTINGS/);
  assert.match(title, /OBSERVER/);
  assert.match(title, /REPLACE SAVE & START/);
  assert.match(title, /ren-apartment-window-title-v1\.png/);
  assert.match(title, /title-window-light/);
  assert.match(title, /title-window-rain/);
  assert.match(title, /title-window-rain-near/);
  assert.match(title, /title-city-flicker/);
  assert.match(title, /title-window-droplets/);
  assert.match(title, /title-rain-impacts/);
  assert.match(title, /rain-title-loop\.mp3/);
  assert.match(title, /title-audio-toggle/);
  assert.match(preferences, /ambience/);
  assert.match(preferences, /ambienceVolume/);
  assert.match(title, /visibilitychange/);
  assert.match(title, /leaveTitle/);
  assert.match(title, /ArrowDown/);
  assert.match(title, /ArrowUp/);
  assert.match(title, /event\.key\.toLowerCase\(\) === "m"/);
  assert.match(title, /menuRef/);
  assert.match(title, /title-controls/);
  assert.match(title, /ENTER<\/kbd> CONFIRM/);
  assert.match(title, /panel !== "menu".*ESC/s);
  await access(new URL("public/game/audio/rain-title-loop.mp3", root));
  assert.doesNotMatch(title, /title-ren/);
  await access(new URL("public/game/ren-apartment-window-title-v1.png", root));
  assert.match(preferences, /RPG_PREFERENCES_KEY/);
  assert.match(preferences, /gameMotion/);
  assert.match(styles, /\.title-screen/);
  assert.match(styles, /data-game-motion/);
  assert.match(styles, /data-game-text/);
  assert.match(styles, /title-selection-breathe/);
});

test("backs up and strictly restores the local RPG campaign", async () => {
  const [game, title, state, styles] = await Promise.all([
    readFile(new URL("app/game/page.tsx", root), "utf8"),
    readFile(new URL("app/game/title-screen.tsx", root), "utf8"),
    readFile(new URL("app/game/game-state.ts", root), "utf8"),
    readFile(new URL("app/globals.css", root), "utf8"),
  ]);
  assert.match(title, /SAVE DATA/);
  assert.match(title, /DOWNLOAD BACKUP/);
  assert.match(title, /RESTORE BACKUP/);
  assert.match(title, /256_000/);
  assert.match(title, /accept="application\/json,\.json"/);
  assert.match(title, /role="status"/);
  assert.match(title, /Backup verified\. Review it before replacing the active campaign/);
  assert.match(title, /CONFIRM RESTORE/);
  assert.match(title, /Restore cancelled\. Your current campaign is unchanged/);
  assert.match(title, /pendingImport/);
  assert.match(state, /export function exportRpgState/);
  assert.match(state, /export function importRpgState/);
  assert.match(state, /return isRpgState\(candidate\) \? candidate : null/);
  assert.match(game, /saveRpgState\(restored\)/);
  assert.match(styles, /\.save-data-panel/);
  assert.match(styles, /\.save-file-input/);
  assert.match(styles, /\.restore-preview/);
});

test("changes the apartment illustration with time weather and winter snowpack", async () => {
  const [game, weather, styles] = await Promise.all([
    readFile(new URL("app/game/page.tsx", root), "utf8"),
    readFile(new URL("app/game/game-weather.ts", root), "utf8"),
    readFile(new URL("app/globals.css", root), "utf8"),
  ]);
  assert.match(game, /apartmentAtmosphere\(rpg\)/);
  assert.match(game, /weather-\$\{atmosphere\.weather\.toLowerCase\(\)\}/);
  assert.match(game, /SNOWPACK/);
  assert.match(weather, /export function gameSeason/);
  assert.match(weather, /export function gameWeather/);
  assert.match(weather, /export function snowAccumulation/);
  assert.match(weather, /ren-apartment-night-v1\.png/);
  assert.match(weather, /ren-apartment-winter-v1\.png/);
  assert.match(styles, /\.apartment-morning/);
  assert.match(styles, /\.apartment-evening/);
  assert.match(styles, /\.apartment-late-night/);
  assert.match(styles, /\.weather-snow/);
  assert.match(styles, /@keyframes apartment-rain/);
  assert.match(styles, /@keyframes apartment-snow/);
  await access(new URL("public/game/ren-apartment-night-v1.png", root));
  await access(new URL("public/game/ren-apartment-winter-v1.png", root));
});

test("carries the living calendar across every Tokyo district map", async () => {
  const [city, weather, styles] = await Promise.all([
    readFile(new URL("app/game/city/page.tsx", root), "utf8"),
    readFile(new URL("app/game/game-weather.ts", root), "utf8"),
    readFile(new URL("app/globals.css", root), "utf8"),
  ]);
  assert.match(city, /gameAtmosphere\(rpg\)/);
  assert.match(city, /city-\$\{rpg\.slot\.toLowerCase/);
  assert.match(city, /weather-\$\{atmosphere\.weather\.toLowerCase/);
  assert.match(city, /city-weather/);
  assert.match(city, /city-snowpack/);
  assert.match(city, /atmosphere\.season/);
  assert.match(weather, /export function gameAtmosphere/);
  assert.match(styles, /\.city-morning/);
  assert.match(styles, /\.city-late-night/);
  assert.match(styles, /\.city-diorama\.weather-snow/);
  assert.match(styles, /@keyframes city-rain/);
  assert.match(styles, /@keyframes city-snow/);
});
test("completes the prologue through explore act and result phases", async () => {
  const [game, styles] = await Promise.all([
    readFile(new URL("app/game/page.tsx", root), "utf8"),
    readFile(new URL("app/globals.css", root), "utf8"),
  ]);
  assert.match(game, /EXPLORE/);
  assert.match(game, /ACT/);
  assert.match(game, /RESULT/);
  assert.match(game, /LEAVE APARTMENT/);
  assert.match(game, /RESET SCENE/);
  assert.match(styles, /prefers-reduced-motion:reduce/);
  assert.match(styles, /@keyframes ren-breathe/);
});
test("ships a Ren-controlled Tokyo route chapter that advances RPG time", async () => {
  const [prologue, city] = await Promise.all([
    readFile(new URL("app/game/page.tsx", root), "utf8"),
    readFile(new URL("app/game/city/page.tsx", root), "utf8"),
  ]);
  assert.match(prologue, /href="\/game\/city"/);
  assert.match(city, /verifyArtifacts/);
  assert.match(city, /snapshot\.whereabouts\.map/);
  assert.match(city, /snapshot\.relationships\.find/);
  assert.match(city, /inspected\.length >= 2/);
  assert.match(city, /chooseRoute/);
  assert.match(city, /TIME ADVANCED/);
  assert.doesNotMatch(city, /fetch\([^)]*method\s*:/);
});
test("gives optional bonds deterministic schedules without blocking travel or canon", async () => {
  const [city, state, styles] = await Promise.all([
    readFile(new URL("app/game/city/page.tsx", root), "utf8"),
    readFile(new URL("app/game/game-state.ts", root), "utf8"),
    readFile(new URL("app/globals.css", root), "utf8"),
  ]);
  for (const name of [
    "Aiko Sato",
    "Daichi Mori",
    "Haruto Ishikawa",
    "Mei Kuroda",
  ])
    assert.match(state, new RegExp(name));
  assert.match(state, /export function bondAvailability/);
  assert.match(state, /ALREADY MET TODAY/);
  assert.match(city, /Spent time with/);
  assert.match(city, /SPEND TIME WITH/);
  assert.match(city, /TRAVEL ·.*status/);
  assert.match(city, /Story-critical meetings still\s+trigger automatically/);
  assert.match(styles, /\.route-node\.contact-away/);
});
test("turns optional bond ranks into authored deterministic relationship moments", async () => {
  const [city, state, styles] = await Promise.all([
    readFile(new URL("app/game/city/page.tsx", root), "utf8"),
    readFile(new URL("app/game/game-state.ts", root), "utf8"),
    readFile(new URL("app/globals.css", root), "utf8"),
  ]);
  assert.match(state, /const BOND_MOMENTS/);
  for (const title of [
    "The Unanswered Message",
    "Ink Against Orders",
    "One Honest Bet",
    "Proof Across Time",
  ])
    assert.match(state, new RegExp(title));
  assert.match(state, /export function bondMoment/);
  assert.match(
    state,
    /level >= 9 \? 3 : level >= 6 \? 2 : level >= 3 \? 1 : 0/,
  );
  assert.match(
    state,
    /Something in the exchange feels remembered from another life/,
  );
  assert.match(state, /BOND COMPLETE/);
  assert.match(city, /bondMoment\(name, level, rpg\.timeline\)/);
  assert.match(city, /className="bond-moment"/);
  assert.match(styles, /\.bond-moment/);
});
test("stages all optional bonds as choice-driven visual-novel encounters", async () => {
  const [city, encounter, styles] = await Promise.all([
    readFile(new URL("app/game/city/page.tsx", root), "utf8"),
    readFile(new URL("app/game/city/bond-encounter.tsx", root), "utf8"),
    readFile(new URL("app/globals.css", root), "utf8"),
  ]);
  for (const name of [
    "Aiko Sato",
    "Daichi Mori",
    "Haruto Ishikawa",
    "Mei Kuroda",
  ])
    assert.match(encounter, new RegExp(name));
  for (const asset of [
    "haruto-full-v1",
    "mei-full-v1",
    "akihabara-night-market-v1",
    "ueno-archive-room-v1",
  ])
    await access(new URL(`public/game/visual-novel/${asset}.png`, root));
  assert.match(encounter, /role="dialog"/);
  assert.match(encounter, /aria-modal="true"/);
  assert.match(encounter, /Digit\[1-3\]/);
  assert.match(encounter, /event\.key === "Escape"/);
  assert.match(encounter, /energyCost/);
  assert.match(encounter, /RETURN TO TOKYO/);
  assert.match(city, /<BondEncounter/);
  assert.match(city, /commitBond/);
  assert.match(city, /rpg\.energy - encounterChoice\.energyCost/);
  assert.match(styles, /\.bond-vn/);
  assert.match(styles, /\.bond-vn-cast/);
});
test("unlocks a deterministic Timeline II relay for mastery lottery Busan and anchor progress", async () => {
  const [relay, city, state, styles] = await Promise.all([
    readFile(new URL("app/game/residual-relay/page.tsx", root), "utf8"),
    readFile(new URL("app/game/city/page.tsx", root), "utf8"),
    readFile(new URL("app/game/game-state.ts", root), "utf8"),
    readFile(new URL("app/globals.css", root), "utf8"),
  ]);
  assert.match(city, /rpg\.timeline >= 2/);
  assert.match(city, /\/game\/residual-relay/);
  assert.match(relay, /save\.timeline < 2/);
  assert.match(relay, /busan-signal-decoded/);
  assert.match(relay, /residual-anchor-complete/);
  assert.match(relay, /mastery < 40/);
  assert.match(relay, /mastery < 100/);
  assert.match(relay, /strongestBond < 6/);
  assert.match(relay, /lotteryTickets: rpg!\.lotteryTickets - 1/);
  assert.match(state, /"lotteryTickets"/);
  assert.match(state, /"fieldKit"/);
  assert.match(styles, /\.relay-shell/);
  await access(
    new URL("public/game/locations/haneda-residual-relay-v1.png", root),
  );
});
test("ships an evidence-complete Gate RPG chapter", async () => {
  const [city, caseboard] = await Promise.all([
    readFile(new URL("app/game/city/page.tsx", root), "utf8"),
    readFile(new URL("app/game/caseboard/page.tsx", root), "utf8"),
  ]);
  assert.match(city, /href="\/game\/caseboard"/);
  assert.match(caseboard, /verifyArtifacts/);
  assert.match(caseboard, /snapshot\.portals\.investigations/);
  assert.match(caseboard, /opened\.length === cases\.length/);
  assert.match(caseboard, /The game will not invent one/);
  assert.match(caseboard, /TAKE REN'S ACTION/);
  assert.match(caseboard, /takeRpgAction/);
  assert.doesNotMatch(caseboard, /fetch\([^)]*method\s*:/);
});
test("ships a deterministic Gate battle that advances time only on resolution", async () => {
  const [caseboard, field, hud, styles] = await Promise.all([
    readFile(new URL("app/game/caseboard/page.tsx", root), "utf8"),
    readFile(new URL("app/game/field/page.tsx", root), "utf8"),
    readFile(new URL("app/game/game-hud.tsx", root), "utf8"),
    readFile(new URL("app/globals.css", root), "utf8"),
  ]);
  assert.match(caseboard, /\/game\/field\?case=/);
  assert.doesNotMatch(hud, />FIELD<\/button>/);
  assert.match(field, /PRECISION STRIKE/);
  assert.match(field, /BARRIER PULSE/);
  assert.match(field, /TACTICAL RETREAT/);
  assert.match(field, /No random rolls/);
  assert.equal((field.match(/takeRpgAction\(/g) ?? []).length, 4);
  assert.match(styles, /\.field-stage/);
  assert.match(styles, /\.field-enemy/);
  assert.doesNotMatch(field, /Math\.random/);
});
test("telegraphs enemy intent and unlocks timeline combat moves deterministically", async () => {
  const [field, styles] = await Promise.all([
    readFile(new URL("app/game/field/page.tsx", root), "utf8"),
    readFile(new URL("app/globals.css", root), "utf8"),
  ]);
  for (const marker of [
    "FRACTURE CLAW",
    "PRESSURE SURGE",
    "CORE EXPOSURE",
    "VECTOR STEP",
    "CAUSAL SEVER",
    "GUARD LATTICE",
  ])
    assert.match(field, new RegExp(marker));
  assert.match(field, /intent\.damage - move\.mitigation/);
  assert.match(field, /move\.damage \+ intent\.exposure/);
  assert.match(field, /rpg\.skillMastery\[move\.skill\]/);
  assert.match(field, /Digit\[1-5\]/);
  assert.match(field, /event\.key\.toLowerCase\(\) === "r"/);
  assert.match(styles, /\.enemy-intent/);
  assert.match(styles, /@keyframes enemy-surge/);
  assert.doesNotMatch(field, /Math\.random/);
});
test("carries the selected Gate and mission plan into distinct field encounters", async () => {
  const [caseboard, field, state, styles] = await Promise.all([
    readFile(new URL("app/game/caseboard/page.tsx", root), "utf8"),
    readFile(new URL("app/game/field/page.tsx", root), "utf8"),
    readFile(new URL("app/game/game-state.ts", root), "utf8"),
    readFile(new URL("app/globals.css", root), "utf8"),
  ]);
  assert.match(caseboard, /case=\$\{encodeURIComponent\(missionCase\)\}/);
  assert.match(caseboard, /plan=\$\{recommendation\.id\}/);
  assert.match(caseboard, /Enter before the signal shifts/);
  for (const marker of [
    "DROWNED ARCHIVIST",
    "UNDERTOW GRIP",
    "GLASS RAIN",
    "MEMORY BLOOM",
    "GUARD LATTICE",
    "WEAK POINT MARKED",
    "UNSTABLE ENTRY",
  ])
    assert.match(field, new RegExp(marker));
  assert.match(field, /reward: 2400/);
  assert.match(field, /plan\.damage/);
  assert.match(field, /plan\.mitigation/);
  assert.match(field, /Cleared the drowned archivist/);
  assert.match(state, /Cleared the drowned archivist/);
  assert.match(styles, /\.enemy-archivist/);
  assert.match(styles, /\.battle-plan/);
  assert.doesNotMatch(field, /Math\.random/);
});
test("persists a bounded apartment field kit and consumes supplies during combat", async () => {
  const [game, field, state, styles] = await Promise.all([
    readFile(new URL("app/game/page.tsx", root), "utf8"),
    readFile(new URL("app/game/field/page.tsx", root), "utf8"),
    readFile(new URL("app/game/game-state.ts", root), "utf8"),
    readFile(new URL("app/globals.css", root), "utf8"),
  ]);
  assert.match(state, /fieldKit: \{/);
  assert.match(state, /weapon: "Utility Knife" \| "Resonance Blade"/);
  assert.match(state, /coat: "Street Jacket" \| "Guildweave Coat"/);
  assert.match(state, /candidate\.fieldKit\?\.bandages \?\?/);
  assert.match(state, /bandages <= 3/);
  assert.match(state, /energyDrinks <= 3/);
  assert.match(game, /Restock the field bag · ¥900/);
  assert.match(game, /money: rpg!\.money - 900/);
  assert.match(game, /field-kit-readout/);
  assert.match(field, /applyFieldItem/);
  assert.match(field, /\+ 18/);
  assert.match(field, /\+ 22/);
  assert.match(field, /wardMitigation/);
  assert.match(field, /saveRpgState\(next\)/);
  assert.match(field, /event\.key\.toLowerCase\(\) === "b"/);
  assert.match(field, /event\.key\.toLowerCase\(\) === "e"/);
  assert.match(styles, /\.field-kit-bar/);
});
test("sells permanent Akihabara equipment and includes it in exact combat previews", async () => {
  const [city, field, state, game, styles] = await Promise.all([
    readFile(new URL("app/game/city/page.tsx", root), "utf8"),
    readFile(new URL("app/game/field/page.tsx", root), "utf8"),
    readFile(new URL("app/game/game-state.ts", root), "utf8"),
    readFile(new URL("app/game/page.tsx", root), "utf8"),
    readFile(new URL("app/globals.css", root), "utf8"),
  ]);
  for (const marker of [
    "Resonance Blade",
    "Guildweave Coat",
    "Haruto's equipment counter",
    "MARKET_GEAR",
  ])
    assert.match(city, new RegExp(marker));
  assert.match(city, /price: 4500/);
  assert.match(city, /price: 3500/);
  assert.match(city, /saveRpgState\(next\)/);
  const purchaseFunction =
    city.match(/function purchaseGear[\s\S]*?\n {2}}/)?.[0] ?? "";
  assert.doesNotMatch(purchaseFunction, /takeRpgAction/);
  assert.match(state, /candidate\.fieldKit\?\.weapon \?\? "Utility Knife"/);
  assert.match(state, /candidate\.fieldKit\?\.coat \?\? "Street Jacket"/);
  assert.match(game, /\.\.\.rpg!\.fieldKit/);
  assert.match(field, /gearDamage/);
  assert.match(field, /gearMitigation/);
  assert.match(field, /plan\.damage \+ gearDamage/);
  assert.match(field, /wardMitigation - gearMitigation/);
  assert.match(styles, /\.market-counter/);
});
test("uses first-person apartment framing and pixel sprites for outside scenes", async () => {
  const [game, city, caseboard, styles] = await Promise.all([
    readFile(new URL("app/game/page.tsx", root), "utf8"),
    readFile(new URL("app/game/city/page.tsx", root), "utf8"),
    readFile(new URL("app/game/caseboard/page.tsx", root), "utf8"),
    readFile(new URL("app/globals.css", root), "utf8"),
  ]);
  for (const name of ["ren", "aiko", "daichi", "mei", "haruto"]) {
    await access(new URL(`public/game/characters/${name}.png`, root));
  }
  assert.match(styles, /image-rendering:pixelated/);
  assert.match(game, /alt="Portrait of Ren Takahashi"/);
  assert.doesNotMatch(game, /alt="Full-body illustration of Ren Takahashi"/);
  assert.match(city, /SPRITES/);
  assert.match(caseboard, /src="\/game\/characters\/ren\.png"/);
  assert.match(game, /src=\{atmosphere\.image\}/);
  await access(new URL("public/game/ren-apartment.png", root));
});
test("places the pixel cast on the Tokyo map and encounter stage", async () => {
  const [city, styles] = await Promise.all([
    readFile(new URL("app/game/city/page.tsx", root), "utf8"),
    readFile(new URL("app/globals.css", root), "utf8"),
  ]);
  assert.match(city, /const SPRITES/);
  assert.match(city, /className="map-origin"/);
  assert.match(city, /SPRITES\[route\.name\]/);
  assert.match(city, /className="route-encounter"/);
  assert.match(styles, /\.route-node img/);
  assert.match(styles, /\.route-encounter/);
});
test("renders Tokyo and four reusable pixel landmark assets", async () => {
  const city = await readFile(new URL("app/game/city/page.tsx", root), "utf8");
  await access(new URL("public/game/tokyo-dusk.png", root));
  for (const name of [
    "hunter-guild",
    "gate-zone",
    "akihabara-market",
    "ueno-library",
  ]) {
    await access(new URL(`public/game/locations/${name}.png`, root));
  }
  assert.match(city, /const LANDMARKS/);
  assert.match(city, /className="tokyo-map-bg"/);
  assert.match(city, /className="landmark-sprite"/);
  assert.match(city, /className="contact-sprite"/);
});
test("embeds landmarks in the city without radar-circle chrome", async () => {
  const [city, styles] = await Promise.all([
    readFile(new URL("app/game/city/page.tsx", root), "utf8"),
    readFile(new URL("app/globals.css", root), "utf8"),
  ]);
  assert.match(city, /route-map city-diorama/);
  assert.doesNotMatch(city, /map-ring/);
  assert.match(styles, /\.city-diorama \.route-art \.landmark-sprite/);
  assert.match(styles, /\.city-diorama \.route-label/);
});
test("uses a separate location layer and dialogue-first social-sim framing", async () => {
  const [game, styles] = await Promise.all([
    readFile(new URL("app/game/page.tsx", root), "utf8"),
    readFile(new URL("app/globals.css", root), "utf8"),
  ]);
  assert.match(game, /apartment-bg/);
  assert.match(game, /dialogue-box/);
  assert.match(styles, /chibi-idle/);
  assert.match(styles, /speaker-tag/);
});
test("renders the current scene profile as text instead of a React object", async () => {
  const game = await readFile(new URL("app/game/page.tsx", root), "utf8");
  assert.match(game, /REN&apos;S APARTMENT/);
  assert.match(game, /atmosphere\.label\.toUpperCase/);
  assert.doesNotMatch(game, /\{scene\.place\}\s*\//);
  assert.doesNotMatch(game, /scene\.weather/);
});
test("moves between three district maps without mutating the chronicle", async () => {
  const [city, styles] = await Promise.all([
    readFile(new URL("app/game/city/page.tsx", root), "utf8"),
    readFile(new URL("app/globals.css", root), "utf8"),
  ]);
  for (const name of ["east-loop", "adachi-fringe"])
    await access(new URL(`public/game/maps/${name}.png`, root));
  await access(new URL("public/game/ren-apartment.png", root));
  assert.match(city, /const DISTRICTS/);
  assert.match(city, /className="district-switcher"/);
  assert.match(city, /setDistrictId/);
  assert.match(city, /visibleRoutes/);
  assert.doesNotMatch(city, /fetch\([^)]*method\s*:/);
  assert.match(styles, /\.district-switcher/);
});
test("stages authenticated Gate files inside the Adachi field scene", async () => {
  const [caseboard, styles] = await Promise.all([
    readFile(new URL("app/game/caseboard/page.tsx", root), "utf8"),
    readFile(new URL("app/globals.css", root), "utf8"),
  ]);
  assert.match(caseboard, /case-files case-zone/);
  assert.match(caseboard, /maps\/adachi-fringe\.png/);
  assert.match(caseboard, /className="case-ren"/);
  assert.match(caseboard, /case-node case-node-/);
  assert.match(styles, /\.case-zone \.case-node/);
  assert.match(styles, /\.case-ren/);
});
test("ships illustrated Gate files and a four-slot local RPG save", async () => {
  const [caseboard, state] = await Promise.all([
    readFile(new URL("app/game/caseboard/page.tsx", root), "utf8"),
    readFile(new URL("app/game/game-state.ts", root), "utf8"),
  ]);
  await access(new URL("public/game/cases/glass-office-labyrinth.png", root));
  await access(new URL("public/game/cases/sunken-courtyard.png", root));
  assert.match(caseboard, /CASE_ART/);
  assert.match(caseboard, /className="case-art"/);
  assert.match(state, /Morning[\s\S]*Afternoon[\s\S]*Evening[\s\S]*Late Night/);
  assert.match(state, /localStorage/);
  assert.match(state, /Math\.floor\(elapsed \/ RPG_SLOTS\.length\)/);
});
test("renders a shared persistent RPG HUD with a safe new-game reset", async () => {
  const [hud, state, game, city, caseboard, styles] = await Promise.all([
    readFile(new URL("app/game/game-hud.tsx", root), "utf8"),
    readFile(new URL("app/game/game-state.ts", root), "utf8"),
    readFile(new URL("app/game/page.tsx", root), "utf8"),
    readFile(new URL("app/game/city/page.tsx", root), "utf8"),
    readFile(new URL("app/game/caseboard/page.tsx", root), "utf8"),
    readFile(new URL("app/globals.css", root), "utf8"),
  ]);
  assert.match(hud, /DAY \{state\.day\}/);
  assert.match(hud, /HP \{state\.health\}/);
  assert.doesNotMatch(hud, /aria-label="RPG locations"/);
  assert.match(state, /resetRpgState/);
  assert.match(state, /localStorage\.removeItem/);
  assert.doesNotMatch(game, /window\.confirm/);
  assert.match(hud, /role="alertdialog"/);
  for (const page of [game, city, caseboard]) assert.match(page, /<GameHud/);
  assert.match(styles, /\.rpg-hud/);
});
test("keeps story routing automatic and validates versioned local saves", async () => {
  const [hud, state, layout] = await Promise.all([
    readFile(new URL("app/game/game-hud.tsx", root), "utf8"),
    readFile(new URL("app/game/game-state.ts", root), "utf8"),
    readFile(new URL("app/layout.tsx", root), "utf8"),
  ]);
  assert.match(hud, /pendingStoryRoute/);
  assert.doesNotMatch(hud, /aria-current/);
  assert.doesNotMatch(hud, /STORY/);
  assert.match(state, /saveVersion: 10/);
  assert.match(state, /isRpgState/);
  assert.match(state, /Number\.isSafeInteger/);
  assert.match(layout, /separate time-management RPG/);
});
test("records a bounded persistent campaign journal and migrates older saves", async () => {
  const [hud, state, styles] = await Promise.all([
    readFile(new URL("app/game/game-hud.tsx", root), "utf8"),
    readFile(new URL("app/game/game-state.ts", root), "utf8"),
    readFile(new URL("app/globals.css", root), "utf8"),
  ]);
  assert.match(state, /saveVersion: 10/);
  assert.match(state, /Array\.isArray\(candidate\.journal\)/);
  assert.match(state, /candidate\.bonds/);
  assert.match(state, /candidate\.completedEvents/);
  assert.match(state, /\.slice\(-12\)/);
  assert.match(hud, /CAMPAIGN JOURNAL/);
  assert.match(hud, /AUTOSAVE ACTIVE/);
  assert.match(hud, /role="alertdialog"/);
  assert.match(hud, /Escape/);
  assert.match(hud, /KEEP CURRENT SAVE/);
  assert.match(hud, /state\.journal/);
  assert.match(styles, /\.rpg-journal/);
  assert.match(styles, /\.reset-dialog/);
});
test("models a lethal one-year campaign with conditional final-day transmigration", async () => {
  const [state, hud, field, title, story, styles] = await Promise.all([
    readFile(new URL("app/game/game-state.ts", root), "utf8"),
    readFile(new URL("app/game/game-hud.tsx", root), "utf8"),
    readFile(new URL("app/game/field/page.tsx", root), "utf8"),
    readFile(new URL("app/game/title-screen.tsx", root), "utf8"),
    readFile(new URL("../STORY.md", root), "utf8"),
    readFile(new URL("app/globals.css", root), "utf8"),
  ]);
  assert.match(state, /CAMPAIGN_ARCS/);
  for (const deadline of [45, 120, 240, 365])
    assert.match(state, new RegExp(`deadline: ${deadline}`));
  assert.match(state, /timeline: Timeline/);
  assert.match(state, /transmigrationEligible/);
  assert.match(state, /restartRpgRun/);
  assert.match(state, /attempt: state\.attempt \+ 1/);
  assert.match(state, /journal: \[\]/);
  assert.match(state, /completedEvents: \[\]/);
  assert.match(state, /next\.health === 0.*game-over/s);
  assert.match(state, /state\.day === 365.*year-ending/s);
  assert.match(state, /transmigrationConditions/);
  assert.match(state, /canTransmigrate/);
  assert.match(state, /transmigrateRpgState/);
  assert.match(state, /"Residual Read": 0/);
  assert.match(state, /state\.skillMastery\["Residual Read"\] === 100/);
  assert.match(state, /state\.skillMastery\["Vector Step"\] === 100/);
  assert.match(hud, /RR \{state\.skillMastery/);
  assert.match(field, /Residual Read.*\+ 12/s);
  assert.match(hud, /EVIDENCE.*SECURED/);
  assert.match(hud, /arc-i-evidence/);
  for (const requirement of [
    "skillMastery",
    "Black Gate Core",
    "read-the-collapsing-gate",
    "busan-signal-decoded",
  ])
    assert.match(state, new RegExp(requirement));
  assert.match(hud, /FIRST TIMELINE/);
  assert.match(hud, /RUN TERMINATED/);
  assert.match(hud, /RETRY TIMELINE/);
  assert.match(hud, /A residual path opens/);
  assert.match(hud, /TRANSMIGRATE TO TIMELINE/);
  assert.match(title, /RETRY RUN/);
  assert.match(field, /Fell to the fracture sentinel/);
  assert.doesNotMatch(
    field,
    /health: 20.*Retreated from the fracture sentinel/,
  );
  assert.match(story, /Death before the final day is Game Over/);
  assert.match(story, /Residual Read/);
  assert.match(story, /Vector Step/);
  assert.match(styles, /\.campaign-deadline/);
  assert.match(styles, /\.reset-dialog\.game-over/);
  assert.match(styles, /\.reset-dialog\.year-ending/);
});
test("paces long campaign stretches with deadline-safe ordinary routines", async () => {
  const [game, state] = await Promise.all([
    readFile(new URL("app/game/page.tsx", root), "utf8"),
    readFile(new URL("app/game/game-state.ts", root), "utf8"),
  ]);
  assert.match(state, /export function routineDaysAvailable/);
  assert.match(state, /Math\.min\(7, deadline - state\.day\)/);
  assert.match(state, /export function followRoutine/);
  assert.match(state, /slot: "Morning"/);
  assert.match(state, /money: state\.money \+ days \* 250/);
  assert.match(state, /saveRpgState\(next\)/);
  assert.match(game, /Follow the ordinary routine/);
  assert.match(game, /routineDaysAvailable\(rpg\)/);
  assert.match(game, /followRoutine\(rpg!\)/);
  assert.match(game, /every skipped day is a choice he cannot take back/);
  assert.match(game, /TIME PASSAGE \/ IRREVERSIBLE/);
  assert.match(game, /OPPORTUNITY COST/);
  assert.match(game, /LET TIME PASS/);
  assert.match(game, /setRoutineConfirm\(false\)/);
  const styles = await readFile(new URL("app/globals.css", root), "utf8");
  assert.match(styles, /\.routine-confirm/);
});
test("adds a post-Gate social chapter with local bond consequences", async () => {
  const [field, evening, state, styles] = await Promise.all([
    readFile(new URL("app/game/field/page.tsx", root), "utf8"),
    readFile(new URL("app/game/evening/page.tsx", root), "utf8"),
    readFile(new URL("app/game/game-state.ts", root), "utf8"),
    readFile(new URL("app/globals.css", root), "utf8"),
  ]);
  assert.match(field, /A canon event has triggered/);
  assert.match(evening, /Aiko Sato/);
  assert.match(evening, /RESPONSES\.map/);
  assert.match(evening, /takeRpgAction/);
  assert.match(evening, /Observer trust remains/);
  assert.match(state, /bonds: Record<string, number>/);
  assert.match(styles, /\.evening-stage/);
  assert.doesNotMatch(evening, /Math\.random/);
});
test("stages one-time canon beats as a full visual-novel scene", async () => {
  const [evening, state, styles] = await Promise.all([
    readFile(new URL("app/game/evening/page.tsx", root), "utf8"),
    readFile(new URL("app/game/game-state.ts", root), "utf8"),
    readFile(new URL("app/globals.css", root), "utf8"),
  ]);
  assert.match(evening, /const STORY_BEATS/);
  assert.match(evening, /CANON EVENT/);
  assert.match(evening, /visual-novel\/adachi-station-dusk\.png/);
  assert.match(evening, /visual-novel\/ren-full\.png/);
  assert.match(evening, /visual-novel\/aiko-full\.png/);
  assert.match(evening, /vn-character/);
  assert.match(evening, /activeSpeaker/);
  assert.match(evening, /completedEvents\.includes\(EVENT_ID\)/);
  assert.match(state, /completedEvents: string\[\]/);
  assert.match(state, /new Set\(value\.completedEvents\)/);
  assert.match(styles, /\.canon-beat/);
  assert.match(styles, /\.vn-character\.speaking/);
  assert.match(styles, /\.vn-character\.listening/);
  for (const asset of ["adachi-station-dusk", "ren-full", "aiko-full"])
    await access(new URL(`public/game/visual-novel/${asset}.png`, root));
});
test("supports keyboard-driven visual-novel pacing and dialogue history", async () => {
  const [evening, styles] = await Promise.all([
    readFile(new URL("app/game/evening/page.tsx", root), "utf8"),
    readFile(new URL("app/globals.css", root), "utf8"),
  ]);
  assert.match(evening, /window\.addEventListener\("keydown"/);
  assert.match(evening, /event\.key === "Enter"/);
  assert.match(evening, /event\.key === " "/);
  assert.match(evening, /Digit\[1-3\]/);
  assert.match(evening, /DIALOGUE LOG/);
  assert.match(evening, /className="vn-progress"/);
  assert.match(styles, /\.vn-history/);
  assert.match(styles, /\.vn-progress/);
});
test("continues canon progression into an authenticated Daichi guild debrief", async () => {
  const [evening, debrief, hud, styles] = await Promise.all([
    readFile(new URL("app/game/evening/page.tsx", root), "utf8"),
    readFile(new URL("app/game/debrief/page.tsx", root), "utf8"),
    readFile(new URL("app/game/game-hud.tsx", root), "utf8"),
    readFile(new URL("app/globals.css", root), "utf8"),
  ]);
  assert.doesNotMatch(evening, /href="\/game\/debrief"/);
  assert.match(debrief, /const PREREQUISITE = "after-the-gate-aiko"/);
  assert.match(debrief, /guild-debrief-daichi/);
  assert.match(debrief, /Daichi Mori/);
  assert.match(debrief, /takeRpgAction/);
  assert.match(debrief, /hunter-guild-briefing\.png/);
  assert.match(debrief, /daichi-full\.png/);
  assert.match(hud, /"debrief"/);
  assert.match(styles, /\.vn-character\.daichi/);
  for (const asset of ["hunter-guild-briefing", "daichi-full"])
    await access(new URL(`public/game/visual-novel/${asset}.png`, root));
});
test("triggers canon events from play criteria and charges their time cost", async () => {
  const [state, field, city, evening, debrief, hud] = await Promise.all([
    readFile(new URL("app/game/game-state.ts", root), "utf8"),
    readFile(new URL("app/game/field/page.tsx", root), "utf8"),
    readFile(new URL("app/game/city/page.tsx", root), "utf8"),
    readFile(new URL("app/game/evening/page.tsx", root), "utf8"),
    readFile(new URL("app/game/debrief/page.tsx", root), "utf8"),
    readFile(new URL("app/game/game-hud.tsx", root), "utf8"),
  ]);
  assert.match(state, /pendingStoryRoute/);
  assert.match(state, /survivedFirstGate/);
  assert.match(state, /state\.location === "Tokyo Hunter Guild"/);
  assert.match(state, /remainingDaySlots/);
  assert.match(hud, /useEffect/);
  assert.match(hud, /pendingStoryRoute\(state\)/);
  assert.match(field, /Aiko is waiting/);
  assert.match(city, /Traveled to/);
  assert.match(evening, /remainingDaySlots\(rpg\)/);
  assert.match(evening, /consumes the rest of Ren/);
  assert.match(debrief, /consumes one time slot/);
  assert.doesNotMatch(hud, /\/game\/story/);
});
test("uses an in-world apartment exit without interface tabs", async () => {
  const [game, styles] = await Promise.all([
    readFile(new URL("app/game/page.tsx", root), "utf8"),
    readFile(new URL("app/game/door.module.css", root), "utf8"),
  ]);
  assert.match(game, /doorStyles\.apartmentDoor/);
  assert.match(game, /doorStyles\.resultPortrait/);
  assert.match(game, /doorStyles\.apartmentPanel/);
  assert.match(game, /visual-novel\/ren-full\.png/);
  assert.match(game, /doorStyles\.fieldBag/);
  assert.match(game, /href="\/game\/city"/);
  assert.doesNotMatch(game, /workspace-tabs/);
  assert.doesNotMatch(game, /"scene" \| "notebook"/);
  assert.doesNotMatch(game, /scene-conclusion/);
  assert.match(styles, /\.apartmentDoor/);
  assert.match(styles, /\.resultPortrait/);
  assert.match(styles, /\.apartmentPanel/);
});
const storyAnchors = [
  [183, "arc_adachi_warning", "The Adachi Warning"],
  [365, "arc_tokyo_fracture", "The Tokyo Fracture"],
  [548, "arc_foreign_signal", "The Foreign Signal"],
  [730, "arc_guild_reckoning", "The Guild Reckoning"],
  [913, "arc_zero_rank_choice", "The Zero-Rank Choice"],
  [1095, "arc_awakened_horizon", "The Awakened Horizon"],
];
const storyFocus = [
  ["Aiko Sato", "Daichi Mori"],
  ["Daichi Mori", "Mei Kuroda"],
  ["Mei Kuroda", "Haruto Ishikawa"],
  ["Aiko Sato", "Daichi Mori"],
  ["Aiko Sato", "Daichi Mori", "Mei Kuroda", "Haruto Ishikawa"],
  ["Aiko Sato", "Daichi Mori", "Mei Kuroda", "Haruto Ishikawa"],
];
const storyDetails = [
  {
    premise:
      "A synchronized Gate pulse forces Tokyo to reassess its weakest districts.",
    scene:
      "Aiko maps apartment residents while Daichi marks the patrol routes the guild abandoned.",
    portal_consequence:
      "The newest portal record reveals which evacuation route will destabilize first.",
    international_link: null,
  },
  {
    premise:
      "Conflicting guild orders divide the people responsible for civilian safety.",
    scene:
      "Daichi brings the disputed orders to Mei, who finds a portal signature hidden in their timestamps.",
    portal_consequence:
      "The recorded portal pattern distinguishes the forged order from the real patrol signal.",
    international_link:
      "The forgery uses routing conventions later traced beyond Japan.",
  },
  {
    premise:
      "A repeating portal signature links Japan to a disaster unfolding overseas.",
    scene:
      "Mei decodes the signal at Haruto's shuttered shop while he inventories supplies for an unknown city.",
    portal_consequence:
      "The latest portal record gives the foreign responders a matching hazard and a safe approach.",
    international_link:
      "Responders in Busan confirm the same signature and establish the chronicle's first overseas contact.",
  },
  {
    premise:
      "Tokyo must decide whether rank or lived evidence defines a hunter's worth.",
    scene:
      "Aiko reads overlooked incident reports into the record as Daichi names the patrols those reports saved.",
    portal_consequence:
      "A documented portal hazard turns Ren's field notes into evidence the hearing cannot dismiss.",
    international_link:
      "The Busan contact submits corroborating records that make the reckoning larger than one guild.",
  },
  {
    premise:
      "Ren's accumulated loyalties and discoveries converge around one final threat.",
    scene:
      "Aiko coordinates civilians, Daichi holds the perimeter, Mei reads the breach, and Haruto keeps the route supplied.",
    portal_consequence:
      "The newest portal record determines where the circle can interrupt the converging breach.",
    international_link:
      "The overseas corridor returns the warning, giving Tokyo time bought by people Ren never met.",
  },
  {
    premise:
      "The three-year chronicle reaches an ending shaped by the life Ren built.",
    scene:
      "At the Arakawa riverbank, Ren's circle compares the city they inherited with the one their records now protect.",
    portal_consequence:
      "Every documented portal remains part of the public warning network rather than disappearing into a private file.",
    international_link:
      "Tokyo and Busan keep the corridor open as the first link in a wider civilian warning network.",
  },
];
const storyOutcomes = {
  isolated: [
    "The warning reached Adachi before Ren had anyone ready to believe him.",
    "The fracture left Ren outside both camps as patrol routes collapsed.",
    "The signal faded overseas with no one willing to stake resources on Ren's warning.",
    "The hearing reduced Ren's life to a rank the guild could dismiss.",
    "Ren confronted the final threat without a network strong enough to share its cost.",
    "Ren survived three years, carrying an unfinished warning into an uncertain future.",
  ],
  resilient: [
    "Ren helped hold one evacuation route while the district absorbed the shock.",
    "Ren carried evidence between rivals, preserving an uneasy working truce.",
    "Ren preserved enough of the signal to guide a limited international response.",
    "Ren's record protected low-rank patrols, even as the old hierarchy survived.",
    "Ren's incomplete circle held long enough to keep the threat from consuming Tokyo.",
    "Ren left Tokyo steadier than he found it, though some fractures remained.",
  ],
  prepared: [
    "Ren's evidence let the guild clear Adachi before the synchronized breach.",
    "Ren's trusted coalition exposed the false order before Tokyo divided.",
    "Ren matched the signal to his portal record and opened a verified aid corridor.",
    "Ren's allies forced the guild to recognize survival evidence beside rank.",
    "Every bond and discovery converged into a coordinated answer to the final threat.",
    "Ren reached the horizon with a trusted circle and a record that changed Tokyo.",
  ],
};
const completedStory = (count, tier = "prepared") =>
  storyAnchors.slice(0, count).map(([day, key, title], index) => {
    const selectedTier = Array.isArray(tier) ? tier[index] : tier;
    return {
      day,
      focus_npcs: storyFocus[index],
      ...storyDetails[index],
      key,
      outcome:
        selectedTier === "legacy-unavailable"
          ? "Outcome tier unavailable in this legacy timeline."
          : storyOutcomes[selectedTier][index],
      tier: selectedTier,
      title,
    };
  });
const endingTiers = (ending) =>
  ending.id === "legacy-unavailable"
    ? Array(6).fill("legacy-unavailable")
    : ending.id === "unfinished-warning"
      ? [
          "prepared",
          "prepared",
          "resilient",
          "resilient",
          "isolated",
          "isolated",
        ]
      : ending.id === "quiet-guardian"
        ? [
            "isolated",
            "prepared",
            "prepared",
            "resilient",
            "resilient",
            "resilient",
          ]
        : ending.id === "open-corridor"
          ? [
              "isolated",
              "resilient",
              "isolated",
              "resilient",
              "resilient",
              "prepared",
            ]
          : ending.id === "scarred-watch"
            ? [
                "isolated",
                "isolated",
                "prepared",
                "isolated",
                "resilient",
                "resilient",
              ]
            : Array(6).fill("prepared");
const syncEnvironment = (snapshot) => {
  const day = ((Math.max(1, snapshot.clock.day) - 1) % 365) + 1;
  const [season, temperature] =
    day <= 91
      ? ["Summer", 29]
      : day <= 182
        ? ["Autumn", 22]
        : day <= 273
          ? ["Winter", 9]
          : ["Spring", 18];
  snapshot.environment.season = season;
  snapshot.environment.weather = "Clear";
  snapshot.environment.temperature_c = temperature;
};
const missionPointsPossible = (completed, points) => {
  if (completed === 0) return points === 0;
  const remainder = points - completed * 10;
  if (remainder < 0 || remainder > completed * 7) return false;
  const minimumSevens = Math.max(0, Math.ceil((remainder - completed * 3) / 4));
  const maximumSevens = Math.min(completed, Math.floor(remainder / 7));
  return minimumSevens + ((remainder - minimumSevens) % 3) <= maximumSevens;
};
const missionCountFor = (points) => {
  for (
    let completed = points === 0 ? 0 : Math.ceil(points / 17);
    completed <= Math.floor(points / 10);
    completed += 1
  ) {
    if (missionPointsPossible(completed, points)) return completed;
  }
  throw new Error(`No mission composition for ${points} points`);
};
const currentGoalFor = (snapshot) => {
  const { day, slot } = snapshot.clock,
    rank = snapshot.protagonist.hunter_rank,
    arrears = snapshot.economy.rent_arrears,
    slotIndex = ["Morning", "Afternoon", "Evening", "Late Night"].indexOf(slot);
  if (day < 3 || (day === 3 && slotIndex < 2))
    return "Earn enough yen to pay rent";
  if (day < 4 || (day === 4 && slotIndex < 1))
    return "Register with the Tokyo Hunter Guild";
  if (arrears > 0)
    return `Clear ¥${arrears.toLocaleString("en-US")} in rent arrears`;
  if (rank === "F") return "Survive gate work and reach Rank E";
  return `Build a stable life as a Rank ${rank} hunter`;
};
const aikoRelationship = {
  affection: 0,
  familiarity: 5,
  loyalty: 4,
  name: "Aiko Sato",
  role: "F-rank guild clerk",
  tension: 0,
  trust: 3,
};
const initialRelationships = {
  "Aiko Sato": aikoRelationship,
  "Daichi Mori": {
    affection: 0,
    familiarity: 3,
    loyalty: 2,
    name: "Daichi Mori",
    role: "Rank E patrol leader",
    tension: 0,
    trust: 4,
  },
  "Mei Kuroda": {
    affection: 0,
    familiarity: 2,
    loyalty: 2,
    name: "Mei Kuroda",
    role: "independent portal researcher",
    tension: 0,
    trust: 1,
  },
  "Haruto Ishikawa": {
    affection: 0,
    familiarity: 3,
    loyalty: 2,
    name: "Haruto Ishikawa",
    role: "hunter supply owner",
    tension: 0,
    trust: 3,
  },
};
const syncRegistration = (snapshot) => {
  const slots = ["Morning", "Afternoon", "Evening", "Late Night"],
    position = snapshot.clock.day * 4 + slots.indexOf(snapshot.clock.slot),
    introduced = {
      "Aiko Sato": 4 * 4 + 1,
      "Daichi Mori": 5 * 4 + 1,
      "Mei Kuroda": 6 * 4 + 2,
      "Haruto Ishikawa": 9 * 4 + 3,
    },
    schedules = {
      "Aiko Sato": {
        Morning: "Tokyo Hunter Guild",
        Afternoon: "Tokyo Hunter Guild",
        Evening: "Kita-Senju Station",
        "Late Night": "Home",
      },
      "Daichi Mori": {
        Morning: "Adachi Gate Zone",
        Afternoon: "Tokyo Hunter Guild",
        Evening: "Arakawa Riverbank",
        "Late Night": "Home",
      },
      "Haruto Ishikawa": {
        Morning: "Akihabara Market",
        Afternoon: "Akihabara Market",
        Evening: "Kita-Senju Station",
        "Late Night": "Home",
      },
      "Mei Kuroda": {
        Morning: "Ueno Library",
        Afternoon: "Adachi Gate Zone",
        Evening: "Ueno Library",
        "Late Night": "Shinjuku Guild Annex",
      },
    },
    fixedHunterRecord =
      (snapshot.clock.day === 3 && snapshot.clock.slot === "Evening") ||
      (snapshot.clock.day === 4 && snapshot.clock.slot === "Afternoon"),
    awakeningMemory = {
      day: 3,
      importance: 10,
      summary: "Awakening assessment: Awakened at Rank F with Threat Sense.",
    },
    registrationMemory = {
      day: 4,
      importance: 8,
      summary:
        "Guild registration: Aiko Sato issued an F-rank license; travel and filing cost ¥0.",
    };
  snapshot.conversations = [];
  snapshot.activity.key_memories =
    position >= 4 * 4 + 1
      ? [awakeningMemory, registrationMemory]
      : position >= 3 * 4 + 2
        ? [awakeningMemory]
        : [];
  if (fixedHunterRecord) {
    snapshot.protagonist.progression.rank_points = 0;
    snapshot.protagonist.progression.missions_attempted = 0;
    snapshot.protagonist.progression.missions_completed = 0;
    snapshot.protagonist.equipment = {
      armor: null,
      inventory: {},
      weapon: null,
    };
    snapshot.portals = {
      active_plan: null,
      discovered: [],
      investigations: [],
    };
  }
  if (snapshot.clock.day === 3 && snapshot.clock.slot === "Evening") {
    snapshot.protagonist.location = "Tokyo Awakening Bureau";
    snapshot.protagonist.progression.ability_mastery = 1;
    snapshot.activity.recent_events = [
      {
        action: "Awakening assessment",
        day: 3,
        outcome: "Awakened at Rank F with Threat Sense.",
        reason:
          "a city gate alert triggered Ren's mandatory screening (world event)",
        slot: "Afternoon",
      },
    ];
  }
  if (snapshot.clock.day === 4 && snapshot.clock.slot === "Afternoon") {
    snapshot.protagonist.location = "Tokyo Hunter Guild";
    snapshot.environment.gate_alert_level = 2;
    snapshot.activity.recent_events = [
      {
        action: "Guild registration",
        day: 4,
        outcome:
          "Aiko Sato issued an F-rank license; travel and filing cost ¥0.",
        reason:
          "newly awakened citizens must register before accepting hunter work (world event)",
        slot: "Morning",
      },
    ];
  }
  snapshot.relationships = snapshot.relationships.filter(
    (item) => position >= introduced[item.name],
  );
  for (const [name, start] of Object.entries(introduced)) {
    if (
      position >= start &&
      !snapshot.relationships.some((item) => item.name === name)
    )
      snapshot.relationships.push({ ...initialRelationships[name] });
    if (position === start)
      snapshot.relationships = snapshot.relationships.map((item) =>
        item.name === name ? { ...initialRelationships[name] } : item,
      );
  }
  snapshot.relationships.sort((a, b) => a.name.localeCompare(b.name));
  snapshot.whereabouts = snapshot.relationships.map(({ name }) => ({
    location:
      snapshot.clock.day % 7 === 0 &&
      ["Aiko Sato", "Haruto Ishikawa"].includes(name)
        ? "Asakusa Shrine District"
        : schedules[name][snapshot.clock.slot],
    name,
  }));
};
const setProgression = (
  snapshot,
  hunter_rank,
  ability,
  rank_points,
  missions_completed = missionCountFor(rank_points),
) => {
  if (hunter_rank === "Unranked" && snapshot.clock.day > 3) {
    snapshot.clock = { day: 3, slot: "Afternoon" };
    snapshot.activity.recent_events = [];
    snapshot.activity.key_memories = [];
    snapshot.story.next.days_remaining = 180;
    snapshot.economy.rent_payments = 0;
    snapshot.economy.rent_arrears = 0;
  }
  if (
    snapshot.clock.day < 4 ||
    (snapshot.clock.day === 4 &&
      ["Morning", "Afternoon"].includes(snapshot.clock.slot))
  ) {
    snapshot.economy.shop_visits = 0;
    snapshot.protagonist.equipment = {
      armor: null,
      inventory: {},
      weapon: null,
    };
    snapshot.portals = {
      active_plan: null,
      discovered: [],
      investigations: [],
    };
  }
  if (hunter_rank === "Unranked")
    snapshot.protagonist.progression.ability_mastery = 0;
  snapshot.protagonist.hunter_rank = hunter_rank;
  snapshot.protagonist.ability = ability;
  snapshot.protagonist.progression.rank_points = rank_points;
  snapshot.protagonist.progression.missions_completed = missions_completed;
  snapshot.protagonist.progression.missions_attempted = missions_completed;
  snapshot.protagonist.current_goal = currentGoalFor(snapshot);
  syncRegistration(snapshot);
};
async function render(path = "/") {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set(
    "test",
    String(process.pid) + "-" + String(Date.now()),
  );
  const { default: worker } = await import(workerUrl.href);
  return worker.fetch(
    new Request("http://localhost" + path),
    {
      ASSETS: { fetch: async () => new Response("Not found", { status: 404 }) },
    },
    { waitUntil() {}, passThroughOnException() {} },
  );
}
test("renders the observer shell with production metadata", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  const html = await response.text();
  assert.match(html, /AWAKENED: ZERO RANK/);
  assert.match(html, /Authenticating chronicle/i);
  assert.doesNotMatch(html, /codex-preview|react-loading-skeleton/i);
});
test("ships authenticated read-only artifacts compatible with each other", async () => {
  const [contract, snapshot, page] = await Promise.all([
    readFile(new URL("public/data/observer-contract.json", root), "utf8").then(
      JSON.parse,
    ),
    readFile(new URL("public/data/observer-snapshot.json", root), "utf8").then(
      JSON.parse,
    ),
    readFile(new URL("app/page.tsx", root), "utf8"),
  ]);
  const verified = await verifyArtifacts(contract, snapshot);
  assert.equal(verified.contract.contract_sha256, contract.contract_sha256);
  assert.equal(verified.snapshot.identity.digest, snapshot.identity.digest);
  assert.equal(contract.read_only, true);
  assert.deepEqual(contract.control_capabilities, []);
  assert.equal(contract.observer_schema_version, snapshot.schema_version);
  assert.ok(page.includes("CONTRACT / "));
});
test("snapshot identity detects content tampering", async () => {
  const [contract, snapshot] = await Promise.all([
    readFile(new URL("public/data/observer-contract.json", root), "utf8").then(
      JSON.parse,
    ),
    readFile(new URL("public/data/observer-snapshot.json", root), "utf8").then(
      JSON.parse,
    ),
  ]);
  snapshot.protagonist.resources.money += 1;
  await assert.rejects(
    verifyArtifacts(contract, snapshot),
    /invalid observer snapshot/,
  );
});
test("runtime guards reject re-hashed malformed render data", async () => {
  const [contract, snapshot] = await Promise.all([
    readFile(new URL("public/data/observer-contract.json", root), "utf8").then(
      JSON.parse,
    ),
    readFile(new URL("public/data/observer-snapshot.json", root), "utf8").then(
      JSON.parse,
    ),
  ]);
  snapshot.protagonist.resources.health = "100";
  const payload = { ...snapshot };
  delete payload.identity;
  delete payload.path;
  snapshot.identity.digest = createHash("sha256")
    .update(canonical(payload))
    .digest("hex");
  await assert.rejects(
    verifyArtifacts(contract, snapshot),
    /malformed observer artifacts/,
  );
  const malformedContract = { ...contract, read_only: "true" };
  const contractPayload = { ...malformedContract };
  delete contractPayload.contract_sha256;
  malformedContract.contract_sha256 = createHash("sha256")
    .update(canonical(contractPayload))
    .digest("hex");
  await assert.rejects(
    verifyArtifacts(
      malformedContract,
      JSON.parse(
        await readFile(
          new URL("public/data/observer-snapshot.json", root),
          "utf8",
        ),
      ),
    ),
    /malformed observer artifacts/,
  );
});
test("refreshes verified artifact pairs without exposing controls", async () => {
  const page = await readFile(new URL("app/page.tsx", root), "utf8");
  assert.match(page, /REFRESH_INTERVAL_MS\s*=\s*60_000/);
  assert.equal((page.match(/cache:\s*"no-store"/g) || []).length, 1);
  assert.match(page, /window\.setInterval\(refresh,\s*REFRESH_INTERVAL_MS\)/);
  assert.match(page, /controller\.abort\(\)/);
  assert.match(page, /window\.clearInterval\(interval\)/);
  assert.match(page, /if \(trusted\)[\s\S]*setStale\(true\)/);
  assert.match(page, /setFailed\(false\)/);
  assert.match(page, /aria-live="polite"/);
  assert.match(page, /document\.visibilityState === "hidden"/);
  assert.match(
    page,
    /document\.addEventListener\("visibilitychange", refreshWhenVisible\)/,
  );
  assert.match(
    page,
    /document\.removeEventListener\("visibilitychange", refreshWhenVisible\)/,
  );
  assert.doesNotMatch(page, /<button|onClick=/);
});

test("signals only verified digest changes with reduced-motion-safe cleanup", async () => {
  const [page, css] = await Promise.all([
    readFile(new URL("app/page.tsx", root), "utf8"),
    readFile(new URL("app/globals.css", root), "utf8"),
  ]);
  assert.match(page, /previousDigest\.current !== null/);
  assert.match(
    page,
    /previousDigest\.current !== nextSnapshot\.identity\.digest/,
  );
  assert.match(
    page,
    /window\.setTimeout\(\(\) => setUpdated\(false\), 1_800\)/,
  );
  assert.match(page, /window\.clearTimeout\(updateTimer\)/);
  assert.match(page, /CHRONICLE ADVANCED \/ VERIFIED/);
  assert.match(page, /chronicle-updated/);
  assert.match(css, /@keyframes chronicle-advance/);
  assert.match(
    css,
    /@media\(prefers-reduced-motion:reduce\)\{\*\{animation:none!important;scroll-behavior:auto!important\}\}/,
  );
});

test("uses semantic section headings and accessible condition meters", async () => {
  const page = await readFile(new URL("app/page.tsx", root), "utf8");
  assert.equal((page.match(/className="section-label"/g) || []).length, 17);
  assert.doesNotMatch(page, /<label|<\/label>/);
  assert.match(page, /<nav aria-label="Current world status">/);
  assert.match(page, /role="status" aria-live="polite" aria-atomic="true"/);
  assert.match(page, /role="progressbar"/);
  assert.match(page, /aria-label="Story arc progress"/);
  assert.match(page, /aria-valuemin=\{0\}/);
  assert.match(page, /aria-valuemax=\{100\}/);
  assert.match(page, /aria-valuenow=\{p\.resources\[k\]\}/);
});
test("renders deterministic rank-gated equipment progression", async () => {
  const [data, page, css] = await Promise.all([
    import("../app/observer-data.ts"),
    readFile(new URL("app/page.tsx", root), "utf8"),
    readFile(new URL("app/globals.css", root), "utf8"),
  ]);
  assert.deepEqual(
    data.EQUIPMENT_CATALOG.map(({ name, kind, price, bonus, minimumRank }) => [
      name,
      kind,
      price,
      bonus,
      minimumRank,
    ]),
    [
      ["Field Knife", "weapon", 2400, 7, "F"],
      ["Padded Jacket", "armor", 3200, 5, "F"],
      ["Reinforced Machete", "weapon", 7200, 11, "E"],
      ["Gateweave Vest", "armor", 8400, 9, "E"],
      ["Mana-edge Saber", "weapon", 14800, 16, "D"],
      ["Barrier Coat", "armor", 16600, 14, "D"],
      ["Riftglass Katana", "weapon", 26000, 23, "C"],
      ["Aegis Longcoat", "armor", 28500, 20, "C"],
    ],
  );
  assert.match(page, /EQUIPMENT PROGRESSION/);
  assert.match(page, /RENT RESERVE PROTECTED/);
  assert.match(page, /item\.price \+ snapshot\.economy\.rent_cost/);
  assert.match(page, /LOCKED \/ RANK/);
  assert.match(page, /EQUIPPED/);
  assert.match(css, /\.gear-grid\{display:grid/);
});
test("renders the exact rank-scaled Gate threat ladder", async () => {
  const [data, page] = await Promise.all([
    import("../app/observer-data.ts"),
    readFile(new URL("app/page.tsx", root), "utf8"),
  ]);
  assert.deepEqual(
    data.GATE_ENCOUNTER_CATALOG.map(
      ({ name, minimumRank, difficulty, reward }) => [
        name,
        minimumRank,
        difficulty,
        reward,
      ],
    ),
    [
      ["Tunnel Slime Nest", "F", 42, 5400],
      ["Goblin Scavenger Pack", "F", 49, 6600],
      ["Armored Fang Boar", "F", 57, 8200],
      ["Echo Wraith Corridor", "E", 64, 10500],
      ["Rift Hound Matriarch", "D", 72, 13800],
      ["Mirror Oni Vanguard", "C", 82, 18000],
    ],
  );
  assert.match(page, /GATE THREAT LADDER/);
  assert.match(page, /RANK-SCALED MISSIONS/);
  assert.match(page, /LOCKED \/ \$\{encounter\.name\}/);
});
test("renders bounded rank-gated field supplies", async () => {
  const [data, page] = await Promise.all([
    import("../app/observer-data.ts"),
    readFile(new URL("app/page.tsx", root), "utf8"),
  ]);
  assert.deepEqual(
    data.FIELD_SUPPLY_CATALOG.map(
      ({ name, minimumRank, price, effect, maximum }) => [
        name,
        minimumRank,
        price,
        effect,
        maximum,
      ],
    ),
    [
      ["Healing Gel", "F", 900, "HEALTH +22", 2],
      ["Energy Drink", "F", 450, "ENERGY +18", 2],
      ["Trauma Foam", "E", 1800, "HEALTH +35", 1],
      ["Focus Ampoule", "E", 1200, "ENERGY +30", 1],
    ],
  );
  assert.match(page, /FIELD SUPPLIES/);
  assert.match(page, /BOUNDED RESERVES/);
  assert.match(page, /\$\{count\} OF \$\{item\.maximum\}/);
});
test("renders the complete portal atlas without leaking unknown evidence", async () => {
  const [data, page, css] = await Promise.all([
    import("../app/observer-data.ts"),
    readFile(new URL("app/page.tsx", root), "utf8"),
    readFile(new URL("app/globals.css", root), "utf8"),
  ]);
  assert.equal(data.PORTAL_PROFILE_CATALOG.length, 8);
  assert.deepEqual(
    data.PORTAL_PROFILE_CATALOG.slice(-2).map(
      ({ name, environment, hazard }) => [name, environment, hazard],
    ),
    [
      ["Kawasaki Floodgate Labyrinth", "underground", "pressure surges"],
      ["Chiba Glasshouse Breach", "forest", "razor vines"],
    ],
  );
  assert.ok(
    data.PORTAL_PROFILE_CATALOG.every(({ aftermath }) => aftermath.length > 20),
  );
  assert.match(page, /PORTAL ATLAS/);
  assert.match(page, /HAZARD \/ CLASSIFIED/);
  assert.match(page, /EFFECT \/ CLASSIFIED/);
  assert.match(page, /VERIFIED EFFECT/);
  assert.match(page, /discovered\.includes\(portal\.name\)/);
  assert.match(css, /\.atlas-grid\{display:grid/);
});
test("publishes canonical share metadata and a keyboard skip path", async () => {
  const [layout, page, css] = await Promise.all([
    readFile(new URL("app/layout.tsx", root), "utf8"),
    readFile(new URL("app/page.tsx", root), "utf8"),
    readFile(new URL("app/globals.css", root), "utf8"),
  ]);
  assert.match(layout, /metadataBase:new URL\(SITE_URL\)/);
  assert.match(layout, /alternates:\{canonical:"\/"\}/);
  assert.match(layout, /openGraph:\{type:"website",url:"\/",/);
  assert.match(layout, /className="skip-link" href="#chronicle"/);
  assert.match(layout, /\\u2014/);
  assert.doesNotMatch(layout, /ZERO RANK \?/);
  assert.match(page, /<main id="chronicle" tabIndex=\{-1\}/);
  assert.match(css, /\.skip-link:focus\{transform:translateY\(0\)\}/);
});
test("keeps a stable main landmark through verification states", async () => {
  const page = await readFile(new URL("app/page.tsx", root), "utf8");
  assert.equal(
    (page.match(/<main id="chronicle" tabIndex=\{-1\}/g) || []).length,
    3,
  );
  assert.match(
    page,
    /className="loading" aria-busy="true"><div role="status" aria-live="polite">/,
  );
  assert.match(page, /className="loading"><div role="alert">/);
  assert.doesNotMatch(page, /<main className="loading">/);
});
test("ships a production-specific observer package", async () => {
  const readme = await readFile(new URL("README.md", root), "utf8");
  assert.match(readme, /# AWAKENED: ZERO RANK Observer/);
  assert.match(readme, /## Trusted data boundary/);
  assert.match(readme, /## Product constraints/);
  assert.doesNotMatch(readme, /vinext-starter|rendered loading skeleton/);
  for (const asset of ["file.svg", "globe.svg", "window.svg"]) {
    await assert.rejects(access(new URL("public/" + asset, root)));
  }
});
test("shows a quiet timestamp only after successful verification", async () => {
  const [page, css] = await Promise.all([
    readFile(new URL("app/page.tsx", root), "utf8"),
    readFile(new URL("app/globals.css", root), "utf8"),
  ]);
  assert.match(
    page,
    /const \[verifiedAt, setVerifiedAt\] = useState<Date \| null>\(null\)/,
  );
  assert.ok(
    page.indexOf("await verifyArtifacts") <
      page.indexOf("setVerifiedAt(new Date())"),
  );
  assert.match(
    page,
    /<\/span>\{verifiedAt&&<time dateTime=\{verifiedAt\.toISOString\(\)\}>LAST VERIFIED \{verifiedAt\.toISOString\(\)\.slice\(11,19\)\} UTC<\/time>\}/,
  );
  assert.match(css, /\.verification time\{margin-top:4px/);
});
test("keeps the private observer out of crawler indexes", async () => {
  const [page, robots] = await Promise.all([render(), render("/robots.txt")]);
  assert.equal(page.status, 200);
  assert.match(
    await page.text(),
    /<meta name="robots" content="noindex, nofollow, noarchive, nosnippet"\/>/,
  );
  assert.equal(robots.status, 200);
  const policy = await robots.text();
  assert.match(policy, /User-Agent: \*/i);
  assert.match(policy, /Disallow: \//i);
});
test("reacts immediately to browser connectivity changes", async () => {
  const page = await readFile(new URL("app/page.tsx", root), "utf8");
  assert.match(
    page,
    /function markOffline\(\) \{\s*if \(trusted\) setStale\(true\);/,
  );
  assert.match(page, /function refreshWhenOnline\(\) \{\s*void refresh\(\);/);
  assert.match(page, /window\.addEventListener\("offline", markOffline\)/);
  assert.match(page, /window\.addEventListener\("online", refreshWhenOnline\)/);
  assert.match(page, /window\.removeEventListener\("offline", markOffline\)/);
  assert.match(
    page,
    /window\.removeEventListener\("online", refreshWhenOnline\)/,
  );
  assert.match(page, /className="stale-notice" role="status"/);
});
test("validates and renders the completed three-year arc", async () => {
  const [snapshot, page] = await Promise.all([
    readFile(new URL("public/data/observer-snapshot.json", root), "utf8").then(
      JSON.parse,
    ),
    readFile(new URL("app/page.tsx", root), "utf8"),
  ]);
  snapshot.clock.day = 1095;
  syncEnvironment(snapshot);
  snapshot.story.completed = completedStory(6);
  snapshot.story.next = null;
  snapshot.story.completed_count = snapshot.story.total_anchors;
  snapshot.story.ending_reached = true;
  snapshot.story.ending = {
    id: "zero-rank-horizon",
    isolated_count: 0,
    prepared_count: 6,
    resilient_count: 0,
    summary:
      "Ren's evidence and trusted circle changed what Tokyo valued in a hunter.",
    tier: "prepared",
    title: "The Zero-Rank Horizon",
  };
  assert.equal(isObserverSnapshot(snapshot), true);
  snapshot.story.ending.summary = "";
  assert.equal(isObserverSnapshot(snapshot), false);
  assert.match(page, /snapshot\.story\.next \? <>/);
  assert.match(page, /snapshot\.story\.ending\?\.title/);
  assert.match(page, /<strong>ARC<small>COMPLETE<\/small><\/strong>/);
  assert.match(page, /className="completed-arcs"/);
  assert.doesNotMatch(page, /next\?\.day|next\?\.days_remaining/);
});
test("renders a spoiler-light authenticated three-year timeline", async () => {
  const [data, page, css, snapshot] = await Promise.all([
    import("../app/observer-data.ts"),
    readFile(new URL("app/page.tsx", root), "utf8"),
    readFile(new URL("app/globals.css", root), "utf8"),
    readFile(new URL("public/data/observer-snapshot.json", root), "utf8").then(
      JSON.parse,
    ),
  ]);
  const timeline = data.storyTimeline(snapshot);
  assert.equal(timeline.length, 6);
  assert.deepEqual(timeline[0], {
    day: 183,
    daysRemaining: 172,
    status: "next",
    title: "The Adachi Warning",
  });
  assert.deepEqual(
    timeline.slice(1).map(({ status, title }) => [status, title]),
    Array(5).fill(["locked", "Unrevealed chapter"]),
  );
  assert.match(page, /VIEW THREE-YEAR TIMELINE/);
  assert.match(page, /SPOILER-LIGHT/);
  assert.match(css, /\.arc-timeline li\.locked\{opacity:/);
});
test("explains valid empty chronicle collections", async () => {
  const [page, css] = await Promise.all([
    readFile(new URL("app/page.tsx", root), "utf8"),
    readFile(new URL("app/globals.css", root), "utf8"),
  ]);
  assert.match(
    page,
    /events\.length===0&&<p className="empty-state">Ren has not made a recorded decision yet\.<\/p>/,
  );
  assert.match(
    page,
    /conversations\.length===0\?<p className="empty-state">No recurring conversation has been recorded yet\.<\/p>/,
  );
  assert.match(
    page,
    /people\.length===0&&<p className="empty-state">No trusted relationships have formed yet\.<\/p>/,
  );
  assert.match(
    page,
    /portalCases\.length===0&&<p className="empty-state">No portals have been discovered yet\.<\/p>/,
  );
  assert.match(page, /No defining memories have formed yet\./);
  assert.equal((page.match(/className="empty-state"/g) || []).length, 6);
  assert.match(css, /\.empty-state\{margin:0;padding:18px 0/);
});
test("renders the complete authenticated chronicle surface", async () => {
  const page = await readFile(new URL("app/page.tsx", root), "utf8");
  for (const heading of [
    "LATEST DAY",
    "RECENT CONVERSATIONS",
    "HUNTER RECORD",
    "LIFE LEDGER",
    "THREE-YEAR ARC",
    "PEOPLE IN ORBIT",
    "PORTAL CASE FILES",
    "KEY MEMORIES",
  ]) {
    assert.match(page, new RegExp(heading));
  }
  for (const field of [
    "event.reason",
    "conversation.npc_line",
    "conversation.ren_line",
    "p.equipment.weapon",
    "p.equipment.armor",
    "snapshot.economy.rent_cost",
    "p.progression.missions_completed",
    "relationship.familiarity",
    "investigation.progress",
    "memory.summary",
  ]) {
    assert.match(page, new RegExp(field.replaceAll(".", "\\.")));
  }
  assert.match(page, /NO CONTROL CAPABILITIES/);
  assert.doesNotMatch(page, /<button|onClick=/);
});
test("joins authenticated portal evidence into read-only case files", async () => {
  const [data, page, css, snapshot] = await Promise.all([
    import("../app/observer-data.ts"),
    readFile(new URL("app/page.tsx", root), "utf8"),
    readFile(new URL("app/globals.css", root), "utf8"),
    readFile(new URL("public/data/observer-snapshot.json", root), "utf8").then(
      JSON.parse,
    ),
  ]);
  const cases = data.portalCaseFiles(snapshot);
  assert.equal(cases.length, snapshot.portals.discovered.length);
  assert.deepEqual(
    cases.map(({ profile }) => profile.name),
    snapshot.portals.discovered,
  );
  assert.equal(
    cases.find(({ active }) => active)?.profile.name ?? null,
    snapshot.portals.active_plan,
  );
  const investigated = cases.find(
    ({ investigation }) => investigation !== null,
  );
  assert.equal(
    investigated?.investigation?.portal_name,
    investigated?.profile.name,
  );
  assert.match(page, /PORTAL CASE FILES/);
  assert.match(page, /VERIFIED EFFECT/);
  assert.match(page, /collaboratorLocation/);
  assert.match(css, /\.portal-case\.active/);
});
test("presents authenticated key memories as a continuity archive", async () => {
  const [data, page, css, snapshot] = await Promise.all([
    import("../app/observer-data.ts"),
    readFile(new URL("app/page.tsx", root), "utf8"),
    readFile(new URL("app/globals.css", root), "utf8"),
    readFile(new URL("public/data/observer-snapshot.json", root), "utf8").then(
      JSON.parse,
    ),
  ]);
  const archive = data.memoryArchive(snapshot);
  assert.equal(archive.length, snapshot.activity.key_memories.length);
  assert.deepEqual(
    archive.map(({ importance }) => importance),
    snapshot.activity.key_memories.map(({ importance }) => importance),
  );
  assert.deepEqual(
    archive.map(({ band }) => band),
    ["formative", "defining", "defining", "defining", "defining"],
  );
  assert.equal(archive[0].ageDays, snapshot.clock.day - archive[0].day);
  assert.match(page, /CONTINUITY ARCHIVE/);
  assert.match(page, /memory\.ageDays/);
  assert.match(css, /\.memories li\.formative>i/);
});
test("summarizes recent authenticated activity without parsing reasons", async () => {
  const [data, page, css, snapshot] = await Promise.all([
    import("../app/observer-data.ts"),
    readFile(new URL("app/page.tsx", root), "utf8"),
    readFile(new URL("app/globals.css", root), "utf8"),
    readFile(new URL("public/data/observer-snapshot.json", root), "utf8").then(
      JSON.parse,
    ),
  ]);
  const rhythm = data.recentRhythm(snapshot);
  assert.equal(rhythm.total, snapshot.activity.recent_events.length);
  assert.equal(rhythm.dominantAction, "Rest");
  assert.equal(rhythm.entries[0].count, 3);
  assert.equal(rhythm.activeDays, 3);
  assert.equal(rhythm.variety, 7);
  assert.match(page, /RECENT RHYTHM/);
  assert.doesNotMatch(data.recentRhythm.toString(), /reason|outcome/);
  assert.match(css, /\.rhythm-lead/);
});
test("keeps large reference catalogs behind accessible native disclosures", async () => {
  const [page, css] = await Promise.all([
    readFile(new URL("app/page.tsx", root), "utf8"),
    readFile(new URL("app/globals.css", root), "utf8"),
  ]);
  assert.equal((page.match(/className="reference-shelf/g) || []).length, 5);
  assert.match(page, /INSPECT EQUIPMENT LADDER/);
  assert.match(page, /INSPECT ANNUAL CALENDAR/);
  assert.match(page, /INSPECT COMPLETE PORTAL CATALOG/);
  assert.doesNotMatch(page, /<details[^>]*open/);
  assert.match(css, /\.reference-shelf summary/);
  assert.match(css, /\.reference-shelf\[open\]/);
});
test("derives the next hunter promotion and equipment runway", async () => {
  const [data, page, css, snapshot] = await Promise.all([
    import("../app/observer-data.ts"),
    readFile(new URL("app/page.tsx", root), "utf8"),
    readFile(new URL("app/globals.css", root), "utf8"),
    readFile(new URL("public/data/observer-snapshot.json", root), "utf8").then(
      JSON.parse,
    ),
  ]);
  assert.deepEqual(data.rankForecast(snapshot), {
    nextRank: "E",
    pointsRemaining: 7,
    progressPercent: 77,
    unlocks: ["Reinforced Machete", "Gateweave Vest"],
  });
  const ceiling = structuredClone(snapshot);
  ceiling.protagonist.hunter_rank = "C";
  ceiling.protagonist.progression.rank_points = 90;
  assert.equal(data.rankForecast(ceiling).nextRank, null);
  assert.match(page, /NEXT PROMOTION/);
  assert.match(page, /Progress toward Rank/);
  assert.match(css, /\.rank-runway/);
});
test("explains current Gate readiness from authenticated field conditions", async () => {
  const [data, page, css, snapshot] = await Promise.all([
    import("../app/observer-data.ts"),
    readFile(new URL("app/page.tsx", root), "utf8"),
    readFile(new URL("app/globals.css", root), "utf8"),
    readFile(new URL("public/data/observer-snapshot.json", root), "utf8").then(
      JSON.parse,
    ),
  ]);
  assert.deepEqual(data.gateReadiness(snapshot), {
    energy: "ready",
    health: "ready",
    plan: null,
    registered: true,
    status: "field ready",
    supplyCount: 0,
  });
  const strained = structuredClone(snapshot);
  strained.protagonist.resources.energy = 39;
  assert.equal(data.gateReadiness(strained).status, "recover first");
  assert.match(page, /GATE READINESS/);
  assert.match(page, /INSPECT GATE THREAT LADDER/);
  assert.match(css, /\.gate-readiness\.recover-first/);
});
test("renders the latest retained day as a four-slot narrative strip", async () => {
  const [data, page, css, snapshot] = await Promise.all([
    import("../app/observer-data.ts"),
    readFile(new URL("app/page.tsx", root), "utf8"),
    readFile(new URL("app/globals.css", root), "utf8"),
    readFile(new URL("public/data/observer-snapshot.json", root), "utf8").then(
      JSON.parse,
    ),
  ]);
  const timeline = data.recentDayTimeline(snapshot);
  assert.equal(timeline.day, 10);
  assert.deepEqual(
    timeline.slots.map(({ slot }) => slot),
    ["Morning", "Afternoon", "Evening", "Late Night"],
  );
  assert.deepEqual(
    timeline.slots.map(({ events }) => events.map(({ action }) => action)),
    [["Eat"], ["Guild patrol"], ["Guild patrol"], ["Rest"]],
  );
  assert.match(page, /className="day-strip"/);
  assert.match(page, /INSPECT DECISION LEDGER/);
  assert.match(css, /\.events \.day-strip/);
});
test("provides responsive contrast print and motion-safe presentation", async () => {
  const css = await readFile(new URL("app/globals.css", root), "utf8");
  assert.match(css, /@media\(max-width:1050px\)/);
  assert.match(css, /@media\(max-width:720px\)/);
  assert.match(css, /@media\(max-width:420px\)/);
  assert.match(css, /@media\(prefers-contrast:more\)/);
  assert.match(css, /@media print/);
  assert.match(css, /scroll-behavior:auto!important/);
});
test("shows authenticated freshness and fail-closed context", async () => {
  const page = await readFile(new URL("app/page.tsx", root), "utf8");
  assert.match(page, /No unverified world data has been rendered\./);
  assert.match(page, /last authenticated chronicle/);
  assert.match(page, /WORLD POSITION/);
  assert.match(page, /SNAPSHOT \/ /);
  assert.match(page, /CONTRACT \/ /);
});
test("adds production browser security and artifact cache policy", async () => {
  const [response, worker] = await Promise.all([
    render(),
    readFile(new URL("worker/index.ts", root), "utf8"),
  ]);
  assert.equal(
    response.headers.get("cross-origin-opener-policy"),
    "same-origin",
  );
  assert.equal(
    response.headers.get("permissions-policy"),
    "camera=(), geolocation=(), microphone=()",
  );
  assert.equal(response.headers.get("referrer-policy"), "no-referrer");
  assert.equal(response.headers.get("x-content-type-options"), "nosniff");
  assert.match(worker, /url\.pathname\.startsWith\("\/data\/"\)/);
  assert.match(worker, /no-store, max-age=0, must-revalidate/);
});
test("rejects contradictory story chronology before rendering", async () => {
  const original = await readFile(
    new URL("public/data/observer-snapshot.json", root),
    "utf8",
  ).then(JSON.parse);
  const badCountdown = structuredClone(original);
  badCountdown.story.next.days_remaining += 1;
  assert.equal(isObserverSnapshot(badCountdown), false);
  const premature = structuredClone(original);
  premature.story.completed_count = premature.story.total_anchors;
  assert.equal(isObserverSnapshot(premature), false);
  const ending = structuredClone(original);
  ending.clock.day = 1095;
  syncEnvironment(ending);
  ending.story.completed = completedStory(6, [
    "isolated",
    "prepared",
    "resilient",
    "resilient",
    "resilient",
    "resilient",
  ]);
  ending.story.next = null;
  ending.story.completed_count = ending.story.total_anchors;
  ending.story.ending_reached = true;
  ending.story.ending = {
    id: "quiet-guardian",
    isolated_count: 1,
    prepared_count: 1,
    resilient_count: 3,
    summary:
      "Ren left Tokyo steadier through persistence rather than recognition.",
    tier: "resilient",
    title: "Tokyo's Quiet Guardian",
  };
  assert.equal(isObserverSnapshot(ending), false);
  ending.story.ending.resilient_count = 4;
  assert.equal(isObserverSnapshot(ending), true);
});
test("rejects future and out-of-order recent activity", async () => {
  const original = await readFile(
    new URL("public/data/observer-snapshot.json", root),
    "utf8",
  ).then(JSON.parse);
  assert.equal(isObserverSnapshot(original), true);
  const reversed = structuredClone(original);
  reversed.activity.recent_events.reverse();
  assert.equal(isObserverSnapshot(reversed), false);
  const current = structuredClone(original);
  const last = current.activity.recent_events.at(-1);
  current.activity.recent_events = [
    { ...last, day: current.clock.day, slot: current.clock.slot },
  ];
  assert.equal(isObserverSnapshot(current), false);
  const invalidSlot = structuredClone(original);
  invalidSlot.activity.recent_events[0].slot = "Midnight";
  assert.equal(isObserverSnapshot(invalidSlot), false);
  const duplicate = structuredClone(original);
  duplicate.activity.recent_events[1] = {
    ...duplicate.activity.recent_events[0],
  };
  assert.equal(isObserverSnapshot(duplicate), false);
});
test("accepts signed trust and rejects non-canonical relationships", async () => {
  const original = await readFile(
    new URL("public/data/observer-snapshot.json", root),
    "utf8",
  ).then(JSON.parse);
  assert.ok(original.relationships.length > 1);
  const strained = structuredClone(original);
  strained.relationships[0].trust = -100;
  assert.equal(isObserverSnapshot(strained), true);
  const fractional = structuredClone(original);
  fractional.relationships[0].trust = 0.5;
  assert.equal(isObserverSnapshot(fractional), false);
  const reversed = structuredClone(original);
  reversed.relationships.reverse();
  assert.equal(isObserverSnapshot(reversed), false);
  const duplicate = structuredClone(original);
  duplicate.relationships[1] = { ...duplicate.relationships[0] };
  assert.equal(isObserverSnapshot(duplicate), false);
  const tooLow = structuredClone(original);
  tooLow.relationships[0].trust = -101;
  assert.equal(isObserverSnapshot(tooLow), false);
});
test("authenticates and renders schedule-consistent known whereabouts", async () => {
  const [original, page] = await Promise.all([
    readFile(new URL("public/data/observer-snapshot.json", root), "utf8").then(
      JSON.parse,
    ),
    readFile(new URL("app/page.tsx", root), "utf8"),
  ]);
  assert.deepEqual(
    original.whereabouts.map(({ name }) => name),
    original.relationships.map(({ name }) => name),
  );
  assert.equal(isObserverSnapshot(original), true);
  const moved = structuredClone(original);
  moved.whereabouts[0].location = "Home";
  assert.equal(isObserverSnapshot(moved), false);
  const unknown = structuredClone(original);
  unknown.whereabouts.push({ location: "Unknown", name: "Unknown Hunter" });
  assert.equal(isObserverSnapshot(unknown), false);
  assert.match(page, /TOKYO TODAY/);
  assert.match(page, /KNOWN WHEREABOUTS/);
});
test("joins authenticated relationships whereabouts and latest exchanges", async () => {
  const [data, page, css, snapshot] = await Promise.all([
    import("../app/observer-data.ts"),
    readFile(new URL("app/page.tsx", root), "utf8"),
    readFile(new URL("app/globals.css", root), "utf8"),
    readFile(new URL("public/data/observer-snapshot.json", root), "utf8").then(
      JSON.parse,
    ),
  ]);
  const dossiers = data.peopleDossiers(snapshot);
  assert.deepEqual(
    dossiers.map(({ relationship }) => relationship.name),
    snapshot.relationships.map(({ name }) => name),
  );
  assert.equal(dossiers[0].location, "Tokyo Hunter Guild");
  assert.equal(dossiers[0].signal, "Growing familiarity");
  assert.equal(dossiers[0].lastConversation.day, 10);
  assert.equal(dossiers[1].lastConversation, null);
  assert.match(page, /LAST EXCHANGE/);
  assert.match(page, /No complete exchange recorded yet/);
  assert.match(css, /\.last-contact\{padding-left:/);
});
test("provides a complete read-only Tokyo location atlas", async () => {
  const [data, page, css, snapshot] = await Promise.all([
    import("../app/observer-data.ts"),
    readFile(new URL("app/page.tsx", root), "utf8"),
    readFile(new URL("app/globals.css", root), "utf8"),
    readFile(new URL("public/data/observer-snapshot.json", root), "utf8").then(
      JSON.parse,
    ),
  ]);
  const names = data.TOKYO_LOCATION_CATALOG.map(({ name }) => name);
  assert.equal(names.length, 13);
  assert.equal(new Set(names).size, names.length);
  assert.ok(names.includes(snapshot.protagonist.location));
  assert.ok(
    snapshot.whereabouts.every(({ location }) => names.includes(location)),
  );
  assert.match(
    page,
    /INSPECT \{TOKYO_LOCATION_CATALOG\.length\} DOCUMENTED PLACES/,
  );
  assert.match(page, /NO KNOWN PRESENCE/);
  assert.doesNotMatch(page, /onClick=/);
  assert.match(css, /\.city-index summary\{cursor:pointer/);
});
test("derives the current scene only from authenticated world fields", async () => {
  const [data, page, css, snapshot] = await Promise.all([
    import("../app/observer-data.ts"),
    readFile(new URL("app/page.tsx", root), "utf8"),
    readFile(new URL("app/globals.css", root), "utf8"),
    readFile(new URL("public/data/observer-snapshot.json", root), "utf8").then(
      JSON.parse,
    ),
  ]);
  assert.deepEqual(data.currentScene(snapshot), {
    atmosphere: "Morning / Clear, 29 C",
    place: {
      name: "Adachi Apartment",
      purpose: "Ren's home and recovery base",
      ward: "Adachi",
    },
    presence: "No known recurring character is nearby.",
    pressure: "No active Gate pressure",
  });
  const shared = structuredClone(snapshot);
  shared.whereabouts[0].location = shared.protagonist.location;
  assert.equal(data.currentScene(shared).presence, "Nearby: Aiko Sato");
  assert.match(page, /CURRENT SCENE/);
  assert.match(page, /LOCAL PRESENCE/);
  assert.match(css, /\.current-scene\{display:grid/);
});
test("requires canonical seasonal environment conditions", async () => {
  const data = await import("../app/observer-data.ts");
  const original = await readFile(
    new URL("public/data/observer-snapshot.json", root),
    "utf8",
  ).then(JSON.parse);
  assert.deepEqual(
    [1, 91, 92, 182, 183, 273, 274, 365, 366].map(data.seasonForDay),
    [
      "Summer",
      "Summer",
      "Autumn",
      "Autumn",
      "Winter",
      "Winter",
      "Spring",
      "Spring",
      "Summer",
    ],
  );
  assert.deepEqual(Object.keys(data.SEASON_TEMPERATURES), [
    "Summer",
    "Autumn",
    "Winter",
    "Spring",
  ]);
  assert.deepEqual(data.SEASON_TEMPERATURES.Winter, {
    Clear: 9,
    Cloudy: 6,
    Rain: 7,
    Snow: 2,
    "Cold Snap": -3,
  });
  for (const [weather, temperature] of Object.entries(
    data.SEASON_TEMPERATURES.Summer,
  )) {
    const valid = structuredClone(original);
    valid.environment.weather = weather;
    valid.environment.temperature_c = temperature;
    assert.equal(isObserverSnapshot(valid), true);
  }
  const mismatch = structuredClone(original);
  mismatch.environment.temperature_c += 1;
  assert.equal(isObserverSnapshot(mismatch), false);
  const alert = structuredClone(original);
  alert.environment.gate_alert_level = 4;
  assert.equal(isObserverSnapshot(alert), false);
  const fractional = structuredClone(original);
  fractional.environment.gate_alert_level = 1.5;
  assert.equal(isObserverSnapshot(fractional), false);
  const season = structuredClone(original);
  season.environment.season = "Winter";
  season.environment.weather = "Snow";
  season.environment.temperature_c = 2;
  assert.equal(isObserverSnapshot(season), false);
  const unknown = structuredClone(original);
  unknown.environment.weather = "Fog";
  assert.equal(isObserverSnapshot(unknown), false);
});
test("renders calendar year season and day-of-year status", async () => {
  const page = await readFile(new URL("app/page.tsx", root), "utf8");
  assert.match(
    page,
    /calendarYear = Math\.floor\(\(snapshot\.clock\.day - 1\) \/ 365\) \+ 1/,
  );
  assert.match(page, /dayOfYear = \(\(snapshot\.clock\.day - 1\) % 365\) \+ 1/);
  assert.match(
    page,
    /YEAR \{calendarYear\} \/ \{snapshot\.environment\.season\} D\{dayOfYear\}/,
  );
});
test("organizes the long chronicle into navigable complete-row chapters", async () => {
  const [page, css] = await Promise.all([
    readFile(new URL("app/page.tsx", root), "utf8"),
    readFile(new URL("app/globals.css", root), "utf8"),
  ]);
  assert.match(page, /aria-label="Chronicle sections"/);
  for (const id of [
    "current-life",
    "progression",
    "story-world",
    "world-records",
  ]) {
    assert.match(page, new RegExp(`id="${id}"`));
    assert.match(page, new RegExp(`href="#${id}"`));
  }
  assert.match(css, /max-width:1280px/);
  assert.match(css, /\.hunter,\.gear,\.economy\{order:21\}/);
  assert.match(css, /\.portals,\.memories\{order:41\}/);
});
test("derives a concise daily briefing only from authenticated snapshot fields", async () => {
  const [data, page] = await Promise.all([
    import("../app/observer-data.ts"),
    readFile(new URL("app/page.tsx", root), "utf8"),
  ]);
  const original = await readFile(
    new URL("public/data/observer-snapshot.json", root),
    "utf8",
  ).then(JSON.parse);
  const briefing = data.dailyBriefing(original);
  assert.equal(briefing.length, 4);
  assert.deepEqual(
    briefing.map((item) => item.label),
    [
      "Immediate pressure",
      "Story horizon",
      "Seasonal horizon",
      "Portal priority",
    ],
  );
  const urgent = structuredClone(original);
  urgent.economy.rent_arrears = 8000;
  assert.deepEqual(data.dailyBriefing(urgent)[0], {
    label: "Immediate pressure",
    value: "Rent arrears",
    detail: "¥8,000 remains overdue.",
    tone: "urgent",
  });
  assert.match(page, /TODAY AT A GLANCE/);
  assert.match(page, /AUTHENTICATED SUMMARY/);
  assert.doesNotMatch(page, /setBriefing|fetch\([^)]*brief/i);
});
test("renders the exact recurring seasonal calendar", async () => {
  const [data, page] = await Promise.all([
    import("../app/observer-data.ts"),
    readFile(new URL("app/page.tsx", root), "utf8"),
  ]);
  assert.deepEqual(
    data.SEASONAL_EVENT_CATALOG.map(({ dayOfYear, season }) => [
      dayOfYear,
      season,
    ]),
    [
      [7, "Summer"],
      [137, "Autumn"],
      [228, "Winter"],
      [319, "Spring"],
    ],
  );
  assert.deepEqual(data.nextSeasonalEvent(320), {
    dayOfYear: 7,
    season: "Summer",
    title: "Tanabata evening",
    place: "Arakawa Riverbank",
    day: 372,
    daysRemaining: 52,
  });
  assert.match(page, /SEASONAL CALENDAR/);
  assert.match(page, /REPEATS YEARLY/);
  assert.match(page, /without giving the observer control/);
});
test("allows only unique authored portal names", async () => {
  const original = await readFile(
    new URL("public/data/observer-snapshot.json", root),
    "utf8",
  ).then(JSON.parse);
  const names = [
    "Flooded Service Tunnel",
    "Ashen Shopping Arcade",
    "Moonlit Cedar Path",
    "Frostbound Platform",
    "Sunken Courtyard",
    "Glass Office Labyrinth",
  ];
  for (const name of names) {
    const valid = structuredClone(original);
    valid.portals.active_plan = null;
    valid.portals.discovered = [name];
    valid.portals.investigations = valid.portals.investigations.filter(
      (investigation) => investigation.portal_name === name,
    );
    assert.equal(isObserverSnapshot(valid), true);
  }
  const unknown = structuredClone(original);
  unknown.portals.discovered = ["Unknown Gate"];
  assert.equal(isObserverSnapshot(unknown), false);
  const duplicate = structuredClone(original);
  duplicate.portals.discovered = [names[0], names[0]];
  assert.equal(isObserverSnapshot(duplicate), false);
  const empty = structuredClone(original);
  empty.portals.active_plan = null;
  empty.portals.discovered = [];
  empty.portals.investigations = [];
  assert.equal(isObserverSnapshot(empty), true);
});
test("requires canonical rendered protagonist status and integers", async () => {
  const original = await readFile(
    new URL("public/data/observer-snapshot.json", root),
    "utf8",
  ).then(JSON.parse);
  for (const [rank, rank_points] of [
    ["Unranked", 0],
    ["F", 0],
    ["E", 30],
    ["D", 60],
    ["C", 90],
  ]) {
    const valid = structuredClone(original);
    setProgression(
      valid,
      rank,
      rank === "Unranked" ? "None" : "Threat Sense",
      rank_points,
    );
    assert.equal(isObserverSnapshot(valid), true);
  }
  for (const location of [
    "Adachi Apartment",
    "Kita-Senju",
    "Ueno Library",
    "Arakawa Riverbank",
    "Tokyo Awakening Bureau",
    "Tokyo Hunter Guild",
    "Adachi Gate Zone",
    "Kita-Senju Hunter Supply",
  ]) {
    const valid = structuredClone(original);
    valid.protagonist.location = location;
    assert.equal(isObserverSnapshot(valid), true);
  }
  const rank = structuredClone(original);
  rank.protagonist.hunter_rank = "S";
  assert.equal(isObserverSnapshot(rank), false);
  const location = structuredClone(original);
  location.protagonist.location = "Osaka";
  assert.equal(isObserverSnapshot(location), false);
  const fractional = structuredClone(original);
  fractional.protagonist.resources.health = 99.5;
  assert.equal(isObserverSnapshot(fractional), false);
  const readiness = structuredClone(original);
  readiness.protagonist.progression.combat_readiness = 101;
  assert.equal(isObserverSnapshot(readiness), false);
  const money = structuredClone(original);
  money.protagonist.resources.money = -1;
  assert.equal(isObserverSnapshot(money), false);
});
test("requires the fixed six-anchor story schedule", async () => {
  const original = await readFile(
    new URL("public/data/observer-snapshot.json", root),
    "utf8",
  ).then(JSON.parse);
  for (const [index, [day, key, title]] of storyAnchors.entries()) {
    const valid = structuredClone(original);
    valid.clock.day =
      index === 0 ? original.clock.day : storyAnchors[index - 1][0];
    syncEnvironment(valid);
    valid.story.completed = completedStory(index);
    valid.story.completed_count = index;
    valid.story.total_anchors = storyAnchors.length;
    valid.story.next = {
      day,
      key,
      title,
      days_remaining: Math.max(0, day - valid.clock.day),
    };
    assert.equal(isObserverSnapshot(valid), true);
  }
  const early = structuredClone(original);
  early.story.completed_count = 1;
  early.story.next = {
    day: 365,
    key: "arc_tokyo_fracture",
    title: "The Tokyo Fracture",
    days_remaining: 354,
  };
  assert.equal(isObserverSnapshot(early), false);
  const title = structuredClone(original);
  title.story.next.title = "The Invented Arc";
  assert.equal(isObserverSnapshot(title), false);
  const day = structuredClone(original);
  day.story.next.day += 1;
  day.story.next.days_remaining += 1;
  assert.equal(isObserverSnapshot(day), false);
  const total = structuredClone(original);
  total.story.total_anchors = 7;
  assert.equal(isObserverSnapshot(total), false);
});
test("validates named and legacy ending semantics", async () => {
  const original = await readFile(
    new URL("public/data/observer-snapshot.json", root),
    "utf8",
  ).then(JSON.parse);
  const complete = (ending) => {
    const value = structuredClone(original);
    value.clock.day = 1095;
    syncEnvironment(value);
    value.story.completed = completedStory(6, endingTiers(ending));
    value.story.completed_count = 6;
    value.story.next = null;
    value.story.ending_reached = true;
    value.story.ending = ending;
    return value;
  };
  const zero = complete({
    id: "zero-rank-horizon",
    isolated_count: 0,
    prepared_count: 6,
    resilient_count: 0,
    summary:
      "Ren's evidence and trusted circle changed what Tokyo valued in a hunter.",
    tier: "prepared",
    title: "The Zero-Rank Horizon",
  });
  assert.equal(isObserverSnapshot(zero), true);
  const legacy = complete({
    id: "legacy-unavailable",
    isolated_count: 0,
    prepared_count: 0,
    resilient_count: 0,
    summary: "This timeline predates authenticated story outcome evidence.",
    tier: "legacy-unavailable",
    title: "Legacy Ending Unavailable",
  });
  assert.equal(isObserverSnapshot(legacy), true);
  const negativeLegacy = structuredClone(legacy);
  negativeLegacy.story.ending.isolated_count = -1;
  assert.equal(isObserverSnapshot(negativeLegacy), false);
  const invented = structuredClone(zero);
  invented.story.ending.summary = "An invented ending.";
  assert.equal(isObserverSnapshot(invented), false);
  const weakZero = structuredClone(zero);
  weakZero.story.ending.prepared_count = 3;
  weakZero.story.ending.resilient_count = 3;
  assert.equal(isObserverSnapshot(weakZero), false);
  const unfinished = complete({
    id: "unfinished-warning",
    isolated_count: 2,
    prepared_count: 2,
    resilient_count: 2,
    summary: "Ren survived, but the warning he carried remained unresolved.",
    tier: "isolated",
    title: "The Unfinished Warning",
  });
  assert.equal(isObserverSnapshot(unfinished), true);
  const quiet = complete({
    id: "quiet-guardian",
    isolated_count: 1,
    prepared_count: 2,
    resilient_count: 3,
    summary:
      "Ren left Tokyo steadier through persistence rather than recognition.",
    tier: "resilient",
    title: "Tokyo's Quiet Guardian",
  });
  assert.equal(isObserverSnapshot(quiet), true);
  const corridor = complete({
    id: "open-corridor",
    isolated_count: 2,
    prepared_count: 1,
    resilient_count: 3,
    summary:
      "Ren ended the chronicle by keeping Tokyo connected to allies beyond Japan.",
    tier: "prepared",
    title: "The Open Corridor",
  });
  assert.equal(isObserverSnapshot(corridor), true);
  const watch = complete({
    id: "scarred-watch",
    isolated_count: 3,
    prepared_count: 1,
    resilient_count: 2,
    summary:
      "Tokyo endured, and Ren's remaining circle kept watch over its unresolved wounds.",
    tier: "resilient",
    title: "The Scarred Watch",
  });
  assert.equal(isObserverSnapshot(watch), true);
});
test("requires supported snapshot and story schema versions", async () => {
  const original = await readFile(
    new URL("public/data/observer-snapshot.json", root),
    "utf8",
  ).then(JSON.parse);
  assert.equal(original.schema_version, 6);
  assert.equal(original.story.schema_version, 4);
  assert.equal(isObserverSnapshot(original), true);
  for (const version of [3, 4, 5, 999]) {
    const snapshot = structuredClone(original);
    snapshot.schema_version = version;
    assert.equal(isObserverSnapshot(snapshot), false);
  }
  for (const version of [2, 3, 5, 999]) {
    const snapshot = structuredClone(original);
    snapshot.story.schema_version = version;
    assert.equal(isObserverSnapshot(snapshot), false);
  }
  const missing = structuredClone(original);
  delete missing.story.schema_version;
  assert.equal(isObserverSnapshot(missing), false);
});
test("authenticates bounded authored conversation history", async () => {
  const original = await readFile(
    new URL("public/data/observer-snapshot.json", root),
    "utf8",
  ).then(JSON.parse);
  assert.ok(original.conversations.length > 0);
  assert.equal(isObserverSnapshot(original), true);
  for (const mutate of [
    (snapshot) => delete snapshot.conversations,
    (snapshot) => (snapshot.conversations[0].ren_line = ""),
    (snapshot) => (snapshot.conversations[0].npc_name = "Unknown Hunter"),
    (snapshot) => (snapshot.conversations[0].shadow = true),
    (snapshot) => (snapshot.conversations[0].day = snapshot.clock.day + 1),
    (snapshot) =>
      (snapshot.conversations = Array(7).fill(snapshot.conversations[0])),
  ]) {
    const invalid = structuredClone(original);
    mutate(invalid);
    assert.equal(isObserverSnapshot(invalid), false);
  }
});
test("requires authored relationship names and roles", async () => {
  const original = await readFile(
    new URL("public/data/observer-snapshot.json", root),
    "utf8",
  ).then(JSON.parse);
  const roles = {
    "Aiko Sato": "F-rank guild clerk",
    "Daichi Mori": "Rank E patrol leader",
    "Haruto Ishikawa": "hunter supply owner",
    "Mei Kuroda": "independent portal researcher",
  };
  assert.deepEqual(
    Object.fromEntries(
      original.relationships.map(({ name, role }) => [name, role]),
    ),
    roles,
  );
  assert.equal(isObserverSnapshot(original), true);
  for (const [name, role] of Object.entries(roles)) {
    const valid = structuredClone(original);
    const selected = valid.relationships.find(
      (relationship) => relationship.name === name,
    );
    selected.role = role;
    selected.trust = -100;
    assert.equal(isObserverSnapshot(valid), true);
  }
  const invented = structuredClone(original);
  invented.relationships = [
    {
      ...original.relationships[0],
      name: "Ren's Shadow",
      role: "inner adviser",
      trust: 100,
    },
  ];
  assert.equal(isObserverSnapshot(invented), false);
  const wrongRole = structuredClone(original);
  wrongRole.relationships[0].role = "S-rank guild master";
  assert.equal(isObserverSnapshot(wrongRole), false);
});
test("rejects integers outside exact browser precision", async () => {
  const original = await readFile(
    new URL("public/data/observer-snapshot.json", root),
    "utf8",
  ).then(JSON.parse);
  assert.equal(isObserverSnapshot(original), true);
  for (const mutate of [
    (snapshot) => (snapshot.seed = Number.MAX_SAFE_INTEGER + 1),
    (snapshot) => (snapshot.clock.day = Number.MAX_SAFE_INTEGER + 1),
    (snapshot) =>
      (snapshot.protagonist.resources.money = Number.MAX_SAFE_INTEGER + 1),
    (snapshot) =>
      (snapshot.protagonist.progression.rank_points =
        Number.MAX_SAFE_INTEGER + 1),
  ]) {
    const unsafe = structuredClone(original);
    mutate(unsafe);
    assert.equal(isObserverSnapshot(unsafe), false);
  }
  const maximum = structuredClone(original);
  maximum.protagonist.resources.money = Number.MAX_SAFE_INTEGER;
  assert.equal(isObserverSnapshot(maximum), true);
});
test("requires authored protagonist identity ability and mood", async () => {
  const original = await readFile(
    new URL("public/data/observer-snapshot.json", root),
    "utf8",
  ).then(JSON.parse);
  for (const ability of [
    "None",
    "Threat Sense",
    "Threat Sense / Echo Fragment",
  ]) {
    const valid = structuredClone(original);
    setProgression(
      valid,
      ability === "None" ? "Unranked" : "E",
      ability,
      ability === "None" ? 0 : 30,
    );
    assert.equal(isObserverSnapshot(valid), true);
  }
  for (const mood of [
    "Uneasy",
    "Anxious",
    "Steady",
    "Hopeful",
    "Exhausted",
    "Overwhelmed",
  ]) {
    const valid = structuredClone(original);
    valid.protagonist.mood = mood;
    assert.equal(isObserverSnapshot(valid), true);
  }
  for (const [rank, ability] of [
    ["Unranked", "Threat Sense"],
    ["F", "None"],
    ["C", "None"],
  ]) {
    const impossible = structuredClone(original);
    impossible.protagonist.hunter_rank = rank;
    impossible.protagonist.ability = ability;
    assert.equal(isObserverSnapshot(impossible), false);
  }
  for (const [field, value] of [
    ["name", "Other Hunter"],
    ["ability", "Omniscience"],
    ["mood", "Invincible"],
  ]) {
    const invented = structuredClone(original);
    invented.protagonist[field] = value;
    assert.equal(isObserverSnapshot(invented), false);
  }
});
test("rejects shadow fields in rendered records", async () => {
  const original = await readFile(
    new URL("public/data/observer-snapshot.json", root),
    "utf8",
  ).then(JSON.parse);
  for (const select of [
    (snapshot) => snapshot.identity,
    (snapshot) => snapshot.clock,
    (snapshot) => snapshot.environment,
    (snapshot) => snapshot.activity.recent_events[0],
    (snapshot) => snapshot.relationships[0],
    (snapshot) => snapshot.story.next,
  ]) {
    const shadowed = structuredClone(original);
    select(shadowed).shadow = "invented";
    assert.equal(isObserverSnapshot(shadowed), false);
  }
});
test("requires the exact authored presentation contract", async () => {
  const [contract, snapshot] = await Promise.all([
    readFile(new URL("public/data/observer-contract.json", root), "utf8").then(
      JSON.parse,
    ),
    readFile(new URL("public/data/observer-snapshot.json", root), "utf8").then(
      JSON.parse,
    ),
  ]);
  assert.equal(
    (await verifyArtifacts(contract, snapshot)).contract
      .comparison_schema_version,
    9,
  );
  for (const mutate of [
    (value) => (value.comparison_schema_version = 8),
    (value) => (value.animation_cues = [...value.animation_cues, "invented"]),
    (value) => (value.update_modes = ["replace"]),
    (value) => (value.recent_activity_relations = ["append", "unchanged"]),
    (value) => (value.shadow = "invented"),
  ]) {
    const changed = structuredClone(contract);
    mutate(changed);
    const payload = { ...changed };
    delete payload.contract_sha256;
    changed.contract_sha256 = createHash("sha256")
      .update(canonical(payload))
      .digest("hex");
    await assert.rejects(
      verifyArtifacts(changed, snapshot),
      /malformed observer artifacts/,
    );
  }
});
test("requires the complete snapshot envelope", async () => {
  const original = await readFile(
    new URL("public/data/observer-snapshot.json", root),
    "utf8",
  ).then(JSON.parse);
  assert.equal(isObserverSnapshot(original), true);
  for (const mutate of [
    (snapshot) => (snapshot.shadow = {}),
    (snapshot) => delete snapshot.conversations,
    (snapshot) => delete snapshot.economy,
    (snapshot) => (snapshot.activity.shadow = true),
    (snapshot) => delete snapshot.activity.key_memories,
    (snapshot) => (snapshot.portals.shadow = true),
    (snapshot) => delete snapshot.portals.investigations,
    (snapshot) => (snapshot.protagonist.shadow = true),
    (snapshot) => delete snapshot.protagonist.equipment,
    (snapshot) => (snapshot.protagonist.resources.shadow = 1),
    (snapshot) => (snapshot.protagonist.progression.shadow = 1),
    (snapshot) => (snapshot.story.shadow = true),
    (snapshot) => delete snapshot.story.completed,
  ]) {
    const malformed = structuredClone(original);
    mutate(malformed);
    assert.equal(isObserverSnapshot(malformed), false);
  }
});
test("requires authored economy values and bounds", async () => {
  const original = await readFile(
    new URL("public/data/observer-snapshot.json", root),
    "utf8",
  ).then(JSON.parse);
  for (const meal_cost of [500, 600, 700, 800]) {
    const valid = structuredClone(original);
    valid.economy.meal_cost = meal_cost;
    assert.equal(isObserverSnapshot(valid), true);
  }
  for (const wage_modifier of [85, 95, 100, 105, 115]) {
    const valid = structuredClone(original);
    valid.economy.wage_modifier = wage_modifier;
    assert.equal(isObserverSnapshot(valid), true);
  }
  for (const mutate of [
    (snapshot) => (snapshot.economy.meal_cost = 650),
    (snapshot) => (snapshot.economy.wage_modifier = 101),
    (snapshot) => (snapshot.economy.rent_due_day = 0),
    (snapshot) => (snapshot.economy.rent_arrears = -1),
    (snapshot) => (snapshot.economy.rent_cost = 0.5),
    (snapshot) => (snapshot.economy.shop_visits = Number.MAX_SAFE_INTEGER + 1),
  ]) {
    const invalid = structuredClone(original);
    mutate(invalid);
    assert.equal(isObserverSnapshot(invalid), false);
  }
});
test("requires the authored rent ledger", async () => {
  const original = await readFile(
    new URL("public/data/observer-snapshot.json", root),
    "utf8",
  ).then(JSON.parse);
  for (const [payments, arrears] of [
    [0, 0],
    [0, 8000],
    [1, 0],
  ]) {
    const valid = structuredClone(original);
    valid.economy.rent_payments = payments;
    valid.economy.rent_arrears = arrears;
    valid.protagonist.current_goal = currentGoalFor(valid);
    assert.equal(isObserverSnapshot(valid), true);
  }
  for (const mutate of [
    (snapshot) => (snapshot.economy.rent_due_day = 7),
    (snapshot) => (snapshot.economy.rent_cost = 7999),
    (snapshot) => (snapshot.economy.rent_arrears = 8001),
    (snapshot) => (snapshot.economy.rent_payments = 2),
    (snapshot) => {
      snapshot.economy.rent_payments = 1;
      snapshot.economy.rent_arrears = 1;
    },
  ]) {
    const invalid = structuredClone(original);
    mutate(invalid);
    assert.equal(isObserverSnapshot(invalid), false);
  }
});
test("rejects rent activity before the deadline is processed", async () => {
  const original = await readFile(
    new URL("public/data/observer-snapshot.json", root),
    "utf8",
  ).then(JSON.parse);
  const at = (day, slot) => {
    const snapshot = structuredClone(original);
    snapshot.clock = { day, slot };
    snapshot.activity.recent_events = [];
    snapshot.activity.key_memories = [];
    snapshot.story.next.days_remaining = 183 - day;
    syncRegistration(snapshot);
    return snapshot;
  };
  for (const [day, slot] of [
    [7, "Late Night"],
    [8, "Morning"],
  ]) {
    const invalid = at(day, slot);
    invalid.economy.rent_payments = 1;
    assert.equal(isObserverSnapshot(invalid), false);
  }
  const valid = at(8, "Afternoon");
  valid.economy.rent_payments = 1;
  assert.equal(isObserverSnapshot(valid), true);
});
test("requires canonical progression bounds and mission counters", async () => {
  const original = await readFile(
    new URL("public/data/observer-snapshot.json", root),
    "utf8",
  ).then(JSON.parse);
  for (const value of [1, 100]) {
    const valid = structuredClone(original);
    valid.protagonist.progression.ability_mastery = value;
    valid.protagonist.progression.combat_readiness = value;
    assert.equal(isObserverSnapshot(valid), true);
  }
  const zeroReadiness = structuredClone(original);
  zeroReadiness.protagonist.progression.combat_readiness = 0;
  assert.equal(isObserverSnapshot(zeroReadiness), true);
  const longTerm = structuredClone(original);
  setProgression(longTerm, "C", "Threat Sense", Number.MAX_SAFE_INTEGER);
  longTerm.protagonist.progression.fitness = Number.MAX_SAFE_INTEGER;
  longTerm.protagonist.progression.knowledge = Number.MAX_SAFE_INTEGER;
  assert.equal(isObserverSnapshot(longTerm), true);
  for (const mutate of [
    (snapshot) => (snapshot.protagonist.progression.ability_mastery = 101),
    (snapshot) => (snapshot.protagonist.progression.ability_mastery = -1),
    (snapshot) => (snapshot.protagonist.progression.missions_attempted = -1),
    (snapshot) =>
      (snapshot.protagonist.progression.missions_completed =
        snapshot.protagonist.progression.missions_attempted + 1),
  ]) {
    const invalid = structuredClone(original);
    mutate(invalid);
    assert.equal(isObserverSnapshot(invalid), false);
  }
});
test("requires canonical inventory and equipped item kinds", async () => {
  const original = await readFile(
    new URL("public/data/observer-snapshot.json", root),
    "utf8",
  ).then(JSON.parse);
  for (const [weapon, armor] of [
    [null, null],
    ["Field Knife", null],
    [null, "Padded Jacket"],
    ["Field Knife", "Padded Jacket"],
  ]) {
    const valid = structuredClone(original);
    valid.protagonist.equipment.weapon = weapon;
    valid.protagonist.equipment.armor = armor;
    assert.equal(isObserverSnapshot(valid), true);
  }
  const upgraded = structuredClone(original);
  setProgression(upgraded, "E", "Threat Sense", 30);
  upgraded.protagonist.equipment = {
    armor: "Gateweave Vest",
    inventory: { "Gateweave Vest": 1, "Reinforced Machete": 1 },
    weapon: "Reinforced Machete",
  };
  assert.equal(isObserverSnapshot(upgraded), true);
  const future = structuredClone(original);
  future.protagonist.equipment.inventory = {
    "Alpha Relic": 2,
    "Energy Drink": 1,
    "Zeta Charm": 3,
  };
  assert.equal(isObserverSnapshot(future), true);
  for (const mutate of [
    (snapshot) => (snapshot.protagonist.equipment.weapon = "Padded Jacket"),
    (snapshot) => (snapshot.protagonist.equipment.weapon = "Gateweave Vest"),
    (snapshot) => (snapshot.protagonist.equipment.armor = "Field Knife"),
    (snapshot) => (snapshot.protagonist.equipment.armor = "Reinforced Machete"),
    (snapshot) =>
      (snapshot.protagonist.equipment.inventory = { "Field Knife": 0 }),
    (snapshot) =>
      (snapshot.protagonist.equipment.inventory = { Zeta: 1, Alpha: 2 }),
    (snapshot) =>
      (snapshot.protagonist.equipment.inventory = { "Field Knife": 1.5 }),
    (snapshot) =>
      (snapshot.protagonist.equipment.inventory = {
        "Field Knife": Number.MAX_SAFE_INTEGER + 1,
      }),
  ]) {
    const invalid = structuredClone(original);
    mutate(invalid);
    assert.equal(isObserverSnapshot(invalid), false);
  }
});
test("requires canonical relationship metric bounds", async () => {
  const original = await readFile(
    new URL("public/data/observer-snapshot.json", root),
    "utf8",
  ).then(JSON.parse);
  for (const [field, values] of [
    ["affection", [-100, 100]],
    ["trust", [-100, 100]],
    ["familiarity", [0, 100]],
    ["loyalty", [0, 100]],
    ["tension", [0, 100]],
  ]) {
    for (const value of values) {
      const valid = structuredClone(original);
      valid.relationships[0][field] = value;
      assert.equal(isObserverSnapshot(valid), true);
    }
  }
  for (const [field, value] of [
    ["affection", -101],
    ["trust", 101],
    ["familiarity", -1],
    ["loyalty", 101],
    ["tension", 0.5],
  ]) {
    const invalid = structuredClone(original);
    invalid.relationships[0][field] = value;
    assert.equal(isObserverSnapshot(invalid), false);
  }
});
test("requires canonical portal investigation semantics", async () => {
  const original = await readFile(
    new URL("public/data/observer-snapshot.json", root),
    "utf8",
  ).then(JSON.parse);
  const investigation = {
    cooperating_npc: "Mei Kuroda",
    joint_missions: 0,
    portal_name: "Ashen Shopping Arcade",
    preparation_bonus: 0,
    preparation_strategy: "Map the stable route",
    progress: 0,
    risk: 100,
  };
  const valid = structuredClone(original);
  valid.portals.discovered = ["Ashen Shopping Arcade"];
  valid.portals.investigations = [investigation];
  valid.portals.active_plan = "Ashen Shopping Arcade";
  assert.equal(isObserverSnapshot(valid), true);
  for (const mutate of [
    (snapshot) => (snapshot.portals.investigations[0].progress = 101),
    (snapshot) => (snapshot.portals.investigations[0].risk = -1),
    (snapshot) => (snapshot.portals.investigations[0].preparation_bonus = -1),
    (snapshot) => (snapshot.portals.investigations[0].joint_missions = 0.5),
    (snapshot) =>
      (snapshot.portals.investigations[0].cooperating_npc = "Unknown Hunter"),
    (snapshot) =>
      (snapshot.portals.investigations[0].preparation_strategy = ""),
    (snapshot) => (snapshot.portals.active_plan = "Frostbound Platform"),
  ]) {
    const invalid = structuredClone(valid);
    mutate(invalid);
    assert.equal(isObserverSnapshot(invalid), false);
  }
  const duplicate = structuredClone(valid);
  duplicate.portals.investigations.push(structuredClone(investigation));
  assert.equal(isObserverSnapshot(duplicate), false);
});
test("requires canonical key memory semantics", async () => {
  const original = await readFile(
    new URL("public/data/observer-snapshot.json", root),
    "utf8",
  ).then(JSON.parse);
  const valid = structuredClone(original);
  valid.activity.key_memories = [
    { day: valid.clock.day, importance: 10, summary: "Highest priority" },
    {
      day: 3,
      importance: 10,
      summary: "Awakening assessment: Awakened at Rank F with Threat Sense.",
    },
    {
      day: 4,
      importance: 8,
      summary:
        "Guild registration: Aiko Sato issued an F-rank license; travel and filing cost ¥0.",
    },
    { day: 1, importance: 1, summary: "Earliest memory" },
  ];
  assert.equal(isObserverSnapshot(valid), true);
  for (const mutate of [
    (snapshot) => (snapshot.activity.key_memories[0].day = 0),
    (snapshot) =>
      (snapshot.activity.key_memories[0].day = snapshot.clock.day + 1),
    (snapshot) => (snapshot.activity.key_memories[0].importance = 11),
    (snapshot) => (snapshot.activity.key_memories[0].importance = 0.5),
    (snapshot) => (snapshot.activity.key_memories[0].summary = ""),
    (snapshot) => snapshot.activity.key_memories.reverse(),
    (snapshot) =>
      snapshot.activity.key_memories.push(
        ...Array.from({ length: 4 }, (_, index) => ({
          day: 1,
          importance: 1,
          summary: `Extra ${index}`,
        })),
      ),
  ]) {
    const invalid = structuredClone(valid);
    mutate(invalid);
    assert.equal(isObserverSnapshot(invalid), false);
  }
});
test("requires canonical completed story records", async () => {
  const original = await readFile(
    new URL("public/data/observer-snapshot.json", root),
    "utf8",
  ).then(JSON.parse);
  const valid = structuredClone(original);
  valid.clock.day = 183;
  syncEnvironment(valid);
  valid.story.completed = completedStory(1);
  valid.story.completed_count = 1;
  valid.story.next = {
    day: 365,
    days_remaining: 182,
    key: "arc_tokyo_fracture",
    title: "The Tokyo Fracture",
  };
  assert.equal(isObserverSnapshot(valid), true);
  for (const mutate of [
    (snapshot) => (snapshot.story.completed_count = 0),
    (snapshot) => (snapshot.story.completed[0].day = 182),
    (snapshot) => (snapshot.story.completed[0].key = "arc_invented"),
    (snapshot) => (snapshot.story.completed[0].title = "Invented Arc"),
    (snapshot) => (snapshot.story.completed[0].tier = "victorious"),
    (snapshot) => (snapshot.story.completed[0].outcome = ""),
    (snapshot) => (snapshot.story.completed[0].focus_npcs = ["Unknown Hunter"]),
    (snapshot) => (snapshot.story.completed[0].shadow = true),
  ]) {
    const invalid = structuredClone(valid);
    mutate(invalid);
    assert.equal(isObserverSnapshot(invalid), false);
  }
});
test("requires authored completed story content", async () => {
  const original = await readFile(
    new URL("public/data/observer-snapshot.json", root),
    "utf8",
  ).then(JSON.parse);
  const valid = structuredClone(original);
  valid.clock.day = 183;
  syncEnvironment(valid);
  valid.story.completed = completedStory(1);
  valid.story.completed_count = 1;
  valid.story.next = {
    day: 365,
    days_remaining: 182,
    key: "arc_tokyo_fracture",
    title: "The Tokyo Fracture",
  };
  assert.equal(isObserverSnapshot(valid), true);
  for (const mutate of [
    (entry) => (entry.outcome = "A plausible but unauthored outcome."),
    (entry) => (entry.scene = "An invented encounter."),
    (entry) => (entry.portal_consequence = "An invented consequence."),
    (entry) => (entry.international_link = "An invented link."),
  ]) {
    const invented = structuredClone(valid);
    mutate(invented.story.completed[0]);
    assert.equal(isObserverSnapshot(invented), false);
  }
  const reordered = structuredClone(valid);
  reordered.story.completed[0].focus_npcs.reverse();
  assert.equal(isObserverSnapshot(reordered), false);
});
test("accepts only string snapshot path provenance", async () => {
  const [contract, original] = await Promise.all([
    readFile(new URL("public/data/observer-contract.json", root), "utf8").then(
      JSON.parse,
    ),
    readFile(new URL("public/data/observer-snapshot.json", root), "utf8").then(
      JSON.parse,
    ),
  ]);
  const external = { ...original, path: "exports/day-11.json" };
  assert.equal(isObserverSnapshot(external), true);
  await assert.doesNotReject(() => verifyArtifacts(contract, external));
  for (const path of [null, 42, {}, []]) {
    const invalid = { ...original, path };
    assert.equal(isObserverSnapshot(invalid), false);
  }
  const shadow = { ...external, source: "invented" };
  assert.equal(isObserverSnapshot(shadow), false);
});
test("accepts signed exact simulation seeds", async () => {
  const original = await readFile(
    new URL("public/data/observer-snapshot.json", root),
    "utf8",
  ).then(JSON.parse);
  for (const seed of [
    Number.MIN_SAFE_INTEGER,
    -1,
    0,
    Number.MAX_SAFE_INTEGER,
  ]) {
    const valid = structuredClone(original);
    valid.seed = seed;
    assert.equal(isObserverSnapshot(valid), true);
  }
  for (const seed of [
    true,
    0.5,
    Number.MIN_SAFE_INTEGER - 1,
    Number.MAX_SAFE_INTEGER + 1,
  ]) {
    const invalid = structuredClone(original);
    invalid.seed = seed;
    assert.equal(isObserverSnapshot(invalid), false);
  }
});
test("requires every portal investigation to be discovered", async () => {
  const original = await readFile(
    new URL("public/data/observer-snapshot.json", root),
    "utf8",
  ).then(JSON.parse);
  assert.ok(original.portals.investigations.length > 0);
  const invalid = structuredClone(original);
  const investigated = invalid.portals.investigations[0].portal_name;
  invalid.portals.discovered = invalid.portals.discovered.filter(
    (name) => name !== investigated,
  );
  assert.equal(isObserverSnapshot(invalid), false);
});
test("requires matching hunter rank and ability lifecycle", async () => {
  const original = await readFile(
    new URL("public/data/observer-snapshot.json", root),
    "utf8",
  ).then(JSON.parse);
  for (const [hunter_rank, ability, rank_points] of [
    ["Unranked", "None", 0],
    ["F", "Threat Sense", 0],
    ["C", "Threat Sense / Echo Fragment", 90],
  ]) {
    const valid = structuredClone(original);
    setProgression(valid, hunter_rank, ability, rank_points);
    assert.equal(isObserverSnapshot(valid), true);
  }
  for (const [hunter_rank, ability] of [
    ["Unranked", "Threat Sense"],
    ["F", "None"],
    ["C", "Unknown Ability"],
  ]) {
    const invalid = structuredClone(original);
    invalid.protagonist.hunter_rank = hunter_rank;
    invalid.protagonist.ability = ability;
    assert.equal(isObserverSnapshot(invalid), false);
  }
});
test("requires the authored Awakening chronology", async () => {
  const original = await readFile(
    new URL("public/data/observer-snapshot.json", root),
    "utf8",
  ).then(JSON.parse);
  const at = (day, slot, rank, ability) => {
    const snapshot = structuredClone(original);
    setProgression(snapshot, rank, ability, 0);
    snapshot.clock = { day, slot };
    snapshot.activity.recent_events = [];
    snapshot.activity.key_memories = [];
    snapshot.story.next.days_remaining = 183 - day;
    snapshot.economy.rent_payments = 0;
    snapshot.economy.rent_arrears = 0;
    snapshot.economy.shop_visits = 0;
    snapshot.protagonist.equipment = {
      armor: null,
      inventory: {},
      weapon: null,
    };
    snapshot.portals = {
      active_plan: null,
      discovered: [],
      investigations: [],
    };
    snapshot.protagonist.current_goal = currentGoalFor(snapshot);
    syncRegistration(snapshot);
    return snapshot;
  };
  for (const [day, slot, rank, ability] of [
    [1, "Morning", "Unranked", "None"],
    [3, "Afternoon", "Unranked", "None"],
    [3, "Evening", "F", "Threat Sense"],
    [4, "Morning", "F", "Threat Sense"],
  ]) {
    assert.equal(isObserverSnapshot(at(day, slot, rank, ability)), true);
  }
  for (const [day, slot, rank, ability] of [
    [1, "Morning", "F", "Threat Sense"],
    [3, "Afternoon", "F", "Threat Sense"],
    [3, "Evening", "Unranked", "None"],
    [4, "Morning", "Unranked", "None"],
  ]) {
    assert.equal(isObserverSnapshot(at(day, slot, rank, ability)), false);
  }
});
test("requires the lifecycle current goal", async () => {
  const original = await readFile(
    new URL("public/data/observer-snapshot.json", root),
    "utf8",
  ).then(JSON.parse);
  const at = (day, slot, rank, ability, arrears = 0) => {
    const snapshot = structuredClone(original);
    snapshot.clock = { day, slot };
    snapshot.activity.recent_events = [];
    snapshot.activity.key_memories = [];
    snapshot.story.next.days_remaining = 183 - day;
    snapshot.economy.rent_payments = 0;
    snapshot.economy.rent_arrears = arrears;
    setProgression(snapshot, rank, ability, rank === "E" ? 30 : 0);
    snapshot.protagonist.current_goal = currentGoalFor(snapshot);
    syncRegistration(snapshot);
    return snapshot;
  };
  for (const args of [
    [1, "Morning", "Unranked", "None"],
    [3, "Evening", "F", "Threat Sense"],
    [4, "Afternoon", "F", "Threat Sense"],
    [8, "Afternoon", "F", "Threat Sense", 1234],
    [11, "Morning", "E", "Threat Sense"],
  ]) {
    assert.equal(isObserverSnapshot(at(...args)), true);
  }
  const invalid = at(4, "Afternoon", "F", "Threat Sense");
  invalid.protagonist.current_goal = "Invented objective";
  assert.equal(isObserverSnapshot(invalid), false);
});
test("requires Guild registration evidence", async () => {
  const original = await readFile(
    new URL("public/data/observer-snapshot.json", root),
    "utf8",
  ).then(JSON.parse);
  const at = (day, slot) => {
    const snapshot = structuredClone(original);
    snapshot.clock = { day, slot };
    snapshot.activity.recent_events = [];
    snapshot.activity.key_memories = [];
    snapshot.story.next.days_remaining = 183 - day;
    snapshot.economy.rent_payments = 0;
    snapshot.economy.rent_arrears = 0;
    setProgression(snapshot, "F", "Threat Sense", 0);
    snapshot.protagonist.current_goal = currentGoalFor(snapshot);
    return snapshot;
  };
  for (const [day, slot, present] of [
    [4, "Morning", false],
    [4, "Afternoon", true],
  ]) {
    const valid = at(day, slot);
    valid.relationships = present ? [aikoRelationship] : [];
    assert.equal(isObserverSnapshot(valid), true);
    const invalid = structuredClone(valid);
    invalid.relationships = present ? [] : [aikoRelationship];
    assert.equal(isObserverSnapshot(invalid), false);
  }
});
test("requires authored relationship introduction chronology", async () => {
  const original = await readFile(
    new URL("public/data/observer-snapshot.json", root),
    "utf8",
  ).then(JSON.parse);
  for (const [name, beforeClock, afterClock] of [
    ["Daichi Mori", [5, "Morning"], [5, "Afternoon"]],
    ["Mei Kuroda", [6, "Afternoon"], [6, "Evening"]],
    ["Haruto Ishikawa", [9, "Evening"], [9, "Late Night"]],
  ]) {
    for (const [clock, present] of [
      [beforeClock, false],
      [afterClock, true],
    ]) {
      const snapshot = structuredClone(original);
      snapshot.clock = { day: clock[0], slot: clock[1] };
      snapshot.activity.recent_events = [];
      snapshot.activity.key_memories = [];
      snapshot.story.next.days_remaining = 183 - clock[0];
      snapshot.economy.rent_payments = 0;
      snapshot.economy.rent_arrears = 0;
      snapshot.protagonist.current_goal = currentGoalFor(snapshot);
      syncRegistration(snapshot);
      assert.equal(
        snapshot.relationships.some((item) => item.name === name),
        present,
      );
      assert.equal(isObserverSnapshot(snapshot), true);
      if (present)
        snapshot.relationships = snapshot.relationships.filter(
          (item) => item.name !== name,
        );
      else {
        snapshot.relationships.push(
          original.relationships.find((item) => item.name === name),
        );
        snapshot.relationships.sort((a, b) => a.name.localeCompare(b.name));
      }
      assert.equal(isObserverSnapshot(snapshot), false);
    }
  }
});
test("requires authored relationship introduction evidence", async () => {
  const original = await readFile(
    new URL("public/data/observer-snapshot.json", root),
    "utf8",
  ).then(JSON.parse);
  for (const [name, day, slot] of [
    ["Aiko Sato", 4, "Afternoon"],
    ["Daichi Mori", 5, "Afternoon"],
    ["Mei Kuroda", 6, "Evening"],
    ["Haruto Ishikawa", 9, "Late Night"],
  ]) {
    const snapshot = structuredClone(original);
    snapshot.clock = { day, slot };
    snapshot.activity.recent_events = [];
    snapshot.activity.key_memories = [];
    snapshot.story.next.days_remaining = 183 - day;
    snapshot.economy.rent_payments = 0;
    snapshot.economy.rent_arrears = 0;
    setProgression(snapshot, "F", "Threat Sense", 0);
    snapshot.protagonist.current_goal = currentGoalFor(snapshot);
    syncRegistration(snapshot);
    assert.equal(isObserverSnapshot(snapshot), true);
    snapshot.relationships.find((item) => item.name === name).trust += 1;
    assert.equal(isObserverSnapshot(snapshot), false);
  }
});
test("requires authored fixed-event locations", async () => {
  const original = await readFile(
    new URL("public/data/observer-snapshot.json", root),
    "utf8",
  ).then(JSON.parse);
  for (const [day, slot, location] of [
    [3, "Evening", "Tokyo Awakening Bureau"],
    [4, "Afternoon", "Tokyo Hunter Guild"],
  ]) {
    const snapshot = structuredClone(original);
    snapshot.clock = { day, slot };
    snapshot.activity.recent_events = [];
    snapshot.activity.key_memories = [];
    snapshot.story.next.days_remaining = 183 - day;
    snapshot.economy.rent_payments = 0;
    snapshot.economy.rent_arrears = 0;
    setProgression(snapshot, "F", "Threat Sense", 0);
    snapshot.protagonist.current_goal = currentGoalFor(snapshot);
    syncRegistration(snapshot);
    assert.equal(snapshot.protagonist.location, location);
    assert.equal(isObserverSnapshot(snapshot), true, `day ${day}`);
    snapshot.protagonist.location = "Adachi Apartment";
    assert.equal(isObserverSnapshot(snapshot), false);
  }
});
test("requires authored fixed-event state evidence", async () => {
  const original = await readFile(
    new URL("public/data/observer-snapshot.json", root),
    "utf8",
  ).then(JSON.parse);
  for (const [day, slot, mutate] of [
    [
      3,
      "Evening",
      (snapshot) => (snapshot.protagonist.progression.ability_mastery = 2),
    ],
    [4, "Afternoon", (snapshot) => (snapshot.environment.gate_alert_level = 1)],
  ]) {
    const snapshot = structuredClone(original);
    snapshot.clock = { day, slot };
    snapshot.activity.recent_events = [];
    snapshot.activity.key_memories = [];
    snapshot.story.next.days_remaining = 183 - day;
    snapshot.economy.rent_payments = 0;
    snapshot.economy.rent_arrears = 0;
    setProgression(snapshot, "F", "Threat Sense", 0);
    snapshot.protagonist.current_goal = currentGoalFor(snapshot);
    syncRegistration(snapshot);
    assert.equal(isObserverSnapshot(snapshot), true);
    mutate(snapshot);
    assert.equal(isObserverSnapshot(snapshot), false);
  }
});
test("prevents ability mastery before Awakening", async () => {
  const original = await readFile(
    new URL("public/data/observer-snapshot.json", root),
    "utf8",
  ).then(JSON.parse);
  for (const [day, slot] of [
    [1, "Morning"],
    [3, "Afternoon"],
  ]) {
    const snapshot = structuredClone(original);
    snapshot.clock = { day, slot };
    snapshot.activity.recent_events = [];
    snapshot.activity.key_memories = [];
    snapshot.story.next.days_remaining = 183 - day;
    snapshot.economy.rent_payments = 0;
    snapshot.economy.rent_arrears = 0;
    setProgression(snapshot, "Unranked", "None", 0);
    snapshot.protagonist.current_goal = currentGoalFor(snapshot);
    syncRegistration(snapshot);
    assert.equal(isObserverSnapshot(snapshot), true);
    snapshot.protagonist.progression.ability_mastery = 1;
    assert.equal(isObserverSnapshot(snapshot), false);
  }
});
test("prevents awakened mastery from reverting to zero", async () => {
  const original = await readFile(
    new URL("public/data/observer-snapshot.json", root),
    "utf8",
  ).then(JSON.parse);
  for (const [day, slot] of [
    [3, "Late Night"],
    [4, "Afternoon"],
    [11, "Morning"],
  ]) {
    const snapshot = structuredClone(original);
    snapshot.clock = { day, slot };
    snapshot.activity.recent_events = [];
    snapshot.activity.key_memories = [];
    snapshot.story.next.days_remaining = 183 - day;
    snapshot.economy.rent_payments =
      day < 8 ? 0 : snapshot.economy.rent_payments;
    snapshot.economy.rent_arrears = 0;
    setProgression(snapshot, "F", "Threat Sense", 0);
    snapshot.protagonist.current_goal = currentGoalFor(snapshot);
    syncRegistration(snapshot);
    assert.equal(isObserverSnapshot(snapshot), true);
    snapshot.protagonist.progression.ability_mastery = 0;
    assert.equal(isObserverSnapshot(snapshot), false);
  }
});
test("requires an empty fixed-event hunter record", async () => {
  const original = await readFile(
    new URL("public/data/observer-snapshot.json", root),
    "utf8",
  ).then(JSON.parse);
  for (const [day, slot] of [
    [3, "Evening"],
    [4, "Afternoon"],
  ]) {
    const snapshot = structuredClone(original);
    snapshot.clock = { day, slot };
    snapshot.activity.recent_events = [];
    snapshot.activity.key_memories = [];
    snapshot.story.next.days_remaining = 183 - day;
    snapshot.economy.rent_payments = 0;
    snapshot.economy.rent_arrears = 0;
    setProgression(snapshot, "F", "Threat Sense", 0);
    snapshot.protagonist.current_goal = currentGoalFor(snapshot);
    syncRegistration(snapshot);
    assert.equal(isObserverSnapshot(snapshot), true);
    snapshot.protagonist.progression.rank_points = 10;
    snapshot.protagonist.progression.missions_attempted = 1;
    snapshot.protagonist.progression.missions_completed = 1;
    assert.equal(isObserverSnapshot(snapshot), false);
  }
});
test("prevents hunter mission records before Guild registration", async () => {
  const original = await readFile(
    new URL("public/data/observer-snapshot.json", root),
    "utf8",
  ).then(JSON.parse);
  for (const [day, slot] of [
    [3, "Afternoon"],
    [3, "Evening"],
    [4, "Afternoon"],
  ]) {
    const snapshot = structuredClone(original);
    snapshot.clock = { day, slot };
    snapshot.activity.recent_events = [];
    snapshot.activity.key_memories = [];
    snapshot.story.next.days_remaining = 183 - day;
    snapshot.economy.rent_payments = 0;
    snapshot.economy.rent_arrears = 0;
    setProgression(
      snapshot,
      day === 3 && slot === "Afternoon" ? "Unranked" : "F",
      day === 3 && slot === "Afternoon" ? "None" : "Threat Sense",
      0,
    );
    snapshot.protagonist.current_goal = currentGoalFor(snapshot);
    syncRegistration(snapshot);
    assert.equal(isObserverSnapshot(snapshot), true);
    snapshot.protagonist.progression.missions_attempted = 1;
    assert.equal(isObserverSnapshot(snapshot), false);
  }
});
test("requires an empty fixed-event equipment record", async () => {
  const original = await readFile(
    new URL("public/data/observer-snapshot.json", root),
    "utf8",
  ).then(JSON.parse);
  for (const [day, slot] of [
    [3, "Evening"],
    [4, "Afternoon"],
  ]) {
    const snapshot = structuredClone(original);
    snapshot.clock = { day, slot };
    snapshot.activity.recent_events = [];
    snapshot.activity.key_memories = [];
    snapshot.story.next.days_remaining = 183 - day;
    snapshot.economy.rent_payments = 0;
    snapshot.economy.rent_arrears = 0;
    setProgression(snapshot, "F", "Threat Sense", 0);
    snapshot.protagonist.current_goal = currentGoalFor(snapshot);
    syncRegistration(snapshot);
    assert.equal(isObserverSnapshot(snapshot), true);
    snapshot.protagonist.equipment = {
      armor: null,
      inventory: { "Field Knife": 1 },
      weapon: "Field Knife",
    };
    assert.equal(isObserverSnapshot(snapshot), false);
  }
});
test("requires an empty fixed-event portal ledger", async () => {
  const original = await readFile(
    new URL("public/data/observer-snapshot.json", root),
    "utf8",
  ).then(JSON.parse);
  for (const [day, slot] of [
    [3, "Evening"],
    [4, "Afternoon"],
  ]) {
    const snapshot = structuredClone(original);
    snapshot.clock = { day, slot };
    snapshot.activity.recent_events = [];
    snapshot.activity.key_memories = [];
    snapshot.story.next.days_remaining = 183 - day;
    snapshot.economy.rent_payments = 0;
    snapshot.economy.rent_arrears = 0;
    setProgression(snapshot, "F", "Threat Sense", 0);
    snapshot.protagonist.current_goal = currentGoalFor(snapshot);
    syncRegistration(snapshot);
    assert.equal(isObserverSnapshot(snapshot), true);
    snapshot.portals.discovered = ["Ashen Shopping Arcade"];
    assert.equal(isObserverSnapshot(snapshot), false);
  }
});
test("requires authored fixed-event activity evidence", async () => {
  const original = await readFile(
    new URL("public/data/observer-snapshot.json", root),
    "utf8",
  ).then(JSON.parse);
  for (const [day, slot] of [
    [3, "Evening"],
    [4, "Afternoon"],
  ]) {
    const snapshot = structuredClone(original);
    snapshot.clock = { day, slot };
    snapshot.activity.recent_events = [];
    snapshot.activity.key_memories = [];
    snapshot.story.next.days_remaining = 183 - day;
    snapshot.economy.rent_payments = 0;
    snapshot.economy.rent_arrears = 0;
    setProgression(snapshot, "F", "Threat Sense", 0);
    snapshot.protagonist.current_goal = currentGoalFor(snapshot);
    syncRegistration(snapshot);
    assert.equal(isObserverSnapshot(snapshot), true);
    snapshot.activity.recent_events.at(-1).action = "Invented event";
    assert.equal(isObserverSnapshot(snapshot), false);
  }
});
test("requires authored fixed-event memory evidence", async () => {
  const original = await readFile(
    new URL("public/data/observer-snapshot.json", root),
    "utf8",
  ).then(JSON.parse);
  for (const [day, slot, memoryDay] of [
    [3, "Evening", 3],
    [4, "Afternoon", 4],
  ]) {
    const snapshot = structuredClone(original);
    snapshot.clock = { day, slot };
    snapshot.activity.recent_events = [];
    snapshot.activity.key_memories = [];
    snapshot.story.next.days_remaining = 183 - day;
    snapshot.economy.rent_payments = 0;
    snapshot.economy.rent_arrears = 0;
    setProgression(snapshot, "F", "Threat Sense", 0);
    snapshot.protagonist.current_goal = currentGoalFor(snapshot);
    syncRegistration(snapshot);
    assert.equal(isObserverSnapshot(snapshot), true);
    snapshot.activity.key_memories = snapshot.activity.key_memories.filter(
      (memory) => memory.day !== memoryDay,
    );
    assert.equal(isObserverSnapshot(snapshot), false);
  }
});
test("requires fixed-event memories across their lifecycle", async () => {
  const original = await readFile(
    new URL("public/data/observer-snapshot.json", root),
    "utf8",
  ).then(JSON.parse);
  for (const [day, slot, mutate] of [
    [
      3,
      "Afternoon",
      (snapshot) =>
        (snapshot.activity.key_memories = [
          {
            day: 3,
            importance: 10,
            summary:
              "Awakening assessment: Awakened at Rank F with Threat Sense.",
          },
        ]),
    ],
    [3, "Late Night", (snapshot) => (snapshot.activity.key_memories = [])],
    [
      4,
      "Morning",
      (snapshot) =>
        snapshot.activity.key_memories.push({
          day: 4,
          importance: 8,
          summary:
            "Guild registration: Aiko Sato issued an F-rank license; travel and filing cost ¥0.",
        }),
    ],
    [
      5,
      "Morning",
      (snapshot) =>
        (snapshot.activity.key_memories = snapshot.activity.key_memories.filter(
          (memory) => memory.day !== 4,
        )),
    ],
  ]) {
    const snapshot = structuredClone(original);
    snapshot.clock = { day, slot };
    snapshot.activity.recent_events = [];
    snapshot.activity.key_memories = [];
    snapshot.story.next.days_remaining = 183 - day;
    snapshot.economy.rent_payments = 0;
    snapshot.economy.rent_arrears = 0;
    setProgression(
      snapshot,
      day === 3 && slot === "Afternoon" ? "Unranked" : "F",
      day === 3 && slot === "Afternoon" ? "None" : "Threat Sense",
      0,
    );
    snapshot.protagonist.current_goal = currentGoalFor(snapshot);
    syncRegistration(snapshot);
    assert.equal(isObserverSnapshot(snapshot), true);
    mutate(snapshot);
    assert.equal(isObserverSnapshot(snapshot), false);
  }
});
test("prevents hunter-shop visits before Guild registration", async () => {
  const original = await readFile(
    new URL("public/data/observer-snapshot.json", root),
    "utf8",
  ).then(JSON.parse);
  for (const [day, slot] of [
    [3, "Evening"],
    [4, "Afternoon"],
  ]) {
    const snapshot = structuredClone(original);
    snapshot.clock = { day, slot };
    snapshot.activity.recent_events = [];
    snapshot.activity.key_memories = [];
    snapshot.story.next.days_remaining = 183 - day;
    snapshot.economy.rent_payments = 0;
    snapshot.economy.rent_arrears = 0;
    setProgression(snapshot, "F", "Threat Sense", 0);
    snapshot.protagonist.current_goal = currentGoalFor(snapshot);
    syncRegistration(snapshot);
    assert.equal(snapshot.economy.shop_visits, 0);
    assert.equal(isObserverSnapshot(snapshot), true);
    snapshot.economy.shop_visits = 1;
    assert.equal(isObserverSnapshot(snapshot), false);
  }
});
test("prevents hunter equipment before the Guild shop unlock", async () => {
  const original = await readFile(
    new URL("public/data/observer-snapshot.json", root),
    "utf8",
  ).then(JSON.parse);
  for (const [day, slot] of [
    [3, "Afternoon"],
    [3, "Evening"],
    [4, "Afternoon"],
  ]) {
    const snapshot = structuredClone(original);
    snapshot.clock = { day, slot };
    snapshot.activity.recent_events = [];
    snapshot.activity.key_memories = [];
    snapshot.story.next.days_remaining = 183 - day;
    snapshot.economy.rent_payments = 0;
    snapshot.economy.rent_arrears = 0;
    setProgression(
      snapshot,
      day === 3 && slot === "Afternoon" ? "Unranked" : "F",
      day === 3 && slot === "Afternoon" ? "None" : "Threat Sense",
      0,
    );
    snapshot.protagonist.current_goal = currentGoalFor(snapshot);
    syncRegistration(snapshot);
    assert.equal(isObserverSnapshot(snapshot), true);
    snapshot.protagonist.equipment = {
      armor: null,
      inventory: { "Field Knife": 1 },
      weapon: "Field Knife",
    };
    assert.equal(isObserverSnapshot(snapshot), false);
  }
});
test("prevents portal evidence before Guild registration", async () => {
  const original = await readFile(
    new URL("public/data/observer-snapshot.json", root),
    "utf8",
  ).then(JSON.parse);
  for (const [day, slot] of [
    [3, "Afternoon"],
    [3, "Evening"],
    [4, "Afternoon"],
  ]) {
    const snapshot = structuredClone(original);
    snapshot.clock = { day, slot };
    snapshot.activity.recent_events = [];
    snapshot.activity.key_memories = [];
    snapshot.story.next.days_remaining = 183 - day;
    snapshot.economy.rent_payments = 0;
    snapshot.economy.rent_arrears = 0;
    setProgression(
      snapshot,
      day === 3 && slot === "Afternoon" ? "Unranked" : "F",
      day === 3 && slot === "Afternoon" ? "None" : "Threat Sense",
      0,
    );
    snapshot.protagonist.current_goal = currentGoalFor(snapshot);
    syncRegistration(snapshot);
    assert.equal(isObserverSnapshot(snapshot), true);
    snapshot.portals.discovered = ["Ashen Shopping Arcade"];
    assert.equal(isObserverSnapshot(snapshot), false);
  }
});
test("requires rank points to match hunter promotion", async () => {
  const original = await readFile(
    new URL("public/data/observer-snapshot.json", root),
    "utf8",
  ).then(JSON.parse);
  for (const [hunter_rank, ability, rank_points] of [
    ["Unranked", "None", 0],
    ["F", "Threat Sense", 27],
    ["E", "Threat Sense", 30],
    ["E", "Threat Sense", 59],
    ["D", "Threat Sense", 60],
    ["D", "Threat Sense", 89],
    ["C", "Threat Sense", 90],
  ]) {
    const valid = structuredClone(original);
    setProgression(valid, hunter_rank, ability, rank_points);
    assert.equal(isObserverSnapshot(valid), true);
  }
  for (const [hunter_rank, ability, rank_points] of [
    ["F", "Threat Sense", 30],
    ["E", "Threat Sense", 29],
    ["E", "Threat Sense", 60],
    ["D", "Threat Sense", 90],
    ["C", "Threat Sense", 89],
  ]) {
    const invalid = structuredClone(original);
    invalid.protagonist.hunter_rank = hunter_rank;
    invalid.protagonist.ability = ability;
    invalid.protagonist.progression.rank_points = rank_points;
    assert.equal(isObserverSnapshot(invalid), false);
  }
});
test("requires mission evidence for rank points", async () => {
  const original = await readFile(
    new URL("public/data/observer-snapshot.json", root),
    "utf8",
  ).then(JSON.parse);
  for (const [completed, points] of [
    [0, 0],
    [1, 10],
    [1, 17],
    [3, 30],
    [3, 51],
  ]) {
    const valid = structuredClone(original);
    valid.protagonist.hunter_rank = points < 30 ? "F" : "E";
    valid.protagonist.ability = "Threat Sense";
    valid.protagonist.progression.missions_attempted = Math.max(
      valid.protagonist.progression.missions_attempted,
      completed,
    );
    valid.protagonist.progression.missions_completed = completed;
    valid.protagonist.progression.rank_points = points;
    valid.protagonist.current_goal = currentGoalFor(valid);
    assert.equal(isObserverSnapshot(valid), true);
  }
  for (const [completed, points] of [
    [0, 10],
    [1, 9],
    [1, 18],
    [3, 29],
    [3, 52],
  ]) {
    const invalid = structuredClone(original);
    invalid.protagonist.hunter_rank = points >= 30 ? "E" : "F";
    invalid.protagonist.ability = "Threat Sense";
    invalid.protagonist.progression.missions_attempted = Math.max(
      invalid.protagonist.progression.missions_attempted,
      completed,
    );
    invalid.protagonist.progression.missions_completed = completed;
    invalid.protagonist.progression.rank_points = points;
    assert.equal(isObserverSnapshot(invalid), false);
  }
});
test("requires exact authored mission award composition", async () => {
  const original = await readFile(
    new URL("public/data/observer-snapshot.json", root),
    "utf8",
  ).then(JSON.parse);
  for (const [completed, points] of [
    [1, 10],
    [1, 13],
    [1, 17],
    [2, 20],
    [2, 23],
    [2, 26],
    [2, 27],
    [2, 30],
    [2, 34],
    [3, 40],
  ]) {
    const valid = structuredClone(original);
    setProgression(
      valid,
      points < 30 ? "F" : points < 60 ? "E" : "D",
      "Threat Sense",
      points,
      completed,
    );
    assert.equal(isObserverSnapshot(valid), true);
  }
  for (const [completed, points] of [
    [1, 11],
    [1, 12],
    [1, 14],
    [1, 16],
    [2, 21],
    [2, 24],
    [2, 28],
    [2, 33],
    [3, 31],
  ]) {
    const invalid = structuredClone(original);
    setProgression(
      invalid,
      points < 30 ? "F" : "E",
      "Threat Sense",
      points,
      completed,
    );
    assert.equal(isObserverSnapshot(invalid), false);
  }
});

test("replays all four deadlines in Timeline II with Vector Step alternatives", async () => {
  const [state, one, two, three, black] = await Promise.all([
    readFile(new URL("../app/game/game-state.ts", import.meta.url), "utf8"),
    readFile(
      new URL("../app/game/deadline/arc-one/page.tsx", import.meta.url),
      "utf8",
    ),
    readFile(
      new URL("../app/game/deadline/arc-two/page.tsx", import.meta.url),
      "utf8",
    ),
    readFile(
      new URL("../app/game/deadline/arc-three/page.tsx", import.meta.url),
      "utf8",
    ),
    readFile(
      new URL("../app/game/deadline/black-gate/page.tsx", import.meta.url),
      "utf8",
    ),
  ]);
  assert.match(state, /state\.timeline <= 3/);
  assert.match(one, /timeline-ii-arc-i-rescue/);
  assert.match(one, /vector >= 20/);
  assert.match(two, /timeline-ii-seven-route-rescue/);
  assert.match(two, /vector >= 50/);
  assert.match(three, /timeline-ii-command-purge-outrun/);
  assert.match(three, /vector >= 80/);
  assert.match(black, /busan-signal-decoded/);
  assert.match(black, /residual-anchor-complete/);
});

test("gives Timeline III a complete year and Causal Sever preparation route", async () => {
  const [state, city, relay, black] = await Promise.all([
    readFile(new URL("../app/game/game-state.ts", import.meta.url), "utf8"),
    readFile(new URL("../app/game/city/page.tsx", import.meta.url), "utf8"),
    readFile(
      new URL("../app/game/residual-relay/page.tsx", import.meta.url),
      "utf8",
    ),
    readFile(
      new URL("../app/game/deadline/black-gate/page.tsx", import.meta.url),
      "utf8",
    ),
  ]);
  assert.match(state, /state\.timeline <= 3/);
  assert.match(city, /FINAL-TIMELINE ROUTE/);
  assert.match(relay, /causal-spine-mapped/);
  assert.match(relay, /severance-key-complete/);
  assert.match(
    relay,
    /activeSkill = finalTimeline \? "Causal Sever" : "Vector Step"/,
  );
  assert.match(black, /causal-spine-mapped/);
  assert.match(black, /severance-key-complete/);
});

test("ends Timeline III by severing the Black Gate instead of opening a fourth loop", async () => {
  const [state, black, hud] = await Promise.all([
    readFile(new URL("../app/game/game-state.ts", import.meta.url), "utf8"),
    readFile(
      new URL("../app/game/deadline/black-gate/page.tsx", import.meta.url),
      "utf8",
    ),
    readFile(new URL("../app/game/game-hud.tsx", import.meta.url), "utf8"),
  ]);
  assert.match(state, /"completed"/);
  assert.match(state, /black-gate-causal-severed/);
  assert.match(black, /SEVER THE GATE&apos;S FOUNDING CAUSE/);
  assert.match(black, /The fourth year never needs to begin/);
  assert.match(hud, /TRUE ENDING · TIMELINE 3/);
  assert.match(hud, /The loop is over/);
});

test("gives Timeline III a distinct Causal Sever solution at the first deadline", async () => {
  const arc = await readFile(
    new URL("../app/game/deadline/arc-one/page.tsx", import.meta.url),
    "utf8",
  );
  assert.match(arc, /choice === "causal"/);
  assert.match(arc, /causal >= 25/);
  assert.match(arc, /timeline-iii-route-cause-severed/);
  assert.match(arc, /SEVER THE COLLAPSE'S FIRST CAUSE/);
  assert.match(arc, /resolve\(rpg\.timeline === 3 \? "causal" : "vector"\)/);
});

test("gives Timeline III a distinct Causal Sever solution at the second deadline", async () => {
  const arc = await readFile(
    new URL("../app/game/deadline/arc-two/page.tsx", import.meta.url),
    "utf8",
  );
  assert.match(arc, /choice === "causal"/);
  assert.match(arc, /causal >= 55/);
  assert.match(arc, /timeline-iii-breach-chain-severed/);
  assert.match(arc, /SEVER THE SHARED BREACH TRIGGER/);
  assert.match(arc, /resolve\(rpg\.timeline === 3 \? "causal" : "vector"\)/);
});

test("gives Timeline III a distinct Causal Sever solution at the third deadline", async () => {
  const arc = await readFile(
    new URL("../app/game/deadline/arc-three/page.tsx", import.meta.url),
    "utf8",
  );
  assert.match(arc, /choice === "causal"/);
  assert.match(arc, /causal >= 85/);
  assert.match(arc, /timeline-iii-command-forgery-severed/);
  assert.match(arc, /SEVER THE FORGERY FROM COMMAND/);
  assert.match(arc, /resolve\(rpg\.timeline === 3 \? "causal" : "vector"\)/);
});

test("requires all three Causal Sever arc outcomes for the true ending", async () => {
  const black = await readFile(
    new URL("../app/game/deadline/black-gate/page.tsx", import.meta.url),
    "utf8",
  );
  for (const event of [
    "timeline-iii-route-cause-severed",
    "timeline-iii-breach-chain-severed",
    "timeline-iii-command-forgery-severed",
  ])
    assert.match(black, new RegExp(event));
  assert.match(black, /prepared && causalArcReady/);
  assert.match(black, /trueEndingReady = ready && causalArcReady/);
  assert.match(black, /CAUSAL ARC I · II · III REQUIRED/);
});

test("offers deterministic location work with exact costs and daily limits", async () => {
  const city = await readFile(
    new URL("../app/game/city/page.tsx", import.meta.url),
    "utf8",
  );
  for (const shift of [
    "Guild Patrol",
    "Night Courier",
    "Archive Indexing",
    "Perimeter Watch",
  ])
    assert.match(city, new RegExp(shift));
  for (const pay of ["pay: 1600", "pay: 1100", "pay: 850", "pay: 1900"])
    assert.match(city, new RegExp(pay));
  assert.match(
    city,
    /entry\.day === rpg\.day && entry\.action === shift\.action/,
  );
  assert.match(city, /rpg\.energy < shift\.energy/);
  assert.match(city, /takeRpgAction\(rpg, shift\.action/);
  assert.match(city, /One shift per location each day/);
  assert.doesNotMatch(city, /Math\.random/);
});

test("runs a local monthly rent ledger without charging existing saves", async () => {
  const [state, game, styles] = await Promise.all([
    readFile(new URL("../app/game/game-state.ts", import.meta.url), "utf8"),
    readFile(new URL("../app/game/page.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/globals.css", import.meta.url), "utf8"),
  ]);
  assert.match(state, /RPG_RENT_COST = 8000/);
  assert.match(state, /RPG_RENT_PERIOD_DAYS = 30/);
  assert.match(state, /export function rentPaymentDue/);
  assert.match(state, /export function payRent/);
  assert.match(state, /while \(state\.day > paidThroughDay/);
  assert.match(state, /candidate\.rentLedger \?\?/);
  assert.match(state, /arrears: 0/);
  assert.doesNotMatch(
    state.match(/export function payRent[\s\S]*?\n}/)?.[0] ?? "",
    /takeRpgAction/,
  );
  assert.match(game, /PAID THROUGH DAY/);
  assert.match(game, /NO TIME SLOT/);
  assert.match(styles, /\.rent-ledger/);
});

test("keeps rent pressure visible across every RPG chapter", async () => {
  const [hud, styles] = await Promise.all([
    readFile(new URL("../app/game/game-hud.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/globals.css", import.meta.url), "utf8"),
  ]);
  assert.match(hud, /HOUSING/);
  assert.match(hud, /rentDaysRemaining/);
  assert.match(hud, /RENT DUE SOON/);
  assert.match(hud, /RENT OVERDUE/);
  assert.match(hud, /role=\{rentStatus === "overdue" \? "alert" : "status"\}/);
  assert.match(styles, /\.housing-status\.due-soon/);
  assert.match(styles, /\.rent-warning\.overdue/);
  assert.match(styles, /nth-child\(5\)/);
});

test("adds exact once-daily Residual Read training at two risk levels", async () => {
  const [city, styles] = await Promise.all([
    readFile(new URL("../app/game/city/page.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/globals.css", import.meta.url), "utf8"),
  ]);
  assert.match(city, /Controlled Residual Read/);
  assert.match(city, /Live Residual Read/);
  assert.match(city, /mastery: 6,\s*energy: 20,\s*health: 0/);
  assert.match(city, /mastery: 10,\s*energy: 28,\s*health: 6/);
  assert.match(city, /trainedToday/);
  assert.match(city, /Math\.min\(drill\.mastery, 100 - mastery\)/);
  assert.match(city, /takeRpgAction\(rpg, drill\.action/);
  assert.match(city, /One drill per location each day/);
  assert.doesNotMatch(city, /Math\.random/);
  assert.match(styles, /\.skill-training/);
});

test("charges homeward travel only after Ren has left the apartment", async () => {
  const [city, styles] = await Promise.all([
    readFile(new URL("../app/game/city/page.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/globals.css", import.meta.url), "utf8"),
  ]);
  assert.match(city, /function returnHome\(\)/);
  assert.match(city, /rpg\.location === "Ren's Apartment"/);
  assert.match(city, /takeRpgAction\(rpg, "Returned home from Tokyo"/);
  assert.match(city, /energy: rpg\.energy - 4/);
  assert.match(city, /RETURN HOME · 1 SLOT/);
  assert.match(city, /← CANCEL MAP/);
  assert.doesNotMatch(city, /<Link href="\/game">← PROLOGUE<\/Link>/);
  assert.match(styles, /\.homeward-travel/);
});

test("condenses city activities into keyboard-native in-world drawers", async () => {
  const [city, styles] = await Promise.all([
    readFile(new URL("../app/game/city/page.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/globals.css", import.meta.url), "utf8"),
  ]);
  assert.match(city, /className="location-activities"/);
  assert.match(city, /<details open>/);
  assert.match(city, /<summary>\s*<span>WORK<\/span>/);
  assert.match(city, /<summary>\s*<span>TRAIN<\/span>/);
  assert.match(city, /<summary>\s*<span>SHOP<\/span>/);
  assert.doesNotMatch(city, /role="tab"/);
  assert.match(styles, /\.location-activities>details/);
  assert.match(styles, /summary:focus-visible/);
  assert.match(styles, /flex-wrap:wrap/);
});

test("makes daily apartment sustenance an explicit bounded RPG choice", async () => {
  const game = await readFile(
    new URL("../app/game/page.tsx", import.meta.url),
    "utf8",
  );
  assert.match(game, /Eat a proper meal · ¥650/);
  assert.match(game, /Ate a proper meal/);
  assert.match(game, /money: rpg!\.money - 650/);
  assert.match(game, /energy: rpg!\.energy \+ 18/);
  assert.match(game, /health: rpg!\.health \+ 3/);
  assert.match(game, /entry\.day === rpg\.day/);
  assert.match(game, /rpg\.money < 650 \|\| ateToday/);
  assert.match(game, /PROPER MEAL ALREADY EATEN TODAY/);
});

test("charges a transparent outbound Tokyo train fare without trapping Ren", async () => {
  const city = await readFile(
    new URL("../app/game/city/page.tsx", import.meta.url),
    "utf8",
  );
  assert.match(city, /const TOKYO_TRAIN_FARE = 220/);
  assert.match(city, /rpg\.money < TOKYO_TRAIN_FARE/);
  assert.match(city, /money: rpg!\.money - TOKYO_TRAIN_FARE/);
  assert.match(city, /TRAVEL · ¥\{TOKYO_TRAIN_FARE\} · −6 EN · 1 SLOT/);
  assert.match(city, /Returning home remains free of cash cost/);
  assert.match(city, /Fare paid ¥\{TOKYO_TRAIN_FARE\}/);
  assert.doesNotMatch(city, /money: rpg\.money - TOKYO_TRAIN_FARE[\s\S]{0,180}Returned home/);
});

test("sells capped field consumables individually at Akihabara", async () => {
  const city = await readFile(
    new URL("../app/game/city/page.tsx", import.meta.url),
    "utf8",
  );
  for (const marker of ["MARKET_SUPPLIES", "Field Bandage", "Energy Drink", "Ward Charm"])
    assert.match(city, new RegExp(marker));
  assert.match(city, /bandages: Math\.min\(3, rpg\.fieldKit\.bandages \+ 1\)/);
  assert.match(city, /energyDrinks: Math\.min\(3, rpg\.fieldKit\.energyDrinks \+ 1\)/);
  assert.match(city, /wardCharm: true/);
  assert.match(city, /money: rpg\.money - item\.price/);
  assert.match(city, /saveRpgState\(next\)/);
  assert.match(city, /No additional time slot was spent/);
  assert.match(city, /PACK FULL/);
});

test("offers bounded once-daily paid treatment at the Guild clinic", async () => {
  const [city, styles] = await Promise.all([
    readFile(new URL("../app/game/city/page.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/globals.css", import.meta.url), "utf8"),
  ]);
  assert.match(city, /const GUILD_CLINIC_FEE = 1800/);
  assert.match(city, /Received Guild Clinic Treatment/);
  assert.match(city, /Math\.min\(25, 100 - rpg\.health\)/);
  assert.match(city, /money: rpg\.money - GUILD_CLINIC_FEE/);
  assert.match(city, /health: rpg\.health \+ restored/);
  assert.match(city, /treatedToday \|\| rpg\.health >= 100 \|\| rpg\.money < GUILD_CLINIC_FEE/);
  assert.match(city, /TREATMENT ALREADY RECEIVED TODAY/);
  assert.match(city, /Guild Medical Wing/);
  assert.match(styles, /\.guild-clinic/);
});

test("shows the current Persona-style day as a four-slot journal ledger", async () => {
  const [hud, styles] = await Promise.all([
    readFile(new URL("../app/game/game-hud.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/globals.css", import.meta.url), "utf8"),
  ]);
  assert.match(hud, /RPG_SLOTS/);
  assert.match(hud, /RPG_SLOTS\.indexOf\(state\.slot\)/);
  assert.match(hud, /TODAY \{currentSlotIndex\} \/ 4 SPENT/);
  assert.match(hud, /className="day-ledger"/);
  assert.match(hud, /data-status=\{index < currentSlotIndex/);
  assert.match(hud, /"SPENT".*"NOW".*"OPEN"/s);
  assert.match(styles, /\.rpg-journal \.day-ledger/);
  assert.match(styles, /\.day-ledger \.current/);
});

test("uses one current version label across the title and playable campaign", async () => {
  const [version, title, game] = await Promise.all([
    readFile(new URL("../app/game/game-version.ts", import.meta.url), "utf8"),
    readFile(new URL("../app/game/title-screen.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/game/page.tsx", import.meta.url), "utf8"),
  ]);
  assert.match(version, /GAME_VERSION = "0\.1380"/);
  assert.match(title, /PRIVATE RPG CAMPAIGN \/ v\{GAME_VERSION\}/);
  assert.match(game, /REN RPG \/ v\{GAME_VERSION\}/);
  assert.match(title, /from "\.\/game-version"/);
  assert.match(game, /from "\.\/game-version"/);
  assert.doesNotMatch(title, /v0\.1010/);
});

test("avoids the failing vinext RSC prefetch path throughout the RPG", async () => {
  const wrapper = await readFile(
    new URL("../app/game/game-link.tsx", import.meta.url),
    "utf8",
  );
  assert.match(wrapper, /<NextLink \{\.\.\.props\} prefetch=\{false\} \/>/);
  const pages = [
    "page.tsx", "title-screen.tsx", "city/page.tsx", "caseboard/page.tsx",
    "evening/page.tsx", "debrief/page.tsx", "field/page.tsx",
    "residual-relay/page.tsx", "awakening/page.tsx", "awakening/second/page.tsx",
    "awakening/final/page.tsx", "deadline/arc-one/page.tsx",
    "deadline/arc-two/page.tsx", "deadline/arc-three/page.tsx",
    "deadline/black-gate/page.tsx",
  ];
  const sources = await Promise.all(
    pages.map((page) => readFile(new URL(`../app/game/${page}`, import.meta.url), "utf8")),
  );
  for (const source of sources) {
    assert.doesNotMatch(source, /from "next\/link"/);
    assert.match(source, /game-link"/);
  }
});
