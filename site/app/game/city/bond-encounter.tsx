"use client";

import Image from "next/image";
import { useCallback, useEffect, useState } from "react";

import type { BondMoment, Timeline } from "../game-state";

export type BondEncounterChoice = {
  id: string;
  label: string;
  reply: string;
  energyCost: number;
};

const ENCOUNTERS: Record<string, {
  portraitSheet: string;
  background: string;
  opening: string;
  prompt: string;
  choices: readonly BondEncounterChoice[];
}> = {
  "Aiko Sato": {
    portraitSheet: "/game/visual-novel/expressions/aiko-sheet-v2.png",
    background: "/game/visual-novel/adachi-station-dusk.png",
    opening: "Aiko waits beyond the ticket gates, pretending she was already headed this way.",
    prompt: "“You came all this way. So—are you going to tell me what you actually need?”",
    choices: [
      { id: "honest", label: "Tell Aiko the truth without softening it.", reply: "Aiko listens without interrupting. “Good. Now I know which part we're carrying together.”", energyCost: 3 },
      { id: "listen", label: "Ask how Aiko's patrol has been.", reply: "Aiko blinks, then laughs once. “You remembered I have problems too. That's progress.”", energyCost: 4 },
      { id: "quiet", label: "Share the silence beside her.", reply: "Aiko stays until the next train passes. “You don't always have to fill the quiet, Ren.”", energyCost: 5 },
    ],
  },
  "Daichi Mori": {
    portraitSheet: "/game/visual-novel/expressions/daichi-sheet-v2.png",
    background: "/game/visual-novel/hunter-guild-briefing.png",
    opening: "Daichi clears the last unsigned report from the second chair before Ren arrives.",
    prompt: "“You have one hour before command remembers I'm supposed to be busy. Use it.”",
    choices: [
      { id: "evidence", label: "Compare field evidence line by line.", reply: "Daichi marks the final contradiction in red. “This survives review. More importantly, so might you.”", energyCost: 5 },
      { id: "strategy", label: "Ask how Daichi would break the next ambush.", reply: "Daichi redraws the route around Ren's weakest flank. “You asked the right question before bleeding. Keep doing that.”", energyCost: 4 },
      { id: "coffee", label: "Bring coffee and talk about anything else.", reply: "Daichi accepts the cup after a long pause. “For the record, this meeting never happened.”", energyCost: 3 },
    ],
  },
  "Haruto Ishikawa": {
    portraitSheet: "/game/visual-novel/expressions/haruto-sheet-v2.png",
    background: "/game/visual-novel/akihabara-night-market-v1.png",
    opening: "Haruto raises one shutter after midnight and leaves the price board facedown.",
    prompt: "“Tonight I'm selling information, bad advice, and exactly one honest answer. Pick carefully.”",
    choices: [
      { id: "truth", label: "Spend the honest answer on Haruto himself.", reply: "Haruto's smile fades into something real. “Cruel purchase. Fine—you get the truth.”", energyCost: 4 },
      { id: "ledger", label: "Trace who is buying corrupted Gate relics.", reply: "Haruto opens a ledger he usually keeps beneath the floor. “Names cost more than money. You can owe me courage.”", energyCost: 5 },
      { id: "game", label: "Challenge Haruto to one harmless wager.", reply: "Haruto loses, suspiciously, and pushes the winnings back. “Don't get sentimental. I was testing your face.”", energyCost: 3 },
    ],
  },
  "Mei Kuroda": {
    portraitSheet: "/game/visual-novel/expressions/mei-sheet-v2.png",
    background: "/game/visual-novel/ueno-archive-room-v1.png",
    opening: "Mei locks the archive door, checks it twice, and places Ren's file beneath the green lamp.",
    prompt: "“The official record omits you in three places. Which omission do you want to correct first?”",
    choices: [
      { id: "memory", label: "Record the memory no report believes.", reply: "Mei writes every word without looking away. “Belief is optional. Preservation isn't.”", energyCost: 4 },
      { id: "case", label: "Reconstruct the missing Gate chronology.", reply: "Mei aligns the pages into a pattern neither of them likes. “Now it can be proven. That makes it dangerous.”", energyCost: 5 },
      { id: "ordinary", label: "Ask Mei about an ordinary book instead.", reply: "Mei chooses a worn novel from her private shelf. “Return it. I'd prefer to discuss the ending with you.”", energyCost: 3 },
    ],
  },
};

type Expression = "neutral" | "concerned" | "warm" | "firm";

function ExpressionPortrait({ sheet, expression, side, active }: {
  sheet: string;
  expression: Expression;
  side: "left" | "right";
  active: boolean;
}) {
  return <span className={`vn-expression ${side} ${expression} ${active ? "speaking" : "listening"}`}><Image src={sheet} alt="" width={1240} height={1536} priority /></span>;
}

export function BondEncounter({ name, location, level, timeline, moment, onCommit, onClose }: {
  name: string;
  location: string;
  level: number;
  timeline: Timeline;
  moment: BondMoment;
  onCommit: (choice: BondEncounterChoice) => void;
  onClose: () => void;
}) {
  const [beat, setBeat] = useState(0);
  const [result, setResult] = useState<BondEncounterChoice | null>(null);
  const encounter = ENCOUNTERS[name];
  const choose = useCallback((choice: BondEncounterChoice) => {
    if (result) return;
    setResult(choice);
    onCommit(choice);
  }, [onCommit, result]);

  useEffect(() => {
    function handleKey(event: KeyboardEvent) {
      if (event.altKey || event.ctrlKey || event.metaKey) return;
      if (event.key === "Escape" && !result) { onClose(); return; }
      if (beat < 2 && (event.key === "Enter" || event.key === " ")) {
        event.preventDefault();
        setBeat((value) => Math.min(2, value + 1));
        return;
      }
      if (beat === 2 && !result && /^Digit[1-3]$/.test(event.code)) {
        const choice = encounter?.choices[Number(event.code.at(-1)) - 1];
        if (choice) choose(choice);
      }
    }
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [beat, choose, encounter, onClose, result]);

  if (!encounter) return null;
  const speaker = beat === 0 ? "NARRATION" : name.split(" ")[0].toUpperCase();
  const line = beat === 0 ? encounter.opening : beat === 1 ? moment.dialogue : encounter.prompt;
  const npcExpression: Expression = result ? (result.id === "honest" || result.id === "coffee" || result.id === "game" || result.id === "ordinary" ? "warm" : "firm") : beat === 0 ? "neutral" : beat === 1 ? "concerned" : "firm";
  const renExpression: Expression = result ? "warm" : beat === 2 ? "concerned" : "neutral";
  return <section className="bond-vn" role="dialog" aria-modal="true" aria-labelledby="bond-vn-title">
    <Image className="bond-vn-bg" src={encounter.background} alt={`Illustrated ${location}`} fill sizes="100vw" priority />
    <div className="bond-vn-shade" />
    <div className="bond-vn-cast" aria-hidden="true"><ExpressionPortrait side="left" sheet="/game/visual-novel/expressions/ren-sheet-v2.png" expression={renExpression} active={speaker === "REN"} /><ExpressionPortrait side="right" sheet={encounter.portraitSheet} expression={npcExpression} active={speaker !== "NARRATION"} /></div>
    <header><small>OPTIONAL BOND / TIMELINE {timeline} / RANK {level}</small><h1 id="bond-vn-title">{moment.title}</h1><span>{location}</span></header>
    <div className="bond-vn-panel">
      {!result && beat < 2 && <div className="bond-vn-line" aria-live="polite"><small>{speaker}</small><p>{line}</p><button onClick={() => setBeat((value) => value + 1)}>CONTINUE <span>ENTER / SPACE</span></button></div>}
      {!result && beat === 2 && <div className="bond-vn-choice"><small>{name.toUpperCase()}</small><p>{line}</p>{encounter.choices.map((choice, index) => <button key={choice.id} onClick={() => choose(choice)}><b>{index + 1}</b><span>{choice.label}</span><small>{choice.energyCost} ENERGY</small></button>)}</div>}
      {result && <div className="bond-vn-result" aria-live="polite"><small>BOND RANK {level} / {moment.chapter}</small><p>{result.reply}</p><dl><div><dt>RELATIONSHIP</dt><dd>+1</dd></div><div><dt>ENERGY</dt><dd>−{result.energyCost}</dd></div><div><dt>TIME</dt><dd>1 SLOT</dd></div></dl><button onClick={onClose}>RETURN TO TOKYO</button></div>}
    </div>
  </section>;
}
