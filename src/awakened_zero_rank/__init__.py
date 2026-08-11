"""AWAKENED ZERO RANK simulation package."""

from .observer import observer_snapshot
from .simulation import Simulation

__version__ = "0.165.0"

__all__ = ["Simulation", "__version__", "observer_snapshot"]
