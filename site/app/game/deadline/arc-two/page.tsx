/* eslint-disable react/no-unescaped-entities */
"use client";

import Image from "next/image";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { verifyArtifacts } from "../../../observer-data";
import { loadRpgState, pendingStoryRoute, remainingDaySlots, takeRpgAction, type RpgState } from "../../game-state";
import { applyGamePreferences, loadGamePreferences } from "../../game-preferences";

const EVENT_ID = "arc-ii-deadline-resolved";
const BEATS = [
  { speaker: "DISPATCH", line: "Seven synchronized breaches. North and east evacuation corridors are collapsing together." },
  { speaker: "AIKO", line: "I can keep the civilians moving, but only if you trust my route and hold the pulse away from them." },
  { speaker: "REN", line: "The fractures share one repeating vector. Residual Read can find it—but reading the live network may tear him apart." },
] as const;
type Outcome = { title: string; copy: string; success: boolean };

export default function ArcTwoDeadlinePage() {
  const [rpg, setRpg] = useState<RpgState | null>(null);
  const [beat, setBeat] = useState(0);
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    applyGamePreferences(loadGamePreferences()); const controller = new AbortController();
    async function load() { try { const options = { cache: "no-store" as RequestCache, signal: controller.signal }; const [contract, snapshot] = await Promise.all([fetch("/data/observer-contract.json", options), fetch("/data/observer-snapshot.json", options)]); if (!contract.ok || !snapshot.ok) throw new Error("artifacts unavailable"); const verified = await verifyArtifacts(await contract.json(), await snapshot.json()); const save = loadRpgState(verified.snapshot); if (pendingStoryRoute(save) !== "/game/deadline/arc-two") window.location.replace("/game"); else if (!controller.signal.aborted) setRpg(save); } catch (error) { if (!(error instanceof DOMException && error.name === "AbortError")) setFailed(true); } }
    void load(); return () => controller.abort();
  }, []);

  const resolve = useCallback((choice: "route" | "network") => {
    if (!rpg || outcome) return;
    const trusted = (rpg.bonds["Aiko Sato"] ?? 0) >= 2;
    const mastery = rpg.skillMastery["Residual Read"] ?? 0;
    const priorProof = rpg.completedEvents.includes("arc-i-authenticated-trace");
    const events = new Set(rpg.completedEvents); events.add(EVENT_ID);
    const bonds = { ...rpg.bonds };
    let health = rpg.health, energy = rpg.energy, action: string, result: Outcome;
    if (choice === "route") {
      health -= priorProof ? 10 : 15; energy -= 18;
      if (trusted) { events.add("arc-ii-evidence"); events.add("adachi-civilians-survived"); bonds["Aiko Sato"] = Math.min(10, (bonds["Aiko Sato"] ?? 0) + 2); action = "Held the pulse for Aiko's evacuation"; result = { success: true, title: "The corridors hold.", copy: "Aiko's route clears the district while Ren diverts the synchronized pulse. Survivor records authenticate the second pattern." }; }
      else { events.add("arc-ii-deadline-failed"); action = "Held one corridor without a coordinator"; result = { success: false, title: "One route survives.", copy: "Ren holds the north corridor alone. The east route collapses, and the surviving records are too incomplete to prove coordination." }; }
    } else {
      energy -= 26;
      if (mastery >= 40) { health -= priorProof ? 22 : 30; events.add("arc-ii-evidence"); events.add("synchronized-network-mapped"); action = "Read and split the synchronized Gate network"; result = { success: true, title: "Seven pulses become one map.", copy: "Ren reads the shared vector and forces the breaches out of phase. The district survives with a complete causal map." }; }
      else { health = 0; events.add("arc-ii-deadline-failed"); action = "Was consumed by the synchronized Gate network"; result = { success: false, title: "The network reads him back.", copy: "Residual Read cannot contain seven live breaches below 40% mastery. Ordinary death ends this run." }; }
    }
    setRpg(takeRpgAction(rpg, action, { health, energy, location: "Adachi Breach Corridor", bonds, completedEvents: [...events] }, remainingDaySlots(rpg))); setOutcome(result);
  }, [outcome, rpg]);

  useEffect(() => { const key = (event: KeyboardEvent) => { if (outcome || event.altKey || event.ctrlKey || event.metaKey) return; if (beat < BEATS.length && (event.key === "Enter" || event.key === " ")) { event.preventDefault(); setBeat((v) => Math.min(BEATS.length, v + 1)); } else if (event.key === "Escape") setBeat(BEATS.length); else if (beat >= BEATS.length && event.code === "Digit1") resolve("route"); else if (beat >= BEATS.length && event.code === "Digit2") resolve("network"); }; window.addEventListener("keydown", key); return () => window.removeEventListener("keydown", key); }, [beat, outcome, resolve]);
  if (failed) return <main className="game-loading"><p>DEADLINE LINK OFFLINE</p><h1>The Arc II record could not be verified.</h1><Link href="/game">Return home</Link></main>;
  if (!rpg) return <main className="game-loading" aria-busy="true"><p>DAY 120 / DISTRICT BREACH</p><h1>Opening the evacuation corridor…</h1></main>;
  const trusted = (rpg.bonds["Aiko Sato"] ?? 0) >= 2, mastery = rpg.skillMastery["Residual Read"] ?? 0, priorProof = rpg.completedEvents.includes("arc-i-authenticated-trace"), current = BEATS[Math.min(beat, BEATS.length - 1)];
  return <main className="deadline-cutscene arc-two-deadline" aria-label="Arc II Adachi Countdown deadline"><Image className="deadline-bg" src="/game/cutscenes/adachi-day120-breach-v1.png" alt="District-wide Gate breach across an Adachi evacuation corridor" fill sizes="100vw" priority /><div className="deadline-shade" aria-hidden="true" /><Image className="deadline-ren" src="/game/visual-novel/ren-full.png" alt="Ren Takahashi facing the synchronized breach" width={1024} height={1536} priority /><Image className="deadline-aiko" src="/game/visual-novel/aiko-full.png" alt="Aiko Sato coordinating the evacuation" width={1024} height={1536} priority /><header className="deadline-caption"><span>ARC II DEADLINE / DAY {rpg.day}</span><b>THE ADACHI COUNTDOWN</b><small>{priorProof ? "ARC I PROOF RETAINED" : "NO PRIOR PROOF"} · AIKO BOND {rpg.bonds["Aiko Sato"] ?? 0} · RR {mastery}%</small></header>{!outcome && beat < BEATS.length && <button className="deadline-skip" onClick={() => setBeat(BEATS.length)}>SKIP TO DECISION <span>ESC</span></button>}<section className="deadline-panel" aria-live="polite">{outcome ? <div className={`deadline-result ${outcome.success ? "success" : "failure"}`}><small>{rpg.status === "game-over" ? "GAME OVER" : "ARC II RESOLVED"}</small><h1>{outcome.title}</h1><p>{outcome.copy}</p><dl><div><dt>HP</dt><dd>{rpg.health}</dd></div><div><dt>ENERGY</dt><dd>{rpg.energy}</dd></div><div><dt>NEXT</dt><dd>{rpg.status === "game-over" ? "RETRY" : "ARC III"}</dd></div></dl><Link href="/game">{rpg.status === "game-over" ? "FACE THE CONSEQUENCE" : "CONTINUE TO ARC III"}</Link></div> : beat < BEATS.length ? <div className="deadline-beat" key={`${current.speaker}-${beat}`}><small>{current.speaker} / {beat + 1} OF {BEATS.length}</small><p>{current.line}</p><button onClick={() => setBeat((v) => v + 1)}>CONTINUE <span>ENTER / SPACE</span></button></div> : <div className="deadline-choice"><small>IRREVERSIBLE DECISION</small><h1>Seven breaches. Two ways to answer.</h1><p>Trust and mastery were built before tonight. Ren cannot create either at the deadline.</p><div><button onClick={() => resolve("route")}><b>1</b><span>HOLD AIKO'S EVACUATION ROUTE</span><small>{trusted ? "BOND READY · EVIDENCE + SURVIVORS" : "BOND BELOW 2 · PARTIAL FAILURE"}</small></button><button onClick={() => resolve("network")}><b>2</b><span>READ THE LIVE BREACH NETWORK</span><small>{mastery >= 40 ? "40% MASTERY READY · SEVERE COST" : "40% MASTERY REQUIRED · LETHAL"}</small></button></div></div>}</section></main>;
}
