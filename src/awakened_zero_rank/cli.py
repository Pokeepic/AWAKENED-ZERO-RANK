from __future__ import annotations

import argparse

from .journal import journal_entry
from .persistence import load_simulation, save_simulation
from .simulation import Simulation


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Observe an autonomous zero-rank life.")
    parser.add_argument("--days", type=int, default=7, help="days to simulate (default: 7)")
    parser.add_argument("--seed", type=int, default=42, help="reproducible seed")
    parser.add_argument("--load", metavar="FILE", help="continue an existing save")
    parser.add_argument("--save", metavar="FILE", help="save after this run")
    parser.add_argument("--technical-log", action="store_true", help="show decision reasons")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.days < 1:
        raise SystemExit("--days must be at least 1")

    simulation = load_simulation(args.load) if args.load else Simulation(seed=args.seed)
    protagonist = simulation.state.protagonist
    print("AWAKENED ZERO RANK — Ren's Chronicle")
    print(f"{protagonist.name} | {protagonist.location}\n")
    for _ in range(args.days * 4):
        event = simulation.step()
        print(event if args.technical_log else journal_entry(
            event, simulation.state.weather, simulation.state.temperature_c,
            simulation.state.protagonist.mood
        ))
        print()

    p = simulation.state.protagonist
    print("\nFinal state")
    print(
        f"Money: ¥{p.money:,} | Health: {p.health} | Energy: {p.energy} | "
        f"Hunger: {p.hunger} | Stress: {p.stress} | Knowledge: {p.knowledge} | "
        f"Fitness: {p.fitness} | Rank: {p.hunter_rank} ({p.rank_points} RP) | "
        f"Readiness: {p.combat_readiness} | Missions: {p.missions_completed}/{p.missions_attempted} | "
        f"Injuries: {p.injuries} (severity {p.injury_severity}/5) | Ability: {p.ability} | Location: {p.location} | "
        f"Rent arrears: ¥{p.rent_arrears:,}"
    )
    print(f"Mood: {p.mood} | Morale: {p.morale}/100 | Social confidence: {p.social_confidence}")
    print(
        f"Hunter attributes: STR {p.strength} | AGI {p.agility} | END {p.endurance} | "
        f"PER {p.perception} | MANA {p.mana} | LUCK {p.luck} | "
        f"Ability mastery {p.ability_mastery}/100 | Echo exposure {p.echo_fragments}"
    )
    inventory = ", ".join(f"{name} x{count}" for name, count in sorted(p.inventory.items())) or "empty"
    print(f"Equipment: {p.equipped_weapon or 'none'} / {p.equipped_armor or 'none'} | Inventory: {inventory}")
    print(f"Weather: {simulation.state.weather}, {simulation.state.temperature_c}°C | Season: {simulation.state.season}")
    print(f"Current goal: {p.current_goal}")
    if p.relationships:
        print("Relationships: " + "; ".join(
            f"{person.name} ({person.role}) trust {person.trust}, familiarity {person.familiarity}, "
            f"affection {person.affection}, tension {person.tension}, loyalty {person.loyalty}"
            for person in p.relationships.values()
        ))
    if simulation.state.discovered_portals:
        print("Portals discovered: " + ", ".join(simulation.state.discovered_portals))
    if p.memories:
        print("Key memories:")
        for memory in p.memories[:5]:
            print(f"- Day {memory.day}: {memory.summary}")
    if args.save:
        save_simulation(simulation, args.save)
        print(f"\nTimeline saved to {args.save}")
