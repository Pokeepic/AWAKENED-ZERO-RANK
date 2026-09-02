"use client";

import Image from "next/image";
import Link from "../game-link";
import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { verifyArtifacts, type ObserverSnapshot } from "../../observer-data";
import { loadRpgState, saveRpgState, takeRpgAction, type RpgState } from "../game-state";
import { GameHud } from "../game-hud";
import { gameAtmosphere } from "../game-weather";

type MoveId = "strike" | "pulse" | "guard" | "vector" | "sever";
type MotionId = MoveId | "item";
type Move = { id: MoveId; label: string; damage: number; cost: number; mitigation: number; note: string; skill?: "Vector Step" | "Causal Sever"; requiredMastery?: number };
const BASE_MOVES: readonly Move[] = [
  { id: "strike", label: "PRECISION STRIKE", damage: 24, cost: 5, mitigation: 0, note: "Ren cuts through the nearest fracture before it can reform." },
  { id: "pulse", label: "BARRIER PULSE", damage: 17, cost: 12, mitigation: 7, note: "Residual Read folds the Gate pressure back against its source." },
  { id: "guard", label: "GUARD & READ", damage: 9, cost: 2, mitigation: 99, note: "Ren gives ground, reads the telegraph, then answers from cover." },
];
const TIMELINE_MOVES: readonly Move[] = [
  { id: "vector", label: "VECTOR STEP", damage: 27, cost: 10, mitigation: 12, skill: "Vector Step", requiredMastery: 20, note: "Ren crosses the attack line before the sentinel can close it." },
  { id: "sever", label: "CAUSAL SEVER", damage: 36, cost: 18, mitigation: 99, skill: "Causal Sever", requiredMastery: 25, note: "Ren cuts the sentinel's attack away from the cause that formed it." },
];
const INTENTS = [
  { id: "claw", label: "FRACTURE CLAW", damage: 8, exposure: 0, cue: "A narrow limb draws back. Direct impact incoming." },
  { id: "surge", label: "PRESSURE SURGE", damage: 15, exposure: 0, cue: "The corridor compresses around the sentinel. Guard or evade." },
  { id: "core", label: "CORE EXPOSURE", damage: 10, exposure: 8, cue: "Its core opens to attack. Every move deals +8 damage this round." },
] as const;

const ENCOUNTERS = {
  "Glass Office Labyrinth": {
    enemy: "FRACTURE SENTINEL", hp: 60, reward: 1800, className: "sentinel",
    background: "/game/portals/glass-office-labyrinth-interior-v1.png",
    intro: "A fracture sentinel blocks the inner corridor.",
    intents: INTENTS,
  },
  "Sunken Courtyard": {
    enemy: "DROWNED ARCHIVIST", hp: 78, reward: 2400, className: "archivist",
    background: "/game/portals/sunken-courtyard-interior-v1.png",
    intro: "A drowned archivist rises between Ren and the submerged record.",
    intents: [
      { id: "undertow", label: "UNDERTOW GRIP", damage: 11, exposure: 0, cue: "Water pulls toward the core. Brace before the floor gives way." },
      { id: "rain", label: "GLASS RAIN", damage: 17, exposure: 0, cue: "The ceiling fractures into a descending blade pattern." },
      { id: "bloom", label: "MEMORY BLOOM", damage: 9, exposure: 10, cue: "Its archive opens. The exposed record amplifies every strike by 10." },
    ],
  },
} as const;
const PLANS = {
  prepare: { label: "GUARD LATTICE", damage: 0, mitigation: 3, note: "Preparation absorbs 3 incoming damage." },
  investigate: { label: "WEAK POINT MARKED", damage: 4, mitigation: 0, note: "Investigation adds 4 damage to every move." },
  rush: { label: "UNSTABLE ENTRY", damage: 0, mitigation: -2, note: "The rushed entry adds 2 incoming damage." },
} as const;
type PlanId = keyof typeof PLANS;

type Battle = { enemyHp: number; round: number; log: string[]; resolved: "victory" | "retreat" | "death" | null };
type CombatFeedback = { dealt: number; incoming: number; restored: number; blocked: boolean; finisher: boolean; intentLabel: string; heavy: boolean };

export default function FieldPage() {
  const searchParams = useSearchParams();
  const [snapshot, setSnapshot] = useState<ObserverSnapshot | null>(null);
  const [rpg, setRpg] = useState<RpgState | null>(null);
  const [failed, setFailed] = useState(false);
  const [turnLocked, setTurnLocked] = useState(false);
  const [attackMotion, setAttackMotion] = useState<{ count: number; move: MotionId; counter: boolean }>({ count: 0, move: "strike", counter: false });
  const [feedback, setFeedback] = useState<CombatFeedback>({ dealt: 0, incoming: 0, restored: 0, blocked: false, finisher: false, intentLabel: "", heavy: false });
  const caseName = searchParams.get("case");
  const encounter = caseName && caseName in ENCOUNTERS ? ENCOUNTERS[caseName as keyof typeof ENCOUNTERS] : ENCOUNTERS["Glass Office Labyrinth"];
  const requestedPlan = searchParams.get("plan");
  const planId: PlanId = requestedPlan && requestedPlan in PLANS ? requestedPlan as PlanId : "rush";
  const plan = PLANS[planId];
  const [battle, setBattle] = useState<Battle>(() => ({ enemyHp: encounter.hp, round: 1, log: [encounter.intro], resolved: null }));

  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      try {
        const options = { cache: "no-store" as RequestCache, signal: controller.signal };
        const [contractResponse, snapshotResponse] = await Promise.all([fetch("/data/observer-contract.json", options), fetch("/data/observer-snapshot.json", options)]);
        if (!contractResponse.ok || !snapshotResponse.ok) throw new Error("artifacts unavailable");
        const verified = await verifyArtifacts(await contractResponse.json(), await snapshotResponse.json());
        if (!controller.signal.aborted) { setSnapshot(verified.snapshot); setRpg(loadRpgState(verified.snapshot)); }
      } catch (error) {
        if (!(error instanceof DOMException && error.name === "AbortError")) setFailed(true);
      }
    }
    void load();
    return () => controller.abort();
  }, []);

  const moves = useMemo(() => [
    ...BASE_MOVES,
    ...(rpg?.timeline && rpg.timeline >= 2 ? [TIMELINE_MOVES[0]] : []),
    ...(rpg?.timeline === 3 ? [TIMELINE_MOVES[1]] : []),
  ], [rpg]);
  const intent = encounter.intents[(battle.round - 1) % encounter.intents.length];
  const moveReady = useCallback((move: Move) => Boolean(rpg && rpg.energy >= move.cost && (!move.skill || (rpg.skillMastery[move.skill] ?? 0) >= (move.requiredMastery ?? 0))), [rpg]);
  const wardMitigation = rpg?.fieldKit.wardCharm ? 2 : 0;
  const gearDamage = rpg?.fieldKit.weapon === "Resonance Blade" ? 3 : 0;
  const gearMitigation = rpg?.fieldKit.coat === "Guildweave Coat" ? 2 : 0;

  useEffect(() => {
    if (!turnLocked) return;
    const timer = window.setTimeout(() => setTurnLocked(false), 1100);
    return () => window.clearTimeout(timer);
  }, [attackMotion.count, turnLocked]);

  const act = useCallback((id: MoveId) => {
    if (!rpg || battle.resolved || turnLocked) return;
    const move = moves.find((candidate) => candidate.id === id);
    if (!move || !moveReady(move)) return;
    const dealt = move.damage + intent.exposure + plan.damage + gearDamage;
    const enemyHp = Math.max(0, battle.enemyHp - dealt);
    const incoming = enemyHp === 0 ? 0 : Math.max(0, intent.damage - move.mitigation - plan.mitigation - wardMitigation - gearMitigation);
    setTurnLocked(true);
    setAttackMotion((value) => ({ count: value.count + 1, move: id, counter: incoming > 0 }));
    setFeedback({ dealt, incoming, restored: 0, blocked: enemyHp > 0 && incoming === 0, finisher: enemyHp === 0, intentLabel: intent.label, heavy: intent.id === "surge" || intent.id === "rain" });
    const health = Math.max(0, rpg.health - incoming);
    const energy = Math.max(0, rpg.energy - move.cost);
    if (enemyHp === 0) {
      const skillMastery = { ...rpg.skillMastery, "Residual Read": Math.min(100, (rpg.skillMastery["Residual Read"] ?? 0) + 12) };
      const action = encounter.enemy === "FRACTURE SENTINEL" ? "Cleared the fracture sentinel" : "Cleared the drowned archivist";
      const next = takeRpgAction({ ...rpg, health, energy }, action, { health, energy, money: rpg.money + encounter.reward, location: caseName ?? "Glass Office Labyrinth", skillMastery });
      setRpg(next);
      setBattle((current) => ({ ...current, enemyHp, log: [...current.log, `${move.note} ${dealt} damage.`, `${encounter.enemy} collapses. The Gate stabilizes.`], resolved: "victory" }));
    } else if (health === 0) {
      const action = encounter.enemy === "FRACTURE SENTINEL" ? "Fell to the fracture sentinel" : "Fell to the drowned archivist";
      const next = takeRpgAction({ ...rpg, health, energy }, action, { health, energy, location: caseName ?? "Glass Office Labyrinth" });
      setRpg(next);
      setBattle((current) => ({ ...current, enemyHp, log: [...current.log, `${move.note} ${intent.label} deals ${incoming} damage.`, "The Gate closes. No residual path answers Ren."], resolved: "death" }));
    } else {
      const next = { ...rpg, health, energy };
      saveRpgState(next);
      setRpg(next);
      setBattle((current) => ({ enemyHp, round: current.round + 1, log: [...current.log, `${move.note} ${dealt} dealt; ${intent.label} answers for ${incoming}.`].slice(-4), resolved: null }));
    }
  }, [battle.enemyHp, battle.resolved, caseName, encounter, gearDamage, gearMitigation, intent, moveReady, moves, plan.damage, plan.mitigation, rpg, turnLocked, wardMitigation]);

  const applyFieldItem = useCallback((item: "bandage" | "energyDrink") => {
    if (!rpg || battle.resolved || turnLocked) return;
    const available = item === "bandage" ? rpg.fieldKit.bandages : rpg.fieldKit.energyDrinks;
    if (available === 0 || (item === "bandage" ? rpg.health >= 100 : rpg.energy >= 100)) return;
    const fieldKit = { ...rpg.fieldKit, [item === "bandage" ? "bandages" : "energyDrinks"]: available - 1 };
    const restoredHealth = item === "bandage" ? Math.min(100, rpg.health + 18) : rpg.health;
    const energy = item === "energyDrink" ? Math.min(100, rpg.energy + 22) : rpg.energy;
    const incoming = Math.max(0, intent.damage - plan.mitigation - wardMitigation - gearMitigation);
    setTurnLocked(true);
    setAttackMotion((value) => ({ count: value.count + 1, move: "item", counter: incoming > 0 }));
    setFeedback({ dealt: 0, incoming, restored: item === "bandage" ? restoredHealth - rpg.health : energy - rpg.energy, blocked: incoming === 0, finisher: false, intentLabel: intent.label, heavy: intent.id === "surge" || intent.id === "rain" });
    const health = Math.max(0, restoredHealth - incoming);
    const label = item === "bandage" ? "BANDAGE" : "ENERGY DRINK";
    const next = { ...rpg, health, energy, fieldKit };
    if (health === 0) {
      setRpg(takeRpgAction(next, `Fell to ${encounter.enemy.toLowerCase()}`, { health, energy, fieldKit, location: caseName ?? "Glass Office Labyrinth" }));
      setBattle((current) => ({ ...current, log: [...current.log, `${label} used; ${intent.label} deals ${incoming} damage.`, "The Gate closes. No residual path answers Ren."], resolved: "death" }));
      return;
    }
    saveRpgState(next);
    setRpg(next);
    setBattle((current) => ({ ...current, round: current.round + 1, log: [...current.log, `${label} used; ${intent.label} answers for ${incoming}.`].slice(-4) }));
  }, [battle.resolved, caseName, encounter.enemy, gearMitigation, intent, plan.mitigation, rpg, turnLocked, wardMitigation]);

  const retreat = useCallback(() => {
    if (!rpg || battle.resolved) return;
    const skillMastery = { ...rpg.skillMastery, "Residual Read": Math.min(100, (rpg.skillMastery["Residual Read"] ?? 0) + 5) };
    const action = encounter.enemy === "FRACTURE SENTINEL" ? "Withdrew from the fracture sentinel" : "Withdrew from the drowned archivist";
    const next = takeRpgAction(rpg, action, { energy: Math.max(0, rpg.energy - 2), location: "Adachi Gate Zone", skillMastery });
    setRpg(next);
    setBattle((current) => ({ ...current, log: [...current.log, "Ren marks the pattern and withdraws before the corridor seals."], resolved: "retreat" }));
  }, [battle.resolved, encounter.enemy, rpg]);

  useEffect(() => {
    function handleKey(event: KeyboardEvent) {
      if (battle.resolved || turnLocked || event.altKey || event.ctrlKey || event.metaKey) return;
      if (/^Digit[1-5]$/.test(event.code)) {
        const move = moves[Number(event.code.at(-1)) - 1];
        if (move) act(move.id);
      } else if (event.key.toLowerCase() === "b") applyFieldItem("bandage");
      else if (event.key.toLowerCase() === "e") applyFieldItem("energyDrink");
      else if (event.key.toLowerCase() === "r") retreat();
    }
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [act, applyFieldItem, battle.resolved, moves, retreat, turnLocked]);

  if (failed) return <main id="chronicle" className="game-loading"><p>FIELD LINK OFFLINE</p><h1>The Gate could not be verified.</h1><Link href="/game/caseboard">Return to caseboard</Link></main>;
  if (!snapshot || !rpg) return <main id="chronicle" className="game-loading" aria-busy="true"><p>LOADING FIELD SAVE</p><h1>Opening the Gate…</h1></main>;

  const caseFile = snapshot.portals.investigations.find((item) => item.portal_name === caseName) ?? snapshot.portals.investigations[0];
  const atmosphere = gameAtmosphere(rpg);
  return <main id="chronicle" className="field-shell">
    <header className="game-header"><Link href="/game/caseboard">← CASEBOARD</Link><b>AWAKENED <i>ZERO RANK</i></b><span>CHAPTER 04 / FIRST CONTACT</span></header>
    <GameHud state={rpg} current="field" />
    <section className="field-intro"><div><small>ACTIVE CASE / {caseFile?.portal_name ?? "VERIFIED GATE"}</small><h1>Hold the line.</h1></div><p><b>RISK {caseFile?.risk ?? "UNKNOWN"}</b><span>{rpg.slot.toUpperCase()} / {atmosphere.weather.toUpperCase()}</span>Battle moves are tactical turns. Time advances when the encounter resolves.</p></section>
    <section className="field-stage" aria-label="Gate battle">
      <div key={`${caseName}-${attackMotion.count}`} className={`field-arena portal-interior enemy-${encounter.className} intent-${intent.id} move-${attackMotion.move} ${turnLocked ? "battle-attacking" : ""} ${turnLocked && attackMotion.counter ? "enemy-countering" : ""} ${turnLocked && feedback.heavy ? "counter-heavy" : ""} ${turnLocked && feedback.finisher ? "finishing-blow" : ""}`}><Image src={encounter.background} alt={`Illustrated interior of ${caseFile?.portal_name ?? "the verified Gate"}`} fill sizes="(max-width: 800px) 100vw, 70vw" priority /><div className="field-shade" /><span className="field-ren field-ren-battle"><Image className="ren-battle-idle" src="/game/characters/ren-battle-back-v2.png" alt="Ren Takahashi viewed from behind in a defensive combat stance" width={1024} height={1536} priority /><Image className="ren-battle-strike" src="/game/characters/ren-battle-strike-v1.png" alt="" aria-hidden="true" width={1024} height={1536} priority /><i className="barrier-effect" aria-hidden="true" /><i className="read-effect" aria-hidden="true" /><i className="counter-impact" aria-hidden="true" /><b>REN</b></span><span className="field-enemy" aria-label={encounter.enemy}><i /><i /><i /><b>{encounter.enemy}</b></span>{turnLocked && <div className="combat-feedback" aria-hidden="true">{attackMotion.counter && <span className="resolved-intent">{feedback.intentLabel}</span>}{feedback.dealt > 0 && <strong className="damage-enemy">-{feedback.dealt}</strong>}{feedback.incoming > 0 && <strong className="damage-ren">-{feedback.incoming}</strong>}{feedback.blocked && <strong className="blocked-hit">BLOCKED</strong>}{feedback.restored > 0 && <strong className="restored-stat">+{feedback.restored}</strong>}{feedback.finisher && <strong className="finisher-label">BREAK</strong>}</div>}<div className={`enemy-intent ${turnLocked ? "intent-queued" : ""}`}><small>{turnLocked ? "NEXT TELEGRAPH" : "NEXT ATTACK"} / {intent.label}</small><b>{intent.damage} DAMAGE</b><p>{intent.cue}</p></div></div>
      <aside className="battle-panel" aria-live="polite" aria-busy={turnLocked}><div className="dossier-tab">COMBAT DOSSIER / {String(battle.round).padStart(2, "0")}</div><div className="battle-bars"><span>REN / HP {rpg.health}</span><meter min="0" max="100" value={rpg.health} /><span>{encounter.enemy} / HP {battle.enemyHp}</span><meter min="0" max={encounter.hp} value={battle.enemyHp} /></div><small>ROUND {battle.round} / {plan.label}</small><p>{battle.log.at(-1)}</p><div className="battle-plan"><b>{plan.label}</b><span>{plan.note}</span></div>{!battle.resolved ? <div className="battle-actions">{moves.map((move, index) => { const ready = moveReady(move); const dealt = move.damage + intent.exposure + plan.damage + gearDamage; const incoming = Math.max(0, intent.damage - move.mitigation - plan.mitigation - wardMitigation - gearMitigation); return <button className={`move-card move-${move.id}`} key={move.id} disabled={!ready || turnLocked} onClick={() => act(move.id)}><i>{String(index + 1).padStart(2, "0")}</i><b>{move.label}</b><span>{ready ? `${dealt} DMG / ${move.cost} EN / TAKE ${incoming}` : move.skill ? `${move.skill.toUpperCase()} ${move.requiredMastery}% REQUIRED` : `${move.cost} ENERGY REQUIRED`}</span></button>; })}<button className="retreat" disabled={turnLocked} onClick={retreat}><i>EX</i><b>TACTICAL RETREAT</b><span>2 EN / SAFE EXIT</span></button></div> : <div className={`battle-result ${battle.resolved}`}><small>{battle.resolved === "victory" ? "GATE SECURED" : battle.resolved === "death" ? "RUN TERMINATED" : "TACTICAL RETREAT"}</small><h2>{battle.resolved === "victory" ? `+¥${encounter.reward.toLocaleString()} / TIME ADVANCED` : battle.resolved === "death" ? "GAME OVER" : "REN SURVIVED / TIME ADVANCED"}</h2><p>{battle.resolved === "death" ? "Only the final day can open a path to transmigration." : battle.resolved === "retreat" ? "Ren keeps the evidence he gathered. Aiko is waiting beyond the exclusion-zone perimeter…" : "A canon event has triggered. Aiko is waiting at Adachi Station…"}</p><nav>{battle.resolved === "death" ? <Link href="/game">RETURN TO CAMPAIGN</Link> : <Link href="/game/evening">CONTINUE TO ADACHI STATION</Link>}</nav></div>}</aside>
    </section>
    {!battle.resolved && <section className="field-kit-bar" aria-label="Field kit"><div className="field-combat-loadout" aria-label="Equipped field loadout"><span className={`combat-gear ${rpg.fieldKit.weapon === "Resonance Blade" ? "gear-blade" : "gear-knife"}`}><i aria-hidden="true" /><small>WEAPON</small><b>{rpg.fieldKit.weapon}</b></span><span className={`combat-gear ${rpg.fieldKit.coat === "Guildweave Coat" ? "gear-guildweave" : "gear-jacket"}`}><i aria-hidden="true" /><small>COAT</small><b>{rpg.fieldKit.coat}</b></span><span className={`combat-gear gear-ward ${rpg.fieldKit.wardCharm ? "is-ready" : "is-empty"}`}><i aria-hidden="true" /><small>WARD</small><b>{rpg.fieldKit.wardCharm ? "READY" : "EMPTY"}</b></span></div><button disabled={turnLocked || rpg.fieldKit.bandages === 0 || rpg.health >= 100} onClick={() => applyFieldItem("bandage")}><b>B · BANDAGE ×{rpg.fieldKit.bandages}</b><span>+18 HP / ENEMY ACTS</span></button><button disabled={turnLocked || rpg.fieldKit.energyDrinks === 0 || rpg.energy >= 100} onClick={() => applyFieldItem("energyDrink")}><b>E · ENERGY DRINK ×{rpg.fieldKit.energyDrinks}</b><span>+22 EN / ENEMY ACTS</span></button></section>}
    <footer className="game-footer"><b>DETERMINISTIC FIELD ENCOUNTER</b><p>No random rolls. Every move shows its exact cost and effect.</p><span>ENERGY {rpg.energy}</span></footer>
  </main>;
}
