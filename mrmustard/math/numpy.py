# Copyright 2021 Xanadu Quantum Technologies Inc.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""This module contains the numpy implementation of the :class:`Math` interface."""

from math import lgamma as mlgamma
from typing import Callable, List, Optional, Sequence, Tuple, Union
from scipy.linalg import expm as scipy_expm
from scipy.special import xlogy as scipy_xlogy

import numpy as np

from mrmustard import settings
from mrmustard.math.autocast import Autocast
from mrmustard.math.lattice import strategies
from mrmustard.typing import Tensor, Trainable

from .math_interface import MathInterface


# pylint: disable=too-many-public-methods,no-self-argument,arguments-differ
class NPMath(MathInterface):
    r"""Numpy implementation of the :class:`Math` interface."""

    float64 = np.float64
    float32 = np.float32
    complex64 = np.complex64
    complex128 = np.complex128

    def __getattr__(self, name):
        return getattr(np, name)

    # ~~~~~~~~~
    # Basic ops
    # ~~~~~~~~~

    def abs(self, array: np.array) -> np.array:
        return np.abs(array)

    def any(self, array: np.array) -> np.array:
        return np.any(array)

    def arange(self, start: int, limit: int = None, delta: int = 1, dtype=np.float64) -> np.array:
        return np.arange(start, limit, delta, dtype=dtype)

    def asnumpy(self, tensor: np.array) -> np.array:
        return tensor

    def assign(self, tensor: np.array, value: np.array) -> np.array:
        # ??
        # How do we handle this?
        tensor = value
        return tensor

    def astensor(self, array: Union[np.ndarray, np.array], dtype=None) -> np.array:
        from tensorflow import convert_to_tensor, float64

        dtype = dtype or float64
        return convert_to_tensor(array, dtype=dtype)

    def atleast_1d(self, array: np.array, dtype=None) -> np.array:
        return self.cast(np.atleast_1d(array), dtype=dtype)

    def cast(self, array: np.array, dtype=None) -> np.array:
        if dtype is None:
            return array
        # ??
        # arrays can sometimes be float?
        if not isinstance(array, np.ndarray):
            return array
        return array.astype(dtype)  # gotta fix the warning

    def clip(self, array, a_min, a_max) -> np.array:
        return np.clip(array, a_min, a_max)

    def concat(self, values: List[np.array], axis: int) -> np.array:
        return np.concatenate(values, axis)

    def conj(self, array: np.array) -> np.array:
        return np.conj(array)

    def constraint_func(self, bounds: Tuple[Optional[float], Optional[float]]) -> None:
        # ??
        pass

    # pylint: disable=arguments-differ
    @Autocast()
    def convolution(
        self,
        array: np.array,
        filters: np.array,
        strides: Optional[List[int]] = None,
        padding="VALID",
        data_format="NWC",
        dilations: Optional[List[int]] = None,
    ) -> np.array:
        # ?? Seem to only be able to do 2D convolutions
        pass

    def cos(self, array: np.array) -> np.array:
        return np.cos(array)

    def cosh(self, array: np.array) -> np.array:
        return np.cosh(array)

    def atan2(self, y: np.array, x: np.array) -> np.array:
        # ??
        # add test
        return np.arctan(y, x)

    def make_complex(self, real: np.array, imag: np.array) -> np.array:
        return real + 1j * imag

    def det(self, matrix: np.array) -> np.array:
        return np.linalg.det(matrix)

    def diag(self, array: np.array, k: int = 0) -> np.array:
        # ??
        # this is hard. is it correct?
        # thi difficulty is due to the fact that np.diag does a
        # different thing for shapes > 2 (it just gets the diagonal)
        if len(array.shape) == 1:
            return np.diag(array, k=k)
        elif len(array.shape) == 2:
            return np.array([np.diag(l, k=k).tolist() for l in array])
        else:
            # fallback into more complex algorithm
            original_sh = array.shape

            ravelled_sh = (np.prod(original_sh[:-1]), original_sh[-1])
            array = array.ravel().reshape(*ravelled_sh)

            ret = []
            for line in array:
                ret.append(np.diag(line, k))

            ret = np.array(ret)
            inner_shape = (
                original_sh[-1] + abs(k),
                original_sh[-1] + abs(k),
            )
            return ret.reshape(original_sh[:-1] + inner_shape)

    def diag_part(self, array: np.array) -> np.array:
        # ??
        # seems like it's always only used on 2-D matrices
        if array.shape != 2:
            raise ValueError("`diag_part` only supports 2-D arrays.")
        return np.diag(array)

    def einsum(self, string: str, *tensors) -> np.array:
        if type(string) is str:
            return np.einsum(string, *tensors)
        return None  # provide same functionality as numpy.einsum or upgrade to opt_einsum

    def exp(self, array: np.array) -> np.array:
        return np.exp(array)

    def expand_dims(self, array: np.array, axis: int) -> np.array:
        return np.expand_dims(array, axis)

    def expm(self, matrix: np.array) -> np.array:
        return scipy_expm(matrix)

    def eye(self, size: int, dtype=np.float64) -> np.array:
        return np.eye(size, dtype=dtype)

    def eye_like(self, array: np.array) -> Tensor:
        return np.eye(array.shape[-1], dtype=array.dtype)

    def from_backend(self, value) -> bool:
        return isinstance(value, np.ndarray)

    def gather(self, array: np.array, indices: np.array, axis: int = None) -> np.array:
        return np.take(array, indices, axis=axis)

    def hash_tensor(self, tensor: np.array) -> int:
        return hash(tensor.tobytes())

    def imag(self, array: np.array) -> np.array:
        return np.imag(array)

    def inv(self, tensor: np.array) -> np.array:
        return np.linalg.inv(tensor)

    def is_trainable(self, tensor: np.array) -> bool:
        return True

    def lgamma(self, x: np.array) -> np.array:
        return mlgamma(x)

    def log(self, x: np.array) -> np.array:
        return np.log(x)

    @Autocast()
    def matmul(
        self,
        a: np.array,
        b: np.array,
        transpose_a=False,
        transpose_b=False,
        adjoint_a=False,
        adjoint_b=False,
    ) -> np.array:
        a = a.T if transpose_a else a
        b = b.T if transpose_b else b
        a = np.conj(a) if adjoint_a else a
        b = np.conj(b) if adjoint_b else b
        return np.matmul(a, b)

    @Autocast()
    def matvec(self, a: np.array, b: np.array, transpose_a=False, adjoint_a=False) -> np.array:
        # ??
        # difference between matvec and matmul?
        return self.matmul(a, b, transpose_a, adjoint_a)

    @Autocast()
    def maximum(self, a: np.array, b: np.array) -> np.array:
        return np.maximum(a, b)

    @Autocast()
    def minimum(self, a: np.array, b: np.array) -> np.array:
        return np.minimum(a, b)

    def new_variable(
        self,
        value,
        bounds: Union[Tuple[Optional[float], Optional[float]], None],
        name: str,
        dtype=np.float64,
    ):
        return np.array(value, dtype=dtype)

    def new_constant(self, value, name: str, dtype=np.float64):
        return np.array(value, dtype=dtype)

    def norm(self, array: np.array) -> np.array:
        return np.linalg.norm(array)

    def ones(self, shape: Sequence[int], dtype=np.float64) -> np.array:
        return np.ones(shape, dtype=dtype)

    def ones_like(self, array: np.array) -> np.array:
        return np.ones(array.shape)

    @Autocast()
    def outer(self, array1: np.array, array2: np.array) -> np.array:
        return np.outer(array1, array2)

    def pad(
        self,
        array: np.array,
        paddings: Sequence[Tuple[int, int]],
        mode="constant",
        constant_values=0,
    ) -> np.array:
        return np.pad(array, paddings, mode, constant_values=constant_values)

    @staticmethod
    def pinv(matrix: np.array) -> np.array:
        return np.linalg.pinv(matrix)

    @Autocast()
    def pow(self, x: np.array, y: float) -> np.array:
        return np.power(x, y)

    def real(self, array: np.array) -> np.array:
        return np.real(array)

    def reshape(self, array: np.array, shape: Sequence[int]) -> np.array:
        return np.reshape(array, shape)

    def sin(self, array: np.array) -> np.array:
        return np.sin(array)

    def sinh(self, array: np.array) -> np.array:
        return np.sinh(array)

    def solve(self, matrix: np.array, rhs: np.array) -> np.array:
        if len(rhs.shape) == len(matrix.shape) - 1:
            rhs = np.expand_dims(rhs, -1)
            return np.linalg.solve(matrix, rhs)[..., 0]
        return np.linalg.solve(matrix, rhs)

    def sqrt(self, x: np.array, dtype=None) -> np.array:
        return np.sqrt(self.cast(x, dtype))

    def sum(self, array: np.array, axes: Sequence[int] = None):
        return np.sum(array, axes)

    @Autocast()
    def tensordot(self, a: np.array, b: np.array, axes: List[int]) -> np.array:
        return np.tensordot(a, b, axes)

    def tile(self, array: np.array, repeats: Sequence[int]) -> np.array:
        return np.tile(array, repeats)

    def trace(self, array: np.array, dtype=None) -> np.array:
        return self.cast(np.trace(array), dtype)

    def transpose(self, a: np.array, perm: Sequence[int] = None) -> np.array:
        if a is None:
            return None  # TODO: remove and address None inputs where tranpose is used
        return np.transpose(a, perm)

    @Autocast()
    def update_tensor(self, tensor: np.array, indices: np.array, values: np.array):
        # return np.array_scatter_nd_update(tensor, indices, values)
        # ??
        pass

    @Autocast()
    def update_add_tensor(self, tensor: np.array, indices: np.array, values: np.array):
        # ??
        # https://stackoverflow.com/questions/65734836/numpy-equivalent-to-tf-tensor-scatter-nd-add-method
        indices = np.array(indices)  # figure out why we need this
        indices = tuple(indices.reshape(-1, indices.shape[-1]).T)
        np.add.at(tensor, indices, values)
        return tensor

    def unique_tensors(self, lst: List[Tensor]) -> List[Tensor]:
        hash_dict = {}
        for tensor in lst:
            try:
                if (hash := self.hash_tensor(tensor)) not in hash_dict:
                    hash_dict[hash] = tensor
            except TypeError:
                continue
        return list(hash_dict.values())

    def zeros(self, shape: Sequence[int], dtype=np.float64) -> np.array:
        return np.zeros(shape, dtype=dtype)

    def zeros_like(self, array: np.array) -> np.array:
        return np.zeros(array.shape)

    def map_fn(self, func, elements):
        # ??
        # Is this done like this?
        return np.array([func(e) for e in elements])

    def squeeze(self, tensor, axis=None):
        return np.squeeze(tensor, axis=axis)

    def cholesky(self, input: Tensor):
        return np.linalg.cholesky(input)

    def Categorical(self, probs: Tensor, name: str):
        # return tfp.distributions.Categorical(probs=probs, name=name)
        # ??
        pass

    def MultivariateNormalTriL(self, loc: Tensor, scale_tril: Tensor):
        # return tfp.distributions.MultivariateNormalTriL(loc=loc, scale_tril=scale_tril)
        # ??
        pass

    # ~~~~~~~~~~~~~~~~~
    # Special functions
    # ~~~~~~~~~~~~~~~~~

    # TODO: is a wrapper class better?
    @staticmethod
    def DefaultEuclideanOptimizer() -> None:
        r"""Default optimizer for the Euclidean parameters."""
        return None

    def value_and_gradients(
        self, cost_fn: Callable, parameters: List[Trainable]
    ) -> Tuple[np.array, List[np.array]]:
        r"""Computes the loss and gradients of the given cost function.

        Args:
            cost_fn (Callable with no args): The cost function.
            parameters (List[Trainable]): The parameters to optimize.

        Returns:
            tuple(Tensor, List[Tensor]): the loss and the gradients
        """
        # ??
        pass

    def hermite_renormalized(
        self, A: np.array, B: np.array, C: np.array, shape: Tuple[int]
    ) -> np.array:
        r"""Renormalized multidimensional Hermite polynomial given by the "exponential" Taylor
        series of :math:`exp(C + Bx + 1/2*Ax^2)` at zero, where the series has :math:`sqrt(n!)`
        at the denominator rather than :math:`n!`. It computes all the amplitudes within the
        tensor of given shape.

        Args:
            A: The A matrix.
            B: The B vector.
            C: The C scalar.
            shape: The shape of the final tensor.

        Returns:
            The renormalized Hermite polynomial of given shape.
        """
        _A, _B, _C = self.asnumpy(A), self.asnumpy(B), self.asnumpy(C)
        G = strategies.vanilla(tuple(shape), _A, _B, _C)

        # def grad(dLdGconj):
        #     dLdA, dLdB, dLdC = strategies.vanilla_vjp(G, _C, np.conj(dLdGconj))
        #     return self.conj(dLdA), self.conj(dLdB), self.conj(dLdC)

        # return G, grad
        return G

    def hermite_renormalized_binomial(
        self,
        A: np.array,
        B: np.array,
        C: np.array,
        shape: Tuple[int],
        max_l2: Optional[float],
        global_cutoff: Optional[int],
    ) -> np.array:
        r"""Renormalized multidimensional Hermite polynomial given by the "exponential" Taylor
        series of :math:`exp(C + Bx + 1/2*Ax^2)` at zero, where the series has :math:`sqrt(n!)`
        at the denominator rather than :math:`n!`. The computation fills a tensor of given shape
        up to a given L2 norm or global cutoff, whichever applies first. The max_l2 value, if
        not provided, is set to the default value of the AUTOCUTOFF_PROBABILITY setting.

        Args:
            A: The A matrix.
            B: The B vector.
            C: The C scalar.
            shape: The shape of the final tensor (local cutoffs).
            max_l2 (float): The maximum squared L2 norm of the tensor.
            global_cutoff (optional int): The global cutoff.

        Returns:
            The renormalized Hermite polynomial of given shape.
        """
        G, _ = strategies.binomial(
            tuple(shape),
            A,
            B,
            C,
            max_l2=max_l2 or settings.AUTOCUTOFF_PROBABILITY,
            global_cutoff=global_cutoff or sum(shape) - len(shape) + 1,
        )

        def grad(dLdGconj):
            dLdA, dLdB, dLdC = strategies.vanilla_vjp(G, C, np.conj(dLdGconj))
            return self.conj(dLdA), self.conj(dLdB), self.conj(dLdC)

        return G, grad

    def reorder_AB_bargmann(self, A: np.array, B: np.array) -> Tuple[np.array, np.array]:
        r"""In mrmustard.math.numba.compactFock~ dimensions of the Fock representation are ordered like [mode0,mode0,mode1,mode1,...]
        while in mrmustard.physics.bargmann the ordering is [mode0,mode1,...,mode0,mode1,...]. Here we reorder A and B.
        """
        ordering = np.arange(2 * A.shape[0] // 2).reshape(2, -1).T.flatten()
        A = self.gather(A, ordering, axis=1)
        A = self.gather(A, ordering)
        B = self.gather(B, ordering)
        return A, B

    def hermite_renormalized_diagonal(
        self, A: np.array, B: np.array, C: np.array, cutoffs: Tuple[int]
    ) -> np.array:
        r"""First, reorder A and B parameters of Bargmann representation to match conventions in mrmustard.math.numba.compactFock~
        Then, calculate the required renormalized multidimensional Hermite polynomial.
        """
        # A, B = self.reorder_AB_bargmann(A, B)
        # return self.hermite_renormalized_diagonal_reorderedAB(A, B, C, cutoffs=cutoffs)
        # ??
        pass

    def hermite_renormalized_diagonal_reorderedAB(
        self, A: np.array, B: np.array, C: np.array, cutoffs: Tuple[int]
    ) -> np.array:
        r"""Renormalized multidimensional Hermite polynomial given by the "exponential" Taylor
        series of :math:`exp(C + Bx - Ax^2)` at zero, where the series has :math:`sqrt(n!)` at the
        denominator rather than :math:`n!`. Note the minus sign in front of ``A``.

        Calculates the diagonal of the Fock representation (i.e. the PNR detection probabilities of all modes)
        by applying the recursion relation in a selective manner.

        Args:
            A: The A matrix.
            B: The B vector.
            C: The C scalar.
            cutoffs: upper boundary of photon numbers in each mode

        Returns:
            The renormalized Hermite polynomial.
        """
        # ??
        pass

    def hermite_renormalized_1leftoverMode(
        self, A: np.array, B: np.array, C: np.array, cutoffs: Tuple[int]
    ) -> np.array:
        r"""First, reorder A and B parameters of Bargmann representation to match conventions in mrmustard.math.numba.compactFock~
        Then, calculate the required renormalized multidimensional Hermite polynomial.
        """
        # ??
        pass

    def hermite_renormalized_1leftoverMode_reorderedAB(
        self, A: np.array, B: np.array, C: np.array, cutoffs: Tuple[int]
    ) -> np.array:
        r"""Renormalized multidimensional Hermite polynomial given by the "exponential" Taylor
        series of :math:`exp(C + Bx - Ax^2)` at zero, where the series has :math:`sqrt(n!)` at the
        denominator rather than :math:`n!`. Note the minus sign in front of ``A``.

        Calculates all possible Fock representations of mode 0,
        where all other modes are PNR detected.
        This is done by applying the recursion relation in a selective manner.

        Args:
            A: The A matrix.
            B: The B vector.
            C: The C scalar.
            cutoffs: upper boundary of photon numbers in each mode

        Returns:
            The renormalized Hermite polynomial.
        """
        # ??
        pass

    @staticmethod
    def eigvals(tensor: np.array) -> Tensor:
        """Returns the eigenvalues of a matrix."""
        return np.linalg.eigvals(tensor)

    @staticmethod
    def eigvalsh(tensor: np.array) -> Tensor:
        """Returns the eigenvalues of a Real Symmetric or Hermitian matrix."""
        return np.linalg.eigvalsh(tensor)

    @staticmethod
    def svd(tensor: np.array) -> Tensor:
        """Returns the Singular Value Decomposition of a matrix."""
        return np.linalg.svd(tensor)

    @staticmethod
    def xlogy(x: np.array, y: np.array) -> Tensor:
        """Returns 0 if ``x == 0,`` and ``x * log(y)`` otherwise, elementwise."""
        return scipy_xlogy(x, y)

    @staticmethod
    def eigh(tensor: np.array) -> Tensor:
        """Returns the eigenvalues and eigenvectors of a matrix."""
        return np.linalg.eigh(tensor)

    def sqrtm(self, tensor: np.array, rtol=1e-05, atol=1e-08) -> Tensor:
        """Returns the matrix square root of a square matrix, such that ``sqrt(A) @ sqrt(A) = A``."""

        # The sqrtm function has issues with matrices that are close to zero, hence we branch
        if np.allclose(tensor, 0, rtol=rtol, atol=atol):
            return self.zeros_like(tensor)
        return np.linalg.sqrtm(tensor)

    @staticmethod
    def boolean_mask(tensor: np.array, mask: np.array) -> Tensor:
        """Returns a tensor based on the truth value of the boolean mask."""
        # ??
        pass

    @staticmethod
    def custom_gradient(func, *args, **kwargs):
        """Decorator to define a function with a custom gradient."""
        # ??
        pass