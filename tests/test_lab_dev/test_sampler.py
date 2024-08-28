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

"""Tests for the sampler."""

# pylint: disable=missing-function-docstring

import pytest

from mrmustard import math

from mrmustard.lab_dev.sampler import Sampler, PNRSampler
from mrmustard.lab_dev import Number, Vacuum, Coherent


class TestSampler:
    r"""
    Tests ``Sampler`` objects.
    """

    def test_init(self):
        meas_outcomes = list(range(3))
        meas_ops = [Number([0], n) for n in range(3)]
        prob_dist = [0.3, 0.4, 0.5]

        sampler = Sampler(meas_outcomes, meas_ops, prob_dist)
        assert sampler.meas_outcomes == meas_outcomes
        assert sampler.meas_ops == meas_ops
        assert sampler.prob_dist == prob_dist

        sampler2 = Sampler(meas_outcomes)
        assert sampler2.meas_outcomes == meas_outcomes
        assert sampler2.meas_ops is None
        assert sampler2.prob_dist is None

    def test_probabilities(self):
        meas_outcomes = list(range(3))
        meas_ops = [Number([0], n) for n in range(3)]
        prob_dist = [0.3, 0.4, 0.5]

        sampler = Sampler(meas_outcomes, meas_ops, prob_dist)
        assert sampler.probabilities() == prob_dist

        sampler2 = Sampler(meas_outcomes, meas_ops)
        assert sampler2.probabilities() is None

        state = Vacuum([0])
        assert sampler2.probabilities(state) == [1, 0, 0]

        with pytest.raises(ValueError, match="incompatible"):
            sampler_two_mode = Sampler(
                meas_outcomes, [Number([0, 1], n) for n in range(3)], prob_dist
            )
            sampler_two_mode.probabilities(state)

    def test_sample(self):
        meas_outcomes = list(range(3))
        meas_ops = [Number([0], n) for n in range(3)]
        prob_dist = [0, 0, 1]

        sampler = Sampler(meas_outcomes, meas_ops, prob_dist)
        assert all(sampler.sample() == 2)
        assert all(sampler.sample(Vacuum([0])) == 0)


class TestPNRSampler:
    def test_init(self):
        sampler = PNRSampler([0, 1], cutoff=10)
        assert sampler.meas_outcomes == list(range(10))
        assert sampler.meas_ops == [Number([0, 1], n) for n in range(10)]
        assert sampler.prob_dist is None

    def test_probabilities(self):
        sampler = PNRSampler([0, 1], cutoff=10)
        vac_prob = [1.0] + [0.0] * 9
        assert sampler.probabilities() is None
        assert sampler.probabilities(Vacuum([0, 1])) == vac_prob
        assert sampler.probabilities(Vacuum([0, 1, 2])) == vac_prob

        state = Coherent([0, 1], x=[0, 1])
        fock_state = state.to_fock()
        assert math.allclose(sampler.probabilities(state), sampler.probabilities(fock_state))
