"use client";

import Image from "next/image";
import Link from "../../game-link";
import { useCallback, useEffect, useState } from "react";

import { verifyArtifacts } from "../../../observer-data";
import { loadRpgState, pendingStoryRoute, saveRpgState, type RpgState } from "../../game-state";
import { applyGamePreferences, loadGamePreferences } from "../../game-preferences";

const EVENT_ID = "third-awakening-intro";
export const FINAL_AWAKENING_SHOTS = [
  { speaker: "", label: "SECOND TRANSMIGRATION / DAY 1", line: "The Bureau chamber is unchanged. Ren is not.", camera: "wide" },
  { speaker: "BUREAU SYSTEM", label: "REASSESSMENT IN PROGRESS", line: "Three incompatible resonance signatures detected in one awakened subject.", camera: "scanner" },
  { speaker: "REN", label: "RESIDUAL READ / VECTOR STEP", line: "First I learned to see the chain. Then I learned to move between its links.", camera: "ren" },
  { speaker: "BUREAU SYSTEM", label: "THIRD AWAKENING CONFIRMED", line: "NEW ABILITY: CAUSAL SEVER. Classification cannot be assigned.", camera: "result" },
  { speaker: "REN", label: "FINAL TIMELINE", line: "One severed cause. One consequence denied. There won't be a fourth chance, so this one has to be enough.", camera: "resolve" },
] as const;

export default function FinalAwakeningPage() {
  const [rpg, setRpg] = useState<RpgState | null>(null);
  const [shot, setShot] = useState(0);
  const [failed, setFailed] = useState(false);
  const current = FINAL_AWAKENING_SHOTS[shot];

  useEffect(() => {
    applyGamePreferences(loadGamePreferences());
    const controller = new AbortController();
    async function load() {
      try {
        const options = { cache: "no-store" as RequestCache, signal: controller.signal };
        const [contract, snapshot] = await Promise.all([fetch("/data/observer-contract.json", options), fetch("/data/observer-snapshot.json", options)]);
        if (!contract.ok || !snapshot.ok) throw new Error("artifacts unavailable");
        const verified = await verifyArtifacts(await contract.json(), await snapshot.json());
        const save = loadRpgState(verified.snapshot);
        if (pendingStoryRoute(save) !== "/game/awakening/final") window.location.replace("/game");
        else if (!controller.signal.aborted) setRpg(save);
      } catch (error) {
        if (!(error instanceof DOMException && error.name === "AbortError")) setFailed(true);
      }
    }
    void load();
    return () => controller.abort();
  }, []);

  const finish = useCallback(() => {
    if (!rpg) return;
    saveRpgState({ ...rpg, completedEvents: [...new Set([...rpg.completedEvents, EVENT_ID])], lastAction: "Third awakening: Causal Sever" });
    window.location.assign("/game");
  }, [rpg]);
  const advance = useCallback(() => shot === FINAL_AWAKENING_SHOTS.length - 1 ? finish() : setShot((value) => value + 1), [finish, shot]);

  useEffect(() => {
    const keydown = (event: KeyboardEvent) => {
      if (event.altKey || event.ctrlKey || event.metaKey) return;
      if (event.key === "Enter" || event.key === " ") { event.preventDefault(); advance(); }
      if (event.key === "Escape") finish();
    };
    window.addEventListener("keydown", keydown);
    return () => window.removeEventListener("keydown", keydown);
  }, [advance, finish]);

  if (failed) return <main className="game-loading"><p>REASSESSMENT LINK OFFLINE</p><h1>The third awakening could not be verified.</h1><Link href="/game">Return home</Link></main>;
  if (!rpg) return <main className="game-loading" aria-busy="true"><p>FINAL TIMELINE / DAY 1</p><h1>Reading three resonance signatures…</h1></main>;
  return <main className={`awakening-cutscene final-awakening shot-${current.camera}`} aria-label="Ren's third awakening cutscene">
    <Image className="awakening-bg" src="/game/cutscenes/awakening-bureau-establishing-v1.png" alt="Tokyo Awakening Bureau assessment chamber on the final timeline" fill sizes="100vw" priority />
    <div className="awakening-camera" aria-hidden="true" /><div className="awakening-scan" aria-hidden="true" /><div className="causal-sever" aria-hidden="true" />
    {shot >= 2 && <Image className="awakening-ren" src="/game/visual-novel/ren-full.png" alt="Ren Takahashi during his third awakening" width={1024} height={1536} priority />}
    <div className="cinematic-bars" aria-hidden="true" />
    <header className="cinematic-caption"><span>THIRD AWAKENING</span><b>{current.label}</b></header>
    <button className="cinematic-skip" onClick={finish}>SKIP <span>ESC</span></button>
    <section className="cinematic-dialogue" aria-live="polite" key={`${current.label}-${shot}`}>{current.speaker && <small>{current.speaker}</small>}<p>{current.line}</p><button onClick={advance}>{shot === FINAL_AWAKENING_SHOTS.length - 1 ? "BEGIN FINAL TIMELINE" : "CONTINUE"}<span>ENTER / SPACE</span></button></section>
    <nav className="cinematic-progress" aria-label={`Shot ${shot + 1} of ${FINAL_AWAKENING_SHOTS.length}`}>{FINAL_AWAKENING_SHOTS.map((item, index) => <i className={index <= shot ? "seen" : ""} key={item.label} />)}</nav>
  </main>;
}
