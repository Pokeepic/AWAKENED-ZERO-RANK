/* eslint-disable react/no-unescaped-entities */
"use client";

import Link from "next/link";
import Image from "next/image";
import { useEffect, useState } from "react";

import { verifyArtifacts, type ObserverSnapshot } from "../../observer-data";
import { loadRpgState, takeRpgAction, type RpgState } from "../game-state";
import { GameHud } from "../game-hud";

const SPRITES: Record<string, string> = {
  "Aiko Sato": "/game/characters/aiko.png",
  "Daichi Mori": "/game/characters/daichi.png",
  "Haruto Ishikawa": "/game/characters/haruto.png",
  "Mei Kuroda": "/game/characters/mei.png",
};

const LANDMARKS: Record<string, string> = {
  "Tokyo Hunter Guild": "/game/locations/hunter-guild.png",
  "Adachi Gate Zone": "/game/locations/gate-zone.png",
  "Akihabara Market": "/game/locations/akihabara-market.png",
  "Ueno Library": "/game/locations/ueno-library.png",
};

const DISTRICTS = [
  { id: "central", label: "CENTRAL TOKYO", image: "/game/tokyo-dusk.png", locations: ["Tokyo Hunter Guild"] },
  { id: "east", label: "EAST LOOP", image: "/game/maps/east-loop.png", locations: ["Akihabara Market", "Ueno Library"] },
  { id: "adachi", label: "ADACHI FRINGE", image: "/game/maps/adachi-fringe.png", locations: ["Adachi Gate Zone"] },
] as const;

function routeResponse(snapshot: ObserverSnapshot, personName: string, location: string) {
  const relationship = snapshot.relationships.find((item) => item.name === personName);
  if (location === snapshot.protagonist.location) return `Ren folds the route card. “I'm already at ${location}. Staying is still a choice—but it has to earn the time.”`;
  if ((relationship?.trust ?? 0) >= 10) return `Ren marks the line toward ${location}. “${personName} has earned a hearing. I'll consider it when I choose my route.”`;
  return `Ren notes ${personName} at ${location}. “Useful lead. Not an order. I'll judge the risk when I leave.”`;
}

export default function CityRoutePage() {
  const [snapshot, setSnapshot] = useState<ObserverSnapshot | null>(null);
  const [failed, setFailed] = useState(false);
  const [inspected, setInspected] = useState<string[]>([]);
  const [active, setActive] = useState<string | null>(null);
  const [choice, setChoice] = useState<{ name: string; location: string } | null>(null);
  const [districtId, setDistrictId] = useState<(typeof DISTRICTS)[number]["id"]>("central");
  const [rpg, setRpg] = useState<RpgState | null>(null);

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

  function inspect(location: string) {
    setActive(location);
    setInspected((known) => known.includes(location) ? known : [...known, location]);
  }
  function reset() { setInspected([]); setActive(null); setChoice(null); }
  function chooseRoute(name: string, location: string) {
    setChoice({ name, location });
    setRpg(takeRpgAction(rpg!, `Traveled to ${location}`, { location, energy: rpg!.energy - 6 }));
  }

  if (failed) return <main id="chronicle" className="game-loading"><p>ROUTE BOARD OFFLINE</p><h1>The chronicle could not be verified.</h1><Link href="/game">Return to prologue</Link></main>;
  if (!snapshot || !rpg) return <main id="chronicle" className="game-loading" aria-busy="true"><p>LOADING RPG SAVE</p><h1>Drawing today's routes…</h1></main>;

  const routes = snapshot.whereabouts.map((whereabout) => ({ ...whereabout, relationship: snapshot.relationships.find((item) => item.name === whereabout.name) }));
  const district = DISTRICTS.find((item) => item.id === districtId) ?? DISTRICTS[0];
  const visibleRoutes = routes.filter((route) => district.locations.some((location) => location === route.location));
  const activeRoute = routes.find((route) => route.location === active);
  const ready = inspected.length >= 2;

  return <main id="chronicle" className="city-shell">
    <header className="game-header"><Link href="/game">← PROLOGUE</Link><b>AWAKENED <i>ZERO RANK</i></b><span>CHAPTER 02 / ROUTE BOARD</span></header>
    <GameHud state={rpg} current="city" />
    <section className="city-intro"><small>DAY {rpg.day} / {rpg.slot} / {rpg.location}</small><h1>Choose where Ren<br />goes next.</h1><p>Explore the districts, inspect two signals, then travel. The trip spends one RPG time slot.</p></section>
    <nav className="district-switcher" aria-label="Tokyo districts">{DISTRICTS.map((item, index) => <button key={item.id} aria-pressed={districtId === item.id} onClick={() => { setDistrictId(item.id); setActive(null); }}><small>0{index + 1}</small><span>{item.label}</span><b>{item.locations.length} SIGNAL{item.locations.length === 1 ? "" : "S"}</b></button>)}</nav>
    <section className="route-board" aria-label="Tokyo route board">
      <div className={`route-map city-diorama district-${district.id}`}><Image className="tokyo-map-bg" src={district.image} alt={`Pixel-art ${district.label.toLowerCase()}`} fill sizes="(max-width: 800px) 90vw, 65vw" priority /><div className="map-atmosphere" aria-hidden="true" /><span className="district-stamp">{district.label}<b>LOCAL MAP</b></span><span className="map-origin"><Image src="/game/characters/ren.png" alt="Pixel sprite of Ren Takahashi" width={72} height={72} /><small>REN</small><b>VIEWING {district.label}</b></span>{visibleRoutes.map((route, index) => <button key={route.name} className={`route-node node-${index + 1} ${inspected.includes(route.location) ? "inspected" : ""}`} onClick={() => inspect(route.location)} aria-pressed={active === route.location}><span className="route-art"><Image className="landmark-sprite" src={LANDMARKS[route.location]} alt="" width={120} height={120} /><Image className="contact-sprite" src={SPRITES[route.name]} alt="" width={48} height={48} /></span><span className="route-label"><small>{route.name}</small><b>{route.location}</b></span></button>)}</div>
      <aside className="route-dossier" aria-live="polite"><div className="game-progress"><span>SIGNALS CHECKED</span><b>{inspected.length} / {routes.length}</b></div>{!activeRoute && <div className="game-copy"><small>CITY MAP</small><h2>Choose Ren's destination.</h2><p>Every marker begins from authenticated world data, then your local RPG campaign moves independently.</p></div>}{activeRoute && <div className="game-copy character-dossier"><Image src={SPRITES[activeRoute.name]} alt={`Pixel sprite of ${activeRoute.name}`} width={80} height={80} /><small>{activeRoute.relationship?.role ?? "KNOWN CONTACT"}</small><h2>{activeRoute.name}</h2><p>{activeRoute.location}. Trust {activeRoute.relationship?.trust ?? 0}; familiarity {activeRoute.relationship?.familiarity ?? 0}; tension {activeRoute.relationship?.tension ?? 0}.</p></div>}<div className="route-options"><small>TRAVEL AS REN</small>{routes.map((route) => <button key={route.name} disabled={!ready || choice !== null} onClick={() => chooseRoute(route.name, route.location)}><span>{route.location}</span><small>VISIT {route.name}</small></button>)}{!ready && <p>Inspect {2 - inspected.length} more signal{2 - inspected.length === 1 ? "" : "s"} first.</p>}</div></aside>
    </section>
    {choice && <section className="route-result" aria-labelledby="route-result-title"><div className="route-encounter" aria-hidden="true"><Image src="/game/characters/ren.png" alt="" width={80} height={80} /><i /><Image src={SPRITES[choice.name]} alt="" width={80} height={80} /></div><small>TRAVEL COMPLETE / TIME ADVANCED</small><h2 id="route-result-title">{choice.location}</h2><blockquote>{routeResponse(snapshot, choice.name, choice.location)}</blockquote><p>RPG clock: Day {rpg.day}, {rpg.slot}. Energy {rpg.energy}. The Observer timeline remains separate.</p><nav><Link className="primary" href="/game/caseboard">CONTINUE TO GATE FIELD</Link><button onClick={reset}>EXPLORE ANOTHER ROUTE</button><Link href="/">OPEN OBSERVER</Link></nav></section>}
    <footer className="game-footer"><b>AUTHENTICATED CITY STATE</b><p>{snapshot.environment.weather}, {snapshot.environment.temperature_c} C / Gate alert {snapshot.environment.gate_alert_level}</p><span>SEED {snapshot.seed}</span></footer>
  </main>;
}
