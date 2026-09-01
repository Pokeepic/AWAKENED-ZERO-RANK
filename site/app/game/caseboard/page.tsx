/* eslint-disable react/no-unescaped-entities */
"use client";

import Link from "../game-link";
import Image from "next/image";
import { useEffect, useRef, useState } from "react";

import { gateReadiness, verifyArtifacts, type ObserverSnapshot } from "../../observer-data";
import { loadRpgState, takeRpgAction, type RpgState } from "../game-state";
import { GameHud } from "../game-hud";
import { adachiMapImage, gameAtmosphere } from "../game-weather";

const CASE_ART: Record<string, string> = {
  "Glass Office Labyrinth": "/game/cases/glass-office-labyrinth.png",
  "Sunken Courtyard": "/game/cases/sunken-courtyard.png",
};

const RECOMMENDATIONS = [
  { id: "prepare", label: "Prepare before committing", tone: "DISCIPLINE" },
  { id: "investigate", label: "Investigate the weaker signal", tone: "CURIOSITY" },
  { id: "rush", label: "Enter before the signal shifts", tone: "RISK" },
] as const;

function renResponse(snapshot: ObserverSnapshot, recommendation: string) {
  const readiness = gateReadiness(snapshot);
  if (recommendation === "prepare") return readiness.supplyCount > 0
    ? `Ren checks ${readiness.supplyCount} field supply${readiness.supplyCount === 1 ? "" : "ies"}. “Preparation first. Then I enter on my terms.”`
    : "Ren closes the file. “I need field supplies before I commit.”";
  if (recommendation === "investigate") {
    const lowest = [...snapshot.portals.investigations].sort((a, b) => a.risk - b.risk || a.portal_name.localeCompare(b.portal_name))[0];
    return lowest ? `Ren circles ${lowest.portal_name}, risk ${lowest.risk}. “That's the weaker signal. I'll scout its perimeter.”` : "Ren finds no authenticated Gate file to follow. “Then there is nothing to investigate.”";
  }
  return `Ren closes the file and checks the Gate alert at ${snapshot.environment.gate_alert_level}. “If the signal shifts, the route closes. I move now.”`;
}

export default function CaseboardPage() {
  const [snapshot, setSnapshot] = useState<ObserverSnapshot | null>(null);
  const [failed, setFailed] = useState(false);
  const [opened, setOpened] = useState<string[]>([]);
  const [active, setActive] = useState<string | null>(null);
  const [recommendation, setRecommendation] = useState<(typeof RECOMMENDATIONS)[number] | null>(null);
  const [missionCase, setMissionCase] = useState<string | null>(null);
  const [rpg, setRpg] = useState<RpgState | null>(null);
  const boardRef = useRef<HTMLElement>(null);
  const verdictRef = useRef<HTMLElement>(null);
  const verdictHeadingRef = useRef<HTMLHeadingElement>(null);

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

  useEffect(() => {
    if (!recommendation) return;
    const frame = window.requestAnimationFrame(() => {
      verdictRef.current?.scrollIntoView({ behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start" });
      verdictHeadingRef.current?.focus({ preventScroll: true });
    });
    return () => window.cancelAnimationFrame(frame);
  }, [recommendation]);

  function openFile(name: string) { setActive(name); setOpened((known) => known.includes(name) ? known : [...known, name]); }
  function replay() {
    setOpened([]); setActive(null); setRecommendation(null); setMissionCase(null);
    window.requestAnimationFrame(() => boardRef.current?.scrollIntoView({ behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start" }));
  }
  function decide(item: (typeof RECOMMENDATIONS)[number]) {
    if (!activeCase) return;
    setRecommendation(item);
    setMissionCase(activeCase.portal_name);
    const residual = rpg!.skillMastery["Residual Read"] ?? 0;
    const effects = item.id === "prepare" ? { energy: rpg!.energy - 8, location: "Adachi Gate Zone", skillMastery: { ...rpg!.skillMastery, "Residual Read": Math.min(100, residual + 4) } }
      : item.id === "investigate" ? { energy: rpg!.energy - 12, health: rpg!.health - 2, location: "Adachi Gate Zone", skillMastery: { ...rpg!.skillMastery, "Residual Read": Math.min(100, residual + 8) }, completedEvents: [...new Set([...rpg!.completedEvents, "arc-i-evidence"])] }
      : { energy: rpg!.energy - 3, location: "Adachi Gate Zone" };
    setRpg(takeRpgAction(rpg!, item.label, effects));
  }

  if (failed) return <main id="chronicle" className="game-loading"><p>CASEBOARD OFFLINE</p><h1>The chronicle could not be verified.</h1><Link href="/game/city">Return to Tokyo</Link></main>;
  if (!snapshot || !rpg) return <main id="chronicle" className="game-loading" aria-busy="true"><p>LOADING RPG SAVE</p><h1>Checking the Gate ledger…</h1></main>;

  const cases = snapshot.portals.investigations;
  const activeCase = cases.find((item) => item.portal_name === active);
  const ready = cases.length > 0 && opened.length === cases.length;
  const atmosphere = gameAtmosphere(rpg);
  const mapImage = adachiMapImage(rpg.slot);

  return <main id="chronicle" className="case-shell">
    <header className="game-header"><Link href="/game/city">← TOKYO BOARD</Link><b>AWAKENED <i>ZERO RANK</i></b><span>CHAPTER 03 / GATE CASEBOARD</span></header>
    <GameHud state={rpg} current="cases" />
    <section className="case-intro"><small>DAY {rpg.day} / {rpg.slot} / {atmosphere.season} / {atmosphere.weather} / ENERGY {rpg.energy}</small><h1>Two Gates. Ren chooses.</h1><p>Inspect every case, then take Ren's next action. Every decision spends one RPG time slot.</p></section>

    {cases.length === 0 ? <section className="case-empty"><small>NO DISCOVERED CASES</small><h2>The board is blank.</h2><p>Ren has no authenticated portal investigation yet. The game will not invent one.</p><Link href="/">RETURN TO CHRONICLE</Link></section> : <section ref={boardRef} className="caseboard" aria-label="Gate investigation caseboard">
      <div className={`case-files case-zone city-${rpg.slot.toLowerCase().replace(" ", "-")} weather-${atmosphere.weather.toLowerCase()} snow-depth-${atmosphere.snowDepth}`}><Image className="case-zone-bg" src={mapImage} alt={`Pixel-art Adachi Gate exclusion zone during ${atmosphere.label}`} fill sizes="(max-width: 800px) 90vw, 65vw" priority /><div className="case-zone-shade" aria-hidden="true" />{(atmosphere.weather === "Rain" || atmosphere.weather === "Snow") && <div className="city-weather field-weather" aria-hidden="true"><i /><i /><i /></div>}<span className="case-ren"><Image src="/game/characters/ren.png" alt="Pixel sprite of Ren Takahashi" width={72} height={72} /><b>FIELD BRIEFING</b></span>{cases.map((item, index) => <button key={item.portal_name} onClick={() => openFile(item.portal_name)} className={`case-node case-node-${index + 1} ${opened.includes(item.portal_name) ? "opened" : ""}`} aria-pressed={active === item.portal_name}>{CASE_ART[item.portal_name] && <Image className="case-art" src={CASE_ART[item.portal_name]} alt={`Pixel art of ${item.portal_name}`} width={220} height={120} />}<span>CASE {String(index + 1).padStart(2, "0")}</span><h2>{item.portal_name}</h2><small>{opened.includes(item.portal_name) ? "FILE OPENED" : "SEALED EVIDENCE"}</small></button>)}</div>
      <aside className="case-detail" aria-live="polite">{!activeCase ? <><small>CASEBOARD</small><h2>Open the evidence.</h2><p>Risk and progress remain hidden until you inspect each file.</p></> : <><small>{activeCase.preparation_strategy}</small><h2>{activeCase.portal_name}</h2><dl><div><dt>RISK</dt><dd>{activeCase.risk}</dd></div><div><dt>PROGRESS</dt><dd>{activeCase.progress}%</dd></div><div><dt>PREP BONUS</dt><dd>+{activeCase.preparation_bonus}</dd></div><div><dt>JOINT MISSIONS</dt><dd>{activeCase.joint_missions}</dd></div></dl><p>{activeCase.cooperating_npc ? `Cooperating with ${activeCase.cooperating_npc}.` : "No cooperating contact recorded."}</p></>}
        <div className="case-options"><small>TAKE REN'S ACTION</small>{RECOMMENDATIONS.map((item) => <button key={item.id} disabled={!ready || recommendation !== null} onClick={() => decide(item)}>{item.label}</button>)}{!ready && <p>Open {cases.length - opened.length} remaining file{cases.length - opened.length === 1 ? "" : "s"}.</p>}</div>
      </aside>
    </section>}

    {recommendation && missionCase && <section ref={verdictRef} className="case-verdict"><Image className="verdict-chibi" src="/game/characters/ren.png" alt="Pixel sprite of Ren Takahashi" width={96} height={96} /><small>{recommendation.tone} / TIME ADVANCED</small><h2 ref={verdictHeadingRef} tabIndex={-1}>{missionCase} selected.</h2><blockquote>{renResponse(snapshot, recommendation.id)}</blockquote><div><span>RPG CLOCK</span><b>DAY {rpg.day} / {rpg.slot}</b><span>STATUS</span><b>HP {rpg.health} / EN {rpg.energy}</b></div><nav><Link className="primary" href={`/game/field?case=${encodeURIComponent(missionCase)}&plan=${recommendation.id}`}>ENTER THE GATE</Link><button onClick={replay}>REOPEN CASEBOARD</button><Link href="/game/city">RETURN TO TOKYO</Link></nav></section>}
    <footer className="game-footer"><b>REN'S LOCAL RPG CAMPAIGN</b><p>Actions consume a time slot here. The autonomous Observer timeline remains separate.</p><span>{cases.length} AUTHENTICATED CASES</span></footer>
  </main>;
}
