from __future__ import annotations

import random

from .agent import UtilityAgent
from .environment import SUMMER_WEATHER, summer_weather
from .models import Event, Memory, Relationship, WorldState
from .world import GATE_ENCOUNTERS, ITEMS, travel_cost


RANK_THRESHOLDS = ((90, "C"), (60, "D"), (30, "E"))


class Simulation:
    def __init__(self, seed: int = 42, state: WorldState | None = None) -> None:
        self.seed = seed
        self.state = state or WorldState()
        self.rng = random.Random(seed)
        self.agent = UtilityAgent(self.rng)

    def step(self) -> Event:
        clock = self.state.clock
        protagonist = self.state.protagonist
        self._update_weather()
        special = self._special_event()
        if special is not None:
            self.state.events.append(special)
            self._remember(special)
            self._update_goal()
            clock.advance()
            return special
        action, reason = self.agent.choose(
            protagonist, clock.slot, self.state.gate_alert_level, self.state.weather
        )
        if action.name == "Visit hunter shop" and self._weather().shop_closed:
            outcome = "The hunter supply shop was closed under the severe-weather advisory."
        else:
            outcome = self._resolve_gate_mission() if action.name == "Gate mission" else action.apply(protagonist)
        if action.name == "Visit hunter shop":
            self.state.shop_visits += 1
        self._apply_passive_needs()
        self._apply_weather_cost(action.name)
        protagonist.clamp()
        event = Event(clock.day, clock.slot, action.name, reason, outcome)
        self.state.events.append(event)
        self._remember(event)
        self._update_goal()
        self._update_gate_alert()
        clock.advance()
        return event

    def _weather(self):
        return next(weather for weather in SUMMER_WEATHER if weather.name == self.state.weather)

    def _update_weather(self) -> None:
        clock = self.state.clock
        if self.state.weather_day == clock.day:
            return
        weather = summer_weather(self.rng)
        self.state.weather = weather.name
        self.state.temperature_c = weather.temperature_c
        self.state.weather_day = clock.day

    def _apply_weather_cost(self, action_name: str) -> None:
        weather = self._weather()
        if action_name in {"Train", "Gate mission", "Guild patrol", "Part-time work"}:
            self.state.protagonist.energy -= weather.energy_modifier

    def run(self, steps: int) -> list[Event]:
        return [self.step() for _ in range(steps)]

    def _apply_passive_needs(self) -> None:
        p = self.state.protagonist
        if p.hunger >= 85:
            p.health -= 8
        if p.energy <= 10:
            p.health -= 5
            p.stress += 8

    def _special_event(self) -> Event | None:
        clock = self.state.clock
        p = self.state.protagonist

        if clock.day == 7 and clock.slot.value == "Evening" and "Tanabata" not in self.state.calendar_events_seen:
            self.state.calendar_events_seen.append("Tanabata")
            p.stress -= 8
            p.relationships.get("Aiko Sato") and p.relationships["Aiko Sato"].change(2, 3)
            p.clamp()
            return Event(clock.day, clock.slot, "Tanabata evening",
                         "the neighborhood festival arrived on the calendar (world event)",
                         "Stopped beneath the paper wishes and festival lights; the city felt hopeful for once.")

        if clock.day == 3 and clock.slot.value == "Afternoon" and not p.awakened:
            p.money -= min(p.money, 320)
            p.location = "Tokyo Awakening Bureau"
            p.awakened = True
            p.hunter_rank = "F"
            p.ability = "Threat Sense"
            p.reputation += 1
            return Event(clock.day, clock.slot, "Awakening assessment",
                         "a city gate alert triggered Ren's mandatory screening (world event)",
                         "Awakened at Rank F with Threat Sense.")

        if clock.day == 4 and clock.slot.value == "Morning" and p.awakened and not p.guild_registered:
            fare = min(p.money, travel_cost(p.location, "Tokyo Hunter Guild"))
            p.money -= fare
            p.location = "Tokyo Hunter Guild"
            p.guild_registered = True
            p.relationships["Aiko Sato"] = Relationship(
                name="Aiko Sato", role="F-rank guild clerk", trust=3, familiarity=5, meetings=1
            )
            p.reputation += 1
            self.state.gate_alert_level = 2
            event = Event(clock.day, clock.slot, "Guild registration",
                         "newly awakened citizens must register before accepting hunter work (world event)",
                         f"Aiko Sato issued an F-rank license; travel and filing cost ¥{fare:,}.")
            return event

        if clock.day == p.rent_due_day and clock.slot.value == "Morning":
            paid = min(p.money, p.rent_cost)
            p.money -= paid
            unpaid = p.rent_cost - paid
            p.rent_arrears += unpaid
            p.stress += 5 if unpaid == 0 else 25
            p.clamp()
            self.state.rent_payments += int(unpaid == 0)
            outcome = (f"Paid ¥{paid:,} rent in full." if unpaid == 0 else
                       f"Paid ¥{paid:,}; ¥{unpaid:,} became rent arrears.")
            return Event(clock.day, clock.slot, "Rent deadline",
                         "the apartment payment was automatically due (world event)", outcome)
        return None

    def _remember(self, event: Event, importance: int | None = None) -> None:
        p = self.state.protagonist
        important_actions = {
            "Awakening assessment": 10, "Guild registration": 8,
            "Gate mission": 7, "Rent deadline": 8, "Talk with Aiko": 4,
        }
        rating = importance if importance is not None else important_actions.get(event.action)
        if rating is None:
            return
        p.memories.append(Memory(event.day, f"{event.action}: {event.outcome}", rating))
        p.memories.sort(key=lambda memory: (-memory.importance, -memory.day))
        del p.memories[12:]

    def _update_goal(self) -> None:
        p = self.state.protagonist
        if not p.awakened:
            p.current_goal = "Earn enough yen to pay rent"
        elif not p.guild_registered:
            p.current_goal = "Register with the Tokyo Hunter Guild"
        elif p.rent_arrears:
            p.current_goal = f"Clear ¥{p.rent_arrears:,} in rent arrears"
        elif p.hunter_rank == "F":
            p.current_goal = "Survive gate work and reach Rank E"
        else:
            p.current_goal = f"Build a stable life as a Rank {p.hunter_rank} hunter"

    def _resolve_gate_mission(self) -> str:
        p = self.state.protagonist
        fare = min(p.money, travel_cost(p.location, "Adachi Gate Zone"))
        p.money -= fare
        p.location = "Adachi Gate Zone"
        p.missions_attempted += 1
        alert = self.state.gate_alert_level
        maximum_index = min(len(GATE_ENCOUNTERS) - 1, max(0, alert - 1))
        encounter = GATE_ENCOUNTERS[self.rng.randint(0, maximum_index)]
        weather = self._weather()
        difficulty = encounter.difficulty + alert * 3 + weather.gate_difficulty
        preparation = []
        if p.health < 68 and p.consume_item("Healing Gel"):
            healed = min(22, 100 - p.health)
            p.health += healed
            preparation.append(f"used Healing Gel (+{healed} health)")
        if p.energy < 48 and p.consume_item("Energy Drink"):
            restored = min(18, 100 - p.energy)
            p.energy += restored
            preparation.append(f"used Energy Drink (+{restored} energy)")
        roll = p.combat_readiness + self.rng.randint(-12, 12)
        p.energy -= 28
        p.hunger += 18
        p.stress += 12
        self.state.gate_alert_level = max(0, alert - 2)
        prep_text = f" Preparation: {', '.join(preparation)}." if preparation else ""
        if roll >= difficulty:
            reward = encounter.reward
            points = encounter.rank_points
            p.money += reward
            p.rank_points += points
            p.combat_experience += 5
            p.missions_completed += 1
            p.reputation += 2
            promotion = self._promote_if_eligible()
            suffix = f" Promoted to Rank {promotion}!" if promotion else ""
            return (f"Cleared {encounter.name} in {weather.name.lower()} weather "
                    f"(roll {roll} vs {difficulty}) for ¥{reward:,} "
                    f"and {points} rank points; fare cost ¥{fare:,}.{prep_text}{suffix}")
        armor_reduction = ITEMS[p.equipped_armor].combat_bonus if p.equipped_armor else 0
        damage = max(8, difficulty - roll + 8 + encounter.damage_bonus - armor_reduction)
        p.health -= damage
        p.injuries += 1
        p.combat_experience += 2
        return (f"Retreated from {encounter.name} in {weather.name.lower()} weather "
                f"(roll {roll} vs {difficulty}); suffered "
                f"{damage} damage and received no reward. Fare cost ¥{fare:,}.{prep_text}")

    def _promote_if_eligible(self) -> str | None:
        p = self.state.protagonist
        order = {"F": 0, "E": 1, "D": 2, "C": 3}
        for threshold, rank in RANK_THRESHOLDS:
            if p.rank_points >= threshold and order.get(rank, 0) > order.get(p.hunter_rank, -1):
                p.hunter_rank = rank
                return rank
        return None

    def _update_gate_alert(self) -> None:
        if self.rng.random() < 0.12:
            self.state.gate_alert_level = min(3, self.state.gate_alert_level + 1)
            self.state.protagonist.gates_witnessed += 1
        elif self.state.gate_alert_level:
            self.state.gate_alert_level -= 1
