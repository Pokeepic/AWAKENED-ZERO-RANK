"use client";

import Link from "next/link";
import type { RpgState } from "./game-state";

export function GameHud({ state, current, onNewGame }: { state: RpgState; current: "home" | "city" | "cases"; onNewGame?: () => void }) {
  return <><nav className="rpg-nav" aria-label="RPG locations">
    <Link className={current === "home" ? "active" : undefined} aria-current={current === "home" ? "page" : undefined} href="/game">HOME</Link>
    <Link className={current === "city" ? "active" : undefined} aria-current={current === "city" ? "page" : undefined} href="/game/city">TOKYO</Link>
    <Link className={current === "cases" ? "active" : undefined} aria-current={current === "cases" ? "page" : undefined} href="/game/caseboard">GATE CASES</Link>
  </nav><section className="rpg-hud" aria-label="Ren RPG status">
    <div><small>CALENDAR</small><b>DAY {state.day}</b><span>{state.slot}</span></div>
    <div><small>LOCATION</small><b>{state.location}</b><span>{state.turns} ACTION{state.turns === 1 ? "" : "S"}</span></div>
    <div><small>CONDITION</small><b>HP {state.health}</b><span>EN {state.energy}</span></div>
    <div><small>FUNDS</small><b>¥{state.money.toLocaleString()}</b><span>{state.lastAction}</span></div>
    {onNewGame && <button onClick={onNewGame}>NEW GAME</button>}
  </section></>;
}
