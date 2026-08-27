/* eslint-disable react/no-unescaped-entities */
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Image from "next/image";

import { currentScene, verifyArtifacts, type ObserverSnapshot } from "../observer-data";

type Hotspot = {
  id: string;
  label: string;
  cue: string;
  detail: (snapshot: ObserverSnapshot) => string;
};

const HOTSPOTS: Hotspot[] = [
  {
    id: "field-bag",
    label: "FIELD BAG",
    cue: "Preparedness",
    detail: (snapshot) => {
      const carried = Object.entries(snapshot.protagonist.equipment.inventory)
        .map(([name, count]) => `${name} x${count}`)
        .join(", ");
      return carried
        ? `Everything is counted: ${carried}. Ren's readiness is ${snapshot.protagonist.progression.combat_readiness}.`
        : "The bag is light. Ren has no recorded field equipment to rely on.";
    },
  },
  {
    id: "rent-envelope",
    label: "RENT ENVELOPE",
    cue: "Stability",
    detail: (snapshot) => {
      const reserve = snapshot.protagonist.resources.money - snapshot.economy.rent_cost;
      return snapshot.economy.rent_arrears > 0
        ? `The ledger shows ¥${snapshot.economy.rent_arrears.toLocaleString()} overdue.`
        : `Rent is accounted for. After a ¥${snapshot.economy.rent_cost.toLocaleString()} reserve, ¥${Math.max(0, reserve).toLocaleString()} remains.`;
    },
  },
  {
    id: "gate-notice",
    label: "GATE NOTICE",
    cue: "Risk",
    detail: (snapshot) => snapshot.portals.active_plan
      ? `A route is already marked: ${snapshot.portals.active_plan}. The city alert level is ${snapshot.environment.gate_alert_level}.`
      : `No active Gate plan is pinned. The city alert level is ${snapshot.environment.gate_alert_level}.`,
  },
];

const SUGGESTIONS = [
  { id: "gate", label: "Check the Gate plan", theme: "COURAGE" },
  { id: "rent", label: "Protect tomorrow's rent", theme: "CAUTION" },
  { id: "rest", label: "Recover before moving", theme: "CARE" },
] as const;

function responseFor(snapshot: ObserverSnapshot, suggestion: string) {
  const p = snapshot.protagonist;
  if (suggestion === "gate") {
    return snapshot.portals.active_plan
      ? `Ren studies ${snapshot.portals.active_plan}, then closes the notice. “The route is useful. The decision is still mine.”`
      : `Ren checks the empty notice board. “No assignment yet. I won't invent one just to feel busy.”`;
  }
  if (suggestion === "rent") {
    return snapshot.economy.rent_arrears > 0
      ? `Ren counts the shortfall twice. “You're right about the danger. I'll decide how to answer it.”`
      : `Ren leaves ¥${snapshot.economy.rent_cost.toLocaleString()} untouched. “Already protected. Some victories are deliberately boring.”`;
  }
  return p.resources.energy < 45 || p.resources.health < 70
    ? `Ren feels the warning in his body and sits down. “Advice accepted. Survival comes before pride.”`
    : `Ren rolls his shoulders, energy still at ${p.resources.energy}. “I hear you. I don't need the bed yet—but I won't waste the margin.”`;
}

export default function GamePage() {
  const [snapshot, setSnapshot] = useState<ObserverSnapshot | null>(null);
  const [failed, setFailed] = useState(false);
  const [clues, setClues] = useState<string[]>([]);
  const [activeClue, setActiveClue] = useState<string | null>(null);
  const [selectedSuggestion, setSelectedSuggestion] = useState<string | null>(null);
  const [response, setResponse] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      try {
        const options = { cache: "no-store" as RequestCache, signal: controller.signal };
        const [contractResponse, snapshotResponse] = await Promise.all([
          fetch("/data/observer-contract.json", options),
          fetch("/data/observer-snapshot.json", options),
        ]);
        if (!contractResponse.ok || !snapshotResponse.ok) throw new Error("artifacts unavailable");
        const verified = await verifyArtifacts(
          await contractResponse.json(),
          await snapshotResponse.json(),
        );
        if (!controller.signal.aborted) setSnapshot(verified.snapshot);
      } catch (error) {
        if (!(error instanceof DOMException && error.name === "AbortError")) setFailed(true);
      }
    }
    void load();
    return () => controller.abort();
  }, []);

  function inspect(hotspot: Hotspot) {
    setActiveClue(hotspot.id);
    setClues((known) => known.includes(hotspot.id) ? known : [...known, hotspot.id]);
  }

  function replay() {
    setClues([]);
    setActiveClue(null);
    setSelectedSuggestion(null);
    setResponse(null);
  }

  function suggest(id: string) {
    setSelectedSuggestion(id);
    setResponse(responseFor(snapshot!, id));
  }

  if (failed) return <main id="chronicle" className="game-loading"><p>PROLOGUE OFFLINE</p><h1>The chronicle could not be verified.</h1><Link href="/">Return to Observer</Link></main>;
  if (!snapshot) return <main id="chronicle" className="game-loading" aria-busy="true"><p>AUTHENTICATING SCENE</p><h1>Loading Ren's morning…</h1></main>;

  const scene = currentScene(snapshot);
  const active = HOTSPOTS.find((hotspot) => hotspot.id === activeClue);
  const selected = SUGGESTIONS.find((suggestion) => suggestion.id === selectedSuggestion);
  const unlocked = clues.length >= 2;
  const phase = response ? 3 : unlocked ? 2 : 1;

  return <main id="chronicle" className="game-shell">
    <header className="game-header"><Link href="/">← OBSERVER</Link><b>AWAKENED <i>ZERO RANK</i></b><span>PLAYABLE PROLOGUE / v0.560</span></header>
    <section className="game-intro" aria-labelledby="game-title">
      <small>DAY {snapshot.clock.day} / {snapshot.clock.slot} / {snapshot.protagonist.location}</small>
      <h1 id="game-title">A quiet room.<br />A life already moving.</h1>
      <p>Inspect the scene. You may offer one thought. Ren decides what it means.</p>
      <ol className="game-phases" aria-label="Scene progress">
        <li className={phase >= 1 ? "active" : ""}><b>01</b><span>OBSERVE</span></li>
        <li className={phase >= 2 ? "active" : ""}><b>02</b><span>SUGGEST</span></li>
        <li className={phase >= 3 ? "active" : ""}><b>03</b><span>LISTEN</span></li>
      </ol>
    </section>

    <section className="game-board" aria-label="Point-and-click scene">
      <div className="game-room">
        <div className="persona-room" aria-hidden="true"><i className="room-window" /><i className="room-bed" /><i className="room-desk" /><i className="room-notice" /></div>
        <Image className="chibi-sprite ren-chibi" src="/game/characters/ren.png" alt="Chibi portrait of Ren Takahashi" width={420} height={420} priority />
        {HOTSPOTS.map((hotspot, index) => <button
          key={hotspot.id}
          className={`hotspot hotspot-${index + 1} ${clues.includes(hotspot.id) ? "found" : ""}`}
          onClick={() => inspect(hotspot)}
          aria-pressed={activeClue === hotspot.id}
        ><i aria-hidden="true" /><span>{hotspot.label}</span></button>)}
        <p className="scene-caption">{scene.place} / {scene.weather} / {scene.presence}</p>
      </div>

      <aside className="game-panel" aria-live="polite">
        <div className="game-progress"><span>CLUES FOUND</span><b>{clues.length} / {HOTSPOTS.length}</b></div>
        {!active && <div className="game-copy"><small>REN'S ROOM</small><h2>Look before you speak.</h2><p>Two observations are enough to form a suggestion. Nothing here changes the authenticated chronicle.</p></div>}
        {active && <div className="game-copy"><small>OBSERVATION / {active.label}</small><h2>{active.label}</h2><p>{active.detail(snapshot)}</p></div>}
        <div className="suggestions">
          <small>OFFER ONE THOUGHT</small>
          {SUGGESTIONS.map((suggestion) => <button key={suggestion.id} disabled={!unlocked || response !== null} onClick={() => suggest(suggestion.id)}>{suggestion.label}</button>)}
          {!unlocked && <p>Inspect {2 - clues.length} more point{2 - clues.length === 1 ? "" : "s"} in the room.</p>}
        </div>
        {response && <blockquote className="dialogue-box"><span className="speaker-tag">REN</span><small>REN'S RESPONSE</small><p>{response}</p></blockquote>}
      </aside>
    </section>

    <section className="evidence-notebook" aria-labelledby="notebook-title">
      <header><small>LOCAL NOTEBOOK</small><h2 id="notebook-title">What you noticed</h2><p>Evidence is revealed only after inspection and is cleared when the scene is replayed.</p></header>
      <ol>{HOTSPOTS.map((hotspot, index) => {
        const found = clues.includes(hotspot.id);
        return <li key={hotspot.id} className={found ? "found" : undefined}><b>{String(index + 1).padStart(2, "0")}</b><div><small>{hotspot.cue}</small><span>{found ? hotspot.label : "UNEXAMINED"}</span>{found && <p>{hotspot.detail(snapshot)}</p>}</div></li>;
      })}</ol>
    </section>

    {response && selected && <section className="scene-conclusion" aria-labelledby="conclusion-title">
      <small>PROLOGUE COMPLETE / {selected.theme}</small>
      <h2 id="conclusion-title">You offered a thought.<br />Ren kept the choice.</h2>
      <div><p><b>YOUR SUGGESTION</b>{selected.label}</p><p><b>CANON STATUS</b>Unchanged — the next autonomous turn remains Ren's.</p></div>
      <nav aria-label="Prologue completion actions"><Link className="primary" href="/game/city">CONTINUE TO TOKYO</Link><button onClick={replay}>REPLAY THIS MORNING</button><Link href="/">RETURN TO LIVE CHRONICLE</Link></nav>
    </section>}

    <footer className="game-footer"><b>LOCAL PLAY ONLY</b><p>Your inspection and suggestion stay in this browser session. The simulator remains autonomous and unchanged.</p><span>AUTHENTICATED SNAPSHOT / SEED {snapshot.seed}</span></footer>
  </main>;
}
