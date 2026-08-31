"use client";

import Image from "next/image";
import Link from "../../game-link";
import { useCallback, useEffect, useState } from "react";

import { verifyArtifacts } from "../../../observer-data";
import { loadRpgState, pendingStoryRoute, saveRpgState, type RpgState } from "../../game-state";
import { applyGamePreferences, loadGamePreferences } from "../../game-preferences";

const EVENT_ID = "second-awakening-intro";
export const SECOND_AWAKENING_SHOTS = [
  { speaker: "", label: "FIRST TRANSMIGRATION / DAY 1", line: "Ren wakes beneath the same Bureau lights, carrying a year nobody else remembers.", camera: "wide" },
  { speaker: "BUREAU SYSTEM", label: "REASSESSMENT IN PROGRESS", line: "Residual signature retained. A second resonance is forming along the subject's movement vectors.", camera: "scanner" },
  { speaker: "REN", label: "RESIDUAL READ / MASTERED", line: "I know where the chain breaks now. Knowing isn't enough if I can't reach it in time.", camera: "ren" },
  { speaker: "BUREAU SYSTEM", label: "SECOND AWAKENING CONFIRMED", line: "NEW ABILITY: VECTOR STEP. Provisional combat classification approved.", camera: "result" },
  { speaker: "REN", label: "SECOND TIMELINE", line: "One year of answers. One new way to arrive before the damage is done.", camera: "resolve" },
] as const;

export default function SecondAwakeningPage() {
  const [rpg, setRpg] = useState<RpgState | null>(null);
  const [shot, setShot] = useState(0);
  const [failed, setFailed] = useState(false);
  const current = SECOND_AWAKENING_SHOTS[shot];

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
        if (pendingStoryRoute(save) !== "/game/awakening/second") window.location.replace("/game");
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
    saveRpgState({ ...rpg, completedEvents: [...new Set([...rpg.completedEvents, EVENT_ID])], lastAction: "Second awakening: Vector Step" });
    window.location.assign("/game");
  }, [rpg]);
  const advance = useCallback(() => shot === SECOND_AWAKENING_SHOTS.length - 1 ? finish() : setShot((value) => value + 1), [finish, shot]);

  useEffect(() => {
    const keydown = (event: KeyboardEvent) => {
      if (event.altKey || event.ctrlKey || event.metaKey) return;
      if (event.key === "Enter" || event.key === " ") { event.preventDefault(); advance(); }
      if (event.key === "Escape") finish();
    };
    window.addEventListener("keydown", keydown);
    return () => window.removeEventListener("keydown", keydown);
  }, [advance, finish]);

  if (failed) return <main className="game-loading"><p>REASSESSMENT LINK OFFLINE</p><h1>The second awakening could not be verified.</h1><Link href="/game">Return home</Link></main>;
  if (!rpg) return <main className="game-loading" aria-busy="true"><p>SECOND TIMELINE / DAY 1</p><h1>Reading a new movement resonance…</h1></main>;
  return <main className={`awakening-cutscene second-awakening shot-${current.camera}`} aria-label="Ren's second awakening cutscene">
    <Image className="awakening-bg" src="/game/cutscenes/awakening-bureau-establishing-v1.png" alt="Tokyo Awakening Bureau assessment chamber after Ren's first transmigration" fill sizes="100vw" priority />
    <div className="awakening-camera" aria-hidden="true" /><div className="awakening-scan" aria-hidden="true" /><div className="vector-step-trace" aria-hidden="true"><i /><i /><i /></div>
    {shot >= 2 && <Image className="awakening-ren" src="/game/visual-novel/ren-full.png" alt="Ren Takahashi during his second awakening" width={1024} height={1536} priority />}
    <div className="cinematic-bars" aria-hidden="true" />
    <header className="cinematic-caption"><span>SECOND AWAKENING</span><b>{current.label}</b></header>
    <button className="cinematic-skip" onClick={finish}>SKIP <span>ESC</span></button>
    <section className="cinematic-dialogue" aria-live="polite" key={`${current.label}-${shot}`}>{current.speaker && <small>{current.speaker}</small>}<p>{current.line}</p><button onClick={advance}>{shot === SECOND_AWAKENING_SHOTS.length - 1 ? "BEGIN SECOND TIMELINE" : "CONTINUE"}<span>ENTER / SPACE</span></button></section>
    <nav className="cinematic-progress" aria-label={`Shot ${shot + 1} of ${SECOND_AWAKENING_SHOTS.length}`}>{SECOND_AWAKENING_SHOTS.map((item, index) => <i className={index <= shot ? "seen" : ""} key={item.label} />)}</nav>
  </main>;
}
