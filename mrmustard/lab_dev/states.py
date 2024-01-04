# Copyright 2023 Xanadu Quantum Technologies Inc.

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
The classes representing states in quantum circuits.
"""

from __future__ import annotations

from typing import Sequence

from mrmustard import math
from ..physics.representations import Bargmann
from ..utils.typing import Batch, ComplexMatrix, ComplexTensor, ComplexVector, Mode
from .circuits import Circuit
from .circuit_components import CircuitComponent

__all__ = ["Pure", "State", "Vacuum"]


class State(CircuitComponent):
    r"""
    Base class for all states.
    """
    def __init__(self, name, representation, **modes):
        super().__init__(name, representation, **modes)

    def __rshift__(self, other: Circuit | CircuitComponent):
        r"""
        Returns a ``Circuit`` with two components, light-copied from ``self`` and ``other``.
        """
        if isinstance(other, Circuit):
            return Circuit([self, *other.components])
        return Circuit([self, other])


class Ket(State):
    r"""
    Base class for all pure states. When called directly, it creates
    the N-mode vacuum ket on the specified modes. [TODO]

    Arguments:
        name: The name of this pure state.
        modes: The modes of this pure states.
    """

    def __init__(self, name: str, representation, modes: Sequence[Mode]):
        M = len(modes)
        representation = representation or Bargmann(math.zeros((M, M)), math.zeros((M,)), 1)
        super().__init__(name, representation, modes_out_ket=modes)

class DM(State):
    r"""
    Base class for all density matrices. When called directly, it creates
    the N-mode vacuum density matrix on the specified modes. [TODO]

    Arguments:
        name: The name of this density matrix.
        modes: The modes of this density matrix.
    """

    def __init__(self, name: str, representation, modes: Sequence[Mode]):
        M = len(modes)
        representation = representation or Bargmann(math.zeros((2*M, 2*M)), math.zeros((2*M,)), 1)
        super().__init__(name, representation, modes_out_bra=modes, modes_out_ket=modes)


class Vacuum(Ket):
    r"""
    The N-mode vacuum state.

    Args:
        num_modes (int): the number of modes.
    """

    def __init__(self, modes: list[int]) -> None:
        super().__init__("Vacuum", None, modes=modes)

