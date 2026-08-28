"use client";

import { useEffect, useRef, useState } from "react";

import { pendingStoryRoute, type RpgState } from "./game-state";

export function GameHud({ state, current, onNewGame }: { state: RpgState; current: "home" | "city" | "cases" | "field" | "evening" | "debrief"; onNewGame?: () => void }) {
  const [confirmingReset, setConfirmingReset] = useState(false);
  const cancelReset = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const route = pendingStoryRoute(state);
    const alreadyShowing = (route === "/game/evening" && current === "evening") || (route === "/game/debrief" && current === "debrief");
    if (route && !alreadyShowing) window.location.assign(route);
  }, [current, state]);

  useEffect(() => {
    if (!confirmingReset) return;
    cancelReset.current?.focus();
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setConfirmingReset(false);
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [confirmingReset]);

  const resetCampaign = () => {
    setConfirmingReset(false);
    onNewGame?.();
  };

  return <><section className="rpg-hud" aria-label="Ren RPG status">
    <div><small>CALENDAR</small><b>DAY {state.day}</b><span>{state.slot}</span></div>
    <div><small>LOCATION</small><b>{state.location}</b><span>{state.turns} ACTION{state.turns === 1 ? "" : "S"}</span></div>
    <div><small>CONDITION</small><b>HP {state.health}</b><span>EN {state.energy}</span></div>
    <div><small>FUNDS</small><b>¥{state.money.toLocaleString()}</b><span>{state.lastAction}</span></div>
    {onNewGame && <button onClick={() => setConfirmingReset(true)} aria-haspopup="dialog">NEW GAME</button>}
  </section><details className="rpg-journal">
    <summary>CAMPAIGN JOURNAL <span>LOCAL SAVE · {state.journal.length} / 12</span></summary>
    <div className="save-status"><b>AUTOSAVE ACTIVE</b><span>DAY {state.day} · {state.slot} · {state.location}</span><small>Every committed action is saved on this device.</small></div>
    {state.journal.length === 0 ? <p>No actions recorded yet. Ren&apos;s first committed choice will appear here.</p> : <ol>{[...state.journal].reverse().map((entry, index) => <li key={`${entry.day}-${entry.slot}-${index}`}><b>DAY {entry.day} / {entry.slot}</b><span>{entry.action}</span><small>{entry.location}</small></li>)}</ol>}
  </details>{confirmingReset && <div className="reset-shade" role="presentation"><section className="reset-dialog" role="alertdialog" aria-modal="true" aria-labelledby="reset-title" aria-describedby="reset-copy"><small>LOCAL CAMPAIGN</small><h2 id="reset-title">Begin Ren&apos;s story again?</h2><p id="reset-copy">This replaces the RPG save on this device. The authenticated Observer timeline is never changed.</p><dl><div><dt>CURRENT SAVE</dt><dd>Day {state.day}, {state.slot}</dd></div><div><dt>RECORDED ACTIONS</dt><dd>{state.turns}</dd></div></dl><nav><button ref={cancelReset} onClick={() => setConfirmingReset(false)}>KEEP CURRENT SAVE</button><button className="danger" onClick={resetCampaign}>START NEW GAME</button></nav><small>PRESS ESCAPE TO CANCEL</small></section></div>}</>;
}
