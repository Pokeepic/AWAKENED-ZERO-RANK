import unittest

from awakened_zero_rank.models import TimeSlot
from awakened_zero_rank.simulation import Simulation


class SimulationTests(unittest.TestCase):
    def test_four_actions_advance_exactly_one_day(self) -> None:
        simulation = Simulation(seed=1)
        simulation.run(4)
        self.assertEqual(simulation.state.clock.day, 2)
        self.assertEqual(simulation.state.clock.slot, TimeSlot.MORNING)

    def test_same_seed_produces_identical_log(self) -> None:
        first = [str(event) for event in Simulation(seed=77).run(60)]
        second = [str(event) for event in Simulation(seed=77).run(60)]
        self.assertEqual(first, second)

    def test_simulation_preserves_stat_bounds(self) -> None:
        simulation = Simulation(seed=12)
        simulation.run(400)
        p = simulation.state.protagonist
        for value in (p.health, p.energy, p.hunger, p.stress):
            self.assertGreaterEqual(value, 0)
            self.assertLessEqual(value, 100)

    def test_every_event_explains_the_decision(self) -> None:
        events = Simulation(seed=3).run(20)
        self.assertTrue(all(event.reason for event in events))
        self.assertTrue(all("utility" in event.reason for event in events if "world event" not in event.reason))

    def test_awakening_occurs_at_bureau_on_day_three(self) -> None:
        simulation = Simulation(seed=3)
        events = simulation.run(10)
        p = simulation.state.protagonist
        self.assertEqual(events[-1].action, "Awakening assessment")
        self.assertEqual((p.hunter_rank, p.ability), ("F", "Threat Sense"))

    def test_guild_registration_unlocks_hunter_work(self) -> None:
        simulation = Simulation(seed=3)
        events = simulation.run(13)
        self.assertEqual(events[-1].action, "Guild registration")
        self.assertTrue(simulation.state.protagonist.guild_registered)

    def test_gate_missions_track_outcomes_and_injuries(self) -> None:
        simulation = Simulation(seed=42)
        events = simulation.run(80)
        p = simulation.state.protagonist
        self.assertTrue(any(event.action == "Gate mission" for event in events))
        self.assertEqual(p.missions_attempted, p.missions_completed + p.injuries)
        self.assertGreaterEqual(p.combat_experience, p.missions_attempted * 2)

    def test_successful_missions_can_promote_hunter(self) -> None:
        simulation = Simulation(seed=42)
        simulation.run(240)
        p = simulation.state.protagonist
        self.assertGreater(p.missions_completed, 0)
        if p.rank_points >= 30:
            self.assertNotEqual(p.hunter_rank, "F")

    def test_rent_deadline_is_resolved_once(self) -> None:
        simulation = Simulation(seed=9)
        events = simulation.run(29)
        self.assertEqual(sum(event.action == "Rent deadline" for event in events), 1)
        resolved = simulation.state.rent_payments + int(simulation.state.protagonist.rent_arrears > 0)
        self.assertEqual(resolved, 1)

    def test_money_never_becomes_negative(self) -> None:
        simulation = Simulation(seed=18)
        simulation.run(100)
        self.assertGreaterEqual(simulation.state.protagonist.money, 0)


if __name__ == "__main__":
    unittest.main()
