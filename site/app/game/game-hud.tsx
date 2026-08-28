"use client";

import { useEffect } from "react";

import { pendingStoryRoute, type RpgState } from "./game-state";

export function GameHud({ state, current, onNewGame }: { state: RpgState; current: "home" | "city" | "cases" | "field" | "evening" | "debrief"; onNewGame?: () => void }) {
  useEffect(() => {
    const route = pendingStoryRoute(state);
    const alreadyShowing = (route === "/game/evening" && current === "evening") || (route === "/game/debrief" && current === "debrief");
    if (route && !alreadyShowing) window.location.assign(route);
  }, [current, state]);

  return <><nav className="rpg-nav" aria-label="RPG locations">
    <button className={current === "home" ? "active" : undefined} aria-current={current === "home" ? "page" : undefined} onClick={() => window.location.assign("/game")}>HOME</button>
    <button className={current === "city" ? "active" : undefined} aria-current={current === "city" ? "page" : undefined} onClick={() => window.location.assign("/game/city")}>TOKYO</button>
    <button className={current === "cases" ? "active" : undefined} aria-current={current === "cases" ? "page" : undefined} onClick={() => window.location.assign("/game/caseboard")}>GATE CASES</button>
    <button className={current === "field" ? "active" : undefined} aria-current={current === "field" ? "page" : undefined} onClick={() => window.location.assign("/game/field")}>FIELD</button>
  </nav><section className="rpg-hud" aria-label="Ren RPG status">
    <div><small>CALENDAR</small><b>DAY {state.day}</b><span>{state.slot}</span></div>
    <div><small>LOCATION</small><b>{state.location}</b><span>{state.turns} ACTION{state.turns === 1 ? "" : "S"}</span></div>
    <div><small>CONDITION</small><b>HP {state.health}</b><span>EN {state.energy}</span></div>
    <div><small>FUNDS</small><b>¥{state.money.toLocaleString()}</b><span>{state.lastAction}</span></div>
    {onNewGame && <button onClick={onNewGame}>NEW GAME</button>}
  </section><details className="rpg-journal">
    <summary>CAMPAIGN JOURNAL <span>{state.journal.length} / 12</span></summary>
    {state.journal.length === 0 ? <p>No actions recorded yet. Ren&apos;s first committed choice will appear here.</p> : <ol>{[...state.journal].reverse().map((entry, index) => <li key={`${entry.day}-${entry.slot}-${index}`}><b>DAY {entry.day} / {entry.slot}</b><span>{entry.action}</span><small>{entry.location}</small></li>)}</ol>}
  </details></>;
}
