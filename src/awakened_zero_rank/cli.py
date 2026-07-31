from __future__ import annotations

import argparse

from .simulation import Simulation


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Observe an autonomous zero-rank life.")
    parser.add_argument("--days", type=int, default=7, help="days to simulate (default: 7)")
    parser.add_argument("--seed", type=int, default=42, help="reproducible seed")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.days < 1:
        raise SystemExit("--days must be at least 1")

    simulation = Simulation(seed=args.seed)
    protagonist = simulation.state.protagonist
    print("AWAKENED ZERO RANK — Observer Log")
    print(f"Watching {protagonist.name} in {protagonist.location} (seed {args.seed})\n")
    for event in simulation.run(args.days * 4):
        print(event)

    p = simulation.state.protagonist
    print("\nFinal state")
    print(
        f"Money: ¥{p.money:,} | Health: {p.health} | Energy: {p.energy} | "
        f"Hunger: {p.hunger} | Stress: {p.stress} | "
        f"Knowledge: {p.knowledge} | Fitness: {p.fitness} | Rank: {p.hunter_rank}"
    )

