"use client";

import { useState } from "react";
import Image from "next/image";
import Link from "next/link";

import { loadGamePreferences, saveGamePreferences, type GamePreferences } from "./game-preferences";
import type { RpgState } from "./game-state";

export function TitleScreen({ state, onContinue, onNewGame }: { state: RpgState; onContinue: () => void; onNewGame: () => void }) {
  const [panel, setPanel] = useState<"menu" | "settings" | "new-game">("menu");
  const [preferences, setPreferences] = useState<GamePreferences>(() => loadGamePreferences());
  const hasProgress = state.turns > 0 || state.completedEvents.length > 0;

  const updatePreferences = (next: GamePreferences) => {
    setPreferences(next);
    saveGamePreferences(next);
  };

  return <main className="title-screen">
    <Image className="title-bg" src="/game/ren-apartment-window-title-v1.png" alt="Rain falling beyond the balcony window of Ren's dark apartment" fill sizes="100vw" priority />
    <div className="title-window-light" aria-hidden="true" />
    <div className="title-window-rain" aria-hidden="true" />
    <div className="title-window-rain title-window-rain-near" aria-hidden="true" />
    <div className="title-window-droplets" aria-hidden="true">
      <i /><i /><i /><i /><i /><i /><i /><i />
    </div>
    <div className="title-city-flicker" aria-hidden="true" />
    <div className="title-curtain-shadow" aria-hidden="true" />
    <div className="title-shade" aria-hidden="true" />
    <header><Link href="/">← OBSERVER</Link><span>PRIVATE RPG CAMPAIGN / v0.860</span></header>
    <section className="title-lockup" aria-labelledby="title-heading">
      <small>REN&apos;S APARTMENT / ADACHI / 02:13</small>
      <h1 id="title-heading"><span>AWAKENED</span>ZERO RANK</h1>
      <p>THE RAIN HASN&apos;T STOPPED</p>
    </section>
    <section className="title-menu" aria-label={panel === "menu" ? "Main menu" : panel === "settings" ? "Settings" : "New game confirmation"}>
      {panel === "menu" && <>
        <button className="primary" onClick={onContinue}><b>{hasProgress ? "CONTINUE" : "START GAME"}</b><span>Day {state.day} · {state.slot} · {state.location}</span></button>
        <button onClick={() => setPanel("new-game")}><b>NEW GAME</b><span>Begin again from the authenticated world seed</span></button>
        <button onClick={() => setPanel("settings")}><b>SETTINGS</b><span>Motion and dialogue readability</span></button>
        <Link href="/"><b>OBSERVER</b><span>Open Ren&apos;s autonomous chronicle</span></Link>
      </>}
      {panel === "settings" && <div className="title-subpanel">
        <small>SETTINGS</small><h2>Presentation</h2>
        <fieldset><legend>MOTION</legend><button className={preferences.motion === "full" ? "selected" : ""} onClick={() => updatePreferences({ ...preferences, motion: "full" })}>FULL</button><button className={preferences.motion === "reduced" ? "selected" : ""} onClick={() => updatePreferences({ ...preferences, motion: "reduced" })}>REDUCED</button></fieldset>
        <fieldset><legend>TEXT SIZE</legend><button className={preferences.textSize === "normal" ? "selected" : ""} onClick={() => updatePreferences({ ...preferences, textSize: "normal" })}>NORMAL</button><button className={preferences.textSize === "large" ? "selected" : ""} onClick={() => updatePreferences({ ...preferences, textSize: "large" })}>LARGE</button></fieldset>
        <p>Settings are saved on this device and apply throughout the RPG.</p>
        <button className="back" onClick={() => setPanel("menu")}>← BACK TO MENU</button>
      </div>}
      {panel === "new-game" && <div className="title-subpanel warning">
        <small>NEW GAME</small><h2>{hasProgress ? "Replace the current campaign?" : "Begin Ren's campaign?"}</h2>
        <p>{hasProgress ? `Your Day ${state.day} local RPG save with ${state.turns} recorded actions will be replaced. The Observer remains unchanged.` : "A new local RPG save will begin from the verified Observer world seed."}</p>
        <button className="primary confirm" onClick={onNewGame}>{hasProgress ? "REPLACE SAVE & START" : "START NEW GAME"}</button>
        <button className="back" onClick={() => setPanel("menu")}>← KEEP CURRENT SAVE</button>
      </div>}
    </section>
    <footer><span>LOCAL SAVE / OWNER-ONLY SITE</span><span>© AWAKENED: ZERO RANK</span></footer>
  </main>;
}
