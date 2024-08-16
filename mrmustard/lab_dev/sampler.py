# Copyright 2024 Xanadu Quantum Technologies Inc.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
"""

from __future__ import annotations

from typing import Any

import numpy as np

from mrmustard import math

from ..physics.representations import Fock
from .states import State, Number, QuadratureEigenstate
from .transformations import Identity

__all__ = ["Sampler", "PNRSampler", "HomodyneSampler"]


class Sampler:
    r""" """

    def __init__(
        self, meas_out: list[Any], meas_ops: list[State], probs: None | list[float] = None
    ):
        self._meas_ops = meas_ops
        self._meas_outcomes = meas_out
        self._probs = probs

    @property
    def meas_ops(self):
        r""" """
        return self._meas_ops

    def _verify_povms(self):
        summation = sum(self.meas_ops[1:], self.meas_ops[0])
        summation = summation / np.max(summation.representation.ansatz.array)
        identity = (
            Identity(summation.modes).to_fock()
            if isinstance(summation.representation, Fock)
            else Identity(summation.modes)
        )
        if summation.representation != identity.representation:
            raise ValueError("POVMs do not sum to the identity.")

    def sample(self, state: State, n_samples: int) -> list[Any]:
        r""" """
        rng = np.random.default_rng()
        return [rng.choice(a=self._meas_outcomes, p=self.probs(state)) for _ in range(n_samples)]

    def probs(self, state: State | None = None):
        r""" """
        if self._probs is None:
            states = [state >> meas_op.dual for meas_op in self.meas_ops]
            probs = [
                state.probability if isinstance(state, State) else math.real(state)
                for state in states
            ]
            return probs / sum(probs)
        return self._probs


class PNRSampler(Sampler):
    r""" """

    def __init__(self, cutoff: int) -> None:
        super().__init__(list(range(cutoff)), [Number([0], n).dm() for n in range(cutoff)])


class HomodyneSampler(Sampler):
    r""" """

    def __init__(
        self,
        q_bounds: tuple[float, float],
        bin_num: int,
    ):
        qs = np.linspace(*q_bounds, num=bin_num)
        super().__init__(qs, [QuadratureEigenstate([0], x=q, phi=0).dm() for q in qs])