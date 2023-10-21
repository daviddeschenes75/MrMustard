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

from __future__ import annotations

from typing import Optional, Union
from itertools import product
import numpy as np

from mrmustard import settings
from mrmustard.physics.representations import Data, MatVecData
from mrmustard.physics.bargmann import contract_two_Abc, reorder_abc
from mrmustard.math import Math
from mrmustard.utils.typing import Batch, ComplexMatrix, ComplexVector, Matrix, Scalar, Vector

math = Math()


class Bargmann(MatVecData):
    r"""Exponential of quadratic polynomial for the Fock-Bargmann function.

    Quadratic polynomial is made of: quadratic coefficients, linear coefficients, constant.
    Each of these has a batch dimension, and the batch dimension is the same for all of them.
    They are the parameters of the function `c * exp(x^T A x / 2 + x^T b)`.

    Note that if constants are not provided, they will all be initialized at 1.

    Args:
        A (Batch[ComplexMatrix]):          series of quadratic coefficient
        b (Batch[ComplexVector]):          series of linear coefficients
        c (Optional[Batch[complex]]):series of constants
    """

    def __init__(
        self, A: Batch[ComplexMatrix], b: Batch[ComplexVector], c: Optional[Batch[Scalar]] = None
    ) -> None:
        super().__init__(mat=A, vec=b, coeffs=c)
        self._contract_idxs = []

    def __call__(self, z: ComplexVector) -> Scalar:
        r"""Value of this Fock-Bargmann function at z.

        Args:
            z (ComplexVector): point at which the function is evaluated

        Returns:
            Scalar: value of the function
        """
        val = 0.0
        for A, b, c in zip(self.A, self.b, self.c):
            val += math.exp(0.5 * math.sum(z * math.matvec(A, z)) + math.sum(z * b)) * c
        return val

    @property
    def A(self) -> Batch[ComplexMatrix]:
        return self.mat

    @property
    def b(self) -> Batch[ComplexVector]:
        return self.vec

    @property
    def c(self) -> Batch[Scalar]:
        return self.coeffs

    def __mul__(self, other: Union[Scalar, Bargmann]) -> Bargmann:
        if isinstance(other, Bargmann):
            new_a = [A1 + A2 for A1, A2 in product(self.A, other.A)]
            new_b = [b1 + b2 for b1, b2 in product(self.b, other.b)]
            new_c = [c1 * c2 for c1, c2 in product(self.c, other.c)]
            return self.__class__(A=new_a, b=new_b, c=new_c)
        else:
            try:  # scalar
                return self.__class__(self.A, self.b, other * self.c)
            except Exception as e:  # Neither same object type nor a scalar case
                raise TypeError(f"Cannot multiply {self.__class__} and {other.__class__}.") from e

    def __and__(self, other: Bargmann) -> Bargmann:
        As = [math.block_diag(a1, a2) for a1 in self.A for a2 in other.A]
        bs = [math.concat([b1, b2], axis=-1) for b1 in self.b for b2 in other.b]
        cs = [c1 * c2 for c1 in self.c for c2 in other.c]
        return self.__class__(As, bs, cs)

    def conj(self):
        new = self.__class__(math.conj(self.A), math.conj(self.b), math.conj(self.c))
        new._contract_idxs = self._contract_idxs
        return new

    def __matmul__(self, other: Bargmann) -> Bargmann:
        r"""Implements the contraction of (A,b,c) triples across the marked indices."""
        A, b, c = contract_two_Abc(
            (self.A, self.b, self.c),
            (other.A, other.b, other.c),
            self._contract_idxs,
            other._contract_idxs,
        )

        return self.__class__(A, b, c)

    def __getitem__(self, idx: int | tuple[int, ...]) -> Bargmann:
        idx = (idx,) if isinstance(idx, int) else idx
        for i in idx:
            if i > self.dim:
                raise IndexError(
                    f"Index {i} out of bounds for {self.__class__.__qualname__} of dimension {self.dim}."
                )
        new = self.__class__(self.A, self.b, self.c)
        new._contract_idxs = idx
        return new

    def reorder(self, order: tuple[int, ...] | list[int]) -> Bargmann:
        A, b, c = reorder_abc((self.A, self.b, self.c), order)
        new = self.__class__(A, b, c)
        new._contract_idxs = self._contract_idxs
        return new