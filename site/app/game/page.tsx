/* eslint-disable react/no-unescaped-entities */
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Image from "next/image";

import { currentScene, verifyArtifacts, type ObserverSnapshot } from "../observer-data";
import { loadRpgState, resetRpgState, takeRpgAction, type RpgState } from "./game-state";
import { GameHud } from "./game-hud";
import { applyGamePreferences, loadGamePreferences, RPG_SESSION_KEY } from "./game-preferences";
import { TitleScreen } from "./title-screen";
import doorStyles from "./door.module.css";

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
      ? `Ren studies ${snapshot.portals.active_plan} and marks the safest approach. “Route checked. I know where to move next.”`
      : `Ren checks the empty notice board. “No assignment yet. I won't invent one just to feel busy.”`;
  }
  if (suggestion === "rent") {
    return snapshot.economy.rent_arrears > 0
      ? `Ren counts the shortfall twice. “The arrears come first. I need a paying shift.”`
      : `Ren leaves ¥${snapshot.economy.rent_cost.toLocaleString()} untouched. “Already protected. Some victories are deliberately boring.”`;
  }
  return p.resources.energy < 45 || p.resources.health < 70
    ? `Ren feels the warning in his body and lies down. “Survival comes before pride.”`
    : `Ren rests deliberately, energy at ${p.resources.energy}. “A clear head is worth the time.”`;
}

export default function GamePage() {
  const [snapshot, setSnapshot] = useState<ObserverSnapshot | null>(null);
  const [failed, setFailed] = useState(false);
  const [clues, setClues] = useState<string[]>([]);
  const [activeClue, setActiveClue] = useState<string | null>(null);
  const [selectedSuggestion, setSelectedSuggestion] = useState<string | null>(null);
  const [response, setResponse] = useState<string | null>(null);
  const [rpg, setRpg] = useState<RpgState | null>(null);
  const [showTitle, setShowTitle] = useState<boolean | null>(null);

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
        if (!controller.signal.aborted) {
          setSnapshot(verified.snapshot);
          setRpg(loadRpgState(verified.snapshot));
          applyGamePreferences(loadGamePreferences());
          setShowTitle(window.sessionStorage.getItem(RPG_SESSION_KEY) !== "active");
        }
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
  function newGame() {
    setRpg(resetRpgState(snapshot!));
    replay();
  }

  function enterCampaign() {
    window.sessionStorage.setItem(RPG_SESSION_KEY, "active");
    setShowTitle(false);
  }

  function startFromTitle() {
    newGame();
    enterCampaign();
  }

  function suggest(id: string) {
    setSelectedSuggestion(id);
    const next = id === "rest"
      ? takeRpgAction(rpg!, "Rested at the apartment", { energy: rpg!.energy + 25, health: rpg!.health + 5, location: "Ren's Apartment" })
      : id === "rent"
        ? takeRpgAction(rpg!, "Protected the rent reserve", { energy: rpg!.energy - 3, location: "Ren's Apartment" })
        : takeRpgAction(rpg!, "Prepared the Gate route", { energy: rpg!.energy - 8, location: "Ren's Apartment" });
    setRpg(next);
    setResponse(responseFor(snapshot!, id));
  }

  if (failed) return <main id="chronicle" className="game-loading"><p>PROLOGUE OFFLINE</p><h1>The chronicle could not be verified.</h1><Link href="/">Return to Observer</Link></main>;
  if (!snapshot || !rpg || showTitle === null) return <main id="chronicle" className="game-loading" aria-busy="true"><p>LOADING RPG SAVE</p><h1>Preparing Ren's day…</h1></main>;
  if (showTitle) return <TitleScreen state={rpg} onContinue={enterCampaign} onNewGame={startFromTitle} />;

  const scene = currentScene(snapshot);
  const active = HOTSPOTS.find((hotspot) => hotspot.id === activeClue);
  const selected = SUGGESTIONS.find((suggestion) => suggestion.id === selectedSuggestion);
  const unlocked = clues.length >= 2;
  const phase = response ? 3 : unlocked ? 2 : 1;

  return <main id="chronicle" className="game-shell">
    <header className="game-header"><Link href="/">← OBSERVER</Link><b>AWAKENED <i>ZERO RANK</i></b><span>REN RPG / v0.860</span></header>
    <GameHud state={rpg} current="home" onNewGame={newGame} />
    <section className="game-intro" aria-labelledby="game-title">
      <small>DAY {rpg.day} / {rpg.slot} / {rpg.location}</small>
      <h1 id="game-title">A quiet room.<span>A life already moving.</span></h1>
      <p>You are Ren. Inspect the apartment, choose an action, and spend one time slot.</p>
      <ol className="game-phases" aria-label="Scene progress">
        <li className={phase >= 1 ? "active" : ""}><b>01</b><span>EXPLORE</span></li>
        <li className={phase >= 2 ? "active" : ""}><b>02</b><span>ACT</span></li>
        <li className={phase >= 3 ? "active" : ""}><b>03</b><span>RESULT</span></li>
      </ol>
    </section>

    <section className="game-board" aria-label="Point-and-click scene">
      <div className="game-room">
        <Image className="apartment-bg" src="/game/ren-apartment.png" alt="Pixel-art interior of Ren's apartment" fill sizes="(max-width: 800px) 90vw, 65vw" priority />
        <div className="apartment-shade" aria-hidden="true" />
        <Link className={doorStyles.apartmentDoor} href="/game/city" aria-label="Leave Ren's apartment for Tokyo"><i aria-hidden="true" /><span>LEAVE APARTMENT</span></Link>
        {HOTSPOTS.map((hotspot, index) => <button
          key={hotspot.id}
          className={`hotspot hotspot-${index + 1} ${[doorStyles.fieldBag, doorStyles.rentEnvelope, doorStyles.gateNotice][index]} ${clues.includes(hotspot.id) ? "found" : ""}`}
          onClick={() => inspect(hotspot)}
          aria-pressed={activeClue === hotspot.id}
        ><i aria-hidden="true" /><span>{hotspot.label}</span></button>)}
        <p className="scene-caption">{scene.place.name} / {scene.atmosphere} / {scene.presence}</p>
      </div>

      <aside className={`game-panel ${doorStyles.apartmentPanel}`} aria-live="polite">
        <div className="game-progress"><span>CLUES FOUND</span><b>{clues.length} / {HOTSPOTS.length}</b></div>
        {!active && <div className="game-copy"><small>REN'S ROOM</small><h2>Decide how to spend the slot.</h2><p>Inspect two points, then act as Ren. This RPG campaign has its own local save, separate from the Observer.</p></div>}
        {active && <div className="game-copy"><small>OBSERVATION / {active.label}</small><h2>{active.label}</h2><p>{active.detail(snapshot)}</p></div>}
        <div className="suggestions">
          <small>TAKE ONE ACTION</small>
          {SUGGESTIONS.map((suggestion) => <button key={suggestion.id} disabled={!unlocked || response !== null} onClick={() => suggest(suggestion.id)}>{suggestion.label}</button>)}
          {!unlocked && <p>Inspect {2 - clues.length} more point{2 - clues.length === 1 ? "" : "s"} in the room.</p>}
        </div>
        {response && selected && <blockquote className="dialogue-box"><Image className={doorStyles.resultPortrait} src="/game/visual-novel/ren-full.png" alt="Portrait of Ren Takahashi" width={1024} height={1536} /><span className="speaker-tag">REN</span><small>ACTION COMPLETE / {selected.theme}</small><p>{response}</p><nav className="panel-actions" aria-label="Continue campaign"><Link href="/game/city">GO TO TOKYO</Link><button onClick={replay}>RESET SCENE</button></nav></blockquote>}
      </aside>
    </section>

    <footer className="game-footer"><b>REN'S LOCAL RPG SAVE</b><p>You control Ren here. Actions advance the RPG clock; the separate Observer simulation remains unchanged.</p><span>{rpg.turns} TURNS / SEED {snapshot.seed}</span></footer>
  </main>;
}
