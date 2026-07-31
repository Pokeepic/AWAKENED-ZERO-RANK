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
        first = [str(event) for event in Simulation(seed=77).run(28)]
        second = [str(event) for event in Simulation(seed=77).run(28)]
        self.assertEqual(first, second)

    def test_simulation_preserves_stat_bounds(self) -> None:
        simulation = Simulation(seed=12)
        simulation.run(400)
        p = simulation.state.protagonist
        for value in (p.health, p.energy, p.hunger, p.stress):
            self.assertGreaterEqual(value, 0)
            self.assertLessEqual(value, 100)

    def test_every_event_explains_the_decision(self) -> None:
        events = Simulation(seed=3).run(12)
        self.assertTrue(all(event.reason for event in events))
        self.assertTrue(all("utility" in event.reason for event in events if "world event" not in event.reason))

    def test_awakening_occurs_at_bureau_on_day_three(self) -> None:
        simulation = Simulation(seed=3)
        events = simulation.run(10)
        p = simulation.state.protagonist
        self.assertEqual(events[-1].action, "Awakening assessment")
        self.assertTrue(p.awakened)
        self.assertEqual((p.hunter_rank, p.ability), ("F", "Threat Sense"))
        self.assertEqual(p.location, "Tokyo Awakening Bureau")

    def test_rent_deadline_is_resolved_once(self) -> None:
        simulation = Simulation(seed=9)
        events = simulation.run(29)
        self.assertEqual(sum(event.action == "Rent deadline" for event in events), 1)
        resolved = simulation.state.rent_payments + int(simulation.state.protagonist.rent_arrears > 0)
        self.assertEqual(resolved, 1)

    def test_travel_never_makes_money_negative(self) -> None:
        simulation = Simulation(seed=18)
        simulation.run(80)
        self.assertGreaterEqual(simulation.state.protagonist.money, 0)


if __name__ == "__main__":
    unittest.main()
