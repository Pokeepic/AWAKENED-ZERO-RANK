"use client";

import Image from "next/image";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { verifyArtifacts, type ObserverSnapshot } from "../../observer-data";
import { loadRpgState, takeRpgAction, type RpgState } from "../game-state";
import { GameHud } from "../game-hud";

type MoveId = "strike" | "pulse" | "guard" | "vector" | "sever";
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

type Battle = { enemyHp: number; round: number; log: string[]; resolved: "victory" | "retreat" | "death" | null };

export default function FieldPage() {
  const [snapshot, setSnapshot] = useState<ObserverSnapshot | null>(null);
  const [rpg, setRpg] = useState<RpgState | null>(null);
  const [failed, setFailed] = useState(false);
  const [battle, setBattle] = useState<Battle>({ enemyHp: 60, round: 1, log: ["A fracture sentinel blocks the inner corridor."], resolved: null });

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
  const intent = INTENTS[(battle.round - 1) % INTENTS.length];
  const moveReady = useCallback((move: Move) => Boolean(rpg && rpg.energy >= move.cost && (!move.skill || (rpg.skillMastery[move.skill] ?? 0) >= (move.requiredMastery ?? 0))), [rpg]);

  const act = useCallback((id: MoveId) => {
    if (!rpg || battle.resolved) return;
    const move = moves.find((candidate) => candidate.id === id);
    if (!move || !moveReady(move)) return;
    const dealt = move.damage + intent.exposure;
    const enemyHp = Math.max(0, battle.enemyHp - dealt);
    const incoming = enemyHp === 0 ? 0 : Math.max(0, intent.damage - move.mitigation);
    const health = Math.max(0, rpg.health - incoming);
    const energy = Math.max(0, rpg.energy - move.cost);
    if (enemyHp === 0) {
      const skillMastery = { ...rpg.skillMastery, "Residual Read": Math.min(100, (rpg.skillMastery["Residual Read"] ?? 0) + 12) };
      const next = takeRpgAction({ ...rpg, health, energy }, "Cleared the fracture sentinel", { health, energy, money: rpg.money + 1800, location: "Glass Office Labyrinth", skillMastery });
      setRpg(next);
      setBattle((current) => ({ ...current, enemyHp, log: [...current.log, `${move.note} ${dealt} damage.`, "The sentinel collapses. The corridor stabilizes."], resolved: "victory" }));
    } else if (health === 0) {
      const next = takeRpgAction({ ...rpg, health, energy }, "Fell to the fracture sentinel", { health, energy, location: "Glass Office Labyrinth" });
      setRpg(next);
      setBattle((current) => ({ ...current, enemyHp, log: [...current.log, `${move.note} ${intent.label} deals ${incoming} damage.`, "The corridor closes. No residual path answers Ren."], resolved: "death" }));
    } else {
      setRpg({ ...rpg, health, energy });
      setBattle((current) => ({ enemyHp, round: current.round + 1, log: [...current.log, `${move.note} ${dealt} dealt; ${intent.label} answers for ${incoming}.`].slice(-4), resolved: null }));
    }
  }, [battle.enemyHp, battle.resolved, intent, moveReady, moves, rpg]);

  const retreat = useCallback(() => {
    if (!rpg || battle.resolved) return;
    const skillMastery = { ...rpg.skillMastery, "Residual Read": Math.min(100, (rpg.skillMastery["Residual Read"] ?? 0) + 5) };
    const next = takeRpgAction(rpg, "Withdrew from the fracture sentinel", { energy: Math.max(0, rpg.energy - 2), location: "Adachi Gate Zone", skillMastery });
    setRpg(next);
    setBattle((current) => ({ ...current, log: [...current.log, "Ren marks the pattern and withdraws before the corridor seals."], resolved: "retreat" }));
  }, [battle.resolved, rpg]);

  useEffect(() => {
    function handleKey(event: KeyboardEvent) {
      if (battle.resolved || event.altKey || event.ctrlKey || event.metaKey) return;
      if (/^Digit[1-5]$/.test(event.code)) {
        const move = moves[Number(event.code.at(-1)) - 1];
        if (move) act(move.id);
      } else if (event.key.toLowerCase() === "r") retreat();
    }
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [act, battle.resolved, moves, retreat]);

  if (failed) return <main id="chronicle" className="game-loading"><p>FIELD LINK OFFLINE</p><h1>The Gate could not be verified.</h1><Link href="/game/caseboard">Return to caseboard</Link></main>;
  if (!snapshot || !rpg) return <main id="chronicle" className="game-loading" aria-busy="true"><p>LOADING FIELD SAVE</p><h1>Opening the Gate…</h1></main>;

  const caseFile = snapshot.portals.investigations[0];
  return <main id="chronicle" className="field-shell">
    <header className="game-header"><Link href="/game/caseboard">← CASEBOARD</Link><b>AWAKENED <i>ZERO RANK</i></b><span>CHAPTER 04 / FIRST CONTACT</span></header>
    <GameHud state={rpg} current="field" />
    <section className="field-intro"><small>{caseFile?.portal_name ?? "VERIFIED GATE"} / RISK {caseFile?.risk ?? "UNKNOWN"}</small><h1>Hold the line.</h1><p>Battle moves are tactical turns. The RPG clock advances once when the encounter resolves.</p></section>
    <section className="field-stage" aria-label="Gate battle">
      <div className={`field-arena intent-${intent.id}`}><Image src="/game/maps/adachi-fringe.png" alt="Pixel-art Gate exclusion zone" fill sizes="(max-width: 800px) 100vw, 70vw" priority /><div className="field-shade" /><span className="field-ren"><Image src="/game/characters/ren.png" alt="Pixel sprite of Ren Takahashi" width={96} height={96} /><b>REN</b></span><span className="field-enemy" aria-label="Fracture sentinel"><i /><i /><i /><b>FRACTURE SENTINEL</b></span><div className="enemy-intent"><small>NEXT ATTACK / {intent.label}</small><b>{intent.damage} DAMAGE</b><p>{intent.cue}</p></div></div>
      <aside className="battle-panel" aria-live="polite"><div className="battle-bars"><span>REN / HP {rpg.health}</span><meter min="0" max="100" value={rpg.health} /><span>SENTINEL / HP {battle.enemyHp}</span><meter min="0" max="60" value={battle.enemyHp} /></div><small>ROUND {battle.round} / TELEGRAPH LOCKED</small><p>{battle.log.at(-1)}</p>{!battle.resolved ? <div className="battle-actions">{moves.map((move, index) => { const ready = moveReady(move); const dealt = move.damage + intent.exposure; const incoming = Math.max(0, intent.damage - move.mitigation); return <button key={move.id} disabled={!ready} onClick={() => act(move.id)}><b>{index + 1} · {move.label}</b><span>{ready ? `${dealt} DMG / ${move.cost} EN / TAKE ${incoming}` : move.skill ? `${move.skill.toUpperCase()} ${move.requiredMastery}% REQUIRED` : `${move.cost} ENERGY REQUIRED`}</span></button>; })}<button className="retreat" onClick={retreat}><b>R · TACTICAL RETREAT</b><span>2 EN / SAFE EXIT</span></button></div> : <div className={`battle-result ${battle.resolved}`}><small>{battle.resolved === "victory" ? "GATE SECURED" : battle.resolved === "death" ? "RUN TERMINATED" : "TACTICAL RETREAT"}</small><h2>{battle.resolved === "victory" ? "+¥1,800 / TIME ADVANCED" : battle.resolved === "death" ? "GAME OVER" : "REN SURVIVED / TIME ADVANCED"}</h2><p>{battle.resolved === "death" ? "Only the final day can open a path to transmigration." : "A canon event has triggered. Aiko is waiting at Adachi Station…"}</p></div>}</aside>
    </section>
    <footer className="game-footer"><b>DETERMINISTIC FIELD ENCOUNTER</b><p>No random rolls. Every move shows its exact cost and effect.</p><span>ENERGY {rpg.energy}</span></footer>
  </main>;
}
