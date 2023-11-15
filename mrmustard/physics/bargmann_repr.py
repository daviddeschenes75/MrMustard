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

from itertools import product
from typing import Iterable, Optional, Union

import numpy as np

from mrmustard.math.tensor_networks.wires import Wires
import mrmustard.math as math
from mrmustard import settings
from mrmustard.lab.abstract.representation import Representation
from mrmustard.physics.bargmann import contract_two_Abc, reorder_abc
from mrmustard.utils.typing import Batch, ComplexMatrix, ComplexTensor, ComplexVector, Scalar


class Bargmann(Representation):
    r"""Fock-Bargmann function constrained to the functional form of a sum of exponentials of a quadratic polynomial
    times a fixed-degree polynomial: `F(z) = sum_i poly_i(z) c_i * exp(1/2 z^T A_i z + z^T b_i)`.

    The i-th quadratic polynomial in the exponential is parametrized by a triple (A_i,b_i,c_i) of tensors,
    where A_i is a complex matrix, b_i is a compatible complex vector, and c_i is a complex scalar.

    This function supports linear tensor algebra (linear combinations, outer product and inner product).
    The inner product is defined as the contraction of two Fock-Bargmann objects across marked indices.
    This can also be used to contract existing indices in one Bargmann object, e.g. to implement the partial trace.

    Args:
        A (Batch[ComplexMatrix]):          batch of quadratic coefficient A_i
        b (Batch[ComplexVector]):          batch of linear coefficients b_i
        c (Optional[Batch[complex]]):      batch of coefficients c_i (default: [1.0])
        poly (Optional[Batch[ComplexTensor]]):    batch of fixed-degree polynomial (default: [1.0])
        modesSpec (Optional[dict]):        dictionary of modes specifications
    """

    def __init__(
        self,
        A: Batch[ComplexMatrix],
        b: Batch[ComplexVector],
        c: Batch[Scalar],
        poly: Optional[Batch[ComplexTensor]] = None,
        modes_in_bra=[],
        modes_in_ket=[],
        modes_out_bra=[],
        modes_out_ket=[],
    ):

        self.A = math.atleast_3d(math.astensor(A))
        self.b = math.atleast_2d(math.astensor(b))
        self.c = math.atleast_1d(math.astensor(c))
        self.poly = (poly if len(poly.shape) == len(self.A.shape) else math.reshape(poly, (-1,) + poly.shape))
        assert len(self.A) == len(self.b) == len(self.c) == len(self.poly), "All inputs must have the same batch size."
        assert self.A.shape[-1] == self.A.shape[-2] == self.b.shape[-1], "A and b must have compatible dimensions"
        self.batch_dim = self.A.shape[0]
        self.dim = self.A.shape[-1]
        self.wires = Wires(
            modes_out_bra=modes_out_bra,
            modes_in_bra=modes_in_bra,
            modes_out_ket=modes_out_ket,
            modes_in_ket=modes_in_ket,
        )

    def _from_self(self, A=None, b=None, c=None, poly=None):
        new = self.__class__(A or self.A, b or self.b, c or self.c, poly or self.poly)
        new.wires = self.wires
        return new

    def __neg__(self) -> Bargmann:
        return self._from_self(self.A, self.b, -self.c)

    def __eq__(self, other: Bargmann, exclude_scalars: bool = False) -> bool:
        A, B = sorted([self, other], key=lambda x: x.batch_dim)  # A is a smaller or equal batch than B
        # check scalars
        Ac = np.around(A.coeffs, settings.EQ_TRANSFORMATION_RTOL_GAUSS)
        Bc = memoryview(np.around(B.coeffs, settings.EQ_TRANSFORMATION_RTOL_GAUSS)).tobytes()
        if exclude_scalars or all(memoryview(c).tobytes() in Bc for c in Ac):
            # check vectors
            Av = np.around(A.vec, settings.EQ_TRANSFORMATION_RTOL_GAUSS)
            Bv = memoryview(np.around(B.vec, settings.EQ_TRANSFORMATION_RTOL_GAUSS)).tobytes()
            if all(memoryview(v).tobytes() in Bv for v in Av):
                # check matrices
                Am = np.around(A.mat, settings.EQ_TRANSFORMATION_RTOL_GAUSS)
                Bm = memoryview(np.around(B.mat, settings.EQ_TRANSFORMATION_RTOL_GAUSS)).tobytes()
                if all(memoryview(m).tobytes() in Bm for m in Am):
                    # check poly
                    Ap = np.around(A.poly, settings.EQ_TRANSFORMATION_RTOL_GAUSS)
                    Bp = memoryview(np.around(B.poly, settings.EQ_TRANSFORMATION_RTOL_GAUSS)).tobytes()
                    if all(memoryview(p).tobytes() in Bp for p in Ap):
                        return True
        return False

    def __add__(self, other: Bargmann) -> Bargmann:
        if self.__eq__(other, exclude_scalars=True):
            return self._from_self(self.A, self.b, self.c + other.c)
        combined_A = math.concat([self.A, other.A], axis=0)
        combined_b = math.concat([self.b, other.b], axis=0)
        combined_c = math.concat([self.c, other.c], axis=0)
        return self._from_self(combined_A, combined_b, combined_c)

    def __truediv__(self, x: Scalar) -> Bargmann:
        if not isinstance(x, (int, float, complex)):
            raise TypeError(f"Cannot divide {self.__class__} by {x.__class__}.")
        return self._from_self(self.A, self.b, self.c / x)

    def __call__(self, z: ComplexVector) -> Scalar:
        r"""Value of this Fock-Bargmann function at z.

        Args:
            z (ComplexVector): point at which the function is evaluated

        Returns:
            Scalar: value of the function
        """
        assert len(z) == self.dim
        val = 0.0
        for A, b, c in zip(self.A, self.b, self.c):
            val += math.exp(0.5 * math.sum(z * math.matvec(A, z)) + math.sum(z * b)) * c
        return val

    def __mul__(self, other: Union[Scalar, Bargmann]) -> Bargmann:
        if isinstance(other, Bargmann):
            new_a = [A1 + A2 for A1, A2 in product(self.A, other.A)]
            new_b = [b1 + b2 for b1, b2 in product(self.b, other.b)]
            new_c = [c1 * c2 for c1, c2 in product(self.c, other.c)]
            return self._from_self(math.astensor(new_a), math.astensor(new_b), math.astensor(new_c))
        else:  # assume other is a scalar
            return self._from_self(self.A, self.b, other * self.c)

    def __and__(self, other: Bargmann) -> Bargmann:
        As = [math.block_diag(a1, a2) for a1 in self.A for a2 in other.A]
        bs = [math.concat([b1, b2], axis=-1) for b1 in self.b for b2 in other.b]
        cs = [c1 * c2 for c1 in self.c for c2 in other.c]
        return self.__class_from_self(math.astensor(As), math.astensor(bs), math.astensor(cs))

    def conj(self):
        return self._from_self(math.conj(self.A), math.conj(self.b), math.conj(self.c))

    def __matmul__(self, other: Bargmann) -> Bargmann:
        r"""Implements the contraction of (A,b,c) triples across the marked indices."""
        Abc = []
        for A1, b1, c1 in zip(self.A, self.b, self.c):
            for A2, b2, c2 in zip(other.A, other.b, other.c):
                Abc.append(
                    contract_two_Abc(
                        (A1, b1, c1),
                        (A2, b2, c2),
                        self._contract_idxs,
                        other._contract_idxs,
                    )
                )
        A, b, c = zip(*Abc)
        # now we just make a new Bargmann object with the contracted A,b,c
        return self.__class__(math.astensor(A), math.astensor(b), math.astensor(c), **self.modesSpec)

    def __getitem__(self, modes: int | Iterable[int]) -> Bargmann:
        # flags the in/out/ket/bra wires at the given modes
        modes = [modes] if isinstance(modes, int) else modes
        new = self.from_self(modes=self.modes).flag(modes=modes)
        return new

    def reorder(self, order: list[int]) -> Bargmann:
        A, b, c = reorder_abc((self.A, self.b, self.c), order)
        new = self.__class__(A, b, c)
        transposed_idxs = {i: j for j, i in enumerate(order)}
        new._contract_idxs = [transposed_idxs[i] for i in self._contract_idxs]
        return new

    def simplify(self) -> None:
        r"""use math.unique_tensors to remove duplicates of a tensor in the A stack, b stack, and c stack"""
        # indices unique tensors of A,b,c stacks
        unique_A = (i for i, _ in math.unique_tensors(self.A))
        unique_b = (i for i, _ in math.unique_tensors(self.b))
        unique_c = (i for i, _ in math.unique_tensors(self.c))
        # unique triples of A,b,c
        uniques = [i for i in unique_A if i in unique_b and i in unique_c]
        # gather unique triples
        self.mat = math.gather(self.A, uniques, axis=0)
        self.vec = math.gather(self.b, uniques, axis=0)
        self.coeff = math.gather(self.c, uniques, axis=0)