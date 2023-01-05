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

# pylint: disable=redefined-outer-name

"""
This module contains functions for performing calculations on Fock states.
"""

from functools import lru_cache
import numpy as np


from mrmustard.physics.bargmann import (
    wigner_to_bargmann_psi,
    wigner_to_bargmann_rho,
    wigner_to_bargmann_Choi,
    wigner_to_bargmann_U,
)

from mrmustard.math.mmtensor import MMTensor
from mrmustard.math.caching import tensor_int_cache
from mrmustard.types import List, Tuple, Tensor, Scalar, Matrix, Sequence, Vector
from mrmustard import settings
from mrmustard.math import Math

math = Math()

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# ~~~~~~~~~~~~~~ static functions ~~~~~~~~~~~~~~
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


def fock_state(n: Sequence[int]) -> Tensor:
    r"""Returns a pure or mixed Fock state.

    Args:
        n: a list of photon numbers

    Returns:
        the Fock state up to cutoffs ``n+1``
    """
    psi = np.zeros(np.array(n) + np.ones_like(n), dtype=np.complex128)
    psi[tuple(np.atleast_1d(n))] = 1
    return psi


def autocutoffs(
    number_stdev: Matrix, number_means: Vector, max_cutoff: int = None, min_cutoff: int = None
) -> Tuple[int, ...]:
    r"""Returns the autocutoffs of a Wigner state.

    Args:
        number_stdev: the photon number standard deviation in each mode
            (i.e. the square root of the diagonal of the covariance matrix)
        number_means: the photon number means vector
        max_cutoff: the maximum cutoff

    Returns:
        Tuple[int, ...]: the suggested cutoffs
    """
    if max_cutoff is None:
        max_cutoff = settings.AUTOCUTOFF_MAX_CUTOFF
    if min_cutoff is None:
        min_cutoff = settings.AUTOCUTOFF_MIN_CUTOFF
    autocutoffs = settings.AUTOCUTOFF_MIN_CUTOFF + math.cast(
        number_means + number_stdev * settings.AUTOCUTOFF_STDEV_FACTOR, "int32"
    )
    return [int(n) for n in math.clip(autocutoffs, min_cutoff, max_cutoff)]


def wigner_to_fock_state(
    cov: Matrix,
    means: Vector,
    shape: Sequence[int],
    return_dm: bool = True,
) -> Tensor:
    r"""Returns the Fock representation of a Gaussian state.
    Use with caution: if the cov matrix is that of a mixed state,
    setting return_dm to False will produce nonsense.

    * If the state is pure it can return the state vector (ket) or the density matrix.
    * If the state is mixed it can return the density matrix.

    Args:
        cov: the Wigner covariance matrix
        means: the Wigner means vector
        shape: the shape of the tensor
        return_dm: whether to return the density matrix (otherwise it returns the ket)

    Returns:
        Tensor: the fock representation
    """
    if return_dm:
        A, B, C = wigner_to_bargmann_rho(cov, means)
        N = len(shape) // 2
        return math.transpose(
            math.hermite_renormalized(-A, B, C, shape=shape), list(range(N, 2 * N)) + list(range(N))
        )
    else:
        A, B, C = wigner_to_bargmann_psi(cov, means)
        return math.hermite_renormalized(-A, B, C, shape=shape)


def wigner_to_fock_transformation(
    X: Matrix,
    Y: Matrix,
    d: Vector,
    shape: Sequence[int],
    return_choi: bool = False,
) -> Tensor:
    r"""Returns the Fock representation of a Gaussian transformation.

    * If the transformation is unitary it returns the unitary transformation matrix.
    * If the transformation is not unitary it returns the Choi matrix.

    Args:
        X: the X matrix
        Y: the Y matrix
        d: the d vector
        shape: the shape of the tensor
        return_choi: whether to return the Choi matrix (otherwise it returns the unitary)
    """
    if return_choi:
        A, B, C = wigner_to_bargmann_Choi(X, Y, d)
    else:
        A, B, C = wigner_to_bargmann_U(X, d)
    return math.hermite_renormalized(-A, B, C, shape=shape)


def ket_to_dm(ket: Tensor) -> Tensor:
    r"""Maps a ket to a density matrix.

    Args:
        ket: the ket

    Returns:
        Tensor: the density matrix
    """
    return math.outer(ket, math.conj(ket))


def dm_to_ket(dm: Tensor) -> Tensor:
    r"""Maps a density matrix to a ket if the state is pure.

    If the state is pure :math:`\hat \rho= |\psi\rangle\langle \psi|` then the
    ket is the eigenvector of :math:`\rho` corresponding to the eigenvalue 1.

    Args:
        dm (Tensor): the density matrix

    Returns:
        Tensor: the ket

    Raises:
        ValueError: if ket for mixed states cannot be calculated
    """

    is_pure_dm = np.isclose(purity(dm), 1.0, atol=1e-6)
    if not is_pure_dm:
        raise ValueError("Cannot calculate ket for mixed states.")

    cutoffs = dm.shape[: len(dm.shape) // 2]
    d = int(np.prod(cutoffs))
    dm = math.reshape(dm, (d, d))

    eigvals, eigvecs = math.eigh(dm)
    # eigenvalues and related eigenvectors are sorted in non-decreasing order,
    # meaning the associated eigvec to largest eigval is stored last.
    ket = eigvecs[:, -1] * math.sqrt(eigvals[-1])
    ket = math.reshape(ket, cutoffs)

    return ket


def ket_to_probs(ket: Tensor) -> Tensor:
    r"""Maps a ket to probabilities.

    Args:
        ket: the ket

    Returns:
        Tensor: the probabilities vector
    """
    return math.abs(ket) ** 2


def dm_to_probs(dm: Tensor) -> Tensor:
    r"""Extracts the diagonals of a density matrix.

    Args:
        dm: the density matrix

    Returns:
        Tensor: the probabilities vector
    """
    return math.all_diagonals(dm, real=True)


def U_to_choi(U: Tensor) -> Tensor:
    r"""Converts a unitary transformation to a Choi tensor.

    Args:
        U: the unitary transformation

    Returns:
        Tensor: the Choi tensor. Index order is [output_left, input_left, input_right, output_right]
        in this way, the two groups of indices in the middle are those that contract with the input dm.
    """
    cutoffs = U.shape[: len(U.shape) // 2]
    N = len(cutoffs)
    return math.outer(U, math.conj(U))
    # return math.transpose(
    #     outer,
    #     list(range(0, N))
    #     + list(range(2 * N, 3 * N))
    #     + list(range(N, 2 * N))
    #     + list(range(3 * N, 4 * N)),
    # )  # NOTE: mode blocks 1 and 3 are at the end so we can tensordot dm with them


def fidelity(state_a, state_b, a_ket: bool, b_ket: bool) -> Scalar:
    r"""Computes the fidelity between two states in Fock representation."""
    if a_ket and b_ket:
        min_cutoffs = [slice(min(a, b)) for a, b in zip(state_a.shape, state_b.shape)]
        state_a = state_a[min_cutoffs]
        state_b = state_b[min_cutoffs]
        return math.abs(math.sum(math.conj(state_a) * state_b)) ** 2

    if a_ket:
        min_cutoffs = [
            slice(min(a, b))
            for a, b in zip(state_a.shape, state_b.shape[: len(state_b.shape) // 2])
        ]
        state_a = state_a[min_cutoffs]
        state_b = state_b[min_cutoffs * 2]
        a = math.reshape(state_a, -1)
        return math.real(
            math.sum(math.conj(a) * math.matvec(math.reshape(state_b, (len(a), len(a))), a))
        )

    if b_ket:
        min_cutoffs = [
            slice(min(a, b))
            for a, b in zip(state_a.shape[: len(state_a.shape) // 2], state_b.shape)
        ]
        state_a = state_a[min_cutoffs * 2]
        state_b = state_b[min_cutoffs]
        b = math.reshape(state_b, -1)
        return math.real(
            math.sum(math.conj(b) * math.matvec(math.reshape(state_a, (len(b), len(b))), b))
        )

    # mixed state
    # Richard Jozsa (1994) Fidelity for Mixed Quantum States, Journal of Modern Optics, 41:12, 2315-2323, DOI: 10.1080/09500349414552171
    return (
        math.trace(
            math.sqrtm(math.matmul(math.matmul(math.sqrtm(state_a), state_b), math.sqrtm(state_a)))
        )
        ** 2
    )


def number_means(tensor, is_dm: bool):
    r"""Returns the mean of the number operator in each mode."""
    probs = math.all_diagonals(tensor, real=True) if is_dm else math.abs(tensor) ** 2
    modes = list(range(len(probs.shape)))
    marginals = [math.sum(probs, axes=modes[:k] + modes[k + 1 :]) for k in range(len(modes))]
    return math.astensor(
        [
            math.sum(marginal * math.arange(len(marginal), dtype=marginal.dtype))
            for marginal in marginals
        ]
    )


def number_variances(tensor, is_dm: bool):
    r"""Returns the variance of the number operator in each mode."""
    probs = math.all_diagonals(tensor, real=True) if is_dm else math.abs(tensor) ** 2
    modes = list(range(len(probs.shape)))
    marginals = [math.sum(probs, axes=modes[:k] + modes[k + 1 :]) for k in range(len(modes))]
    return math.astensor(
        [
            (
                math.sum(marginal * math.arange(marginal.shape[0], dtype=marginal.dtype) ** 2)
                - math.sum(marginal * math.arange(marginal.shape[0], dtype=marginal.dtype)) ** 2
            )
            for marginal in marginals
        ]
    )


def purity(dm: Tensor) -> Scalar:
    r"""Returns the purity of a density matrix."""
    cutoffs = dm.shape[: len(dm.shape) // 2]
    d = int(np.prod(cutoffs))  # combined cutoffs in all modes
    dm = math.reshape(dm, (d, d))
    dm = dm / math.trace(dm)  # assumes all nonzero values are included in the density matrix
    return math.abs(math.sum(math.transpose(dm) * dm))  # tr(rho^2)


def apply_op_to_dm(op, dm, op_modes):
    r"""Applies an operator to a density matrix.
    It assumes that the density matrix is indexed as out_1, ..., out_n, in_1, ..., in_n.

    if op.ndim == 2 * len(op_modes), it is assumed that the operator acts like a unitary or a kraus operator,
    so it's indexed as out_1, ..., out_n, in_1, ..., in_n.
    It will contract its `in` indices once with the `out` indices of `dm` and once on the `in` indices of `dm`
    and replace them with its own `out` indices.

    if op.ndim == 4 * len(op_modes), it is assumed that the operator acts like a channel,
    so it's indexed as out_1, ..., out_n, in_1, ..., in_n, out_1_dual, ..., out_n_dual, in_1_dual, ..., in_n_dual.
    so it will contract the dm on the left and on the right with its `in` and `out_dual` indices
    and replace them with its own `out` and `in_dual` indices.

    Args:
        op (array): the operator to be applied, either a unitary, a kraus operator, or a channel
        dm (array): the density matrix to which the operator is applied
        op_modes (list): the modes the operator acts on (counting from 0)

    Returns:
        array: the resulting density matrix
    """
    dm = MMTensor(
        dm,
        axis_labels=[f"left_{i}" for i in range(dm.ndim // 2)]
        + [f"right_{i}" for i in range(dm.ndim // 2)],
    )

    if op.ndim == 2 * len(op_modes):
        op = MMTensor(
            op,
            axis_labels=[f"left_{m}_op" for m in op_modes] + [f"left_{m}" for m in op_modes],
        )
        op_conj = MMTensor(
            math.conj(op.tensor),
            axis_labels=[f"right_{m}_op" for m in op_modes] + [f"right_{m}" for m in op_modes],
        )
        return (op @ dm @ op_conj).tensor

    elif op.ndim == 4 * len(op_modes):
        op = MMTensor(
            op,
            axis_labels=[f"left_{m}_op" for m in op_modes]
            + [f"left_{m}" for m in op_modes]
            + [f"right_{m}" for m in op_modes]
            + [f"right_{m}_op" for m in op_modes],
        )
        return (op @ dm).tensor

    else:
        raise ValueError(
            "Operator should either have 2 or 4 times as many indices as the number of modes it acts on."
        )


def apply_op_to_ket(op, ket, op_indices):
    r"""Applies an operator to a ket.
    It assumes that the ket is indexed as out_1, ..., out_n.

    if op.ndim == 2 * len(op_indices), it is assumed that the operator acts like a unitary or a kraus operator,
    so it's indexed as out_1, ..., out_n, in_1, ..., in_n.
    It will contract its `in` indices once with the `out` indices of `ket`.

    if op.ndim == 4 * len(op_indices), it is assumed that the operator acts like a channel,
    so it's indexed as out_1, ..., out_n, in_1, ..., in_n, out_1_dual, ..., out_n_dual, in_1_dual, ..., in_n_dual.
    so it will contract a copy of the ket on the left with its `in` indices and a copy of the ket on the right
    with its `out_dual` indices and replace them with its own `out` and `in_dual` indices.

    Args:
        op (array): the operator to be applied, either a unitary, a kraus operator, or a channel
        ket (array): the ket to which the operator is applied
        op_modes (list): the modes the operator acts on (counting from 0)

    Returns:
        array: the resulting ket
    """
    ket = MMTensor(ket, axis_labels=[f"left_{i}" for i in range(ket.ndim)])

    if op.ndim == 2 * len(op_indices):
        op = MMTensor(
            op,
            axis_labels=[f"left_{m}_op" for m in op_indices] + [f"left_{m}" for m in op_indices],
        )
        return (op @ ket).tensor

    elif op.ndim == 4 * len(op_indices):
        ket_dual = MMTensor(
            math.conj(ket.tensor), axis_labels=[f"right_{i}" for i in range(ket.ndim)]
        )
        op = MMTensor(
            op,
            axis_labels=[f"left_{m}_op" for m in op_indices]
            + [f"left_{m}" for m in op_indices]
            + [f"right_{m}" for m in op_indices]
            + [f"right_{m}_op" for m in op_indices],
        )
        return (op @ ket @ ket_dual).tensor

    else:
        raise ValueError(
            "Operator should either have 2 or 4 times as many indices as the number of modes it acts on."
        )


def contract_states(
    stateA, stateB, a_is_mixed: bool, b_is_mixed: bool, modes: List[int], normalize: bool
):
    r"""Contracts two states in the specified modes, it assumes that the modes spanned by ``B`` are a subset of the modes spanned by ``A``.

    Args:
        stateA: the first state
        stateB: the second state (assumed to be on a subset of the modes of stateA)
        a_is_mixed: whether the first state is mixed or not.
        b_is_mixed: whether the second state is mixed or not.
        modes: the modes on which to contract the states.
        normalize: whether to normalize the result

    Returns:
        Tensor: the contracted state tensor (subsystem of ``A``). Either ket or dm.
    """
    indices = list(range(len(modes)))
    if not a_is_mixed and not b_is_mixed:
        out = math.tensordot(math.conj(stateB), stateA, axes=(indices, modes))
        if normalize:
            out = out / math.norm(out)
        return out

    if a_is_mixed and not b_is_mixed:
        Ab = math.tensordot(
            stateA, stateB, axes=([m + len(stateA.shape) // 2 for m in modes], indices)
        )
        out = math.tensordot(math.conj(stateB), Ab, axes=(indices, modes))
    elif not a_is_mixed and b_is_mixed:
        Ba = math.tensordot(stateB, stateA, axes=(indices, modes))  # now B indices are all first
        out = math.tensordot(math.conj(stateA), Ba, axes=(modes, indices))
    elif a_is_mixed and b_is_mixed:
        out = math.tensordot(
            stateA,
            math.conj(stateB),
            axes=(
                list(modes) + [m + len(stateA.shape) // 2 for m in modes],
                list(indices) + [i + len(stateB.shape) // 2 for i in indices],
            ),
        )
    if normalize:
        out = out / math.sum(math.all_diagonals(out, real=False))
    return out


def normalize(fock: Tensor, is_dm: bool):
    r"""Returns the normalized ket state.

    Args:
        fock (Tensor): the state to be normalized
        is_dm (optioanl bool): whether the input tensor is a density matrix

    Returns:
        Tensor: the normalized state
    """
    if is_dm:
        return fock / math.sum(math.all_diagonals(fock, real=False))

    return fock / math.sum(math.norm(fock))


def norm(state: Tensor, is_dm: bool):
    r"""
    Returns the norm of a ket or the trace of the density matrix.
    Note that the "norm" is intended as the float number that is used to normalize the state,
    and depends on the representation. Hence different numbers for different representations
    of the same state (:math:`|amp|` for ``ket`` and :math:`|amp|^2` for ``dm``).
    """
    if is_dm:
        return math.sum(math.all_diagonals(state, real=True))

    return math.abs(math.norm(state))


def is_mixed_dm(dm):
    r"""Evaluates if a density matrix represents a mixed state."""
    cutoffs = dm.shape[: len(dm.shape) // 2]
    square = math.reshape(dm, (int(np.prod(cutoffs)), -1))
    return not np.isclose(math.sum(square * math.transpose(square)), 1.0)


def trace(dm, keep: List[int]):
    r"""Computes the partial trace of a density matrix.
    The indices of the density matrix are in the order (out0, ..., outN-1, in0, ..., inN-1).
    The indices to keep are a subset of the first N indices (they are doubled automatically
    and applied to the second N indices as the trace is computed).

    Args:
        dm: the density matrix
        keep: the modes to keep (0-based)
    """
    dm = MMTensor(
        dm,
        axis_labels=[
            f"out_{i}" if i in keep else f"contract_{i}" for i in range(len(dm.shape) // 2)
        ]
        + [f"in_{i}" if i in keep else f"contract_{i}" for i in range(len(dm.shape) // 2)],
    )
    return dm.contract().tensor


@tensor_int_cache
def oscillator_eigenstate(q: Vector, cutoff: int) -> Tensor:
    r"""Harmonic oscillator eigenstate wavefunction `\psi_n(q) = <n|q>`.

    Args:
        q (Vector): a vector containing the q points at which the function is evaluated (units of \sqrt{\hbar})
        cutoff (int): maximum number of photons
        hbar (optional): value of `\hbar`, defaults to Mr Mustard's internal value

    Returns:
        Tensor: a tensor of size ``len(q)*cutoff``. Each entry with index ``[i, j]`` represents the eigenstate evaluated
            with number of photons ``i`` evaluated at position ``q[j]``, i.e., `\psi_i(q_j)`.

    .. details::

        .. admonition:: Definition
            :class: defn

        The q-quadrature eigenstates are defined as

        .. math::

            \psi_n(x) = 1/sqrt[2^n n!](\frac{\omega}{\pi \hbar})^{1/4}
                \exp{-\frac{\omega}{2\hbar} x^2} H_n(\sqrt{\frac{\omega}{\pi}} x)

        where :math:`H_n(x)` is the (physicists) `n`-th Hermite polynomial.
    """
    omega_over_hbar = math.cast(1 / settings.HBAR, "float64")
    x_tensor = math.sqrt(omega_over_hbar) * math.cast(q, "float64")  # unit-less vector

    # prefactor term (\Omega/\hbar \pi)**(1/4) * 1 / sqrt(2**n)
    prefactor = (omega_over_hbar / np.pi) ** (1 / 4) * math.sqrt(2 ** (-math.arange(0, cutoff)))

    # Renormalized physicist hermite polys: Hn / sqrt(n!)
    R = math.astensor(2 * np.ones([1, 1]))  # to get the physicist polys

    def f_hermite_polys(xi):
        return math.hermite_renormalized(R, 2 * math.astensor([xi]), 1, cutoff)

    hermite_polys = math.cast(math.map_fn(f_hermite_polys, x_tensor), "float64")

    # wavefunction
    psi = math.exp(-(x_tensor**2 / 2)) * math.transpose(prefactor * hermite_polys)
    return psi


@lru_cache
def estimate_dx(cutoff, period_resolution=20):
    r"""Estimates a suitable quadrature discretization interval `dx`. Uses the fact
    that Fock state `n` oscillates with angular frequency :math:`\sqrt{2(n + 1)}`,
    which follows from the relation

    .. math::

            \psi^{[n]}'(q) = q - sqrt(2*(n + 1))*\psi^{[n+1]}(q)

    by setting q = 0, and approximating the oscillation amplitude by `\psi^{[n+1]}(0)

    Ref: https://en.wikipedia.org/wiki/Hermite_polynomials#Hermite_functions

    Args
        cutoff (int): Fock cutoff
        period_resolution (int): Number of points used to sample one Fock
            wavefunction oscillation. Larger values yields better approximations
            and thus smaller `dx`.

    Returns
        (float): discretization value of quadrature
    """
    fock_cutoff_frequency = np.sqrt(2 * (cutoff + 1))
    fock_cutoff_period = 2 * np.pi / fock_cutoff_frequency
    dx_estimate = fock_cutoff_period / period_resolution
    return dx_estimate


@lru_cache
def estimate_xmax(cutoff, minimum=5):
    r"""Estimates a suitable quadrature axis length

    Args
        cutoff (int): Fock cutoff
        minimum (float): Minimum value of the returned xmax

    Returns
        (float): maximum quadrature value
    """
    if cutoff == 0:
        xmax_estimate = 3
    else:
        # maximum q for a classical particle with energy n=cutoff
        classical_endpoint = np.sqrt(2 * cutoff)
        # approximate probability of finding particle outside classical region
        excess_probability = 1 / (7.464 * cutoff ** (1 / 3))
        # Emperical factor that yields reasonable results
        A = 5
        xmax_estimate = classical_endpoint * (1 + A * excess_probability)
    return max(minimum, xmax_estimate)


@lru_cache
def estimate_quadrature_axis(cutoff, minimum=5, period_resolution=20):
    """Generates a suitable quadrature axis.

    Args
        cutoff (int): Fock cutoff
        minimum (float): Minimum value of the returned xmax
        period_resolution (int): Number of points used to sample one Fock
            wavefunction oscillation. Larger values yields better approximations
            and thus smaller dx.

    Returns
        (array): quadrature axis
    """
    xmax = estimate_xmax(cutoff, minimum=minimum)
    dx = estimate_dx(cutoff, period_resolution=period_resolution)
    xaxis = np.arange(-xmax, xmax, dx)
    xaxis = np.append(xaxis, xaxis[-1] + dx)
    xaxis = xaxis - np.mean(xaxis)  # center around 0
    return xaxis


def quadrature_distribution(
    state: Tensor, quadrature_angle: float = 0.0, x: Vector = None, hbar: float = settings.HBAR
):
    r"""Given the ket or density matrix of a single-mode state, it generates the probability
    density distribution :math:`\tr [ \rho |x_\phi><x_\phi| ]`  where `\rho` is the
    density matrix of the state and |x_\phi> the quadrature eigenvector with angle `\phi`
    equal to ``quadrature_angle``.

    Args:
        state (Tensor): single mode state ket or density matrix
        quadrature_angle (float): angle of the quadrature basis vector
        x (Vector): points at which the quadrature distribution is evaluated

    Returns:
        tuple(Vector, Vector): coordinates at which the pdf is evaluated and the probability distribution
    """
    dims = len(state.shape)
    if dims > 2:
        raise ValueError(
            "Input state has dimension {state.shape}. Make sure is either a single-mode ket or dm."
        )

    is_dm = dims == 2
    cutoff = state.shape[0]

    if not np.isclose(quadrature_angle, 0.0):
        # rotate mode to the homodyne basis
        theta = -math.arange(cutoff) * quadrature_angle
        Ur = math.diag(math.make_complex(math.cos(theta), math.sin(theta)))
        state = (
            math.einsum("ij,jk,kl->il", Ur, state, math.dagger(Ur))
            if is_dm
            else math.matvec(Ur, state)
        )

    if x is None:
        x = np.sqrt(hbar) * math.new_constant(estimate_quadrature_axis(cutoff), "q_tensor")

    psi_x = math.cast(oscillator_eigenstate(x, cutoff), "complex128")
    pdf = (
        math.einsum("nm,nj,mj->j", state, psi_x, psi_x)
        if is_dm
        else math.abs(math.einsum("n,nj->j", state, psi_x)) ** 2
    )

    return x, math.cast(pdf, "float64")


def sample_homodyne(
    state: Tensor, quadrature_angle: float = 0.0, hbar: float = settings.HBAR
) -> Tuple[float, float]:
    r"""Given a single-mode state, it generates the pdf of :math:`\tr [ \rho |x_\phi><x_\phi| ]`
    where `\rho` is the reduced density matrix of the state.

    Args:
        state (Tensor): ket or density matrix of the state being measured
        quadrature_angle (float): angle of the quadrature distribution
        hbar: value of hbar

    Returns:
        tuple(float, float): outcome and probability of the outcome
    """
    dims = len(state.shape)
    if dims > 2:
        raise ValueError(
            "Input state has dimension {state.shape}. Make sure is either a single-mode ket or dm."
        )

    x, pdf = quadrature_distribution(state, quadrature_angle, hbar=hbar)
    probs = pdf * (x[1] - x[0])

    # draw a sample from the distribution
    pdf = math.Categorical(probs=probs, name="homodyne_dist")
    sample_idx = pdf.sample()
    homodyne_sample = math.gather(x, sample_idx)
    probability_sample = math.gather(probs, sample_idx)

    return homodyne_sample, probability_sample
