"use client";

import Image from "next/image";
import Link from "../game-link";
import { useCallback, useEffect, useState } from "react";

import { verifyArtifacts, type ObserverSnapshot } from "../../observer-data";
import { loadRpgState, pendingStoryRoute, saveRpgState, type RpgState } from "../game-state";
import { applyGamePreferences, loadGamePreferences } from "../game-preferences";

const EVENT_ID = "worthless-awakening-intro";

export const SHOT_MANIFEST = [
  { id: "establishing", label: "TOKYO AWAKENING BUREAU / DAY 1", speaker: "", line: "Assessment Chamber 04. Rain presses against reinforced glass.", camera: "wide", ren: false },
  { id: "scan", label: "ABILITY ASSESSMENT", speaker: "BUREAU SYSTEM", line: "Resonance detected. Output remains below the registered combat threshold.", camera: "scanner", ren: false },
  { id: "result", label: "CLASSIFICATION COMPLETE", speaker: "BUREAU SYSTEM", line: "ABILITY: RESIDUAL READ. RANK: ZERO.", camera: "result", ren: true },
  { id: "meaning", label: "PROVISIONAL RANK / F", speaker: "REN", line: "So it only tells me what already happened.", camera: "ren", ren: true },
  { id: "verdict", label: "ASSESSMENT CLOSED", speaker: "ASSESSOR", line: "Correct. No combat application. Report to the Hunter Guild if you still intend to register.", camera: "assessor", ren: true },
  { id: "resolve", label: "ARC I / WORTHLESS AWAKENING", speaker: "REN", line: "Worthless is still more than nothing. I just need to survive long enough to understand it.", camera: "resolve", ren: true },
] as const;

export default function AwakeningPage() {
  const [rpg, setRpg] = useState<RpgState | null>(null);
  const [shot, setShot] = useState(0);
  const [failed, setFailed] = useState(false);
  const current = SHOT_MANIFEST[shot];

  useEffect(() => {
    applyGamePreferences(loadGamePreferences());
    const controller = new AbortController();
    async function load() {
      try {
        const options = { cache: "no-store" as RequestCache, signal: controller.signal };
        const [contract, snapshot] = await Promise.all([
          fetch("/data/observer-contract.json", options),
          fetch("/data/observer-snapshot.json", options),
        ]);
        if (!contract.ok || !snapshot.ok) throw new Error("artifacts unavailable");
        const verified = await verifyArtifacts(await contract.json(), await snapshot.json());
        const save = loadRpgState(verified.snapshot as ObserverSnapshot);
        if (pendingStoryRoute(save) !== "/game/awakening") window.location.replace("/game");
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
    const completedEvents = [...new Set([...rpg.completedEvents, EVENT_ID])];
    saveRpgState({ ...rpg, completedEvents, lastAction: "Awakened with Residual Read" });
    window.location.assign("/game");
  }, [rpg]);

  const advance = useCallback(() => {
    if (shot >= SHOT_MANIFEST.length - 1) finish();
    else setShot((value) => value + 1);
  }, [finish, shot]);

  useEffect(() => {
    const keydown = (event: KeyboardEvent) => {
      if (event.altKey || event.ctrlKey || event.metaKey) return;
      if (event.key === "Enter" || event.key === " ") { event.preventDefault(); advance(); }
      if (event.key === "Escape") finish();
    };
    window.addEventListener("keydown", keydown);
    return () => window.removeEventListener("keydown", keydown);
  }, [advance, finish]);

  if (failed) return <main className="game-loading"><p>CINEMATIC LINK OFFLINE</p><h1>The assessment record could not be verified.</h1><Link href="/game">Return home</Link></main>;
  if (!rpg) return <main className="game-loading" aria-busy="true"><p>DAY 1 / FIRST TIMELINE</p><h1>Opening the assessment record…</h1></main>;

  return <main className={`awakening-cutscene shot-${current.camera}`} aria-label="Day One awakening cutscene">
    <Image className="awakening-bg" src="/game/cutscenes/awakening-bureau-establishing-v1.png" alt="Rainy Tokyo Awakening Bureau assessment chamber" fill sizes="100vw" priority />
    <div className="awakening-camera" aria-hidden="true" />
    <div className="awakening-scan" aria-hidden="true" />
    {current.ren && <Image className="awakening-ren" src="/game/visual-novel/ren-full.png" alt="Ren Takahashi awaiting his assessment result" width={1024} height={1536} priority />}
    <div className="cinematic-bars" aria-hidden="true" />
    <header className="cinematic-caption"><span>FIRST TIMELINE</span><b>{current.label}</b></header>
    <button className="cinematic-skip" onClick={finish}>SKIP <span>ESC</span></button>
    <section className="cinematic-dialogue" aria-live="polite" key={current.id}>
      {current.speaker && <small>{current.speaker}</small>}
      <p>{current.line}</p>
      <button onClick={advance}>{shot === SHOT_MANIFEST.length - 1 ? "BEGIN ARC I" : "CONTINUE"}<span>ENTER / SPACE</span></button>
    </section>
    <nav className="cinematic-progress" aria-label={`Shot ${shot + 1} of ${SHOT_MANIFEST.length}`}>
      {SHOT_MANIFEST.map((item, index) => <i className={index <= shot ? "seen" : ""} key={item.id} />)}
    </nav>
  </main>;
}
