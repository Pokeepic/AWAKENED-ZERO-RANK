"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";

import { verifyArtifacts, type ObserverSnapshot } from "../../observer-data";
import { loadRpgState, takeRpgAction, type RpgState } from "../game-state";
import { GameHud } from "../game-hud";

const RESPONSES = [
  { id: "honest", label: "Tell Aiko the Gate frightened you.", bond: 2, energy: 4, reply: "Aiko lowers her voice. “Good. Fear means you're still measuring the cost. You don't have to carry it alone.”" },
  { id: "steady", label: "Say the mission went according to plan.", bond: 1, energy: 2, reply: "Aiko studies Ren for a moment, then nods. “Then let me help with the next plan. No disappearing.”" },
  { id: "distance", label: "Change the subject and head home.", bond: 0, energy: 8, reply: "Aiko lets the silence stand. “All right. But I'm keeping the light on if you change your mind.”" },
] as const;

export default function EveningPage() {
  const [snapshot, setSnapshot] = useState<ObserverSnapshot | null>(null);
  const [rpg, setRpg] = useState<RpgState | null>(null);
  const [failed, setFailed] = useState(false);
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

  function answer(response: (typeof RESPONSES)[number]) {
    if (!rpg || choice) return;
    const currentBond = rpg.bonds["Aiko Sato"] ?? 0;
    const bonds = { ...rpg.bonds, "Aiko Sato": Math.min(10, currentBond + response.bond) };
    setChoice(response);
    setRpg(takeRpgAction(rpg, `Evening with Aiko: ${response.id}`, { energy: Math.min(100, rpg.energy + response.energy), location: "Adachi Station", bonds }));
  }

  if (failed) return <main id="chronicle" className="game-loading"><p>EVENING LINK OFFLINE</p><h1>The scene could not be verified.</h1><Link href="/game/field">Return to Gate field</Link></main>;
  if (!snapshot || !rpg) return <main id="chronicle" className="game-loading" aria-busy="true"><p>LOADING EVENING SAVE</p><h1>Waiting at Adachi Station…</h1></main>;

  const observerBond = snapshot.relationships.find((item) => item.name === "Aiko Sato");
  const bond = rpg.bonds["Aiko Sato"] ?? 0;
  return <main id="chronicle" className="evening-shell">
    <header className="game-header"><Link href="/game/field">← GATE FIELD</Link><b>AWAKENED <i>ZERO RANK</i></b><span>CHAPTER 05 / AFTER THE GATE</span></header>
    <GameHud state={rpg} current="evening" />
    <section className="evening-stage"><Image className="evening-bg" src="/game/tokyo-dusk.png" alt="Pixel-art Tokyo at dusk" fill sizes="100vw" priority /><div className="evening-shade" /><div className="social-cast"><span><Image src="/game/characters/ren.png" alt="Pixel sprite of Ren Takahashi" width={100} height={100} /><b>REN</b></span><span><Image src="/game/characters/aiko.png" alt="Pixel sprite of Aiko Sato" width={100} height={100} /><b>AIKO</b></span></div><div className="social-scene"><small>ADACHI STATION / {rpg.slot.toUpperCase()}</small><h1>After the Gate.</h1><blockquote><b>AIKO</b><p>“You came back quieter than you left. Do you want to tell me what happened?”</p></blockquote>{!choice ? <div className="social-choices">{RESPONSES.map((response) => <button key={response.id} onClick={() => answer(response)}>{response.label}</button>)}</div> : <div className="social-result" aria-live="polite"><blockquote><b>AIKO</b><p>{choice.reply}</p></blockquote><div><span>AIKO BOND</span><b>{bond} / 10 {choice.bond > 0 ? `(+${choice.bond})` : ""}</b><small>Observer trust remains {observerBond?.trust ?? 0}; this bond belongs only to your RPG save.</small></div><nav><Link className="primary" href="/game">END CHAPTER AT HOME</Link><Link href="/game/city">RETURN TO TOKYO</Link></nav></div>}</div></section>
    <footer className="game-footer"><b>PLAYER-DIRECTED SOCIAL LINK</b><p>Dialogue changes the local RPG bond and advances one time slot.</p><span>AIKO BOND {bond} / 10</span></footer>
  </main>;
}
