"""Training episodes, tabular Q-learning, and utility-policy comparison.

The core adapter stays dependency-free. Installing the ``training`` extra upgrades
its compatible fallback spaces to Gymnasium's official Env, Discrete, and Box types.
"""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
from dataclasses import asdict, dataclass, field
import hashlib
import json
import math
import random
from pathlib import Path

try:
    import gymnasium as gym
    import numpy as np
except ImportError:  # The core simulation remains dependency-free.
    gym = None
    np = None

from .actions import available_actions
from .models import Protagonist, Relationship, SLOTS, TimeSlot
from .simulation import Simulation


ACTION_NAMES = (
    "Eat", "Rest", "Part-time work", "Pay rent arrears", "Study", "Train",
    "Visit hunter shop",
    "Talk with Aiko", "Guild patrol", "Prepare portal", "Gate mission", "Seek treatment",
)
REWARD_COMPONENTS = ("survival", "stability", "progress", "social")
EVALUATION_CONDITIONS = ("standard", "financial_pressure", "injury_recovery",
                         "gate_crisis", "compound_crisis")
MAX_DOMINANCE_REGRESSION = 0.15
MIN_TRAINING_CONDITION_EPISODES = 2
SEEN_STATE_COUNTERFACTUAL_HORIZON = 4
ACTION_ENERGY_COSTS = {
    "Part-time work": 22, "Study": 13, "Train": 20,
    "Talk with Aiko": 8, "Guild patrol": 27,
    "Prepare portal": 10, "Gate mission": 28,
}


@dataclass(frozen=True)
class Transition:
    observation: tuple[float, ...]
    reward: float
    action: str
    valid_actions: tuple[str, ...]
    event_outcome: str
    reward_components: tuple[tuple[str, float], ...] = ()
    resolved_action: str = ""


class LearningEnvironment:
    """Small strategic interface suitable for accelerated agent experiments."""

    def __init__(self, seed: int = 42) -> None:
        self.simulation = Simulation(seed=seed)

    @property
    def valid_actions(self) -> tuple[str, ...]:
        names = {action.name for action in available_actions(self.simulation.state.protagonist)}
        return tuple(name for name in ACTION_NAMES if name in names)

    def observe(self) -> tuple[float, ...]:
        state, p = self.simulation.state, self.simulation.state.protagonist
        relationship = p.relationships.get("Aiko Sato")
        network_trust = sum(r.trust for r in p.relationships.values())
        return (
            p.health / 100, p.energy / 100, p.hunger / 100, p.stress / 100,
            min(p.money, 50_000) / 50_000, p.combat_readiness / 100,
            p.rank_points / 100, state.gate_alert_level / 3,
            SLOTS.index(state.clock.slot) / (len(SLOTS) - 1),
            (relationship.trust if relationship else 0) / 100,
            (relationship.tension if relationship else 0) / 100,
            p.morale / 100,
            max(-1, min(1, network_trust / 400)),
            len(state.discovered_portals) / 6,
            int(state.active_portal_plan is not None),
            min(1, sum(i.preparation_bonus for i in state.portal_investigations.values()) / 30),
            min(1, sum(i.joint_missions for i in state.portal_investigations.values()) / 10),
            min(1, sum(state.objective_scores.values()) / 400),
            p.injury_severity / 5,
            self.simulation.state.wage_modifier / 115,
            self.simulation.state.meal_cost / 800,
            min(1, sum(state.objective_progress.values()) / 9),
        )

    def action_mask(self) -> tuple[int, ...]:
        valid = set(self.valid_actions)
        return tuple(int(name in valid) for name in ACTION_NAMES)

    def step(self, action: str) -> Transition:
        if action not in self.valid_actions:
            raise ValueError(f"Invalid action {action!r}; valid actions: {self.valid_actions}")
        before = self.score_components()
        event = self.simulation.step(action)
        components = self._component_delta(before)
        reward = round(sum(value for _, value in components), 3)
        components = self._reconcile_components(components, reward)
        return Transition(self.observe(), reward, action, self.valid_actions,
                          event.outcome, components, event.action)

    def baseline_step(self) -> Transition:
        before = self.score_components()
        event = self.simulation.step()
        components = self._component_delta(before)
        reward = round(sum(value for _, value in components), 3)
        components = self._reconcile_components(components, reward)
        return Transition(self.observe(), reward, event.action, self.valid_actions,
                          event.outcome, components, event.action)

    def score_components(self) -> dict[str, float]:
        p = self.simulation.state.protagonist
        survival = p.health * 0.5 + p.energy * 0.12 - p.hunger * 0.12 - p.stress * 0.08
        stability = min(p.money, p.rent_cost * 2) / 350 - p.rent_arrears / 250
        progress = p.rank_points * 0.7 + p.missions_completed * 2 + p.ability_mastery * 0.2
        social = sum((r.trust - r.tension) * 0.08 for r in p.relationships.values())
        return {"survival": survival, "stability": stability,
                "progress": progress, "social": social}

    def _component_delta(self, before: dict[str, float]) -> tuple[tuple[str, float], ...]:
        after = self.score_components()
        return tuple((name, after[name] - before[name])
                     for name in REWARD_COMPONENTS)

    @staticmethod
    def _reconcile_components(components: tuple[tuple[str, float], ...],
                              reward: float) -> tuple[tuple[str, float], ...]:
        reconciled = list(components)
        name, value = reconciled[-1]
        reconciled[-1] = (name, value + reward - sum(item for _, item in reconciled))
        return tuple(reconciled)

    def _score(self) -> float:
        return sum(self.score_components().values())

class DiscreteSpace:
    def __init__(self, n: int, seed: int | None = None) -> None:
        self.n, self._rng = n, random.Random(seed)

    def seed(self, seed: int | None = None) -> list[int | None]:
        self._rng.seed(seed)
        return [seed]

    def sample(self, mask: tuple[int, ...] | None = None) -> int:
        choices = list(range(self.n) if mask is None else [i for i, valid in enumerate(mask) if valid])
        if not choices:
            raise ValueError("Cannot sample when no actions are valid")
        return self._rng.choice(choices)

    def contains(self, value: object) -> bool:
        return isinstance(value, int) and not isinstance(value, bool) and 0 <= value < self.n


class ObservationSpace:
    shape = (22,)

    @staticmethod
    def contains(value: object) -> bool:
        return (isinstance(value, (tuple, list)) and len(value) == 22 and
                all(isinstance(item, (int, float)) and math.isfinite(item) for item in value))


class TrainingEnvironment(gym.Env if gym else object):
    """Gymnasium-style fixed-horizon episodes with integer policy actions."""
    metadata = {"render_modes": []}

    def __init__(self, seed: int = 42, horizon: int = 120) -> None:
        if horizon < 1:
            raise ValueError("horizon must be at least 1")
        self.initial_seed, self.horizon = seed, horizon
        if gym:
            self.action_space = gym.spaces.Discrete(len(ACTION_NAMES), seed=seed)
            self.observation_space = gym.spaces.Box(
                low=-float("inf"), high=float("inf"), shape=(22,), dtype=np.float32
            )
        else:
            self.action_space = DiscreteSpace(len(ACTION_NAMES), seed)
            self.observation_space = ObservationSpace()
        self.environment = LearningEnvironment(seed)
        self.condition = "standard"
        self.elapsed_steps, self._finished = 0, False

    @property
    def simulation(self) -> Simulation:
        return self.environment.simulation

    def action_masks(self) -> tuple[int, ...]:
        return self.environment.action_mask()

    def reset(self, *, seed: int | None = None, options: dict | None = None
              ) -> tuple[tuple[float, ...], dict]:
        if gym:
            super().reset(seed=seed)
        episode_seed = self.initial_seed if seed is None else seed
        self.condition = (options or {}).get("condition", "standard")
        self.environment = LearningEnvironment(episode_seed)
        _configure_evaluation_condition(self.environment, self.condition)
        self.action_space.seed(episode_seed)
        self.elapsed_steps, self._finished = 0, False
        observation = self.environment.observe()
        if np is not None:
            observation = np.asarray(observation, dtype=np.float32)
        return observation, {"action_mask": self.action_masks(), "seed": episode_seed,
                             "condition": self.condition}

    def step(self, action: int) -> tuple[tuple[float, ...], float, bool, bool, dict]:
        if self._finished:
            raise RuntimeError("Episode is finished; call reset() before step()")
        if not self.action_space.contains(action):
            raise ValueError(f"Action must be an integer from 0 to {len(ACTION_NAMES) - 1}")
        mask = self.action_masks()
        if not mask[action]:
            raise ValueError(f"Action {action} ({ACTION_NAMES[action]}) is currently invalid")
        transition = self.environment.step(ACTION_NAMES[action])
        self.elapsed_steps += 1
        terminated = self.simulation.state.protagonist.health <= 0
        truncated = self.elapsed_steps >= self.horizon and not terminated
        self._finished = terminated or truncated
        info = {"action_mask": self.action_masks(), "action_name": transition.action,
                "event_outcome": transition.event_outcome, "elapsed_steps": self.elapsed_steps,
                "reward_components": dict(transition.reward_components),
                "resolved_action": transition.resolved_action, "condition": self.condition}
        observation = transition.observation
        if np is not None:
            observation = np.asarray(observation, dtype=np.float32)
        return observation, transition.reward, terminated, truncated, info


GymnasiumEnvironment = TrainingEnvironment


@dataclass(frozen=True)
class QLearningConfig:
    episodes: int = 40
    horizon: int = 120
    training_horizons: tuple[int, ...] = ()
    learning_rate: float = 0.15
    discount_factor: float = 0.95
    epsilon_start: float = 0.30
    epsilon_end: float = 0.05
    exploration_bonus: float = 0.40
    progression_exploration_bonus: float = 0.0
    progression_sampling_rate: float = 0.0
    priority_clear_progression_sampling_rate: float = 0.0
    preventive_rest_threshold: int = 0
    preventive_rest_max_injury_severity: int = 0
    energy_preemption_floor: int = 0
    seen_recovery_utility_override: bool = False
    curriculum: bool = True
    training_rent_reserve: bool = False
    training_conditions: tuple[str, ...] = ("standard",)
    unseen_state_fallback: str = "first_valid"

    def __post_init__(self) -> None:
        object.__setattr__(self, "training_conditions", tuple(self.training_conditions))
        horizons = tuple(self.training_horizons) or (self.horizon,)
        object.__setattr__(self, "training_horizons", horizons)
        if any(type(value) is not int or value < 1 for value in horizons):
            raise ValueError("training_horizons must contain positive integers")
        if not self.training_conditions:
            raise ValueError("At least one training condition is required")
        unknown = set(self.training_conditions) - set(EVALUATION_CONDITIONS)
        if unknown:
            raise ValueError(f"Unknown training conditions: {sorted(unknown)}")
        if self.episodes < 1 or self.horizon < 1:
            raise ValueError("episodes and horizon must be at least 1")
        if not 0 < self.learning_rate <= 1 or not 0 <= self.discount_factor <= 1:
            raise ValueError("learning_rate and discount_factor must be between 0 and 1")
        if not 0 <= self.epsilon_end <= self.epsilon_start <= 1:
            raise ValueError("epsilon must satisfy 0 <= end <= start <= 1")
        if self.exploration_bonus < 0:
            raise ValueError("exploration_bonus cannot be negative")
        if self.progression_exploration_bonus < 0:
            raise ValueError("progression_exploration_bonus cannot be negative")
        if not 0 <= self.progression_sampling_rate <= 1:
            raise ValueError("progression_sampling_rate must be between 0 and 1")
        if not 0 <= self.priority_clear_progression_sampling_rate <= 1:
            raise ValueError(
                "priority_clear_progression_sampling_rate must be between 0 and 1")
        progression_modes = (
            bool(self.progression_exploration_bonus),
            bool(self.progression_sampling_rate),
            bool(self.priority_clear_progression_sampling_rate),
        )
        if sum(progression_modes) > 1:
            raise ValueError("progression exploration modes are mutually exclusive")
        if (type(self.preventive_rest_threshold) is not int or
                not 0 <= self.preventive_rest_threshold <= 100):
            raise ValueError("preventive_rest_threshold must be an integer from 0 to 100")
        if (type(self.preventive_rest_max_injury_severity) is not int or
                not 0 <= self.preventive_rest_max_injury_severity <= 4):
            raise ValueError(
                "preventive_rest_max_injury_severity must be an integer from 0 to 4")
        if (type(self.energy_preemption_floor) is not int or
                not 0 <= self.energy_preemption_floor <= 100):
            raise ValueError(
                "energy_preemption_floor must be an integer from 0 to 100")
        if type(self.training_rent_reserve) is not bool:
            raise ValueError("training_rent_reserve must be a boolean")
        if type(self.seen_recovery_utility_override) is not bool:
            raise ValueError("seen_recovery_utility_override must be a boolean")
        if self.unseen_state_fallback not in {"first_valid", "heuristic", "utility"}:
            raise ValueError("unknown unseen-state fallback")


QTable = dict[tuple[int, ...], list[float]]


@dataclass(frozen=True)
class PreparationReturnSample:
    state: tuple[int, ...]
    discounted_return: float
    steps: int
    plan_consumed: bool


@dataclass(frozen=True)
class PreparationPlanReturn:
    initial_state: tuple[int, ...]
    preparation_steps: int
    discounted_return: float
    steps: int
    plan_consumed: bool


@dataclass(frozen=True)
class TrainingResult:
    training_seed: int
    config: QLearningConfig
    q_table: QTable = field(compare=True)
    episode_rewards: tuple[float, ...] = ()
    episode_seeds: tuple[int, ...] = ()
    training_rewards: tuple[float, ...] = ()
    state_count: int = 0
    episode_conditions: tuple[str, ...] = ()
    episode_horizons: tuple[int, ...] = ()
    episode_state_counts: tuple[int, ...] = ()
    visit_table: dict[tuple[int, ...], list[int]] = field(default_factory=dict)
    episode_gate_priority_clear_steps: tuple[int, ...] = ()
    episode_gate_priority_clear_selections: tuple[int, ...] = ()
    episode_preparation_priority_clear_steps: tuple[int, ...] = ()
    episode_preparation_priority_clear_selections: tuple[int, ...] = ()
    episode_preparation_ready_steps: tuple[int, ...] = ()
    episode_preparation_blocker_counts: tuple[
        tuple[tuple[str, int], ...], ...] = ()
    episode_portal_preparations: tuple[int, ...] = ()
    episode_prepared_missions_attempted: tuple[int, ...] = ()
    episode_prepared_missions_completed: tuple[int, ...] = ()
    reward_table: dict[tuple[int, ...], list[float]] = field(default_factory=dict)
    discounted_return_table: dict[
        tuple[int, ...], list[float]] = field(default_factory=dict)
    preparation_return_samples: tuple[PreparationReturnSample, ...] = ()
    preparation_plan_returns: tuple[PreparationPlanReturn, ...] = ()
    preparation_plan_contexts: tuple[tuple[str, int], ...] = ()


@dataclass(frozen=True)
class TrainingConditionSummary:
    condition: str
    episode_count: int
    average_reward: float
    average_training_reward: float
    worst_reward: float
    average_unique_states: float
    minimum_unique_states: int


def summarize_training_conditions(
        result: TrainingResult) -> tuple[TrainingConditionSummary, ...]:
    """Summarize deterministic reward evidence for each observed condition."""
    count = len(result.episode_rewards)
    if (len(result.episode_conditions) != count or
            len(result.training_rewards) != count or
            len(result.episode_state_counts) != count):
        raise ValueError("Training episode diagnostics are incomplete")
    summaries = []
    for condition in dict.fromkeys(result.episode_conditions):
        indices = [index for index, value in enumerate(result.episode_conditions)
                   if value == condition]
        rewards = [result.episode_rewards[index] for index in indices]
        training_rewards = [result.training_rewards[index] for index in indices]
        state_counts = [result.episode_state_counts[index] for index in indices]
        summaries.append(TrainingConditionSummary(
            condition=condition,
            episode_count=len(indices),
            average_reward=round(sum(rewards) / len(rewards), 3),
            average_training_reward=round(
                sum(training_rewards) / len(training_rewards), 3),
            worst_reward=round(min(rewards), 3),
            average_unique_states=round(sum(state_counts) / len(state_counts), 3),
            minimum_unique_states=min(state_counts),
        ))
    return tuple(summaries)


@dataclass(frozen=True)
class PreparationPlanContextSummary:
    condition: str
    horizon: int
    plan_count: int
    consumed_count: int
    positive_consumed_count: int
    average_consumed_return: float | None
    censored_count: int


def summarize_preparation_plan_contexts(
        result: TrainingResult) -> tuple[PreparationPlanContextSummary, ...]:
    """Summarize independent preparation-plan outcomes by training cell."""
    if (not result.preparation_plan_returns or
            len(result.preparation_plan_contexts) !=
            len(result.preparation_plan_returns)):
        raise ValueError("Preparation plan context evidence is unavailable")
    grouped: dict[tuple[str, int], list[PreparationPlanReturn]] = {}
    for context, sample in zip(
            result.preparation_plan_contexts, result.preparation_plan_returns):
        condition, horizon = context
        if (condition not in EVALUATION_CONDITIONS or
                not isinstance(horizon, int) or isinstance(horizon, bool) or
                horizon < 1 or sample.preparation_steps < 1 or sample.steps < 1 or
                not math.isfinite(sample.discounted_return)):
            raise ValueError("Preparation plan context evidence is invalid")
        grouped.setdefault(context, []).append(sample)
    summaries = []
    for (condition, horizon), samples in grouped.items():
        consumed = [sample for sample in samples if sample.plan_consumed]
        summaries.append(PreparationPlanContextSummary(
            condition=condition, horizon=horizon, plan_count=len(samples),
            consumed_count=len(consumed),
            positive_consumed_count=sum(
                sample.discounted_return > 0 for sample in consumed),
            average_consumed_return=(
                round(sum(sample.discounted_return for sample in consumed) /
                      len(consumed), 3) if consumed else None),
            censored_count=len(samples) - len(consumed),
        ))
    return tuple(summaries)


@dataclass(frozen=True)
class TrainingProgressionCoverage:
    action: str
    priority_clear_steps: int
    selection_count: int
    selection_rate: float | None


def summarize_training_progression(
        result: TrainingResult) -> tuple[TrainingProgressionCoverage, ...]:
    """Summarize authenticated priority-clear progression exposure in training."""
    episode_count = len(result.episode_rewards)
    evidence = (
        result.episode_gate_priority_clear_steps,
        result.episode_gate_priority_clear_selections,
        result.episode_preparation_priority_clear_steps,
        result.episode_preparation_priority_clear_selections,
    )
    if any(len(values) != episode_count for values in evidence):
        raise ValueError("Training progression diagnostics are unavailable or incomplete")
    if any(type(value) is not int or value < 0
           for values in evidence for value in values):
        raise ValueError("Training progression diagnostics are invalid")
    if any(selection > step
           for steps, selections in ((evidence[0], evidence[1]),
                                      (evidence[2], evidence[3]))
           for step, selection in zip(steps, selections)):
        raise ValueError("Training progression selections exceed opportunities")
    summaries = []
    for action, steps, selections in (
            ("Gate mission", evidence[0], evidence[1]),
            ("Prepare portal", evidence[2], evidence[3])):
        total_steps, total_selections = sum(steps), sum(selections)
        summaries.append(TrainingProgressionCoverage(
            action=action, priority_clear_steps=total_steps,
            selection_count=total_selections,
            selection_rate=(round(total_selections / total_steps, 3)
                            if total_steps else None),
        ))
    return tuple(summaries)


def summarize_training_preparation_blockers(
        result: TrainingResult) -> tuple[tuple[str, int], ...]:
    """Aggregate authenticated blockers on preparation-ready training steps."""
    episode_count = len(result.episode_rewards)
    if (len(result.episode_preparation_ready_steps) != episode_count or
            len(result.episode_preparation_blocker_counts) != episode_count or
            len(result.episode_preparation_priority_clear_steps) != episode_count):
        raise ValueError("Training preparation blocker diagnostics are unavailable")
    blockers = Counter()
    for episode_blockers in result.episode_preparation_blocker_counts:
        for reason, count in episode_blockers:
            if not isinstance(reason, str) or type(count) is not int or count < 0:
                raise ValueError("Training preparation blocker diagnostics are invalid")
            blockers[reason] += count
    ready = result.episode_preparation_ready_steps
    if any(type(value) is not int or value < 0 for value in ready):
        raise ValueError("Training preparation blocker diagnostics are invalid")
    for ready_steps, clear_steps, episode_blockers in zip(
            ready, result.episode_preparation_priority_clear_steps,
            result.episode_preparation_blocker_counts):
        if clear_steps + sum(count for _, count in episode_blockers) != ready_steps:
            raise ValueError("Training preparation blockers do not reconcile")
    return tuple(sorted(blockers.items()))


@dataclass(frozen=True)
class TrainingActionExposure:
    action: str
    selection_count: int
    state_count: int
    selection_share: float


@dataclass(frozen=True)
class ActionNeighborEvidence:
    state: tuple[int, ...]
    distance: int
    action_visits: int
    q_value: float


@dataclass(frozen=True)
class ActionSafetyGroupEvidence:
    safety_state: tuple[int, ...]
    state_count: int
    action_visits: int
    positive_q_states: int
    average_state_q_value: float


ACTION_NEIGHBOR_SAFETY_INDICES = (0, 1, 2, 7, 11, 12)


def summarize_training_actions(
        result: TrainingResult) -> tuple[TrainingActionExposure, ...]:
    """Summarize exact action exposure retained in a trained policy visit table."""
    if not result.visit_table:
        raise ValueError("Training action exposure is unavailable")
    if any(len(counts) != len(ACTION_NAMES) or
           any(not isinstance(count, int) or count < 0 for count in counts)
           for counts in result.visit_table.values()):
        raise ValueError("Training action visit evidence is invalid")
    action_totals = [
        sum(counts[index] for counts in result.visit_table.values())
        for index in range(len(ACTION_NAMES))
    ]
    total = sum(action_totals)
    return tuple(
        TrainingActionExposure(
            action=name, selection_count=action_totals[index],
            state_count=sum(counts[index] > 0 for counts in result.visit_table.values()),
            selection_share=round(action_totals[index] / max(1, total), 3),
        )
        for index, name in enumerate(ACTION_NAMES)
    )


def summarize_action_safety_groups(
        result: TrainingResult, action: str,
        safety_indices: tuple[int, ...] = ACTION_NEIGHBOR_SAFETY_INDICES,
        ) -> tuple[ActionSafetyGroupEvidence, ...]:
    """Aggregate action evidence by exact safety context for diagnostics."""
    if action not in ACTION_NAMES:
        raise ValueError(f"Unknown action {action!r}")
    if (len(set(safety_indices)) != len(safety_indices) or
            any(not isinstance(index, int) or isinstance(index, bool) or
                not 0 <= index < 16 for index in safety_indices)):
        raise ValueError("Safety indices must be unique strategic-state indices")
    action_index = ACTION_NAMES.index(action)
    grouped: dict[tuple[int, ...], list[tuple[int, float]]] = {}
    for state, counts in result.visit_table.items():
        if (len(state) != 16 or len(counts) != len(ACTION_NAMES) or
                not isinstance(counts[action_index], int) or
                counts[action_index] < 0):
            raise ValueError("Training action visit evidence is invalid")
        if counts[action_index] == 0:
            continue
        values = result.q_table.get(state)
        if (values is None or len(values) != len(ACTION_NAMES) or
                not math.isfinite(values[action_index])):
            raise ValueError("Training action Q-value evidence is invalid")
        safety_state = tuple(state[index] for index in safety_indices)
        grouped.setdefault(safety_state, []).append(
            (counts[action_index], values[action_index]))
    return tuple(
        ActionSafetyGroupEvidence(
            safety_state=safety_state,
            state_count=len(evidence),
            action_visits=sum(visits for visits, _ in evidence),
            positive_q_states=sum(value > 0 for _, value in evidence),
            average_state_q_value=round(
                sum(value for _, value in evidence) / len(evidence), 6),
        )
        for safety_state, evidence in sorted(grouped.items())
    )


def nearest_action_neighbors(
        result: TrainingResult, state: tuple[int, ...], action: str,
        safety_indices: tuple[int, ...] = ACTION_NEIGHBOR_SAFETY_INDICES, *,
        max_distance: int | None = None, min_action_visits: int = 1,
        min_q_value: float | None = None,
        ) -> tuple[ActionNeighborEvidence, ...]:
    """Return nearest action-visited states while preserving safety context.

    This is diagnostic evidence only: policy selection continues to use exact
    tabular states and its configured unseen-state fallback.
    """
    if action not in ACTION_NAMES:
        raise ValueError(f"Unknown action {action!r}")
    if (len(state) != 16 or any(
            not isinstance(value, int) or isinstance(value, bool) or
            not 0 <= value <= 3 for value in state)):
        raise ValueError("Strategic state must contain 16 integers from 0 to 3")
    if (len(set(safety_indices)) != len(safety_indices) or
            any(not isinstance(index, int) or isinstance(index, bool) or
                not 0 <= index < len(state) for index in safety_indices)):
        raise ValueError("Safety indices must be unique strategic-state indices")
    if (max_distance is not None and (
            not isinstance(max_distance, int) or isinstance(max_distance, bool) or
            max_distance < 0)):
        raise ValueError("Maximum distance must be a non-negative integer or None")
    if (not isinstance(min_action_visits, int) or
            isinstance(min_action_visits, bool) or min_action_visits < 1):
        raise ValueError("Minimum action visits must be a positive integer")
    if (min_q_value is not None and (
            not isinstance(min_q_value, (int, float)) or
            isinstance(min_q_value, bool) or not math.isfinite(min_q_value))):
        raise ValueError("Minimum Q-value must be finite or None")
    action_index = ACTION_NAMES.index(action)
    candidates = []
    for candidate, counts in result.visit_table.items():
        if (len(candidate) != len(state) or len(counts) != len(ACTION_NAMES) or
                counts[action_index] < min_action_visits or
                any(candidate[index] != state[index] for index in safety_indices)):
            continue
        distance = sum(abs(left - right) for index, (left, right) in enumerate(
            zip(state, candidate)) if index not in safety_indices)
        q_value = result.q_table[candidate][action_index]
        if ((max_distance is not None and distance > max_distance) or
                (min_q_value is not None and q_value < min_q_value)):
            continue
        candidates.append(ActionNeighborEvidence(
            state=candidate, distance=distance,
            action_visits=counts[action_index], q_value=q_value,
        ))
    if not candidates:
        return ()
    minimum = min(candidate.distance for candidate in candidates)
    return tuple(sorted(
        (candidate for candidate in candidates if candidate.distance == minimum),
        key=lambda candidate: (-candidate.action_visits, -candidate.q_value,
                               candidate.state),
    ))


def abstract_state(observation) -> tuple[int, ...]:
    """Compress the 22-value observation into strategic categorical features."""
    indices = (0, 1, 2, 3, 4, 5, 6, 7, 8, 11, 13, 14, 18, 19, 20, 21)
    return tuple(max(0, min(3, math.floor(float(observation[index]) * 4)))
                 for index in indices)


def discretize(observation) -> tuple[int, ...]:
    """Backward-compatible name for the Update 0.18 state abstraction."""
    return abstract_state(observation)


def curriculum_reward(episode: int, episodes: int, reward: float,
                      components: dict[str, float], enabled: bool = True) -> float:
    """Apply phased shaping while retaining the environment reward for evaluation."""
    if not enabled:
        return reward
    progress = episode / max(1, episodes - 1)
    if progress < 1 / 3:
        adjustment = components["survival"] * 0.35 + components["stability"] * 0.25
    elif progress < 2 / 3:
        adjustment = components["stability"] * 0.20 + components["social"] * 0.10
    else:
        adjustment = components["progress"] * 0.35 + components["social"] * 0.10
    return round(reward + adjustment, 3)


def _greedy_action(values: list[float], mask: tuple[int, ...]) -> int:
    valid = [i for i, allowed in enumerate(mask) if allowed]
    return max(valid, key=lambda index: (values[index], -index))


def _apply_training_rent_reserve(environment: TrainingEnvironment) -> bool:
    """Provide a training-only rent reserve without altering arrears scenarios."""
    p, clock = environment.simulation.state.protagonist, environment.simulation.state.clock
    if p.rent_arrears or clock.day > p.rent_due_day:
        return False
    previous = p.money
    p.money = max(p.money, p.rent_cost)
    return p.money != previous


def train_q_learning(training_seed: int, config: QLearningConfig | None = None) -> TrainingResult:
    """Train reproducible masked Q-learning with curriculum and count exploration."""
    config = config or QLearningConfig()
    rng, table = random.Random(training_seed), {}
    totals, shaped_totals, episode_seeds, episode_conditions = [], [], [], []
    episode_horizons, episode_state_counts = [], []
    visits, action_visits = Counter(), Counter()
    reward_sums, discounted_return_sums = Counter(), Counter()
    gate_clear_steps_by_episode, gate_clear_selections_by_episode = [], []
    preparation_clear_steps_by_episode = []
    preparation_clear_selections_by_episode = []
    preparation_ready_steps_by_episode = []
    preparation_blockers_by_episode = []
    portal_preparations_by_episode = []
    prepared_attempts_by_episode = []
    prepared_completions_by_episode = []
    preparation_return_samples = []
    preparation_plan_returns = []
    preparation_plan_contexts = []
    training_schedule = tuple(
        (condition, horizon)
        for condition in config.training_conditions
        for horizon in config.training_horizons
    )
    for episode in range(config.episodes):
        episode_seed = rng.randrange(2**31)
        condition, episode_horizon = training_schedule[episode % len(training_schedule)]
        episode_seeds.append(episode_seed)
        episode_conditions.append(condition)
        episode_horizons.append(episode_horizon)
        env = TrainingEnvironment(episode_seed, episode_horizon)
        observation, info = env.reset(seed=episode_seed, options={"condition": condition})
        if config.training_rent_reserve and _apply_training_rent_reserve(env):
            observation = env.environment.observe()
            if np is not None:
                observation = np.asarray(observation, dtype=np.float32)
        total = shaped_total = 0.0
        gate_clear_steps = gate_clear_selections = 0
        preparation_clear_steps = preparation_clear_selections = 0
        preparation_ready_steps = portal_preparations = 0
        preparation_blockers = Counter()
        episode_states = set()
        episode_transitions = []
        pending_preparations = []
        epsilon = (config.epsilon_start if config.episodes == 1 else config.epsilon_start +
                   (config.epsilon_end - config.epsilon_start) * episode / (config.episodes - 1))
        while True:
            state = abstract_state(observation)
            episode_states.add(state)
            values = table.setdefault(state, [0.0] * len(ACTION_NAMES))
            mask = info["action_mask"]
            valid = [index for index, allowed in enumerate(mask) if allowed]
            progression = [index for index in valid
                           if ACTION_NAMES[index] in {"Prepare portal", "Gate mission"}]
            heuristic = heuristic_action(env.environment, mask)
            gate_index = ACTION_NAMES.index("Gate mission")
            preparation_index = ACTION_NAMES.index("Prepare portal")
            gate_clear_steps += int(heuristic == gate_index)
            preparation_clear_steps += int(heuristic == preparation_index)
            if _portal_preparation_ready(env.environment):
                preparation_ready_steps += 1
                if heuristic != preparation_index:
                    blocker = ACTION_NAMES[heuristic]
                    preparation_blockers[_progression_displacement_reason(
                        env.environment, blocker, False)] += 1
            clear_progression = (heuristic if heuristic in progression else None)
            if (config.priority_clear_progression_sampling_rate > 0 and
                    clear_progression is not None and
                    rng.random() < config.priority_clear_progression_sampling_rate):
                action = clear_progression
            elif (config.progression_sampling_rate > 0 and progression and
                    rng.random() < config.progression_sampling_rate):
                action = rng.choice(progression)
            elif rng.random() < epsilon:
                action = rng.choice(valid)
            else:
                action = max(valid, key=lambda index: (
                    values[index] + config.exploration_bonus /
                    math.sqrt(visits[(state, index)] + 1) +
                    (config.progression_exploration_bonus /
                     math.sqrt(action_visits[index] + 1)
                     if ACTION_NAMES[index] in {"Prepare portal", "Gate mission"}
                     else 0.0), -index))
            gate_clear_selections += int(
                heuristic == gate_index and action == gate_index)
            preparation_clear_selections += int(
                heuristic == preparation_index and action == preparation_index)
            before_plan = env.simulation.state.active_portal_plan is not None
            next_observation, reward, terminated, truncated, info = env.step(action)
            resolved_preparation = info["resolved_action"] == "Prepare portal"
            portal_preparations += int(resolved_preparation)
            shaped = curriculum_reward(episode, config.episodes, reward,
                                       info["reward_components"], config.curriculum)
            next_state = abstract_state(next_observation)
            episode_states.add(next_state)
            next_values = table.setdefault(next_state, [0.0] * len(ACTION_NAMES))
            future = 0.0 if terminated or truncated else next_values[
                _greedy_action(next_values, info["action_mask"])]
            visits[(state, action)] += 1
            action_visits[action] += 1
            reward_sums[(state, action)] += reward
            episode_transitions.append((state, action, reward))
            if resolved_preparation:
                pending_preparations.append(len(episode_transitions) - 1)
            plan_consumed = (
                before_plan and
                env.simulation.state.active_portal_plan is None and
                info["resolved_action"] == "Gate mission")
            if plan_consumed and pending_preparations:
                first_preparation = pending_preparations[0]
                plan_return = 0.0
                for _, _, window_reward in reversed(
                        episode_transitions[first_preparation:]):
                    plan_return = (
                        window_reward + config.discount_factor * plan_return)
                preparation_plan_returns.append(
                    PreparationPlanReturn(
                        initial_state=episode_transitions[first_preparation][0],
                        preparation_steps=len(pending_preparations),
                        discounted_return=round(plan_return, 6),
                        steps=len(episode_transitions) - first_preparation,
                        plan_consumed=True))
                preparation_plan_contexts.append(
                    (condition, episode_horizon))
                for start in pending_preparations:
                    window_return = 0.0
                    for _, _, window_reward in reversed(
                            episode_transitions[start:]):
                        window_return = (
                            window_reward +
                            config.discount_factor * window_return)
                    preparation_return_samples.append(
                        PreparationReturnSample(
                            state=episode_transitions[start][0],
                            discounted_return=round(window_return, 6),
                            steps=len(episode_transitions) - start,
                            plan_consumed=True))
                pending_preparations.clear()
            values[action] += config.learning_rate * (
                shaped + config.discount_factor * future - values[action])
            observation, total, shaped_total = next_observation, total + reward, shaped_total + shaped
            if terminated or truncated:
                break
        if pending_preparations:
            first_preparation = pending_preparations[0]
            plan_return = 0.0
            for _, _, window_reward in reversed(
                    episode_transitions[first_preparation:]):
                plan_return = (
                    window_reward + config.discount_factor * plan_return)
            preparation_plan_returns.append(
                PreparationPlanReturn(
                    initial_state=episode_transitions[first_preparation][0],
                    preparation_steps=len(pending_preparations),
                    discounted_return=round(plan_return, 6),
                    steps=len(episode_transitions) - first_preparation,
                    plan_consumed=False))
            preparation_plan_contexts.append(
                (condition, episode_horizon))
        for start in pending_preparations:
            window_return = 0.0
            for _, _, window_reward in reversed(episode_transitions[start:]):
                window_return = (
                    window_reward + config.discount_factor * window_return)
            preparation_return_samples.append(
                PreparationReturnSample(
                    state=episode_transitions[start][0],
                    discounted_return=round(window_return, 6),
                    steps=len(episode_transitions) - start,
                    plan_consumed=False))
        discounted_return = 0.0
        for previous_state, previous_action, previous_reward in reversed(
                episode_transitions):
            discounted_return = (
                previous_reward + config.discount_factor * discounted_return)
            discounted_return_sums[
                (previous_state, previous_action)] += discounted_return
        totals.append(round(total, 3))
        shaped_totals.append(round(shaped_total, 3))
        episode_state_counts.append(len(episode_states))
        gate_clear_steps_by_episode.append(gate_clear_steps)
        gate_clear_selections_by_episode.append(gate_clear_selections)
        preparation_clear_steps_by_episode.append(preparation_clear_steps)
        preparation_clear_selections_by_episode.append(
            preparation_clear_selections)
        preparation_ready_steps_by_episode.append(preparation_ready_steps)
        preparation_blockers_by_episode.append(tuple(
            sorted(preparation_blockers.items())))
        protagonist = env.simulation.state.protagonist
        portal_preparations_by_episode.append(portal_preparations)
        prepared_attempts_by_episode.append(protagonist.prepared_missions_attempted)
        prepared_completions_by_episode.append(protagonist.prepared_missions_completed)
    visit_table = {
        state: [visits[(state, index)] for index in range(len(ACTION_NAMES))]
        for state in table
    }
    reward_table = {
        state: [round(reward_sums[(state, index)], 6)
                for index in range(len(ACTION_NAMES))]
        for state in table
    }
    discounted_return_table = {
        state: [round(discounted_return_sums[(state, index)], 6)
                for index in range(len(ACTION_NAMES))]
        for state in table
    }
    return TrainingResult(training_seed, config, table, tuple(totals), tuple(episode_seeds),
                          tuple(shaped_totals), len(table), tuple(episode_conditions),
                          tuple(episode_horizons), tuple(episode_state_counts), visit_table,
                          tuple(gate_clear_steps_by_episode),
                          tuple(gate_clear_selections_by_episode),
                          tuple(preparation_clear_steps_by_episode),
                          tuple(preparation_clear_selections_by_episode),
                          tuple(preparation_ready_steps_by_episode),
                          tuple(preparation_blockers_by_episode),
                          tuple(portal_preparations_by_episode),
                          tuple(prepared_attempts_by_episode),
                          tuple(prepared_completions_by_episode),
                          reward_table,
                          discounted_return_table,
                          tuple(preparation_return_samples),
                          tuple(preparation_plan_returns),
                          tuple(preparation_plan_contexts))
CHECKPOINT_VERSION = 25


def _checkpoint_data(result: TrainingResult) -> dict:
    return {
        "checkpoint_version": CHECKPOINT_VERSION,
        "encoder": "strategic-v2",
        "action_names": ACTION_NAMES,
        "training_seed": result.training_seed,
        "config": asdict(result.config),
        "episode_rewards": result.episode_rewards,
        "episode_seeds": result.episode_seeds,
        "episode_conditions": result.episode_conditions,
        "episode_horizons": result.episode_horizons,
        "episode_state_counts": result.episode_state_counts,
        "training_rewards": result.training_rewards,
        "state_count": result.state_count,
        "q_table": [
            {"state": state, "values": values}
            for state, values in sorted(result.q_table.items())
        ],
        "visit_table": [
            {"state": state, "counts": counts}
            for state, counts in sorted(result.visit_table.items())
        ],
        "reward_table": [
            {"state": state, "rewards": rewards}
            for state, rewards in sorted(result.reward_table.items())
        ],
        "discounted_return_table": [
            {"state": state, "returns": returns}
            for state, returns in sorted(result.discounted_return_table.items())
        ],
        "preparation_return_samples": [
            asdict(sample) for sample in result.preparation_return_samples
        ],
        "preparation_plan_returns": [
            asdict(sample) for sample in result.preparation_plan_returns
        ],
        "preparation_plan_contexts": result.preparation_plan_contexts,
        "episode_gate_priority_clear_steps": (
            result.episode_gate_priority_clear_steps),
        "episode_gate_priority_clear_selections": (
            result.episode_gate_priority_clear_selections),
        "episode_preparation_priority_clear_steps": (
            result.episode_preparation_priority_clear_steps),
        "episode_preparation_priority_clear_selections": (
            result.episode_preparation_priority_clear_selections),
        "episode_preparation_ready_steps": (
            result.episode_preparation_ready_steps),
        "episode_preparation_blocker_counts": (
            result.episode_preparation_blocker_counts),
        "episode_portal_preparations": result.episode_portal_preparations,
        "episode_prepared_missions_attempted": (
            result.episode_prepared_missions_attempted),
        "episode_prepared_missions_completed": (
            result.episode_prepared_missions_completed),
    }


def checkpoint_digest(result: TrainingResult) -> str:
    payload = json.dumps(_checkpoint_data(result), sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def save_checkpoint(result: TrainingResult, path: str | Path) -> Path:
    """Write a deterministic, integrity-protected tabular policy checkpoint."""
    destination = Path(path)
    data = _checkpoint_data(result)
    data["sha256"] = checkpoint_digest(result)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    return destination


def load_checkpoint(path: str | Path) -> TrainingResult:
    """Load a checkpoint only when its schema, actions, and digest are intact."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    digest = data.pop("sha256", None)
    if data.get("checkpoint_version") not in (2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24,
                                                   CHECKPOINT_VERSION):
        raise ValueError("Unsupported checkpoint version")
    if tuple(data.get("action_names", ())) != ACTION_NAMES or data.get("encoder") != "strategic-v2":
        raise ValueError("Checkpoint policy schema does not match this environment")
    payload = json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
    if digest != hashlib.sha256(payload).hexdigest():
        raise ValueError("Checkpoint integrity verification failed")
    table = {tuple(item["state"]): list(item["values"]) for item in data["q_table"]}
    visit_table = {
        tuple(item["state"]): list(item["counts"])
        for item in data.get("visit_table", ())
    }
    reward_table = {
        tuple(item["state"]): list(item["rewards"])
        for item in data.get("reward_table", ())
    }
    discounted_return_table = {
        tuple(item["state"]): list(item["returns"])
        for item in data.get("discounted_return_table", ())
    }
    config_data = dict(data["config"])
    config_data["training_conditions"] = tuple(
        config_data.get("training_conditions", ("standard",)))
    config_data["training_horizons"] = tuple(
        config_data.get("training_horizons", (config_data["horizon"],)))
    config_data.setdefault("unseen_state_fallback", "first_valid")
    config_data.setdefault("progression_exploration_bonus", 0.0)
    config_data.setdefault("progression_sampling_rate", 0.0)
    config_data.setdefault("priority_clear_progression_sampling_rate", 0.0)
    config_data.setdefault("training_rent_reserve", False)
    config_data.setdefault("preventive_rest_threshold", 0)
    config_data.setdefault("energy_preemption_floor", 0)
    config_data.setdefault("seen_recovery_utility_override", False)
    config_data.setdefault(
        "preventive_rest_max_injury_severity",
        1 if data["checkpoint_version"] == 9 else 0,
    )
    episode_rewards = tuple(data["episode_rewards"])
    return TrainingResult(
        training_seed=data["training_seed"], config=QLearningConfig(**config_data),
        q_table=table, episode_rewards=episode_rewards,
        episode_seeds=tuple(data["episode_seeds"]),
        training_rewards=tuple(data["training_rewards"]), state_count=data["state_count"],
        episode_conditions=tuple(data.get(
            "episode_conditions", ("standard",) * len(episode_rewards))),
        episode_horizons=tuple(data.get(
            "episode_horizons", (config_data["horizon"],) * len(episode_rewards))),
        episode_state_counts=tuple(data.get("episode_state_counts", ())),
        visit_table=visit_table,
        episode_gate_priority_clear_steps=tuple(data.get(
            "episode_gate_priority_clear_steps", ())),
        episode_gate_priority_clear_selections=tuple(data.get(
            "episode_gate_priority_clear_selections", ())),
        episode_preparation_priority_clear_steps=tuple(data.get(
            "episode_preparation_priority_clear_steps", ())),
        episode_preparation_priority_clear_selections=tuple(data.get(
            "episode_preparation_priority_clear_selections", ())),
        episode_preparation_ready_steps=tuple(data.get(
            "episode_preparation_ready_steps", ())),
        episode_preparation_blocker_counts=tuple(
            tuple((str(reason), int(count)) for reason, count in episode)
            for episode in data.get("episode_preparation_blocker_counts", ())),
        episode_portal_preparations=tuple(data.get(
            "episode_portal_preparations", ())),
        episode_prepared_missions_attempted=tuple(data.get(
            "episode_prepared_missions_attempted", ())),
        episode_prepared_missions_completed=tuple(data.get(
            "episode_prepared_missions_completed", ())),
        reward_table=reward_table,
        discounted_return_table=discounted_return_table,
        preparation_return_samples=tuple(
            PreparationReturnSample(
                state=tuple(item["state"]),
                discounted_return=float(item["discounted_return"]),
                steps=int(item["steps"]),
                plan_consumed=bool(item["plan_consumed"]),
            )
            for item in data.get("preparation_return_samples", ())),
        preparation_plan_returns=tuple(
            PreparationPlanReturn(
                initial_state=tuple(item["initial_state"]),
                preparation_steps=int(item["preparation_steps"]),
                discounted_return=float(item["discounted_return"]),
                steps=int(item["steps"]),
                plan_consumed=bool(item["plan_consumed"]),
            )
            for item in data.get("preparation_plan_returns", ())),
        preparation_plan_contexts=tuple(
            (str(condition), int(horizon))
            for condition, horizon in data.get(
                "preparation_plan_contexts", ())),
    )

@dataclass(frozen=True)
class BatchComparison:
    training_seed: int
    evaluation_seeds: tuple[int, ...]
    rl_rewards: tuple[float, ...]
    utility_rewards: tuple[float, ...]
    mean_difference: float
    verdict: str


def compare_utility_and_rl(result: TrainingResult, evaluation_seeds: tuple[int, ...],
                           horizon: int | None = None) -> BatchComparison:
    """Evaluate frozen RL and utility policies on identical held-out world seeds."""
    if not evaluation_seeds:
        raise ValueError("At least one evaluation seed is required")
    training_seeds = {result.training_seed, *result.episode_seeds}
    if training_seeds.intersection(evaluation_seeds):
        raise ValueError("Evaluation seeds must be held out from all training seeds")
    horizon = horizon or result.config.horizon
    rl_totals, utility_totals = [], []
    for seed in evaluation_seeds:
        rl_env = TrainingEnvironment(seed, horizon)
        observation, info = rl_env.reset(seed=seed)
        rl_total = 0.0
        while True:
            action, _, _, _ = _frozen_policy_action(
                result, rl_env.environment, observation, info["action_mask"])
            observation, reward, terminated, truncated, info = rl_env.step(action)
            rl_total += reward
            if terminated or truncated:
                break
        utility_env = LearningEnvironment(seed)
        utility_total = sum(utility_env.baseline_step().reward for _ in range(horizon))
        rl_totals.append(round(rl_total, 3))
        utility_totals.append(round(utility_total, 3))
    differences = [rl - utility for rl, utility in zip(rl_totals, utility_totals)]
    mean = sum(differences) / len(differences)
    if len(differences) < 2:
        verdict = "inconclusive"
    else:
        standard_error = math.sqrt(sum((value - mean) ** 2 for value in differences) /
                                   (len(differences) - 1)) / math.sqrt(len(differences))
        margin = 1.96 * standard_error
        verdict = ("promising" if mean - margin > 0 else
                   "baseline remains better" if mean + margin < 0 else "inconclusive")
    return BatchComparison(result.training_seed, tuple(evaluation_seeds), tuple(rl_totals),
                           tuple(utility_totals), round(mean, 3), verdict)
@dataclass(frozen=True)
class DiagnosticStep:
    step: int
    action: str
    reward: float
    health: int
    energy: int
    money: int
    rent_arrears: int
    missions_completed: int


@dataclass(frozen=True)
class PreventiveRestOverride:
    step: int
    replaced_action: str
    energy: int
    health: int
    hunger: int
    stress: int
    injury_severity: int
    slot: str
    unseen_state: bool
    replaced_action_q_value: float | None
    rest_q_value: float | None
    replaced_action_q_advantage: float | None


@dataclass(frozen=True)
class PreparationCounterfactual:
    seed: int
    portal: str
    preparation_bonus: int
    prepared_completed: bool
    unprepared_completed: bool
    prepared_health_delta: int
    unprepared_health_delta: int
    prepared_money_delta: int
    unprepared_money_delta: int
    prepared_rank_points: int
    unprepared_rank_points: int


@dataclass(frozen=True)
class MissionOutcome:
    step: int
    prepared: bool
    completed: bool
    reward: float
    reward_components: tuple[tuple[str, float], ...]


@dataclass(frozen=True)
class SeenStateDecisionOutcome:
    step: int
    learned_action: str
    utility_action: str
    selected_action: str
    disagreed: bool
    selective_recovery_override: bool
    reward: float
    reward_components: tuple[tuple[str, float], ...]
    utility_reward: float
    utility_reward_components: tuple[tuple[str, float], ...]
    reward_difference: float
    counterfactual_horizon: int
    return_reward: float
    return_reward_components: tuple[tuple[str, float], ...]
    utility_return_reward: float
    utility_return_reward_components: tuple[tuple[str, float], ...]
    return_reward_difference: float
    mission_completed: bool
    utility_mission_completed: bool
    window_missions_completed: int
    utility_window_missions_completed: int


@dataclass(frozen=True)
class EpisodeDiagnostics:
    seed: int
    policy: str
    condition: str
    steps: int
    decision_steps: int
    total_reward: float
    reward_components: tuple[tuple[str, float], ...]
    action_counts: tuple[tuple[str, int], ...]
    masked_counts: tuple[tuple[str, int], ...]
    survived: bool
    end_health: int
    end_energy: int
    end_hunger: int
    end_stress: int
    critical_energy_steps: int
    critical_energy_share: float
    critical_energy_decision_steps: int
    critical_energy_action_counts: tuple[tuple[str, int], ...]
    critical_energy_rest_count: int
    critical_energy_rest_share: float
    strained_energy_decision_steps: int
    strained_energy_action_counts: tuple[tuple[str, int], ...]
    strained_energy_rest_count: int
    strained_energy_rest_share: float
    high_hunger_steps: int
    high_hunger_share: float
    high_stress_steps: int
    high_stress_share: float
    rent_due_reached: bool
    rent_paid: bool
    missions_attempted: int
    missions_completed: int
    prepared_missions_attempted: int
    prepared_missions_completed: int
    mission_outcomes: tuple[MissionOutcome, ...]
    unique_actions: int
    dominant_action_share: float
    longest_action_streak: int
    low_need_recovery_count: int
    low_need_recovery_share: float
    social_action_count: int
    social_action_share: float
    unseen_state_count: int
    unseen_state_share: float
    seen_state_decision_count: int
    seen_utility_disagreement_count: int
    seen_utility_disagreement_share: float
    seen_state_decision_outcomes: tuple[SeenStateDecisionOutcome, ...]
    selective_recovery_override_count: int
    selective_recovery_override_pairs: tuple[tuple[str, str], ...]
    preventive_rest_override_count: int
    preventive_rest_override_share: float
    preventive_rest_overrides: tuple[PreventiveRestOverride, ...]
    visit_evidence_steps: int
    zero_visit_action_count: int
    zero_visit_action_share: float
    average_selected_action_visits: float
    gate_mission_available_steps: int
    gate_mission_selection_rate: float
    gate_mission_ready_steps: int
    gate_mission_readiness_blocker_counts: tuple[tuple[str, int], ...]
    portal_preparation_available_steps: int
    portal_preparation_selection_rate: float
    portal_preparation_ready_steps: int
    portal_preparation_readiness_blocker_counts: tuple[tuple[str, int], ...]
    portal_preparation_heuristic_clear_steps: int
    portal_preparation_heuristic_displacement_counts: tuple[tuple[str, int], ...]
    portal_preparation_heuristic_displacement_reason_counts: tuple[tuple[str, int], ...]
    gate_mission_seen_opportunity_steps: int
    gate_mission_greedy_steps: int
    gate_mission_greedy_rate: float
    gate_mission_q_gap_total: float
    gate_mission_average_q_gap: float
    gate_mission_priority_clear_seen_steps: int
    gate_mission_priority_clear_greedy_steps: int
    gate_mission_priority_clear_greedy_rate: float | None
    gate_mission_priority_clear_q_gap_total: float
    gate_mission_priority_clear_average_q_gap: float | None
    gate_mission_unseen_opportunity_steps: int
    gate_mission_fallback_steps: int
    gate_mission_fallback_rate: float
    gate_mission_ready_unseen_opportunity_steps: int
    gate_mission_ready_fallback_steps: int
    gate_mission_ready_fallback_rate: float
    gate_mission_ready_displacement_counts: tuple[tuple[str, int], ...]
    gate_mission_ready_displacement_reason_counts: tuple[tuple[str, int], ...]
    gate_mission_priority_clear_unseen_steps: int
    gate_mission_priority_clear_selection_steps: int
    gate_mission_priority_clear_selection_rate: float
    portal_preparation_seen_opportunity_steps: int
    portal_preparation_greedy_steps: int
    portal_preparation_greedy_rate: float
    portal_preparation_q_gap_total: float
    portal_preparation_average_q_gap: float
    portal_preparation_priority_clear_seen_steps: int
    portal_preparation_priority_clear_greedy_steps: int
    portal_preparation_priority_clear_greedy_rate: float | None
    portal_preparation_priority_clear_q_gap_total: float
    portal_preparation_priority_clear_average_q_gap: float | None
    portal_preparation_unseen_opportunity_steps: int
    portal_preparation_fallback_steps: int
    portal_preparation_fallback_rate: float
    portal_preparation_ready_unseen_opportunity_steps: int
    portal_preparation_ready_fallback_steps: int
    portal_preparation_ready_fallback_rate: float
    portal_preparation_ready_displacement_counts: tuple[tuple[str, int], ...]
    portal_preparation_ready_displacement_reason_counts: tuple[tuple[str, int], ...]
    portal_preparation_priority_clear_unseen_steps: int
    portal_preparation_priority_clear_selection_steps: int
    portal_preparation_priority_clear_selection_rate: float
    exploit_flags: tuple[str, ...]
    trace: tuple[DiagnosticStep, ...]


@dataclass(frozen=True)
class DiagnosticBatch:
    training_seed: int
    evaluation_seeds: tuple[int, ...]
    rl_episodes: tuple[EpisodeDiagnostics, ...]
    utility_episodes: tuple[EpisodeDiagnostics, ...]
    random_episodes: tuple[EpisodeDiagnostics, ...]
    heuristic_episodes: tuple[EpisodeDiagnostics, ...]
    policy_ranking: tuple[str, ...]
    reward_difference: float
    reward_component_differences: tuple[tuple[str, float], ...]
    terminal_wellbeing_differences: tuple[tuple[str, float], ...]
    resource_burden_differences: tuple[tuple[str, float], ...]
    verdict: str
    worst_rl_seeds: tuple[int, ...]
    condition: str = "standard"


def _episode_summary(seed: int, policy: str, condition: str,
                     environment: LearningEnvironment, transitions: list[Transition],
                     masks: list[tuple[int, ...]], trace: list[DiagnosticStep],
                     mission_outcomes: list[MissionOutcome],
                     low_need_recovery_count: int, critical_energy_steps: int,
                     critical_energy_actions: Counter,
                     strained_energy_actions: Counter,
                     high_hunger_steps: int, high_stress_steps: int,
                     unseen_state_count: int,
                     seen_state_decision_count: int,
                     seen_utility_disagreement_count: int,
                     seen_state_decision_outcomes: list[SeenStateDecisionOutcome],
                     preventive_rest_overrides: list[PreventiveRestOverride],
                     visit_evidence_steps: int, zero_visit_action_count: int,
                     selected_action_visit_total: int,
                     gate_ready_steps: int,
                     gate_readiness_blockers: Counter,
                     gate_seen_opportunities: int, gate_greedy_steps: int,
                     gate_q_gap_total: float,
                     gate_clear_seen_steps: int,
                     gate_clear_greedy_steps: int,
                     gate_clear_q_gap_total: float,
                     gate_unseen_opportunities: int,
                     gate_fallback_steps: int,
                     gate_ready_opportunities: int,
                     gate_ready_fallback_steps: int,
                     gate_ready_displacements: Counter,
                     gate_ready_displacement_reasons: Counter,
                     gate_priority_clear_steps: int,
                     gate_priority_clear_selections: int,
                     preparation_ready_steps: int,
                     preparation_readiness_blockers: Counter,
                     preparation_heuristic_clear_steps: int,
                     preparation_heuristic_displacements: Counter,
                     preparation_heuristic_displacement_reasons: Counter,
                     preparation_seen_opportunities: int,
                     preparation_greedy_steps: int,
                     preparation_q_gap_total: float,
                     preparation_clear_seen_steps: int,
                     preparation_clear_greedy_steps: int,
                     preparation_clear_q_gap_total: float,
                     preparation_unseen_opportunities: int,
                     preparation_fallback_steps: int,
                     preparation_ready_opportunities: int,
                     preparation_ready_fallback_steps: int,
                     preparation_ready_displacements: Counter,
                     preparation_ready_displacement_reasons: Counter,
                     preparation_priority_clear_steps: int,
                     preparation_priority_clear_selections: int) -> EpisodeDiagnostics:
    actions = Counter(item.resolved_action or item.action for item in transitions)
    selective_recovery_pairs = Counter(
        (item.learned_action, item.selected_action)
        for item in seen_state_decision_outcomes
        if item.selective_recovery_override)
    policy_actions = Counter(name for name, count in actions.items()
                             for _ in range(count) if name in ACTION_NAMES)
    masked = Counter()
    components = Counter()
    for mask in masks:
        for index, valid in enumerate(mask):
            if not valid:
                masked[ACTION_NAMES[index]] += 1
    for transition in transitions:
        components.update(dict(transition.reward_components))
    longest, current, previous = 0, 0, None
    for transition in transitions:
        action = transition.resolved_action or transition.action
        current = current + 1 if action == previous else 1
        longest, previous = max(longest, current), action
    steps = len(transitions)
    decision_steps = sum(policy_actions.values())
    dominant = (max(policy_actions.values(), default=0) / decision_steps
                if decision_steps else 0.0)
    flags = []
    if decision_steps >= 8 and len(policy_actions) <= 2:
        flags.append("low action diversity")
    if decision_steps >= 8 and longest >= max(8, math.ceil(decision_steps * 0.2)):
        flags.append("repeated-action loop")
    passive = sum(policy_actions[name] for name in ("Eat", "Rest", "Talk with Aiko"))
    if decision_steps >= 8 and passive / decision_steps >= 0.8:
        flags.append("passive-policy dominance")
    p = environment.simulation.state.protagonist
    due_reached = environment.simulation.state.clock.day > p.rent_due_day
    gate_available = sum(mask[ACTION_NAMES.index("Gate mission")] for mask in masks)
    preparation_available = sum(mask[ACTION_NAMES.index("Prepare portal")] for mask in masks)
    return EpisodeDiagnostics(
        seed=seed, policy=policy, condition=condition, steps=steps, decision_steps=decision_steps,
        total_reward=round(sum(item.reward for item in transitions), 3),
        reward_components=tuple((name, round(components[name], 3)) for name in REWARD_COMPONENTS),
        action_counts=tuple(sorted(actions.items())),
        masked_counts=tuple((name, masked[name]) for name in ACTION_NAMES),
        survived=p.health > 0, end_health=p.health, end_energy=p.energy,
        end_hunger=p.hunger, end_stress=p.stress,
        critical_energy_steps=critical_energy_steps,
        critical_energy_share=round(critical_energy_steps / max(1, steps), 3),
        critical_energy_decision_steps=sum(critical_energy_actions.values()),
        critical_energy_action_counts=tuple(sorted(critical_energy_actions.items())),
        critical_energy_rest_count=critical_energy_actions["Rest"],
        critical_energy_rest_share=round(
            critical_energy_actions["Rest"] /
            max(1, sum(critical_energy_actions.values())), 3),
        strained_energy_decision_steps=sum(strained_energy_actions.values()),
        strained_energy_action_counts=tuple(sorted(strained_energy_actions.items())),
        strained_energy_rest_count=strained_energy_actions["Rest"],
        strained_energy_rest_share=round(
            strained_energy_actions["Rest"] /
            max(1, sum(strained_energy_actions.values())), 3),
        high_hunger_steps=high_hunger_steps,
        high_hunger_share=round(high_hunger_steps / max(1, steps), 3),
        high_stress_steps=high_stress_steps,
        high_stress_share=round(high_stress_steps / max(1, steps), 3),
        rent_due_reached=due_reached,
        rent_paid=due_reached and p.rent_arrears == 0,
        missions_attempted=p.missions_attempted, missions_completed=p.missions_completed,
        prepared_missions_attempted=p.prepared_missions_attempted,
        prepared_missions_completed=p.prepared_missions_completed,
        mission_outcomes=tuple(mission_outcomes),
        unique_actions=len(policy_actions), dominant_action_share=round(dominant, 3),
        longest_action_streak=longest,
        low_need_recovery_count=low_need_recovery_count,
        low_need_recovery_share=round(
            low_need_recovery_count / max(1, decision_steps), 3),
        social_action_count=policy_actions["Talk with Aiko"],
        social_action_share=round(
            policy_actions["Talk with Aiko"] / max(1, decision_steps), 3),
        unseen_state_count=unseen_state_count,
        unseen_state_share=round(unseen_state_count / max(1, steps), 3),
        seen_state_decision_count=seen_state_decision_count,
        seen_utility_disagreement_count=seen_utility_disagreement_count,
        seen_utility_disagreement_share=round(
            seen_utility_disagreement_count / max(1, seen_state_decision_count), 3),
        seen_state_decision_outcomes=tuple(seen_state_decision_outcomes),
        selective_recovery_override_count=sum(selective_recovery_pairs.values()),
        selective_recovery_override_pairs=tuple(
            (f"{learned} -> {selected}", count)
            for (learned, selected), count in sorted(selective_recovery_pairs.items())),
        preventive_rest_override_count=len(preventive_rest_overrides),
        preventive_rest_override_share=round(
            len(preventive_rest_overrides) / max(1, steps), 3),
        preventive_rest_overrides=tuple(preventive_rest_overrides),
        visit_evidence_steps=visit_evidence_steps,
        zero_visit_action_count=zero_visit_action_count,
        zero_visit_action_share=round(
            zero_visit_action_count / max(1, visit_evidence_steps), 3),
        average_selected_action_visits=round(
            selected_action_visit_total / max(1, visit_evidence_steps), 3),
        gate_mission_available_steps=gate_available,
        gate_mission_selection_rate=round(
            p.missions_attempted / max(1, gate_available), 3),
        gate_mission_ready_steps=gate_ready_steps,
        gate_mission_readiness_blocker_counts=tuple(
            sorted(gate_readiness_blockers.items())),
        portal_preparation_available_steps=preparation_available,
        portal_preparation_selection_rate=round(
            policy_actions["Prepare portal"] / max(1, preparation_available), 3),
        portal_preparation_ready_steps=preparation_ready_steps,
        portal_preparation_readiness_blocker_counts=tuple(
            sorted(preparation_readiness_blockers.items())),
        portal_preparation_heuristic_clear_steps=(
            preparation_heuristic_clear_steps),
        portal_preparation_heuristic_displacement_counts=tuple(
            sorted(preparation_heuristic_displacements.items())),
        portal_preparation_heuristic_displacement_reason_counts=tuple(
            sorted(preparation_heuristic_displacement_reasons.items())),
        gate_mission_seen_opportunity_steps=gate_seen_opportunities,
        gate_mission_greedy_steps=gate_greedy_steps,
        gate_mission_greedy_rate=round(
            gate_greedy_steps / max(1, gate_seen_opportunities), 3),
        gate_mission_q_gap_total=round(gate_q_gap_total, 3),
        gate_mission_average_q_gap=round(
            gate_q_gap_total / max(1, gate_seen_opportunities), 3),
        gate_mission_priority_clear_seen_steps=gate_clear_seen_steps,
        gate_mission_priority_clear_greedy_steps=gate_clear_greedy_steps,
        gate_mission_priority_clear_greedy_rate=(
            round(gate_clear_greedy_steps / gate_clear_seen_steps, 3)
            if gate_clear_seen_steps else None),
        gate_mission_priority_clear_q_gap_total=round(
            gate_clear_q_gap_total, 3),
        gate_mission_priority_clear_average_q_gap=(
            round(gate_clear_q_gap_total / gate_clear_seen_steps, 3)
            if gate_clear_seen_steps else None),
        gate_mission_unseen_opportunity_steps=gate_unseen_opportunities,
        gate_mission_fallback_steps=gate_fallback_steps,
        gate_mission_fallback_rate=round(
            gate_fallback_steps / max(1, gate_unseen_opportunities), 3),
        gate_mission_ready_unseen_opportunity_steps=gate_ready_opportunities,
        gate_mission_ready_fallback_steps=gate_ready_fallback_steps,
        gate_mission_ready_fallback_rate=round(
            gate_ready_fallback_steps / max(1, gate_ready_opportunities), 3),
        gate_mission_ready_displacement_counts=tuple(
            sorted(gate_ready_displacements.items())),
        gate_mission_ready_displacement_reason_counts=tuple(
            sorted(gate_ready_displacement_reasons.items())),
        gate_mission_priority_clear_unseen_steps=gate_priority_clear_steps,
        gate_mission_priority_clear_selection_steps=(
            gate_priority_clear_selections),
        gate_mission_priority_clear_selection_rate=round(
            gate_priority_clear_selections /
            max(1, gate_priority_clear_steps), 3),
        portal_preparation_seen_opportunity_steps=preparation_seen_opportunities,
        portal_preparation_greedy_steps=preparation_greedy_steps,
        portal_preparation_greedy_rate=round(
            preparation_greedy_steps / max(1, preparation_seen_opportunities), 3),
        portal_preparation_q_gap_total=round(preparation_q_gap_total, 3),
        portal_preparation_average_q_gap=round(
            preparation_q_gap_total / max(1, preparation_seen_opportunities), 3),
        portal_preparation_priority_clear_seen_steps=(
            preparation_clear_seen_steps),
        portal_preparation_priority_clear_greedy_steps=(
            preparation_clear_greedy_steps),
        portal_preparation_priority_clear_greedy_rate=(
            round(preparation_clear_greedy_steps /
                  preparation_clear_seen_steps, 3)
            if preparation_clear_seen_steps else None),
        portal_preparation_priority_clear_q_gap_total=round(
            preparation_clear_q_gap_total, 3),
        portal_preparation_priority_clear_average_q_gap=(
            round(preparation_clear_q_gap_total /
                  preparation_clear_seen_steps, 3)
            if preparation_clear_seen_steps else None),
        portal_preparation_unseen_opportunity_steps=(
            preparation_unseen_opportunities),
        portal_preparation_fallback_steps=preparation_fallback_steps,
        portal_preparation_fallback_rate=round(
            preparation_fallback_steps /
            max(1, preparation_unseen_opportunities), 3),
        portal_preparation_ready_unseen_opportunity_steps=(
            preparation_ready_opportunities),
        portal_preparation_ready_fallback_steps=(
            preparation_ready_fallback_steps),
        portal_preparation_ready_fallback_rate=round(
            preparation_ready_fallback_steps /
            max(1, preparation_ready_opportunities), 3),
        portal_preparation_ready_displacement_counts=tuple(
            sorted(preparation_ready_displacements.items())),
        portal_preparation_ready_displacement_reason_counts=tuple(
            sorted(preparation_ready_displacement_reasons.items())),
        portal_preparation_priority_clear_unseen_steps=(
            preparation_priority_clear_steps),
        portal_preparation_priority_clear_selection_steps=(
            preparation_priority_clear_selections),
        portal_preparation_priority_clear_selection_rate=round(
            preparation_priority_clear_selections /
            max(1, preparation_priority_clear_steps), 3),
        exploit_flags=tuple(flags), trace=tuple(trace),
    )


def _gate_mission_readiness_blocker(
        environment: LearningEnvironment) -> str | None:
    p, state = environment.simulation.state.protagonist, environment.simulation.state
    if state.active_portal_plan is None:
        return "no active portal plan"
    if p.health < 60:
        return "health below 60"
    if p.energy < 42:
        return "energy below 42"
    return None


def _gate_mission_ready(environment: LearningEnvironment) -> bool:
    return _gate_mission_readiness_blocker(environment) is None


def _portal_preparation_readiness_blocker(
        environment: LearningEnvironment) -> str | None:
    p, state = environment.simulation.state.protagonist, environment.simulation.state
    if not p.guild_registered:
        return "not guild registered"
    if state.gate_alert_level < 2:
        return "Gate alert below 2"
    if p.health < 65:
        return "health below 65"
    return None


def _portal_preparation_ready(environment: LearningEnvironment) -> bool:
    return _portal_preparation_readiness_blocker(environment) is None


def _progression_displacement_reason(environment: LearningEnvironment,
                                     action: str,
                                     preventive_rest: bool) -> str:
    p, state = environment.simulation.state.protagonist, environment.simulation.state
    if action == "Seek treatment" and (
            p.injury_severity >= 2 or (p.injury_severity and p.health < 65)):
        return "urgent treatment"
    if action == "Eat" and p.hunger >= 65:
        return "urgent hunger"
    if action == "Rest" and preventive_rest:
        return "preventive recovery"
    if action == "Rest" and (p.energy <= 28 or p.health < 45):
        return "urgent recovery"
    if action == "Pay rent arrears" and p.rent_arrears and p.money > 600:
        return "rent recovery"
    if (action == "Part-time work" and p.money < p.rent_cost and
            state.clock.day <= p.rent_due_day):
        return "rent preparation"
    if action == "Gate mission" and state.active_portal_plan:
        return "direct progression"
    return "unexplained"


def heuristic_action(environment: LearningEnvironment, mask: tuple[int, ...]) -> int:
    """Choose from explicit safety and progression rules, independent of utility scores."""
    p, state = environment.simulation.state.protagonist, environment.simulation.state
    valid = {name for index, name in enumerate(ACTION_NAMES) if mask[index]}
    priorities = []
    if p.injury_severity >= 2 or (p.injury_severity and p.health < 65):
        priorities.append("Seek treatment")
    if p.hunger >= 65:
        priorities.append("Eat")
    if p.energy <= 28 or p.health < 45:
        priorities.append("Rest")
    if p.rent_arrears and p.money > 600:
        priorities.append("Pay rent arrears")
    if p.money < p.rent_cost and state.clock.day <= p.rent_due_day:
        priorities.append("Part-time work")
    if _gate_mission_ready(environment):
        priorities.append("Gate mission")
    if _portal_preparation_ready(environment):
        priorities.append("Prepare portal")
    if p.guild_registered and p.energy >= 45:
        priorities.append("Guild patrol")
    priorities.extend(("Study", "Train", "Part-time work", "Rest", "Eat"))
    choice = next(name for name in priorities if name in valid)
    return ACTION_NAMES.index(choice)


def utility_action(environment: LearningEnvironment, mask: tuple[int, ...]) -> int:
    """Delegate one decision-point choice to the simulator's utility scorer."""
    simulation = environment.simulation
    state, p = simulation.state, simulation.state.protagonist
    choice, _ = simulation.agent.choose(
        p, state.clock.slot, state.gate_alert_level, state.weather,
        state.active_portal_plan is not None,
    )
    action = ACTION_NAMES.index(choice.name)
    if not mask[action]:
        raise ValueError("Utility scorer selected an action outside the valid-action mask")
    return action


def _seen_recovery_override_eligible(action: str, p: Protagonist) -> bool:
    return ((action == "Eat" and p.hunger < 65) or
            (action == "Rest" and p.energy > 28 and p.health >= 45))


def _frozen_policy_action(
        result: TrainingResult, environment: LearningEnvironment,
        observation, mask: tuple[int, ...]) -> tuple[int, bool, bool, int | None]:
    state = discretize(observation)
    unseen = state not in result.q_table
    if unseen and result.config.unseen_state_fallback == "heuristic":
        action = heuristic_action(environment, mask)
    elif unseen and result.config.unseen_state_fallback == "utility":
        action = utility_action(environment, mask)
    else:
        values = result.q_table.get(state, [0.0] * len(ACTION_NAMES))
        action = _greedy_action(values, mask)
    p = environment.simulation.state.protagonist
    if (not unseen and result.config.seen_recovery_utility_override and
            _seen_recovery_override_eligible(ACTION_NAMES[action], p)):
        action = utility_action(environment, mask)
    rest_index = ACTION_NAMES.index("Rest")
    projected_energy = p.energy - ACTION_ENERGY_COSTS.get(
        ACTION_NAMES[action], 0)
    action_cost_preemption = (
        result.config.energy_preemption_floor and
        ACTION_NAMES[action] in ACTION_ENERGY_COSTS and
        projected_energy <= result.config.energy_preemption_floor)
    threshold_preemption = (
        result.config.preventive_rest_threshold and
        p.energy <= result.config.preventive_rest_threshold)
    if (action != rest_index and
            (action_cost_preemption or threshold_preemption) and
            p.injury_severity <=
            result.config.preventive_rest_max_injury_severity and
            p.hunger < 65 and mask[rest_index]):
        return rest_index, unseen, True, action
    return action, unseen, False, None


def _configure_evaluation_condition(environment: LearningEnvironment,
                                    condition: str) -> None:
    if condition not in EVALUATION_CONDITIONS:
        raise ValueError(f"Unknown evaluation condition {condition!r}")
    state, p = environment.simulation.state, environment.simulation.state.protagonist

    def establish_hunter_start() -> None:
        p.awakened, p.guild_registered = True, True
        p.hunter_rank, p.ability, p.ability_mastery = "F", "Threat Sense", 10
        p.relationships["Aiko Sato"] = Relationship(
            name="Aiko Sato", role="F-rank guild clerk", trust=3,
            familiarity=5, meetings=1, loyalty=4,
        )

    if condition == "financial_pressure":
        establish_hunter_start()
        state.clock.day = p.rent_due_day + 1
        p.money, p.rent_arrears, p.hunger, p.stress = 300, p.rent_cost, 55, 70
    elif condition == "injury_recovery":
        p.health, p.energy, p.injury_severity, p.injuries = 42, 30, 3, 1
        p.money, p.stress = 3_500, 65
    elif condition == "gate_crisis":
        establish_hunter_start()
        p.health, p.energy, p.stress = 75, 55, 60
        state.gate_alert_level = 3
    elif condition == "compound_crisis":
        establish_hunter_start()
        state.clock.day = p.rent_due_day + 1
        p.money, p.rent_arrears = 3_000, p.rent_cost
        p.health, p.energy, p.hunger, p.stress = 42, 30, 55, 80
        p.injury_severity, p.injuries = 3, 1
        state.gate_alert_level = 3


def is_low_need_recovery(action: str, protagonist: Protagonist, slot: TimeSlot) -> bool:
    """Return whether recovery was chosen while physical need was conservatively low."""
    if action == "Eat":
        return protagonist.hunger < 35 and protagonist.health >= 60
    if action == "Rest":
        return (protagonist.energy > 70 and protagonist.stress < 40
                and protagonist.injury_severity == 0 and slot is not TimeSlot.LATE_NIGHT)
    return False


def evaluate_preparation_counterfactual(seed: int) -> PreparationCounterfactual:
    """Run paired missions with identical state and RNG but different plan use."""
    environment = LearningEnvironment(seed)
    _configure_evaluation_condition(environment, "gate_crisis")
    simulation = environment.simulation
    p, state = simulation.state.protagonist, simulation.state
    p.guild_registered = True
    p.health, p.energy, p.injury_severity = 80, 80, 0
    state.gate_alert_level = 3
    state.active_portal_plan = None
    energy, stress = p.energy, p.stress
    objective_scores = dict(state.objective_scores)
    simulation._prepare_portal()
    p.energy, p.stress = energy, stress
    state.objective_scores = objective_scores
    portal = state.active_portal_plan
    if portal is None:
        raise RuntimeError("Preparation did not create an active portal plan")
    bonus = state.portal_investigations[portal].preparation_bonus
    prepared, unprepared = deepcopy(simulation), deepcopy(simulation)

    def run(twin: Simulation, use_preparation: bool) -> tuple[bool, int, int, int]:
        before = twin.state.protagonist
        completed, health = before.missions_completed, before.health
        money, rank_points = before.money, before.rank_points
        twin._resolve_gate_mission(use_preparation=use_preparation)
        after = twin.state.protagonist
        return (after.missions_completed > completed, after.health - health,
                after.money - money, after.rank_points - rank_points)

    prepared_result = run(prepared, True)
    unprepared_result = run(unprepared, False)
    return PreparationCounterfactual(
        seed=seed, portal=portal, preparation_bonus=bonus,
        prepared_completed=prepared_result[0],
        unprepared_completed=unprepared_result[0],
        prepared_health_delta=prepared_result[1],
        unprepared_health_delta=unprepared_result[1],
        prepared_money_delta=prepared_result[2],
        unprepared_money_delta=unprepared_result[2],
        prepared_rank_points=prepared_result[3],
        unprepared_rank_points=unprepared_result[3],
    )


def diagnose_episode(seed: int, horizon: int, policy: str,
                     result: TrainingResult | None = None,
                     condition: str = "standard") -> EpisodeDiagnostics:
    """Run one deterministic episode and retain evidence for failure analysis."""
    if horizon < 1:
        raise ValueError("horizon must be at least 1")
    if policy not in {"rl", "utility", "random", "heuristic"}:
        raise ValueError("unknown diagnostic policy")
    if policy == "rl" and result is None:
        raise ValueError("RL diagnostics require a training result")
    environment = LearningEnvironment(seed)
    _configure_evaluation_condition(environment, condition)
    policy_rng = random.Random(seed * 97_409 + 17)
    transitions, masks, trace = [], [], []
    mission_outcomes = []
    low_need_recovery_count = unseen_state_count = 0
    seen_state_decision_count = seen_utility_disagreement_count = 0
    seen_state_decision_outcomes = []
    preventive_rest_overrides = []
    critical_energy_steps = high_hunger_steps = high_stress_steps = 0
    critical_energy_actions = Counter()
    strained_energy_actions = Counter()
    visit_evidence_steps = zero_visit_action_count = selected_action_visit_total = 0
    gate_ready_steps = 0
    gate_readiness_blockers = Counter()
    gate_seen_opportunities = gate_greedy_steps = 0
    gate_clear_seen_steps = gate_clear_greedy_steps = 0
    gate_clear_q_gap_total = 0.0
    gate_unseen_opportunities = gate_fallback_steps = 0
    gate_ready_opportunities = gate_ready_fallback_steps = 0
    gate_ready_displacements = Counter()
    gate_ready_displacement_reasons = Counter()
    gate_priority_clear_steps = gate_priority_clear_selections = 0
    preparation_ready_steps = preparation_heuristic_clear_steps = 0
    preparation_readiness_blockers = Counter()
    preparation_heuristic_displacements = Counter()
    preparation_heuristic_displacement_reasons = Counter()
    preparation_seen_opportunities = preparation_greedy_steps = 0
    preparation_clear_seen_steps = preparation_clear_greedy_steps = 0
    preparation_clear_q_gap_total = 0.0
    preparation_unseen_opportunities = preparation_fallback_steps = 0
    preparation_ready_opportunities = preparation_ready_fallback_steps = 0
    preparation_ready_displacements = Counter()
    preparation_ready_displacement_reasons = Counter()
    preparation_priority_clear_steps = preparation_priority_clear_selections = 0
    gate_q_gap_total = preparation_q_gap_total = 0.0
    for step in range(1, horizon + 1):
        mask = environment.action_mask()
        masks.append(mask)
        gate_index = ACTION_NAMES.index("Gate mission")
        preparation_index = ACTION_NAMES.index("Prepare portal")
        if mask[gate_index]:
            readiness_blocker = _gate_mission_readiness_blocker(environment)
            gate_ready_steps += int(readiness_blocker is None)
            if readiness_blocker is not None:
                gate_readiness_blockers[readiness_blocker] += 1
        if mask[preparation_index]:
            readiness_blocker = _portal_preparation_readiness_blocker(environment)
            preparation_ready_steps += int(readiness_blocker is None)
            if readiness_blocker is not None:
                preparation_readiness_blockers[readiness_blocker] += 1
            else:
                heuristic = heuristic_action(environment, mask)
                preparation_heuristic_clear_steps += int(
                    heuristic == preparation_index)
                if heuristic != preparation_index:
                    chosen = ACTION_NAMES[heuristic]
                    preparation_heuristic_displacements[chosen] += 1
                    preparation_heuristic_displacement_reasons[
                        _progression_displacement_reason(
                            environment, chosen, False)] += 1
        before_p = environment.simulation.state.protagonist
        before_missions_completed = before_p.missions_completed
        before_plan = environment.simulation.state.active_portal_plan is not None
        before_slot = environment.simulation.state.clock.slot
        low_need_eat = is_low_need_recovery("Eat", before_p, before_slot)
        low_need_rest = is_low_need_recovery("Rest", before_p, before_slot)
        before_critical_energy = before_p.energy <= 25
        before_strained_energy = 26 <= before_p.energy <= 45
        if policy == "utility":
            transition = environment.baseline_step()
        elif policy == "random":
            action = policy_rng.choice([index for index, valid in enumerate(mask) if valid])
            transition = environment.step(ACTION_NAMES[action])
        elif policy == "heuristic":
            action = heuristic_action(environment, mask)
            transition = environment.step(ACTION_NAMES[action])
        else:
            observation = environment.observe()
            state = discretize(observation)
            utility_counterfactual = None
            counterfactual_environment = None
            if state in result.q_table:
                rng_state = environment.simulation.rng.getstate()
                utility_counterfactual = utility_action(environment, mask)
                environment.simulation.rng.setstate(rng_state)
                counterfactual_environment = deepcopy(environment)
            learned_action = (
                _greedy_action(result.q_table[state], mask)
                if state in result.q_table else None)
            action, unseen, preventive_rest, replaced_action = _frozen_policy_action(
                result, environment, observation, mask)
            unseen_state_count += int(unseen)
            fallback_action = replaced_action if preventive_rest else action
            if unseen:
                if mask[gate_index]:
                    gate_unseen_opportunities += 1
                    gate_fallback_steps += int(action == gate_index)
                    gate_ready = _gate_mission_ready(environment)
                    if gate_ready:
                        gate_ready_opportunities += 1
                        gate_ready_fallback_steps += int(action == gate_index)
                        if action != gate_index:
                            chosen = ACTION_NAMES[action]
                            gate_ready_displacements[chosen] += 1
                            gate_ready_displacement_reasons[
                                _progression_displacement_reason(
                                    environment, chosen, preventive_rest)] += 1
                        if (result.config.unseen_state_fallback == "heuristic" and
                                fallback_action == gate_index):
                            gate_priority_clear_steps += 1
                            gate_priority_clear_selections += int(action == gate_index)
                if mask[preparation_index]:
                    preparation_unseen_opportunities += 1
                    preparation_fallback_steps += int(action == preparation_index)
                    preparation_ready = _portal_preparation_ready(environment)
                    if preparation_ready:
                        preparation_ready_opportunities += 1
                        preparation_ready_fallback_steps += int(
                            action == preparation_index)
                        if action != preparation_index:
                            chosen = ACTION_NAMES[action]
                            preparation_ready_displacements[chosen] += 1
                            preparation_ready_displacement_reasons[
                                _progression_displacement_reason(
                                    environment, chosen, preventive_rest)] += 1
                        if (result.config.unseen_state_fallback == "heuristic" and
                                fallback_action == preparation_index):
                            preparation_priority_clear_steps += 1
                            preparation_priority_clear_selections += int(
                                action == preparation_index)
            if preventive_rest:
                values = result.q_table.get(state)
                rest_index = ACTION_NAMES.index("Rest")
                replaced_q = values[replaced_action] if values is not None else None
                rest_q = values[rest_index] if values is not None else None
                preventive_rest_overrides.append(PreventiveRestOverride(
                    step=step, replaced_action=ACTION_NAMES[replaced_action],
                    energy=before_p.energy, health=before_p.health,
                    hunger=before_p.hunger, stress=before_p.stress,
                    injury_severity=before_p.injury_severity,
                    slot=before_slot.value, unseen_state=unseen,
                    replaced_action_q_value=(
                        round(replaced_q, 6) if replaced_q is not None else None),
                    rest_q_value=round(rest_q, 6) if rest_q is not None else None,
                    replaced_action_q_advantage=(
                        round(replaced_q - rest_q, 6)
                        if replaced_q is not None and rest_q is not None else None),
                ))
            values = result.q_table.get(state)
            if values is not None:
                greedy = _greedy_action(values, mask)
                best_valid_value = max(value for value, valid in zip(values, mask) if valid)
                heuristic = heuristic_action(environment, mask)
                if mask[gate_index]:
                    gate_seen_opportunities += 1
                    gate_greedy_steps += int(greedy == gate_index)
                    gate_q_gap_total += best_valid_value - values[gate_index]
                    if heuristic == gate_index:
                        gate_clear_seen_steps += 1
                        gate_clear_greedy_steps += int(greedy == gate_index)
                        gate_clear_q_gap_total += (
                            best_valid_value - values[gate_index])
                if mask[preparation_index]:
                    preparation_seen_opportunities += 1
                    preparation_greedy_steps += int(greedy == preparation_index)
                    preparation_q_gap_total += best_valid_value - values[preparation_index]
                    if heuristic == preparation_index:
                        preparation_clear_seen_steps += 1
                        preparation_clear_greedy_steps += int(
                            greedy == preparation_index)
                        preparation_clear_q_gap_total += (
                            best_valid_value - values[preparation_index])
            counts = result.visit_table.get(state)
            if counts is not None:
                visit_evidence_steps += 1
                selected_action_visit_total += counts[action]
                zero_visit_action_count += int(counts[action] == 0)
            transition = environment.step(ACTION_NAMES[action])
            if (not unseen and
                    (transition.resolved_action or transition.action) in ACTION_NAMES):
                seen_state_decision_count += 1
                seen_utility_disagreement_count += int(
                    learned_action != utility_counterfactual)
                utility_transition = counterfactual_environment.step(
                    ACTION_NAMES[utility_counterfactual])
                if ((utility_transition.resolved_action or utility_transition.action) !=
                        ACTION_NAMES[utility_counterfactual]):
                    raise ValueError("Paired utility action did not resolve as selected")
                utility_mission_completed = (
                    counterfactual_environment.simulation.state.protagonist.
                    missions_completed > before_missions_completed)
                learned_rollout = deepcopy(environment)
                learned_return = transition.reward
                utility_return = utility_transition.reward
                learned_components = Counter(dict(transition.reward_components))
                utility_components = Counter(dict(utility_transition.reward_components))
                for _ in range(SEEN_STATE_COUNTERFACTUAL_HORIZON - 1):
                    learned_followup = learned_rollout.baseline_step()
                    utility_followup = counterfactual_environment.baseline_step()
                    learned_return += learned_followup.reward
                    utility_return += utility_followup.reward
                    learned_components.update(dict(learned_followup.reward_components))
                    utility_components.update(dict(utility_followup.reward_components))
                seen_state_decision_outcomes.append(SeenStateDecisionOutcome(
                    step=step, learned_action=ACTION_NAMES[learned_action],
                    utility_action=ACTION_NAMES[utility_counterfactual],
                    selected_action=ACTION_NAMES[action],
                    disagreed=learned_action != utility_counterfactual,
                    selective_recovery_override=(
                        result.config.seen_recovery_utility_override and
                        _seen_recovery_override_eligible(
                            ACTION_NAMES[learned_action], before_p)),
                    reward=transition.reward,
                    reward_components=transition.reward_components,
                    utility_reward=utility_transition.reward,
                    utility_reward_components=utility_transition.reward_components,
                    reward_difference=round(
                        transition.reward - utility_transition.reward, 3),
                    counterfactual_horizon=SEEN_STATE_COUNTERFACTUAL_HORIZON,
                    return_reward=round(learned_return, 3),
                    return_reward_components=tuple(
                        (name, round(learned_components[name], 3))
                        for name in REWARD_COMPONENTS),
                    utility_return_reward=round(utility_return, 3),
                    utility_return_reward_components=tuple(
                        (name, round(utility_components[name], 3))
                        for name in REWARD_COMPONENTS),
                    return_reward_difference=round(
                        learned_return - utility_return, 3),
                    mission_completed=(
                        environment.simulation.state.protagonist.missions_completed >
                        before_missions_completed),
                    utility_mission_completed=utility_mission_completed,
                    window_missions_completed=(
                        learned_rollout.simulation.state.protagonist.missions_completed -
                        before_missions_completed),
                    utility_window_missions_completed=(
                        counterfactual_environment.simulation.state.protagonist.
                        missions_completed - before_missions_completed),
                ))
        transitions.append(transition)
        chosen_action = transition.resolved_action or transition.action
        after_p = environment.simulation.state.protagonist
        if chosen_action == "Gate mission":
            mission_outcomes.append(MissionOutcome(
                step=step, prepared=before_plan,
                completed=after_p.missions_completed > before_missions_completed,
                reward=transition.reward,
                reward_components=transition.reward_components,
            ))
        if before_critical_energy:
            critical_energy_actions[chosen_action] += 1
        if before_strained_energy:
            strained_energy_actions[chosen_action] += 1
        low_need_recovery_count += int(
            (chosen_action == "Eat" and low_need_eat) or
            (chosen_action == "Rest" and low_need_rest))
        p = after_p
        critical_energy_steps += int(p.energy <= 25)
        high_hunger_steps += int(p.hunger >= 75)
        high_stress_steps += int(p.stress >= 75)
        trace.append(DiagnosticStep(step, transition.resolved_action or transition.action,
                                    transition.reward, p.health,
                                    p.energy, p.money, p.rent_arrears,
                                    p.missions_completed))
        if p.health <= 0:
            break
    return _episode_summary(
        seed, policy, condition, environment, transitions, masks, trace,
        mission_outcomes, low_need_recovery_count, critical_energy_steps, critical_energy_actions,
        strained_energy_actions, high_hunger_steps, high_stress_steps,
        unseen_state_count, seen_state_decision_count,
        seen_utility_disagreement_count, seen_state_decision_outcomes,
        preventive_rest_overrides, visit_evidence_steps,
        zero_visit_action_count, selected_action_visit_total,
        gate_ready_steps, gate_readiness_blockers,
        gate_seen_opportunities, gate_greedy_steps, gate_q_gap_total,
        gate_clear_seen_steps, gate_clear_greedy_steps,
        gate_clear_q_gap_total, gate_unseen_opportunities, gate_fallback_steps,
        gate_ready_opportunities, gate_ready_fallback_steps,
        gate_ready_displacements, gate_ready_displacement_reasons,
        gate_priority_clear_steps, gate_priority_clear_selections,
        preparation_ready_steps, preparation_readiness_blockers,
        preparation_heuristic_clear_steps,
        preparation_heuristic_displacements,
        preparation_heuristic_displacement_reasons,
        preparation_seen_opportunities, preparation_greedy_steps,
        preparation_q_gap_total, preparation_clear_seen_steps,
        preparation_clear_greedy_steps, preparation_clear_q_gap_total,
        preparation_unseen_opportunities, preparation_fallback_steps,
        preparation_ready_opportunities, preparation_ready_fallback_steps,
        preparation_ready_displacements,
        preparation_ready_displacement_reasons,
        preparation_priority_clear_steps,
        preparation_priority_clear_selections)


def _honest_verdict(differences: list[float]) -> str:
    if len(differences) < 2:
        return "inconclusive"
    mean = sum(differences) / len(differences)
    standard_error = math.sqrt(sum((value - mean) ** 2 for value in differences) /
                               (len(differences) - 1)) / math.sqrt(len(differences))
    margin = 1.96 * standard_error
    if mean - margin > 0:
        return "promising"
    if mean + margin < 0:
        return "baseline remains better"
    return "inconclusive"


def diagnose_batch(result: TrainingResult, evaluation_seeds: tuple[int, ...],
                   horizon: int | None = None, worst_count: int = 3,
                   condition: str = "standard") -> DiagnosticBatch:
    """Compare policies and retain the weakest held-out RL episodes for inspection."""
    if not evaluation_seeds:
        raise ValueError("At least one evaluation seed is required")
    if worst_count < 1:
        raise ValueError("worst_count must be at least 1")
    training_seeds = {result.training_seed, *result.episode_seeds}
    if training_seeds.intersection(evaluation_seeds):
        raise ValueError("Evaluation seeds must be held out from all training seeds")
    horizon = horizon or result.config.horizon
    rl = tuple(diagnose_episode(seed, horizon, "rl", result, condition)
               for seed in evaluation_seeds)
    utility = tuple(diagnose_episode(seed, horizon, "utility", condition=condition)
                    for seed in evaluation_seeds)
    random_policy = tuple(diagnose_episode(seed, horizon, "random", condition=condition)
                          for seed in evaluation_seeds)
    heuristic = tuple(diagnose_episode(seed, horizon, "heuristic", condition=condition)
                      for seed in evaluation_seeds)
    policies = {"rl": rl, "utility": utility, "random": random_policy,
                "heuristic": heuristic}
    averages = {name: sum(item.total_reward for item in episodes) / len(episodes)
                for name, episodes in policies.items()}
    ranking = tuple(sorted(averages, key=lambda name: (-averages[name], name)))
    differences = [r.total_reward - u.total_reward for r, u in zip(rl, utility)]
    component_differences = tuple(
        (name, round(sum(dict(r.reward_components)[name] -
                         dict(u.reward_components)[name]
                         for r, u in zip(rl, utility)) / len(rl), 3))
        for name in REWARD_COMPONENTS
    )
    terminal_differences = tuple(
        (name, round(sum(getattr(r, attribute) - getattr(u, attribute)
                         for r, u in zip(rl, utility)) / len(rl), 3))
        for name, attribute in (("health", "end_health"), ("energy", "end_energy"),
                                ("hunger", "end_hunger"), ("stress", "end_stress"))
    )
    burden_differences = tuple(
        (name, round(sum(getattr(r, attribute) - getattr(u, attribute)
                         for r, u in zip(rl, utility)) / len(rl), 3))
        for name, attribute in (("critical_energy_share", "critical_energy_share"),
                                ("high_hunger_share", "high_hunger_share"),
                                ("high_stress_share", "high_stress_share"))
    )
    worst = sorted(rl, key=lambda episode: (episode.total_reward, episode.seed))[:worst_count]
    return DiagnosticBatch(
        training_seed=result.training_seed, evaluation_seeds=tuple(evaluation_seeds),
        rl_episodes=rl, utility_episodes=utility, random_episodes=random_policy,
        heuristic_episodes=heuristic, policy_ranking=ranking,
        reward_difference=round(sum(differences) / len(differences), 3),
        reward_component_differences=component_differences,
        terminal_wellbeing_differences=terminal_differences,
        resource_burden_differences=burden_differences,
        verdict=_honest_verdict(differences),
        worst_rl_seeds=tuple(episode.seed for episode in worst), condition=condition,
    )

@dataclass(frozen=True)
class TrialSummary:
    training_seed: int
    evaluation_seeds: tuple[int, ...]
    rl_average_reward: float
    utility_average_reward: float
    mean_difference: float
    verdict: str
    checkpoint_sha256: str


@dataclass(frozen=True)
class RepeatedTrialResult:
    trials: tuple[TrialSummary, ...]
    pooled_mean_difference: float
    verdict: str
    neural_trial_ready: bool


def evaluate_repeated_trials(training_seeds: tuple[int, ...],
                              evaluation_seed_groups: tuple[tuple[int, ...], ...],
                              config: QLearningConfig) -> RepeatedTrialResult:
    """Run independent training/evaluation trials and pool paired held-out evidence."""
    if not training_seeds or len(training_seeds) != len(evaluation_seed_groups):
        raise ValueError("Each training seed requires one non-empty evaluation seed group")
    summaries, pooled = [], []
    for training_seed, evaluation_seeds in zip(training_seeds, evaluation_seed_groups):
        if not evaluation_seeds:
            raise ValueError("Evaluation seed groups cannot be empty")
        result = train_q_learning(training_seed, config)
        batch = diagnose_batch(result, evaluation_seeds, config.horizon, worst_count=1)
        rl_rewards = [item.total_reward for item in batch.rl_episodes]
        utility_rewards = [item.total_reward for item in batch.utility_episodes]
        differences = [rl - utility for rl, utility in zip(rl_rewards, utility_rewards)]
        pooled.extend(differences)
        summaries.append(TrialSummary(
            training_seed=training_seed, evaluation_seeds=evaluation_seeds,
            rl_average_reward=round(sum(rl_rewards) / len(rl_rewards), 3),
            utility_average_reward=round(sum(utility_rewards) / len(utility_rewards), 3),
            mean_difference=round(sum(differences) / len(differences), 3),
            verdict=_honest_verdict(differences), checkpoint_sha256=checkpoint_digest(result),
        ))
    verdict = _honest_verdict(pooled)
    ready = verdict == "promising" and all(item.verdict == "promising" for item in summaries)
    return RepeatedTrialResult(tuple(summaries), round(sum(pooled) / len(pooled), 3),
                               verdict, ready)

@dataclass(frozen=True)
class EvaluationScenario:
    """A named held-out evaluation slice with a horizon and starting condition."""
    name: str
    horizon: int
    evaluation_seeds: tuple[int, ...]
    condition: str = "standard"

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Scenario name cannot be empty")
        if self.horizon < 1:
            raise ValueError("Scenario horizon must be at least 1")
        if not self.evaluation_seeds:
            raise ValueError("Scenario evaluation seeds cannot be empty")
        if len(set(self.evaluation_seeds)) != len(self.evaluation_seeds):
            raise ValueError("Scenario evaluation seeds must be unique")
        if self.condition not in EVALUATION_CONDITIONS:
            raise ValueError(f"Unknown evaluation condition {self.condition!r}")


@dataclass(frozen=True)
class ScenarioComparison:
    name: str
    horizon: int
    condition: str
    evaluation_seeds: tuple[int, ...]
    policy_ranking: tuple[str, ...]
    rl_average_reward: float
    utility_average_reward: float
    mean_difference: float
    rl_survival_rate: float
    utility_survival_rate: float
    rl_average_missions: float
    utility_average_missions: float
    verdict: str
    rl_rent_paid_rate: float = 0.0
    utility_rent_paid_rate: float = 0.0
    rl_dominant_action_share: float = 0.0
    utility_dominant_action_share: float = 0.0
    rl_exploit_flags: tuple[str, ...] = ()
    rl_preparation_coverage: float = 0.0
    utility_preparation_coverage: float = 0.0
    rl_prepared_success_rate: float = 0.0
    utility_prepared_success_rate: float = 0.0
    training_condition_covered: bool | None = None
    training_condition_episodes: int | None = None
    training_horizon_matches: bool | None = None
    training_scenario_episodes: int | None = None


@dataclass(frozen=True)
class ScenarioSuiteResult:
    training_seed: int
    checkpoint_sha256: str
    scenarios: tuple[ScenarioComparison, ...]
    total_episodes: int
    pooled_mean_difference: float
    verdict: str
    adoption_ready: bool


@dataclass(frozen=True)
class AdoptionDecision:
    ready: bool
    checkpoint_sha256: str
    report_sha256: str
    blockers: tuple[str, ...]


def _adoption_blockers(scenarios: tuple[ScenarioComparison, ...],
                       verdict: str) -> tuple[str, ...]:
    blockers = []
    if verdict != "promising":
        blockers.append(f"pooled verdict is {verdict}")
    for scenario in scenarios:
        if scenario.verdict != "promising":
            blockers.append(f"{scenario.name}: verdict is {scenario.verdict}")
        if scenario.training_condition_covered is not True:
            status = "unknown" if scenario.training_condition_covered is None else "absent"
            blockers.append(
                f"{scenario.name}: training condition coverage is {status}")
        elif (scenario.training_condition_episodes is None or
              scenario.training_condition_episodes < MIN_TRAINING_CONDITION_EPISODES):
            count = scenario.training_condition_episodes
            status = "unknown" if count is None else str(count)
            blockers.append(
                f"{scenario.name}: training condition exposure is {status}; "
                f"require {MIN_TRAINING_CONDITION_EPISODES}")
        if scenario.training_horizon_matches is not True:
            status = ("unknown" if scenario.training_horizon_matches is None
                      else "mismatched")
            blockers.append(
                f"{scenario.name}: training horizon alignment is {status}")
        if (scenario.training_scenario_episodes is None or
                scenario.training_scenario_episodes < MIN_TRAINING_CONDITION_EPISODES):
            count = scenario.training_scenario_episodes
            status = "unknown" if count is None else str(count)
            blockers.append(
                f"{scenario.name}: joint training exposure is {status}; "
                f"require {MIN_TRAINING_CONDITION_EPISODES}")
        if scenario.rl_survival_rate < scenario.utility_survival_rate:
            blockers.append(f"{scenario.name}: survival regression")
        if scenario.rl_average_missions < scenario.utility_average_missions:
            blockers.append(f"{scenario.name}: mission regression")
        if scenario.rl_rent_paid_rate < scenario.utility_rent_paid_rate:
            blockers.append(f"{scenario.name}: rent recovery regression")
        if (scenario.rl_dominant_action_share - scenario.utility_dominant_action_share >
                MAX_DOMINANCE_REGRESSION):
            blockers.append(f"{scenario.name}: action dominance regression")
        if scenario.rl_exploit_flags:
            flags = ", ".join(scenario.rl_exploit_flags)
            blockers.append(f"{scenario.name}: behavioral exploit flags ({flags})")
    return tuple(blockers)


def assess_policy_adoption(result: TrainingResult,
                           suite: ScenarioSuiteResult) -> AdoptionDecision:
    """Verify policy identity and explain every blocker to offline adoption."""
    digest = checkpoint_digest(result)
    blockers = list(_adoption_blockers(suite.scenarios, suite.verdict))
    if digest != suite.checkpoint_sha256:
        blockers.insert(0, "checkpoint mismatch")
    return AdoptionDecision(
        ready=not blockers, checkpoint_sha256=digest,
        report_sha256=scenario_suite_digest(suite), blockers=tuple(blockers),
    )


def evaluate_scenario_suite(result: TrainingResult,
                            scenarios: tuple[EvaluationScenario, ...]
                            ) -> ScenarioSuiteResult:
    """Evaluate one frozen policy across named, held-out fixed-horizon scenarios."""
    if not scenarios:
        raise ValueError("At least one evaluation scenario is required")
    names = [scenario.name for scenario in scenarios]
    if len(set(names)) != len(names):
        raise ValueError("Evaluation scenario names must be unique")
    evaluation_seeds = [seed for scenario in scenarios for seed in scenario.evaluation_seeds]
    if len(set(evaluation_seeds)) != len(evaluation_seeds):
        raise ValueError("Evaluation seeds must be unique across scenarios")
    summaries, pooled = [], []
    condition_episode_counts = Counter(result.episode_conditions)
    trained_horizons = set(result.episode_horizons)
    scenario_episode_counts = Counter(zip(
        result.episode_conditions, result.episode_horizons))
    for scenario in scenarios:
        batch = diagnose_batch(result, scenario.evaluation_seeds,
                               horizon=scenario.horizon, worst_count=1,
                               condition=scenario.condition)
        rl_rewards = [episode.total_reward for episode in batch.rl_episodes]
        utility_rewards = [episode.total_reward for episode in batch.utility_episodes]
        differences = [rl - utility for rl, utility in zip(rl_rewards, utility_rewards)]
        pooled.extend(differences)
        count = len(scenario.evaluation_seeds)
        rl_due = sum(episode.rent_due_reached for episode in batch.rl_episodes)
        utility_due = sum(episode.rent_due_reached for episode in batch.utility_episodes)
        rl_attempts = sum(episode.missions_attempted for episode in batch.rl_episodes)
        utility_attempts = sum(episode.missions_attempted for episode in batch.utility_episodes)
        rl_prepared = sum(episode.prepared_missions_attempted for episode in batch.rl_episodes)
        utility_prepared = sum(
            episode.prepared_missions_attempted for episode in batch.utility_episodes)
        rl_prepared_completed = sum(
            episode.prepared_missions_completed for episode in batch.rl_episodes)
        utility_prepared_completed = sum(
            episode.prepared_missions_completed for episode in batch.utility_episodes)
        rl_flags = tuple(sorted({flag for episode in batch.rl_episodes
                                 for flag in episode.exploit_flags}))
        summaries.append(ScenarioComparison(
            name=scenario.name, horizon=scenario.horizon, condition=scenario.condition,
            evaluation_seeds=scenario.evaluation_seeds,
            policy_ranking=batch.policy_ranking,
            rl_average_reward=round(sum(rl_rewards) / count, 3),
            utility_average_reward=round(sum(utility_rewards) / count, 3),
            mean_difference=round(sum(differences) / count, 3),
            rl_survival_rate=round(sum(e.survived for e in batch.rl_episodes) / count, 3),
            utility_survival_rate=round(
                sum(e.survived for e in batch.utility_episodes) / count, 3),
            rl_average_missions=round(
                sum(e.missions_completed for e in batch.rl_episodes) / count, 3),
            utility_average_missions=round(
                sum(e.missions_completed for e in batch.utility_episodes) / count, 3),
            verdict=batch.verdict,
            rl_rent_paid_rate=round(
                sum(e.rent_paid for e in batch.rl_episodes) / max(1, rl_due), 3),
            utility_rent_paid_rate=round(
                sum(e.rent_paid for e in batch.utility_episodes) / max(1, utility_due), 3),
            rl_dominant_action_share=round(
                sum(e.dominant_action_share for e in batch.rl_episodes) / count, 3),
            utility_dominant_action_share=round(
                sum(e.dominant_action_share for e in batch.utility_episodes) / count, 3),
            rl_exploit_flags=rl_flags,
            rl_preparation_coverage=round(rl_prepared / max(1, rl_attempts), 3),
            utility_preparation_coverage=round(
                utility_prepared / max(1, utility_attempts), 3),
            rl_prepared_success_rate=round(
                rl_prepared_completed / max(1, rl_prepared), 3),
            utility_prepared_success_rate=round(
                utility_prepared_completed / max(1, utility_prepared), 3),
            training_condition_covered=condition_episode_counts[scenario.condition] > 0,
            training_condition_episodes=condition_episode_counts[scenario.condition],
            training_horizon_matches=scenario.horizon in trained_horizons,
            training_scenario_episodes=scenario_episode_counts[
                (scenario.condition, scenario.horizon)],
        ))
    verdict = _honest_verdict(pooled)
    adoption_ready = not _adoption_blockers(tuple(summaries), verdict)
    return ScenarioSuiteResult(
        training_seed=result.training_seed, checkpoint_sha256=checkpoint_digest(result),
        scenarios=tuple(summaries), total_episodes=len(pooled),
        pooled_mean_difference=round(sum(pooled) / len(pooled), 3),
        verdict=verdict, adoption_ready=adoption_ready,
    )

SCENARIO_REPORT_VERSION = 8


def _scenario_suite_data(suite: ScenarioSuiteResult) -> dict:
    return {
        "report_version": SCENARIO_REPORT_VERSION,
        "training_seed": suite.training_seed,
        "checkpoint_sha256": suite.checkpoint_sha256,
        "scenarios": [asdict(scenario) for scenario in suite.scenarios],
        "total_episodes": suite.total_episodes,
        "pooled_mean_difference": suite.pooled_mean_difference,
        "verdict": suite.verdict,
        "adoption_ready": suite.adoption_ready,
    }


def scenario_suite_digest(suite: ScenarioSuiteResult) -> str:
    """Return the stable identity of a scenario-suite evaluation payload."""
    payload = json.dumps(_scenario_suite_data(suite), sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def scenario_suite_report(suite: ScenarioSuiteResult) -> str:
    """Render a deterministic, integrity-identified scenario-suite JSON report."""
    data = _scenario_suite_data(suite)
    data["sha256"] = scenario_suite_digest(suite)
    return json.dumps(data, indent=2, sort_keys=True)


def save_scenario_suite_report(suite: ScenarioSuiteResult, path: str | Path) -> Path:
    """Save a canonical scenario-suite report for audits and observer tooling."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(scenario_suite_report(suite), encoding="utf-8")
    return destination

def load_scenario_suite_report(path: str | Path) -> ScenarioSuiteResult:
    """Load a scenario-suite report only when its version and digest are intact."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    digest = data.pop("sha256", None)
    if data.get("report_version") not in (1, 2, 3, 4, 5, 6, 7, SCENARIO_REPORT_VERSION):
        raise ValueError("Unsupported scenario report version")
    payload = json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
    if digest != hashlib.sha256(payload).hexdigest():
        raise ValueError("Scenario report integrity verification failed")
    try:
        scenarios = tuple(ScenarioComparison(
            name=item["name"], horizon=item["horizon"],
            condition=item.get("condition", "standard"),
            evaluation_seeds=tuple(item["evaluation_seeds"]),
            policy_ranking=tuple(item["policy_ranking"]),
            rl_average_reward=item["rl_average_reward"],
            utility_average_reward=item["utility_average_reward"],
            mean_difference=item["mean_difference"],
            rl_survival_rate=item["rl_survival_rate"],
            utility_survival_rate=item["utility_survival_rate"],
            rl_average_missions=item["rl_average_missions"],
            utility_average_missions=item["utility_average_missions"],
            verdict=item["verdict"],
            rl_rent_paid_rate=item.get("rl_rent_paid_rate", 0.0),
            utility_rent_paid_rate=item.get("utility_rent_paid_rate", 0.0),
            rl_dominant_action_share=item.get("rl_dominant_action_share", 0.0),
            utility_dominant_action_share=item.get("utility_dominant_action_share", 0.0),
            rl_exploit_flags=tuple(item.get("rl_exploit_flags", ())),
            rl_preparation_coverage=item.get("rl_preparation_coverage", 0.0),
            utility_preparation_coverage=item.get("utility_preparation_coverage", 0.0),
            rl_prepared_success_rate=item.get("rl_prepared_success_rate", 0.0),
            utility_prepared_success_rate=item.get("utility_prepared_success_rate", 0.0),
            training_condition_covered=item.get("training_condition_covered"),
            training_condition_episodes=item.get("training_condition_episodes"),
            training_horizon_matches=item.get("training_horizon_matches"),
            training_scenario_episodes=item.get("training_scenario_episodes"),
        ) for item in data["scenarios"])
        suite = ScenarioSuiteResult(
            training_seed=data["training_seed"],
            checkpoint_sha256=data["checkpoint_sha256"], scenarios=scenarios,
            total_episodes=data["total_episodes"],
            pooled_mean_difference=data["pooled_mean_difference"],
            verdict=data["verdict"], adoption_ready=data["adoption_ready"],
        )
    except (KeyError, TypeError) as error:
        raise ValueError("Invalid scenario report schema") from error
    return suite


def diagnostics_report(batch: DiagnosticBatch) -> str:
    """Render a deterministic JSON report suitable for versioned experiment records."""
    def aggregate(episodes: tuple[EpisodeDiagnostics, ...]) -> dict:
        count = len(episodes)
        actions = Counter()
        masked = Counter()
        components = Counter()
        flags = Counter()
        critical_energy_actions = Counter()
        strained_energy_actions = Counter()
        preventive_replaced_actions = Counter()
        preventive_seen_advantages = []
        gate_readiness_blockers = Counter()
        gate_ready_displacements = Counter()
        gate_ready_displacement_reasons = Counter()
        preparation_readiness_blockers = Counter()
        preparation_heuristic_displacements = Counter()
        preparation_heuristic_displacement_reasons = Counter()
        preparation_ready_displacements = Counter()
        preparation_ready_displacement_reasons = Counter()
        mission_outcomes = []
        seen_state_outcomes = []
        for episode in episodes:
            actions.update(dict(episode.action_counts))
            mission_outcomes.extend(episode.mission_outcomes)
            seen_state_outcomes.extend(episode.seen_state_decision_outcomes)
            masked.update(dict(episode.masked_counts))
            components.update(dict(episode.reward_components))
            flags.update(episode.exploit_flags)
            critical_energy_actions.update(dict(episode.critical_energy_action_counts))
            strained_energy_actions.update(dict(episode.strained_energy_action_counts))
            preventive_replaced_actions.update(
                item.replaced_action for item in episode.preventive_rest_overrides)
            preventive_seen_advantages.extend(
                item.replaced_action_q_advantage
                for item in episode.preventive_rest_overrides
                if item.replaced_action_q_advantage is not None)
            gate_readiness_blockers.update(dict(
                episode.gate_mission_readiness_blocker_counts))
            gate_ready_displacements.update(dict(
                episode.gate_mission_ready_displacement_counts))
            gate_ready_displacement_reasons.update(dict(
                episode.gate_mission_ready_displacement_reason_counts))
            preparation_readiness_blockers.update(dict(
                episode.portal_preparation_readiness_blocker_counts))
            preparation_heuristic_displacements.update(dict(
                episode.portal_preparation_heuristic_displacement_counts))
            preparation_heuristic_displacement_reasons.update(dict(
                episode.portal_preparation_heuristic_displacement_reason_counts))
            preparation_ready_displacements.update(dict(
                episode.portal_preparation_ready_displacement_counts))
            preparation_ready_displacement_reasons.update(dict(
                episode.portal_preparation_ready_displacement_reason_counts))
        critical_decisions = sum(critical_energy_actions.values())
        strained_decisions = sum(strained_energy_actions.values())

        def mission_group(prepared: bool) -> dict:
            outcomes = [item for item in mission_outcomes
                        if item.prepared is prepared]
            return {
                "attempts": len(outcomes),
                "completed": sum(item.completed for item in outcomes),
                "success_rate": (round(sum(item.completed for item in outcomes) /
                                       len(outcomes), 3)
                                 if outcomes else None),
                "average_reward": (round(sum(item.reward for item in outcomes) /
                                         len(outcomes), 3)
                                   if outcomes else None),
                "average_progress_reward": (
                    round(sum(dict(item.reward_components).get("progress", 0.0)
                              for item in outcomes) / len(outcomes), 3)
                    if outcomes else None),
                "average_survival_reward": (
                    round(sum(dict(item.reward_components).get("survival", 0.0)
                              for item in outcomes) / len(outcomes), 3)
                    if outcomes else None),
            }

        return {
            "average_reward": round(sum(e.total_reward for e in episodes) / count, 3),
            "average_end_health": round(sum(e.end_health for e in episodes) / count, 3),
            "average_end_energy": round(sum(e.end_energy for e in episodes) / count, 3),
            "average_end_hunger": round(sum(e.end_hunger for e in episodes) / count, 3),
            "average_end_stress": round(sum(e.end_stress for e in episodes) / count, 3),
            "average_critical_energy_share": round(
                sum(e.critical_energy_share for e in episodes) / count, 3),
            "critical_energy_action_counts": dict(critical_energy_actions),
            "critical_energy_action_frequencies": {
                name: round(value / max(1, critical_decisions), 3)
                for name, value in critical_energy_actions.items()
            },
            "critical_energy_rest_share": round(
                critical_energy_actions["Rest"] / max(1, critical_decisions), 3),
            "strained_energy_action_counts": dict(strained_energy_actions),
            "strained_energy_action_frequencies": {
                name: round(value / max(1, strained_decisions), 3)
                for name, value in strained_energy_actions.items()
            },
            "strained_energy_rest_share": round(
                strained_energy_actions["Rest"] / max(1, strained_decisions), 3),
            "average_high_hunger_share": round(
                sum(e.high_hunger_share for e in episodes) / count, 3),
            "average_high_stress_share": round(
                sum(e.high_stress_share for e in episodes) / count, 3),
            "average_missions": round(sum(e.missions_completed for e in episodes) / count, 3),
            "mission_outcomes": {
                "prepared": mission_group(True),
                "unprepared": mission_group(False),
            },
            "preparation_coverage": round(
                sum(e.prepared_missions_attempted for e in episodes) /
                max(1, sum(e.missions_attempted for e in episodes)), 3),
            "prepared_success_rate": round(
                sum(e.prepared_missions_completed for e in episodes) /
                max(1, sum(e.prepared_missions_attempted for e in episodes)), 3),
            "survival_rate": round(sum(e.survived for e in episodes) / count, 3),
            "rent_paid_rate_when_due": round(
                sum(e.rent_paid for e in episodes) /
                max(1, sum(e.rent_due_reached for e in episodes)), 3),
            "average_decision_steps": round(sum(e.decision_steps for e in episodes) / count, 3),
            "average_unique_actions": round(sum(e.unique_actions for e in episodes) / count, 3),
            "average_dominant_action_share": round(
                sum(e.dominant_action_share for e in episodes) / count, 3),
            "average_low_need_recovery_count": round(
                sum(e.low_need_recovery_count for e in episodes) / count, 3),
            "average_low_need_recovery_share": round(
                sum(e.low_need_recovery_share for e in episodes) / count, 3),
            "average_social_action_count": round(
                sum(e.social_action_count for e in episodes) / count, 3),
            "average_social_action_share": round(
                sum(e.social_action_share for e in episodes) / count, 3),
            "average_unseen_state_count": round(
                sum(e.unseen_state_count for e in episodes) / count, 3),
            "average_unseen_state_share": round(
                sum(e.unseen_state_share for e in episodes) / count, 3),
            "average_seen_state_decision_count": round(
                sum(e.seen_state_decision_count for e in episodes) / count, 3),
            "average_seen_utility_disagreement_count": round(
                sum(e.seen_utility_disagreement_count for e in episodes) / count, 3),
            "seen_utility_disagreement_share": round(
                sum(e.seen_utility_disagreement_count for e in episodes) /
                max(1, sum(e.seen_state_decision_count for e in episodes)), 3),
            "seen_state_action_pair_counts": dict(Counter(
                f"{item.learned_action} -> {item.utility_action}"
                for item in seen_state_outcomes)),
            "seen_state_agreement_average_reward": (
                round(sum(item.reward for item in seen_state_outcomes if not item.disagreed) /
                      sum(not item.disagreed for item in seen_state_outcomes), 3)
                if any(not item.disagreed for item in seen_state_outcomes) else None),
            "seen_state_disagreement_average_reward": (
                round(sum(item.reward for item in seen_state_outcomes if item.disagreed) /
                      sum(item.disagreed for item in seen_state_outcomes), 3)
                if any(item.disagreed for item in seen_state_outcomes) else None),
            "seen_state_disagreement_average_paired_reward_difference": (
                round(sum(item.reward_difference for item in seen_state_outcomes
                          if item.disagreed) /
                      sum(item.disagreed for item in seen_state_outcomes), 3)
                if any(item.disagreed for item in seen_state_outcomes) else None),
            "seen_state_disagreement_paired_component_differences": {
                name: round(sum(
                    dict(item.reward_components)[name] -
                    dict(item.utility_reward_components)[name]
                    for item in seen_state_outcomes if item.disagreed) /
                    max(1, sum(item.disagreed for item in seen_state_outcomes)), 3)
                for name in REWARD_COMPONENTS
            },
            "seen_state_disagreement_mission_difference": sum(
                item.mission_completed - item.utility_mission_completed
                for item in seen_state_outcomes if item.disagreed),
            "seen_state_counterfactual_horizon": SEEN_STATE_COUNTERFACTUAL_HORIZON,
            "seen_state_disagreement_average_paired_return_difference": (
                round(sum(item.return_reward_difference for item in seen_state_outcomes
                          if item.disagreed) /
                      sum(item.disagreed for item in seen_state_outcomes), 3)
                if any(item.disagreed for item in seen_state_outcomes) else None),
            "seen_state_disagreement_paired_return_component_differences": {
                name: round(sum(
                    dict(item.return_reward_components)[name] -
                    dict(item.utility_return_reward_components)[name]
                    for item in seen_state_outcomes if item.disagreed) /
                    max(1, sum(item.disagreed for item in seen_state_outcomes)), 3)
                for name in REWARD_COMPONENTS
            },
            "seen_state_disagreement_window_mission_difference": sum(
                item.window_missions_completed -
                item.utility_window_missions_completed
                for item in seen_state_outcomes if item.disagreed),
            "average_selective_recovery_override_count": round(
                sum(e.selective_recovery_override_count for e in episodes) / count, 3),
            "selective_recovery_override_pair_counts": dict(Counter(
                pair for e in episodes for pair, amount in
                e.selective_recovery_override_pairs for _ in range(amount))),
            "average_preventive_rest_override_count": round(
                sum(e.preventive_rest_override_count for e in episodes) / count, 3),
            "average_preventive_rest_override_share": round(
                sum(e.preventive_rest_override_share for e in episodes) / count, 3),
            "preventive_rest_replaced_action_counts": dict(
                preventive_replaced_actions),
            "preventive_rest_seen_override_count": len(
                preventive_seen_advantages),
            "preventive_rest_unseen_override_count": (
                sum(e.preventive_rest_override_count for e in episodes) -
                len(preventive_seen_advantages)),
            "preventive_rest_average_replaced_q_advantage": (
                round(sum(preventive_seen_advantages) /
                      len(preventive_seen_advantages), 6)
                if preventive_seen_advantages else None),
            "average_visit_evidence_steps": round(
                sum(e.visit_evidence_steps for e in episodes) / count, 3),
            "average_zero_visit_action_share": round(
                sum(e.zero_visit_action_share for e in episodes) / count, 3),
            "average_selected_action_visits": round(
                sum(e.average_selected_action_visits for e in episodes) / count, 3),
            "gate_mission_available_steps": sum(
                e.gate_mission_available_steps for e in episodes),
            "gate_mission_selection_rate": round(
                sum(e.missions_attempted for e in episodes) /
                max(1, sum(e.gate_mission_available_steps for e in episodes)), 3),
            "gate_mission_ready_steps": sum(
                e.gate_mission_ready_steps for e in episodes),
            "gate_mission_readiness_blocker_counts": dict(
                gate_readiness_blockers),
            "portal_preparation_available_steps": sum(
                e.portal_preparation_available_steps for e in episodes),
            "portal_preparation_selection_rate": round(
                sum(dict(e.action_counts).get("Prepare portal", 0) for e in episodes) /
                max(1, sum(e.portal_preparation_available_steps for e in episodes)), 3),
            "portal_preparation_ready_steps": sum(
                e.portal_preparation_ready_steps for e in episodes),
            "portal_preparation_readiness_blocker_counts": dict(
                preparation_readiness_blockers),
            "portal_preparation_heuristic_clear_steps": sum(
                e.portal_preparation_heuristic_clear_steps for e in episodes),
            "portal_preparation_heuristic_displacement_counts": dict(
                preparation_heuristic_displacements),
            "portal_preparation_heuristic_displacement_reason_counts": dict(
                preparation_heuristic_displacement_reasons),
            "gate_mission_seen_opportunity_steps": sum(
                e.gate_mission_seen_opportunity_steps for e in episodes),
            "gate_mission_greedy_steps": sum(
                e.gate_mission_greedy_steps for e in episodes),
            "gate_mission_greedy_rate": round(
                sum(e.gate_mission_greedy_steps for e in episodes) /
                max(1, sum(e.gate_mission_seen_opportunity_steps for e in episodes)), 3),
            "gate_mission_average_q_gap": round(
                sum(e.gate_mission_q_gap_total for e in episodes) /
                max(1, sum(e.gate_mission_seen_opportunity_steps for e in episodes)), 3),
            "gate_mission_priority_clear_seen_steps": sum(
                e.gate_mission_priority_clear_seen_steps for e in episodes),
            "gate_mission_priority_clear_greedy_steps": sum(
                e.gate_mission_priority_clear_greedy_steps for e in episodes),
            "gate_mission_priority_clear_greedy_rate": (
                round(sum(e.gate_mission_priority_clear_greedy_steps
                          for e in episodes) /
                      sum(e.gate_mission_priority_clear_seen_steps
                          for e in episodes), 3)
                if any(e.gate_mission_priority_clear_seen_steps
                       for e in episodes) else None),
            "gate_mission_priority_clear_average_q_gap": (
                round(sum(e.gate_mission_priority_clear_q_gap_total
                          for e in episodes) /
                      sum(e.gate_mission_priority_clear_seen_steps
                          for e in episodes), 3)
                if any(e.gate_mission_priority_clear_seen_steps
                       for e in episodes) else None),
            "gate_mission_unseen_opportunity_steps": sum(
                e.gate_mission_unseen_opportunity_steps for e in episodes),
            "gate_mission_fallback_steps": sum(
                e.gate_mission_fallback_steps for e in episodes),
            "gate_mission_fallback_rate": round(
                sum(e.gate_mission_fallback_steps for e in episodes) /
                max(1, sum(e.gate_mission_unseen_opportunity_steps
                           for e in episodes)), 3),
            "gate_mission_ready_unseen_opportunity_steps": sum(
                e.gate_mission_ready_unseen_opportunity_steps for e in episodes),
            "gate_mission_ready_fallback_steps": sum(
                e.gate_mission_ready_fallback_steps for e in episodes),
            "gate_mission_ready_fallback_rate": round(
                sum(e.gate_mission_ready_fallback_steps for e in episodes) /
                max(1, sum(e.gate_mission_ready_unseen_opportunity_steps
                           for e in episodes)), 3),
            "gate_mission_ready_displacement_counts": dict(
                gate_ready_displacements),
            "gate_mission_ready_displacement_reason_counts": dict(
                gate_ready_displacement_reasons),
            "gate_mission_priority_clear_unseen_steps": sum(
                e.gate_mission_priority_clear_unseen_steps for e in episodes),
            "gate_mission_priority_clear_selection_steps": sum(
                e.gate_mission_priority_clear_selection_steps for e in episodes),
            "gate_mission_priority_clear_selection_rate": round(
                sum(e.gate_mission_priority_clear_selection_steps
                    for e in episodes) /
                max(1, sum(e.gate_mission_priority_clear_unseen_steps
                           for e in episodes)), 3),
            "portal_preparation_seen_opportunity_steps": sum(
                e.portal_preparation_seen_opportunity_steps for e in episodes),
            "portal_preparation_greedy_steps": sum(
                e.portal_preparation_greedy_steps for e in episodes),
            "portal_preparation_greedy_rate": round(
                sum(e.portal_preparation_greedy_steps for e in episodes) /
                max(1, sum(e.portal_preparation_seen_opportunity_steps
                           for e in episodes)), 3),
            "portal_preparation_average_q_gap": round(
                sum(e.portal_preparation_q_gap_total for e in episodes) /
                max(1, sum(e.portal_preparation_seen_opportunity_steps
                           for e in episodes)), 3),
            "portal_preparation_priority_clear_seen_steps": sum(
                e.portal_preparation_priority_clear_seen_steps
                for e in episodes),
            "portal_preparation_priority_clear_greedy_steps": sum(
                e.portal_preparation_priority_clear_greedy_steps
                for e in episodes),
            "portal_preparation_priority_clear_greedy_rate": (
                round(sum(e.portal_preparation_priority_clear_greedy_steps
                          for e in episodes) /
                      sum(e.portal_preparation_priority_clear_seen_steps
                          for e in episodes), 3)
                if any(e.portal_preparation_priority_clear_seen_steps
                       for e in episodes) else None),
            "portal_preparation_priority_clear_average_q_gap": (
                round(sum(e.portal_preparation_priority_clear_q_gap_total
                          for e in episodes) /
                      sum(e.portal_preparation_priority_clear_seen_steps
                          for e in episodes), 3)
                if any(e.portal_preparation_priority_clear_seen_steps
                       for e in episodes) else None),
            "portal_preparation_unseen_opportunity_steps": sum(
                e.portal_preparation_unseen_opportunity_steps for e in episodes),
            "portal_preparation_fallback_steps": sum(
                e.portal_preparation_fallback_steps for e in episodes),
            "portal_preparation_fallback_rate": round(
                sum(e.portal_preparation_fallback_steps for e in episodes) /
                max(1, sum(e.portal_preparation_unseen_opportunity_steps
                           for e in episodes)), 3),
            "portal_preparation_ready_unseen_opportunity_steps": sum(
                e.portal_preparation_ready_unseen_opportunity_steps
                for e in episodes),
            "portal_preparation_ready_fallback_steps": sum(
                e.portal_preparation_ready_fallback_steps for e in episodes),
            "portal_preparation_ready_fallback_rate": round(
                sum(e.portal_preparation_ready_fallback_steps for e in episodes) /
                max(1, sum(e.portal_preparation_ready_unseen_opportunity_steps
                           for e in episodes)), 3),
            "portal_preparation_ready_displacement_counts": dict(
                preparation_ready_displacements),
            "portal_preparation_ready_displacement_reason_counts": dict(
                preparation_ready_displacement_reasons),
            "portal_preparation_priority_clear_unseen_steps": sum(
                e.portal_preparation_priority_clear_unseen_steps
                for e in episodes),
            "portal_preparation_priority_clear_selection_steps": sum(
                e.portal_preparation_priority_clear_selection_steps
                for e in episodes),
            "portal_preparation_priority_clear_selection_rate": round(
                sum(e.portal_preparation_priority_clear_selection_steps
                    for e in episodes) /
                max(1, sum(e.portal_preparation_priority_clear_unseen_steps
                           for e in episodes)), 3),
            "maximum_action_streak": max(e.longest_action_streak for e in episodes),
            "action_counts": dict(actions),
            "action_frequencies": {name: round(value / sum(actions.values()), 3)
                                   for name, value in actions.items()},
            "masked_counts": dict(masked),
            "masked_frequencies": {
                name: round(value / sum(e.steps for e in episodes), 3)
                for name, value in masked.items()
            },
            "reward_components": {name: round(components[name] / count, 3)
                                  for name in REWARD_COMPONENTS},
            "exploit_flags": dict(flags),
        }
    worst = []
    for seed in batch.worst_rl_seeds:
        episode = next(item for item in batch.rl_episodes if item.seed == seed)
        worst.append({
            "seed": seed, "reward": episode.total_reward,
            "exploit_flags": episode.exploit_flags,
            "trace": [step.__dict__ for step in episode.trace],
        })
    payload = {
        "training_seed": batch.training_seed,
        "condition": batch.condition,
        "evaluation_seeds": batch.evaluation_seeds,
        "rl": aggregate(batch.rl_episodes),
        "utility": aggregate(batch.utility_episodes),
        "random": aggregate(batch.random_episodes),
        "heuristic": aggregate(batch.heuristic_episodes),
        "policy_ranking": batch.policy_ranking,
        "mean_reward_difference": batch.reward_difference,
        "reward_component_differences": dict(batch.reward_component_differences),
        "terminal_wellbeing_differences": dict(
            batch.terminal_wellbeing_differences),
        "resource_burden_differences": dict(batch.resource_burden_differences),
        "verdict": batch.verdict,
        "worst_rl_episodes": worst,
    }
    return json.dumps(payload, indent=2, sort_keys=True)

@dataclass(frozen=True)
class ScenarioResult:
    seed: int
    steps: int
    total_reward: float
    survived: bool
    rent_arrears: int
    missions_completed: int
    investigation_progress: int
    network_trust: int


def evaluate_scenario(seed: int, steps: int = 240) -> ScenarioResult:
    """Run a complete deterministic baseline scenario for later RL comparison."""
    environment = LearningEnvironment(seed)
    total = 0.0
    for _ in range(steps):
        total += environment.baseline_step().reward
    state, p = environment.simulation.state, environment.simulation.state.protagonist
    return ScenarioResult(
        seed=seed, steps=steps, total_reward=round(total, 3), survived=p.health > 0,
        rent_arrears=p.rent_arrears, missions_completed=p.missions_completed,
        investigation_progress=sum(i.progress for i in state.portal_investigations.values()),
        network_trust=sum(r.trust for r in p.relationships.values()),
    )
