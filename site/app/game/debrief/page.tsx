"use client";

import Image from "next/image";
import Link from "../game-link";
import { useCallback, useEffect, useState } from "react";

import { verifyArtifacts, type ObserverSnapshot } from "../../observer-data";
import { loadRpgState, pendingStoryRoute, takeRpgAction, type RpgState } from "../game-state";
import { GameHud } from "../game-hud";

const EVENT_ID = "guild-debrief-daichi";
const PREREQUISITE = "after-the-gate-aiko";
const STORY_BEATS = [
  { speaker: "DAICHI", line: "“Close the door. The official report says the corridor was stable. The floor marks say otherwise.”" },
  { speaker: "REN", line: "Ren sets his field notes beside the patrol map. Zero Rank does not appear anywhere on Daichi's forms." },
  { speaker: "DAICHI", line: "“Rank tells me what the Guild expects. Your route tells me what actually happened. Which one should I file?”" },
] as const;
const RESPONSES = [
  { id: "evidence", label: "Give Daichi the complete field record.", bond: 2, energy: -3, reply: "Daichi takes every page. “Good. If they bury this, they'll have to bury my signature too.”" },
  { id: "challenge", label: "Ask why rank matters more than survival.", bond: 1, energy: -1, reply: "Daichi does not look away. “It shouldn't. Help me prove that where they can't ignore it.”" },
  { id: "withhold", label: "Keep the Zero Rank details private.", bond: 0, energy: 2, reply: "Daichi closes the empty folder. “Your call. But secrets become terrain, and terrain gets people hurt.”" },
] as const;

export default function DebriefPage() {
  const [snapshot, setSnapshot] = useState<ObserverSnapshot | null>(null);
  const [rpg, setRpg] = useState<RpgState | null>(null);
  const [failed, setFailed] = useState(false);
  const [beat, setBeat] = useState(0);
  const [choice, setChoice] = useState<(typeof RESPONSES)[number] | null>(null);

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
    const currentBond = rpg.bonds["Daichi Mori"] ?? 0;
    const bonds = { ...rpg.bonds, "Daichi Mori": Math.min(10, currentBond + response.bond) };
    const completedEvents = [...new Set([...rpg.completedEvents, EVENT_ID])];
    setChoice(response);
    setRpg(takeRpgAction(rpg, `Guild debrief with Daichi: ${response.id}`, { energy: Math.max(0, Math.min(100, rpg.energy + response.energy)), location: "Tokyo Hunter Guild", bonds, completedEvents }));
  }, [choice, rpg]);

  const completed = rpg?.completedEvents.includes(EVENT_ID) ?? false;
  useEffect(() => {
    function handleKey(event: KeyboardEvent) {
      if (completed || choice || event.altKey || event.ctrlKey || event.metaKey) return;
      if (beat < STORY_BEATS.length && (event.key === "Enter" || event.key === " ")) { event.preventDefault(); setBeat((current) => Math.min(STORY_BEATS.length, current + 1)); return; }
      if (beat >= STORY_BEATS.length && /^Digit[1-3]$/.test(event.code)) { const response = RESPONSES[Number(event.code.at(-1)) - 1]; if (response) answer(response); }
    }
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [answer, beat, choice, completed]);

  if (failed) return <main id="chronicle" className="game-loading"><p>DEBRIEF OFFLINE</p><h1>The Guild record could not be verified.</h1><Link href="/game/evening">Return to Adachi Station</Link></main>;
  if (!snapshot || !rpg) return <main id="chronicle" className="game-loading" aria-busy="true"><p>LOADING STORY SAVE</p><h1>Opening the patrol room…</h1></main>;
  if (!rpg.completedEvents.includes(PREREQUISITE) || (!completed && pendingStoryRoute(rpg) !== "/game/debrief")) return <main id="chronicle" className="game-loading"><p>NO CANON EVENT</p><h1>The Guild has no mandatory debrief yet.</h1><Link href="/game/city">RETURN TO TOKYO</Link></main>;

  const currentBeat = STORY_BEATS[beat];
  const activeSpeaker = completed || beat >= STORY_BEATS.length ? "DAICHI" : currentBeat.speaker;
  const history = STORY_BEATS.slice(0, Math.min(beat + 1, STORY_BEATS.length));
  const bond = rpg.bonds["Daichi Mori"] ?? 0;
  const observerBond = snapshot.relationships.find((item) => item.name === "Daichi Mori");
  return <main id="chronicle" className="evening-shell">
    <header className="game-header"><Link href="/game/city">← TOKYO</Link><b>AWAKENED <i>ZERO RANK</i></b><span>CANON EVENT / THE PATROL RECORD</span></header>
    <GameHud state={rpg} current="debrief" />
    <section className="evening-stage debrief-stage"><Image className="evening-bg" src="/game/visual-novel/hunter-guild-briefing.png" alt="Illustrated Tokyo Hunter Guild patrol briefing room" fill sizes="100vw" priority /><div className="evening-shade" /><div className="vn-cast" aria-hidden="true"><Image className={`vn-character ren ${activeSpeaker === "REN" ? "speaking" : "listening"}`} src="/game/visual-novel/ren-full.png" alt="" width={512} height={768} /><Image className={`vn-character daichi ${activeSpeaker === "DAICHI" ? "speaking" : "listening"}`} src="/game/visual-novel/daichi-full.png" alt="" width={512} height={768} /></div><div className="vn-progress" aria-label={`Story beat ${Math.min(beat + 1, STORY_BEATS.length)} of ${STORY_BEATS.length}`}><i style={{ width: `${Math.min(100, ((beat + 1) / STORY_BEATS.length) * 100)}%` }} /></div><div className="social-scene"><small>TOKYO HUNTER GUILD / {rpg.slot.toUpperCase()}</small><h1>The Patrol Record.</h1>{completed && !choice ? <div className="canon-complete"><small>CANON EVENT COMPLETE</small><h2>A signature in ink.</h2><p>Ren and Daichi already settled the patrol record. Their local bond is {bond} / 10.</p><nav><Link className="primary" href="/game">RETURN HOME</Link><Link href="/game/city">OPEN TOKYO MAP</Link></nav></div> : beat < STORY_BEATS.length ? <div className="canon-beat" aria-live="polite"><small>CANON EVENT / {beat + 1} OF {STORY_BEATS.length}</small><blockquote><b>{currentBeat.speaker}</b><p>{currentBeat.line}</p></blockquote><button onClick={() => setBeat((current) => current + 1)}>{beat === STORY_BEATS.length - 1 ? "ANSWER DAICHI" : "CONTINUE"}<span>ENTER / SPACE</span></button></div> : !choice ? <><blockquote><b>DAICHI</b><p>“I can file the rank, or I can file the truth. Decide.”</p></blockquote><div className="social-choices">{RESPONSES.map((response, index) => <button key={response.id} onClick={() => answer(response)}><span>{index + 1}</span>{response.label}</button>)}</div></> : <div className="social-result" aria-live="polite"><blockquote><b>DAICHI</b><p>{choice.reply}</p></blockquote><div><span>DAICHI BOND</span><b>{bond} / 10 {choice.bond > 0 ? `(+${choice.bond})` : ""}</b><small>Observer trust remains {observerBond?.trust ?? 0}; this bond belongs only to your RPG save.</small></div><nav><Link className="primary" href="/game">END CHAPTER AT HOME</Link><Link href="/game/city">RETURN TO TOKYO</Link></nav></div>}<details className="vn-history"><summary>DIALOGUE LOG <span>{history.length}</span></summary><ol>{history.map((line, index) => <li key={`${line.speaker}-${index}`}><b>{line.speaker}</b><p>{line.line}</p></li>)}</ol></details></div></section>
    <footer className="game-footer"><b>AUTOMATIC CANON EVENT</b><p>The debrief triggers when Ren visits the Guild after Aiko&apos;s scene and consumes one time slot.</p><span>DAICHI BOND {bond} / 10</span></footer>
  </main>;
}
