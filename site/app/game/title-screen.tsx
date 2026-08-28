"use client";

import { useEffect, useRef, useState } from "react";
import Image from "next/image";
import Link from "next/link";

import { loadGamePreferences, saveGamePreferences, type GamePreferences } from "./game-preferences";
import type { RpgState } from "./game-state";

export function TitleScreen({ state, onContinue, onNewGame }: { state: RpgState; onContinue: () => void; onNewGame: () => void }) {
  const [panel, setPanel] = useState<"menu" | "settings" | "new-game">("menu");
  const [preferences, setPreferences] = useState<GamePreferences>(() => loadGamePreferences());
  const audioRef = useRef<HTMLAudioElement>(null);
  const [audioPlaying, setAudioPlaying] = useState(false);
  const hasProgress = state.turns > 0 || state.completedEvents.length > 0;

  const updatePreferences = (next: GamePreferences) => {
    setPreferences(next);
    saveGamePreferences(next);
  };

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;
    audio.volume = 0.28;
    if (preferences.ambience === "off") {
      audio.pause();
      return;
    }
    const begin = () => void audio.play().then(() => setAudioPlaying(true)).catch(() => setAudioPlaying(false));
    window.addEventListener("pointerdown", begin, { once: true });
    window.addEventListener("keydown", begin, { once: true });
    return () => {
      window.removeEventListener("pointerdown", begin);
      window.removeEventListener("keydown", begin);
      audio.pause();
    };
  }, [preferences.ambience]);

  const toggleAmbience = () => {
    const next = { ...preferences, ambience: preferences.ambience === "on" ? "off" as const : "on" as const };
    updatePreferences(next);
    if (next.ambience === "on") void audioRef.current?.play().then(() => setAudioPlaying(true)).catch(() => setAudioPlaying(false));
    else setAudioPlaying(false);
  };

  return <main className="title-screen">
    {/* Ambient weather contains no spoken content that requires captions. */}
    {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
    <audio ref={audioRef} src="/game/audio/rain-title-loop.mp3" loop preload="metadata" onPlay={() => setAudioPlaying(true)} onPause={() => setAudioPlaying(false)} />
    <Image className="title-bg" src="/game/ren-apartment-window-title-v1.png" alt="Rain falling beyond the balcony window of Ren's dark apartment" fill sizes="100vw" priority />
    <div className="title-window-light" aria-hidden="true" />
    <div className="title-window-rain" aria-hidden="true" />
    <div className="title-window-rain title-window-rain-near" aria-hidden="true" />
    <div className="title-window-droplets" aria-hidden="true">
      <i /><i /><i /><i /><i /><i /><i /><i />
    </div>
    <div className="title-rain-impacts" aria-hidden="true"><i /><i /><i /><i /><i /></div>
    <div className="title-city-flicker" aria-hidden="true" />
    <div className="title-curtain-shadow" aria-hidden="true" />
    <div className="title-shade" aria-hidden="true" />
    <header><Link href="/">← OBSERVER</Link><span>PRIVATE RPG CAMPAIGN / v0.880</span></header>
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
        <fieldset><legend>RAIN AMBIENCE</legend><button className={preferences.ambience === "on" ? "selected" : ""} onClick={() => preferences.ambience !== "on" && toggleAmbience()}>ON</button><button className={preferences.ambience === "off" ? "selected" : ""} onClick={() => preferences.ambience !== "off" && toggleAmbience()}>OFF</button></fieldset>
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
    <button className="title-audio-toggle" type="button" aria-pressed={preferences.ambience === "on"} onClick={toggleAmbience}><span aria-hidden="true">{preferences.ambience === "on" ? "◖))" : "◖×"}</span> RAIN {preferences.ambience === "on" ? audioPlaying ? "PLAYING" : "READY" : "OFF"}</button>
    <footer><span>LOCAL SAVE / OWNER-ONLY SITE</span><span>© AWAKENED: ZERO RANK</span></footer>
  </main>;
}
