"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";

import { verifyArtifacts, type ObserverSnapshot } from "../../observer-data";
import { loadRpgState, takeRpgAction, type RpgState } from "../game-state";
import { GameHud } from "../game-hud";

const MOVES = {
  strike: { label: "PRECISION STRIKE", damage: 24, cost: 5, retaliation: 8, note: "Ren cuts through the nearest fracture before it can reform." },
  pulse: { label: "BARRIER PULSE", damage: 17, cost: 12, retaliation: 3, note: "Zero Rank folds the Gate pressure back against its source." },
  guard: { label: "GUARD & READ", damage: 9, cost: 2, retaliation: 1, note: "Ren gives ground, reads the pattern, then answers safely." },
} as const;

type MoveId = keyof typeof MOVES;
type Battle = { enemyHp: number; round: number; log: string[]; resolved: "victory" | "retreat" | null };

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

  function act(id: MoveId) {
    if (!rpg || battle.resolved) return;
    const move = MOVES[id];
    if (rpg.energy < move.cost) return;
    const enemyHp = Math.max(0, battle.enemyHp - move.damage);
    const health = Math.max(0, rpg.health - (enemyHp === 0 ? 0 : move.retaliation));
    const energy = Math.max(0, rpg.energy - move.cost);
    if (enemyHp === 0) {
      setRpg(takeRpgAction({ ...rpg, health, energy }, "Cleared the fracture sentinel", { health, energy, money: rpg.money + 1800, location: "Glass Office Labyrinth" }));
      setBattle((current) => ({ ...current, enemyHp, log: [...current.log, move.note, "The sentinel collapses. The corridor stabilizes."], resolved: "victory" }));
    } else if (health === 0) {
      setRpg(takeRpgAction({ ...rpg, health: 20, energy }, "Retreated from the fracture sentinel", { health: 20, energy, location: "Adachi Gate Zone" }));
      setBattle((current) => ({ ...current, enemyHp, log: [...current.log, move.note, "Ren breaks contact before the Gate can close behind him."], resolved: "retreat" }));
    } else {
      setRpg({ ...rpg, health, energy });
      setBattle((current) => ({ enemyHp, round: current.round + 1, log: [...current.log, move.note].slice(-4), resolved: null }));
    }
  }

  function retreat() {
    if (!rpg || battle.resolved) return;
    setRpg(takeRpgAction(rpg, "Withdrew from the fracture sentinel", { energy: Math.max(0, rpg.energy - 2), location: "Adachi Gate Zone" }));
    setBattle((current) => ({ ...current, log: [...current.log, "Ren marks the pattern and withdraws before the corridor seals."], resolved: "retreat" }));
  }

  if (failed) return <main id="chronicle" className="game-loading"><p>FIELD LINK OFFLINE</p><h1>The Gate could not be verified.</h1><Link href="/game/caseboard">Return to caseboard</Link></main>;
  if (!snapshot || !rpg) return <main id="chronicle" className="game-loading" aria-busy="true"><p>LOADING FIELD SAVE</p><h1>Opening the Gate…</h1></main>;

  const caseFile = snapshot.portals.investigations[0];
  return <main id="chronicle" className="field-shell">
    <header className="game-header"><Link href="/game/caseboard">← CASEBOARD</Link><b>AWAKENED <i>ZERO RANK</i></b><span>CHAPTER 04 / FIRST CONTACT</span></header>
    <GameHud state={rpg} current="field" />
    <section className="field-intro"><small>{caseFile?.portal_name ?? "VERIFIED GATE"} / RISK {caseFile?.risk ?? "UNKNOWN"}</small><h1>Hold the line.</h1><p>Battle moves are tactical turns. The RPG clock advances once when Ren wins or retreats.</p></section>
    <section className="field-stage" aria-label="Gate battle">
      <div className="field-arena"><Image src="/game/maps/adachi-fringe.png" alt="Pixel-art Gate exclusion zone" fill sizes="(max-width: 800px) 100vw, 70vw" priority /><div className="field-shade" /><span className="field-ren"><Image src="/game/characters/ren.png" alt="Pixel sprite of Ren Takahashi" width={96} height={96} /><b>REN</b></span><span className="field-enemy" aria-label="Fracture sentinel"><i /><i /><i /><b>FRACTURE SENTINEL</b></span></div>
      <aside className="battle-panel" aria-live="polite"><div className="battle-bars"><span>REN / HP {rpg.health}</span><meter min="0" max="100" value={rpg.health} /><span>SENTINEL / HP {battle.enemyHp}</span><meter min="0" max="60" value={battle.enemyHp} /></div><small>ROUND {battle.round}</small><p>{battle.log.at(-1)}</p>{!battle.resolved ? <div className="battle-actions">{Object.entries(MOVES).map(([id, move]) => <button key={id} disabled={rpg.energy < move.cost} onClick={() => act(id as MoveId)}><b>{move.label}</b><span>{move.damage} DMG / {move.cost} EN</span></button>)}<button className="retreat" onClick={retreat}><b>TACTICAL RETREAT</b><span>2 EN / SAFE EXIT</span></button></div> : <div className={`battle-result ${battle.resolved}`}><small>{battle.resolved === "victory" ? "GATE SECURED" : "TACTICAL RETREAT"}</small><h2>{battle.resolved === "victory" ? "+¥1,800 / TIME ADVANCED" : "REN SURVIVED / TIME ADVANCED"}</h2><nav><Link href="/game/caseboard">REVIEW CASEBOARD</Link><Link href="/game/city">RETURN TO TOKYO</Link></nav></div>}</aside>
    </section>
    <footer className="game-footer"><b>DETERMINISTIC FIELD ENCOUNTER</b><p>No random rolls. Every move shows its exact cost and effect.</p><span>ENERGY {rpg.energy}</span></footer>
  </main>;
}
