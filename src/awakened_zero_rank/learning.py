"""Training episodes, tabular Q-learning, and utility-policy comparison.

The core adapter stays dependency-free. Installing the ``training`` extra upgrades
its compatible fallback spaces to Gymnasium's official Env, Discrete, and Box types.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
import random

try:
    import gymnasium as gym
    import numpy as np
except ImportError:  # The core simulation remains dependency-free.
    gym = None
    np = None

from .actions import available_actions
from .models import SLOTS
from .simulation import Simulation


ACTION_NAMES = (
    "Eat", "Rest", "Part-time work", "Study", "Train", "Visit hunter shop",
    "Talk with Aiko", "Guild patrol", "Prepare portal", "Gate mission",
)


@dataclass(frozen=True)
class Transition:
    observation: tuple[float, ...]
    reward: float
    action: str
    valid_actions: tuple[str, ...]
    event_outcome: str


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
        )

    def action_mask(self) -> tuple[int, ...]:
        valid = set(self.valid_actions)
        return tuple(int(name in valid) for name in ACTION_NAMES)

    def step(self, action: str) -> Transition:
        if action not in self.valid_actions:
            raise ValueError(f"Invalid action {action!r}; valid actions: {self.valid_actions}")
        before = self._score()
        event = self.simulation.step(action)
        reward = round(self._score() - before, 3)
        return Transition(self.observe(), reward, action, self.valid_actions, event.outcome)

    def baseline_step(self) -> Transition:
        before = self._score()
        event = self.simulation.step()
        reward = round(self._score() - before, 3)
        return Transition(self.observe(), reward, event.action, self.valid_actions, event.outcome)

    def _score(self) -> float:
        p = self.simulation.state.protagonist
        survival = p.health * 0.5 + p.energy * 0.12 - p.hunger * 0.12 - p.stress * 0.08
        stability = min(p.money, p.rent_cost * 2) / 350 - p.rent_arrears / 250
        progress = p.rank_points * 0.7 + p.missions_completed * 2 + p.ability_mastery * 0.2
        social = sum((r.trust - r.tension) * 0.08 for r in p.relationships.values())
        return survival + stability + progress + social

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
    shape = (18,)

    @staticmethod
    def contains(value: object) -> bool:
        return (isinstance(value, (tuple, list)) and len(value) == 18 and
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
                low=-float("inf"), high=float("inf"), shape=(18,), dtype=np.float32
            )
        else:
            self.action_space = DiscreteSpace(len(ACTION_NAMES), seed)
            self.observation_space = ObservationSpace()
        self.environment = LearningEnvironment(seed)
        self.elapsed_steps, self._finished = 0, False

    @property
    def simulation(self) -> Simulation:
        return self.environment.simulation

    def action_masks(self) -> tuple[int, ...]:
        return self.environment.action_mask()

    def reset(self, *, seed: int | None = None, options: dict | None = None
              ) -> tuple[tuple[float, ...], dict]:
        del options
        if gym:
            super().reset(seed=seed)
        episode_seed = self.initial_seed if seed is None else seed
        self.environment = LearningEnvironment(episode_seed)
        self.action_space.seed(episode_seed)
        self.elapsed_steps, self._finished = 0, False
        observation = self.environment.observe()
        if np is not None:
            observation = np.asarray(observation, dtype=np.float32)
        return observation, {"action_mask": self.action_masks(), "seed": episode_seed}

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
                "event_outcome": transition.event_outcome, "elapsed_steps": self.elapsed_steps}
        observation = transition.observation
        if np is not None:
            observation = np.asarray(observation, dtype=np.float32)
        return observation, transition.reward, terminated, truncated, info


GymnasiumEnvironment = TrainingEnvironment


@dataclass(frozen=True)
class QLearningConfig:
    episodes: int = 40
    horizon: int = 120
    learning_rate: float = 0.15
    discount_factor: float = 0.95
    epsilon_start: float = 0.30
    epsilon_end: float = 0.05

    def __post_init__(self) -> None:
        if self.episodes < 1 or self.horizon < 1:
            raise ValueError("episodes and horizon must be at least 1")
        if not 0 < self.learning_rate <= 1 or not 0 <= self.discount_factor <= 1:
            raise ValueError("learning_rate and discount_factor must be between 0 and 1")
        if not 0 <= self.epsilon_end <= self.epsilon_start <= 1:
            raise ValueError("epsilon must satisfy 0 <= end <= start <= 1")


QTable = dict[tuple[int, ...], list[float]]


@dataclass(frozen=True)
class TrainingResult:
    training_seed: int
    config: QLearningConfig
    q_table: QTable = field(compare=True)
    episode_rewards: tuple[float, ...] = ()
    episode_seeds: tuple[int, ...] = ()


def discretize(observation) -> tuple[int, ...]:
    return tuple(max(-4, min(4, math.floor(value * 4))) for value in observation)


def _greedy_action(values: list[float], mask: tuple[int, ...]) -> int:
    valid = [i for i, allowed in enumerate(mask) if allowed]
    return max(valid, key=lambda index: (values[index], -index))


def train_q_learning(training_seed: int, config: QLearningConfig | None = None) -> TrainingResult:
    """Train a reproducible masked tabular Q-policy using training seeds only."""
    config = config or QLearningConfig()
    rng, table, totals, episode_seeds = random.Random(training_seed), {}, [], []
    for episode in range(config.episodes):
        episode_seed = rng.randrange(2**31)
        episode_seeds.append(episode_seed)
        env = TrainingEnvironment(episode_seed, config.horizon)
        observation, info = env.reset(seed=episode_seed)
        total = 0.0
        epsilon = (config.epsilon_start if config.episodes == 1 else config.epsilon_start +
                   (config.epsilon_end - config.epsilon_start) * episode / (config.episodes - 1))
        while True:
            state = discretize(observation)
            values = table.setdefault(state, [0.0] * len(ACTION_NAMES))
            mask = info["action_mask"]
            action = (rng.choice([i for i, valid in enumerate(mask) if valid])
                      if rng.random() < epsilon else _greedy_action(values, mask))
            next_observation, reward, terminated, truncated, info = env.step(action)
            next_values = table.setdefault(discretize(next_observation), [0.0] * len(ACTION_NAMES))
            future = 0.0 if terminated or truncated else next_values[_greedy_action(next_values, info["action_mask"])]
            values[action] += config.learning_rate * (reward + config.discount_factor * future - values[action])
            observation, total = next_observation, total + reward
            if terminated or truncated:
                break
        totals.append(round(total, 3))
    return TrainingResult(training_seed, config, table, tuple(totals), tuple(episode_seeds))


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
            values = result.q_table.get(discretize(observation), [0.0] * len(ACTION_NAMES))
            action = _greedy_action(values, info["action_mask"])
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
