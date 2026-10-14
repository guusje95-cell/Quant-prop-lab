"""Strategy interface shared by the built-in and paper strategies (see qpl.lab.strategies for the docs)."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class Param:
    default: float | int | bool | str
    min: float | None = None
    max: float | None = None
    step: float | None = None
    help: str = ""
    choices: tuple | None = None


class Strategy:
    name = "base"
    description = ""
    params: dict = {}
    long_only = False
    # 'engine' = engine applies vol-scaling and equal weights; 'raw' = signal values are already portfolio weights
    sizing = "engine"

    def signal(self, bars, p: dict) -> pd.DataFrame:  # pragma: no cover - interface
        raise NotImplementedError

    def defaults(self):
        return {k: v.default for k, v in self.params.items()}
