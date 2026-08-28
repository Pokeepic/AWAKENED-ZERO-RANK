"use client";

import Image from "next/image";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { verifyArtifacts, type ObserverSnapshot } from "../../observer-data";
import { loadRpgState, takeRpgAction, type RpgState } from "../game-state";
import { GameHud } from "../game-hud";

const RESPONSES = [
  { id: "honest", label: "Tell Aiko the Gate frightened you.", bond: 2, energy: 4, reply: "Aiko lowers her voice. “Good. Fear means you're still measuring the cost. You don't have to carry it alone.”" },
  { id: "steady", label: "Say the mission went according to plan.", bond: 1, energy: 2, reply: "Aiko studies Ren for a moment, then nods. “Then let me help with the next plan. No disappearing.”" },
  { id: "distance", label: "Change the subject and head home.", bond: 0, energy: 8, reply: "Aiko lets the silence stand. “All right. But I'm keeping the light on if you change your mind.”" },
] as const;

const EVENT_ID = "after-the-gate-aiko";
const STORY_BEATS = [
  { speaker: "REN", line: "The Gate is gone, but its pressure still follows Ren into the station lights." },
  { speaker: "AIKO", line: "“Ren.” Aiko steps away from the ticket machines. “You missed two messages.”" },
  { speaker: "REN", line: "He reaches for an easy answer, then stops. What he says next will be his choice." },
] as const;

export default function EveningPage() {
  const [snapshot, setSnapshot] = useState<ObserverSnapshot | null>(null);
  const [rpg, setRpg] = useState<RpgState | null>(null);
  const [failed, setFailed] = useState(false);
  const [choice, setChoice] = useState<(typeof RESPONSES)[number] | null>(null);
  const [beat, setBeat] = useState(0);

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

  const answer = useCallback((response: (typeof RESPONSES)[number]) => {
    if (!rpg || choice) return;
    const currentBond = rpg.bonds["Aiko Sato"] ?? 0;
    const bonds = { ...rpg.bonds, "Aiko Sato": Math.min(10, currentBond + response.bond) };
    const completedEvents = [...new Set([...rpg.completedEvents, EVENT_ID])];
    setChoice(response);
    setRpg(takeRpgAction(rpg, `Evening with Aiko: ${response.id}`, { energy: Math.min(100, rpg.energy + response.energy), location: "Adachi Station", bonds, completedEvents }));
  }, [choice, rpg]);

  const eventCompleted = rpg?.completedEvents.includes(EVENT_ID) ?? false;
  useEffect(() => {
    function handleKey(event: KeyboardEvent) {
      if (eventCompleted || choice || event.altKey || event.ctrlKey || event.metaKey) return;
      if (beat < STORY_BEATS.length && (event.key === "Enter" || event.key === " ")) {
        event.preventDefault();
        setBeat((current) => Math.min(STORY_BEATS.length, current + 1));
        return;
      }
      if (beat >= STORY_BEATS.length && /^Digit[1-3]$/.test(event.code)) {
        const response = RESPONSES[Number(event.code.at(-1)) - 1];
        if (response) answer(response);
      }
    }
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [answer, beat, choice, eventCompleted]);

  if (failed) return <main id="chronicle" className="game-loading"><p>EVENING LINK OFFLINE</p><h1>The scene could not be verified.</h1><Link href="/game/field">Return to Gate field</Link></main>;
  if (!snapshot || !rpg) return <main id="chronicle" className="game-loading" aria-busy="true"><p>LOADING EVENING SAVE</p><h1>Waiting at Adachi Station…</h1></main>;

  const observerBond = snapshot.relationships.find((item) => item.name === "Aiko Sato");
  const bond = rpg.bonds["Aiko Sato"] ?? 0;
  const completed = eventCompleted;
  const currentBeat = STORY_BEATS[beat];
  const activeSpeaker = completed || beat >= STORY_BEATS.length ? "AIKO" : currentBeat.speaker;
  const history = STORY_BEATS.slice(0, Math.min(beat + 1, STORY_BEATS.length));
  return <main id="chronicle" className="evening-shell">
    <header className="game-header"><Link href="/game/field">← GATE FIELD</Link><b>AWAKENED <i>ZERO RANK</i></b><span>CHAPTER 05 / AFTER THE GATE</span></header>
    <GameHud state={rpg} current="evening" />
    <section className="evening-stage"><Image className="evening-bg" src="/game/visual-novel/adachi-station-dusk.png" alt="Illustrated Adachi Station concourse at dusk" fill sizes="100vw" priority /><div className="evening-shade" /><div className="vn-cast" aria-hidden="true"><Image className={`vn-character ren ${activeSpeaker === "REN" ? "speaking" : "listening"}`} src="/game/visual-novel/ren-full.png" alt="" width={512} height={768} /><Image className={`vn-character aiko ${activeSpeaker === "AIKO" ? "speaking" : "listening"}`} src="/game/visual-novel/aiko-full.png" alt="" width={512} height={768} /></div><div className="vn-progress" aria-label={`Story beat ${Math.min(beat + 1, STORY_BEATS.length)} of ${STORY_BEATS.length}`}><i style={{ width: `${Math.min(100, ((beat + 1) / STORY_BEATS.length) * 100)}%` }} /></div><div className="social-scene"><small>ADACHI STATION / {rpg.slot.toUpperCase()}</small><h1>After the Gate.</h1>{completed && !choice ? <div className="canon-complete"><small>CANON EVENT COMPLETE</small><h2>A light left on.</h2><p>Ren and Aiko already shared this evening. Their local bond is {bond} / 10.</p><nav><Link className="primary" href="/game/debrief">CONTINUE TO GUILD DEBRIEF</Link><Link href="/game">RETURN HOME</Link><Link href="/game/city">OPEN TOKYO MAP</Link></nav></div> : beat < STORY_BEATS.length ? <div className="canon-beat" aria-live="polite"><small>CANON EVENT / {beat + 1} OF {STORY_BEATS.length}</small><blockquote><b>{currentBeat.speaker}</b><p>{currentBeat.line}</p></blockquote><button onClick={() => setBeat((current) => current + 1)}>{beat === STORY_BEATS.length - 1 ? "ANSWER AIKO" : "CONTINUE"}<span>ENTER / SPACE</span></button></div> : !choice ? <><blockquote><b>AIKO</b><p>“You came back quieter than you left. Do you want to tell me what happened?”</p></blockquote><div className="social-choices">{RESPONSES.map((response, index) => <button key={response.id} onClick={() => answer(response)}><span>{index + 1}</span>{response.label}</button>)}</div></> : <div className="social-result" aria-live="polite"><blockquote><b>AIKO</b><p>{choice.reply}</p></blockquote><div><span>AIKO BOND</span><b>{bond} / 10 {choice.bond > 0 ? `(+${choice.bond})` : ""}</b><small>Observer trust remains {observerBond?.trust ?? 0}; this bond belongs only to your RPG save.</small></div><nav><Link className="primary" href="/game/debrief">CONTINUE TO GUILD DEBRIEF</Link><Link href="/game">END CHAPTER AT HOME</Link><Link href="/game/city">RETURN TO TOKYO</Link></nav></div>}<details className="vn-history"><summary>DIALOGUE LOG <span>{history.length}</span></summary><ol>{history.map((line, index) => <li key={`${line.speaker}-${index}`}><b>{line.speaker}</b><p>{line.line}</p></li>)}</ol></details></div></section>
    <footer className="game-footer"><b>PLAYER-DIRECTED SOCIAL LINK</b><p>Dialogue changes the local RPG bond and advances one time slot.</p><span>AIKO BOND {bond} / 10</span></footer>
  </main>;
}
