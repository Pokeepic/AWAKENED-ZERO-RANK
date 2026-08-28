"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";

import { verifyArtifacts, type ObserverSnapshot } from "../../observer-data";
import { loadRpgState, type RpgState } from "../game-state";
import { GameHud } from "../game-hud";

const EVENTS = [
  { id: "after-the-gate-aiko", chapter: "05", title: "After the Gate", location: "Adachi Station", href: "/game/evening", image: "/game/visual-novel/adachi-station-dusk.png", bond: "Aiko Sato", prerequisite: null },
  { id: "guild-debrief-daichi", chapter: "06", title: "The Patrol Record", location: "Tokyo Hunter Guild", href: "/game/debrief", image: "/game/visual-novel/hunter-guild-briefing.png", bond: "Daichi Mori", prerequisite: "after-the-gate-aiko" },
] as const;

export default function StoryPage() {
  const [snapshot, setSnapshot] = useState<ObserverSnapshot | null>(null);
  const [rpg, setRpg] = useState<RpgState | null>(null);
  const [failed, setFailed] = useState(false);

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

  if (failed) return <main id="chronicle" className="game-loading"><p>STORY INDEX OFFLINE</p><h1>The campaign record could not be verified.</h1><Link href="/game">Return home</Link></main>;
  if (!snapshot || !rpg) return <main id="chronicle" className="game-loading" aria-busy="true"><p>LOADING STORY SAVE</p><h1>Indexing canon events…</h1></main>;

  const completedCount = EVENTS.filter((event) => rpg.completedEvents.includes(event.id)).length;
  const nextEvent = EVENTS.find((event) => !rpg.completedEvents.includes(event.id) && (!event.prerequisite || rpg.completedEvents.includes(event.prerequisite)));
  return <main id="chronicle" className="story-shell">
    <header className="game-header"><Link href="/game">← REN&apos;S APARTMENT</Link><b>AWAKENED <i>ZERO RANK</i></b><span>STORY / CANON EVENT INDEX</span></header>
    <GameHud state={rpg} current="story" />
    <section className="story-hub-intro"><div><small>PLAYER-DIRECTED CAMPAIGN</small><h1>Ren&apos;s story,<br />in your hands.</h1><p>Canon events unlock in order. Choices change this local RPG save without rewriting the authenticated Observer timeline.</p></div><aside><span>EVENTS COMPLETE</span><b>{completedCount} / {EVENTS.length}</b><span>NEXT AVAILABLE</span><strong>{nextEvent?.title ?? "CURRENT ARC COMPLETE"}</strong></aside></section>
    <section className="story-event-grid" aria-label="Canon events">{EVENTS.map((event) => {
      const complete = rpg.completedEvents.includes(event.id);
      const unlocked = !event.prerequisite || rpg.completedEvents.includes(event.prerequisite);
      const status = complete ? "COMPLETE" : unlocked ? "AVAILABLE" : "LOCKED";
      return <article key={event.id} className={`story-event ${status.toLowerCase()}`}><div className="story-event-art"><Image src={event.image} alt={`Illustrated ${event.location}`} fill sizes="(max-width: 800px) 100vw, 50vw" /><span>CHAPTER {event.chapter}</span></div><div><small>{status} / {event.location}</small><h2>{event.title}</h2><p>{complete ? `${event.bond} bond ${rpg.bonds[event.bond] ?? 0} / 10. Reopen the completed-event summary.` : unlocked ? `A one-time visual-novel event connected to ${event.bond}.` : "Complete the preceding canon event to unlock this chapter."}</p>{unlocked ? <Link href={event.href}>{complete ? "REVIEW EVENT" : "BEGIN EVENT"}</Link> : <span className="story-locked" aria-label={`${event.title} locked`}>LOCKED</span>}</div></article>;
    })}<article className="story-event future"><div><small>AUTHENTICATED FUTURE ANCHOR</small><h2>{snapshot.story.next?.title ?? "Future arc"}</h2><p>Observer schedule: Day {snapshot.story.next?.day ?? "—"}. This remains a future game chapter until its authored RPG route is ready.</p><span className="story-locked">COMING LATER</span></div></article></section>
    <footer className="game-footer"><b>CANON EVENT INDEX</b><p>Completed events are reviewable but never grant duplicate rewards.</p><span>{Object.keys(rpg.bonds).length} LOCAL BONDS</span></footer>
  </main>;
}
