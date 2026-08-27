"use client";

import type { RpgState } from "./game-state";

export function GameHud({ state, onNewGame }: { state: RpgState; onNewGame?: () => void }) {
  return <section className="rpg-hud" aria-label="Ren RPG status">
    <div><small>CALENDAR</small><b>DAY {state.day}</b><span>{state.slot}</span></div>
    <div><small>LOCATION</small><b>{state.location}</b><span>{state.turns} ACTION{state.turns === 1 ? "" : "S"}</span></div>
    <div><small>CONDITION</small><b>HP {state.health}</b><span>EN {state.energy}</span></div>
    <div><small>FUNDS</small><b>¥{state.money.toLocaleString()}</b><span>{state.lastAction}</span></div>
    {onNewGame && <button onClick={onNewGame}>NEW GAME</button>}
  </section>;
}
