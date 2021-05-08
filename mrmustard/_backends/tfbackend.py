import numpy as np
import tensorflow as tf
from numba import njit 
from functools import lru_cache
from scipy.stats import unitary_group, truncnorm
from scipy.linalg import expm
from numpy.typing import ArrayLike
from typing import List, Tuple, Callable, Sequence, Optional
from itertools import product

from mrmustard._gates import GateBackendInterface
from mrmustard._opt import OptimizerBackendInterface
from mrmustard._circuit import CircuitBackendInterface
from mrmustard._backends import MathBackendInterface

import mrmustard._backends.utils as utils

class TFCircuitBackend(CircuitBackendInterface):

    def _Qmat(self, cov:tf.Tensor, hbar=2):
        r"""Returns the :math:`Q` Husimi matrix of the Gaussian state.
        Args:
            cov (array): :math:`2N\times 2N xp-` Wigner covariance matrix
            hbar (float): the value of :math:`\hbar` in the commutation
                relation :math:`[\x,\p]=i\hbar`.
        Returns:
            array: the :math:`Q` matrix.
        """
        N = cov.shape[-1] // 2 # number of modes
        I = tf.eye(N, dtype=tf.complex128)

        x = tf.cast(cov[:N, :N] * 2 / hbar, tf.complex128)
        xp = tf.cast(cov[:N, N:] * 2 / hbar, tf.complex128)
        p = tf.cast(cov[N:, N:] * 2 / hbar, tf.complex128)
        aidaj = (x + p + 1j * (xp - tf.transpose(xp)) - 2 * I) / 4
        aiaj = (x - p + 1j * (xp + tf.transpose(xp))) / 4
        return tf.concat([tf.concat([aidaj, tf.math.conj(aiaj)], axis=1), tf.concat([aiaj, tf.math.conj(aidaj)], axis=1)], axis=0) + tf.eye(2 * N, dtype=tf.complex128)

    def _ABC(self, cov:tf.Tensor, means:tf.Tensor, mixed:bool=False, hbar:float=2.0) -> Tuple[tf.Tensor, tf.Tensor, tf.Tensor]:
        num_modes = means.shape[-1] // 2
        N = num_modes + num_modes*mixed 
        R = tf.cast(utils.rotmat(num_modes), tf.complex128)
        
        sigma = (1 / hbar) * R @ tf.cast(cov, tf.complex128) @ tf.math.conj(tf.transpose(R))
        I = tf.eye(sigma.shape[-1], dtype=tf.complex128)
        A = tf.matmul(tf.cast(utils.Xmat(num_modes), tf.complex128), (I - tf.linalg.inv(sigma + 0.5 * I)))

        alpha = tf.cast(tf.complex(means[:num_modes],means[num_modes:]), tf.complex128) / tf.cast(tf.math.sqrt(2.0 * hbar), tf.complex128)
        B = tf.concat([alpha, tf.math.conj(alpha)], axis=0)
        
        Q = self._Qmat(cov, hbar=hbar)
        C = tf.math.exp(-0.5 * tf.einsum('i,ij,j', B, tf.linalg.inv(Q), tf.math.conj(B))) / tf.math.sqrt(tf.linalg.det(Q))
        return A[:N, :N], B[:N], C**(0.5 + 0.5*mixed) # will be off by global phase
    
    @tf.custom_gradient
    def _recursive_state(self, A:tf.Tensor, B:tf.Tensor, C:tf.Tensor, cutoffs:Sequence[int]):
        mixed = len(B) == 2*len(cutoffs)
        cutoffs_minus_1 = tuple([c-1 for c in cutoffs] + [c-1 for c in cutoffs]*mixed)
        state = np.zeros(tuple(cutoffs)+tuple(cutoffs)*mixed, dtype=np.complex128)
        state[(0,)*(len(cutoffs) + len(cutoffs)*mixed)] = C
        state = utils.fill_amplitudes(state, A, B, cutoffs_minus_1)
        def grad(dy):
            dA = np.zeros(tuple(cutoffs)+tuple(cutoffs)*mixed + A.shape, dtype=np.complex128)
            dB = np.zeros(tuple(cutoffs)+tuple(cutoffs)*mixed + B.shape, dtype=np.complex128)
            dA, dB = utils.fill_gradients(dA, dB, state, A, B, cutoffs_minus_1)
            dC = state / C
            dLdA = np.sum(dy[...,None,None]*np.conj(dA), axis=tuple(range(dy.ndim)))
            dLdB = np.sum(dy[...,None]*np.conj(dB), axis=tuple(range(dy.ndim)))
            dLdC = np.sum(dy*np.conj(dC), axis=tuple(range(dy.ndim)))
            return dLdA, dLdB, dLdC
        return state, grad

    def _photon_number_mean(self, cov:tf.Tensor, means:tf.Tensor, hbar:int) -> tf.Tensor:
        N = len(means) // 2
        return (means[:N] ** 2
            + means[N:] ** 2
            + tf.linalg.diag_part(cov[:N, :N])
            + tf.linalg.diag_part(cov[N:, N:])
            - hbar
            ) / (2 * hbar)

    def _photon_number_covariance(self, cov, means, hbar)->tf.Tensor:
        pass
            

    

class TFOptimizerBackend(OptimizerBackendInterface):
    _backend_opt = tf.optimizers.Adam

    def _loss_and_gradients(self, symplectic_params:Sequence[tf.Tensor], euclidean_params:Sequence[tf.Tensor], loss_fn:Callable):
        with tf.GradientTape() as tape:
            loss = loss_fn()
        symp_grads, eucl_grads = tape.gradient(loss, [symplectic_params, euclidean_params])
        return loss.numpy(), symp_grads, eucl_grads

    def _update_symplectic(self, symplectic_grads:Sequence[tf.Tensor], symplectic_params:Sequence[tf.Tensor]) -> None:
        for S,dS_eucl in zip(symplectic_params, symplectic_grads):
            Jmat = utils.J(S.shape[-1] // 2)
            Z = np.matmul(np.transpose(S), dS_eucl)
            Y = 0.5 * (Z + np.matmul(np.matmul(Jmat, Z.T), Jmat))
            S.assign(S @ expm(-self._symplectic_lr * np.transpose(Y)) @ expm(-self._symplectic_lr * (Y - np.transpose(Y))), read_value=False)

    def _update_euclidean(self, euclidean_grads:Sequence[tf.Tensor], euclidean_params:Sequence[tf.Tensor]) -> None:
        self._opt.apply_gradients(zip(euclidean_grads, euclidean_params))

    def _all_symplectic_parameters(self, circuits:Sequence):
        symp = []
        for circ in circuits:
            for s in circ.symplectic_parameters:
                if s.ref() not in symp:
                    symp.append(s.ref())
        return [s.deref() for s in symp]

    def _all_euclidean_parameters(self, circuits:Sequence):
        eucl = []
        for circ in circuits:
            for e in circ.euclidean_parameters:
                if e.ref() not in eucl:
                    eucl.append(e.ref())
        return [e.deref() for e in eucl]




class TFGateBackend(GateBackendInterface):

    def _loss_X(self, transmissivity:Sequence[float], hbar=2) -> ArrayLike:
        r"""Returns the X matrix for the lossy bosonic channel.
        The channel is applied to a covariance matrix `\Sigma` as `X\Sigma X^T + Y`.
        """
        diag = np.hstack([np.sqrt(eta)*np.ones(2) for eta in transmissivity])
        return tf.convert_to_tensor(np.diag(diag), dtype=tf.float64)

    def _loss_Y(self, transmissivity:Sequence[float], hbar=2) -> ArrayLike:
        r"""Returns the Y (noise) matrix for the lossy bosonic channel.
        The channel is applied to a covariance matrix `\Sigma` as `X\Sigma X^T + Y`.
        """
        diag = np.hstack([(1-eta)*hbar/2*np.ones(2) for eta in transmissivity])
        return tf.convert_to_tensor(np.diag(diag), dtype=tf.float64)

    def _thermal_X(self, nbar: Sequence[float], hbar=2) -> Tuple[ArrayLike, ArrayLike]:
        raise NotImplementedError

    def _thermal_Y(self, nbar: Sequence[float], hbar=2) -> Tuple[ArrayLike, ArrayLike]:
        raise NotImplementedError

    def _beam_splitter_symplectic(self, theta:float, phi:float):
        r"""Beam-splitter.
        Args:
            theta (float): transmissivity parameter
            phi (float): phase parameter
        Returns:
            array: symplectic-orthogonal transformation matrix of an interferometer with angles theta and phi
        """

        ct = tf.cast(tf.math.cos(theta), tf.float64)
        st = tf.cast(tf.math.sin(theta), tf.float64)
        cp = tf.cast(tf.math.cos(phi), tf.float64)
        sp = tf.cast(tf.math.sin(phi), tf.float64)

        return tf.convert_to_tensor([[ct, -cp * st, 0, -sp * st],
                                    [cp * st, ct, -sp * st, 0],
                                    [0, sp * st, ct, -cp * st],
                                    [sp * st, 0, cp * st, ct]])
    
    def _rotation_symplectic(self, phi:float):
        f"""Rotation gate.
        Args:
            phi (float): rotation angle
        Returns:
            array: rotation matrix by angle theta
        """
        x = tf.cast(tf.math.cos(phi), tf.float64)
        y = tf.cast(tf.math.sin(phi), tf.float64)
        return tf.convert_to_tensor([[x, -y],[y, x]])

    def _squeezing_symplectic(self, r:float, phi:float):
        r"""Squeezing. In fock space this corresponds to \exp(\tfrac{1}{2}r e^{i \phi} (a^2 - a^{\dagger 2}) ).

        Args:
            r (float): squeezing magnitude
            phi (float): rotation parameter
        Returns:
            array: symplectic transformation matrix
        """
        # pylint: disable=assignment-from-no-return
        cp = tf.cast(tf.math.cos(phi), tf.float64)
        sp = tf.cast(tf.math.sin(phi), tf.float64)
        ch = tf.cast(tf.math.cosh(r), tf.float64)
        sh = tf.cast(tf.math.sinh(r), tf.float64)
        return tf.convert_to_tensor([[ch - cp*sh, -sp*sh], [-sp*sh, ch + cp*sh]])

    def _two_mode_squeezing_symplectic(self, r:float, phi:float):
        r"""Two-mode squeezing.
        Args:
            r (float): squeezing magnitude
            phi (float): rotation parameter
        Returns:
            array: symplectic transformation matrix
        """
        # pylint: disable=assignment-from-no-return
        cp = tf.cast(tf.math.cos(phi), tf.float64)
        sp = tf.cast(tf.math.sin(phi), tf.float64)
        ch = tf.cast(tf.math.cosh(r), tf.float64)
        sh = tf.cast(tf.math.sinh(r), tf.float64)

        return tf.convert_to_tensor([[ch, cp * sh, 0, sp * sh],
                                    [cp * sh, ch, sp * sh, 0],
                                    [0, sp * sh, ch, -cp * sh],
                                    [sp * sh, 0, -cp * sh, ch]])




class TFMathbackend(MathBackendInterface):

    def identity(self, size:int) -> tf.Tensor:
        return tf.eye(size, dtype=tf.float64)

    def zeros(self, size:int) -> tf.Tensor:
        return tf.zeros(size, dtype=tf.float64)

    def add(self, old:tf.Tensor, new:Optional[tf.Tensor], modes:List[int]) -> tf.Tensor:
        if new is None:
            return old
        N = old.shape[-1] // 2
        indices = modes + [m+N for m in modes]
        return tf.tensor_scatter_nd_add(old, list(product(*[indices]*len(new.shape))), tf.reshape(new,-1))

    def concat(self, lst:List[tf.Tensor]) -> tf.Tensor:
        return tf.concat(lst, axis=0)

    def sandwich(self, bread:Optional[tf.Tensor], filling:tf.Tensor, modes:List[int]) -> tf.Tensor:
        if bread is None:
            return filling
        N = filling.shape[-1] // 2
        indices = modes + [m+N for m in modes]
        rows = bread @ tf.gather(filling, indices)
        filling = tf.tensor_scatter_nd_update(filling, [[i] for i in indices], rows)
        columns = bread @ tf.gather(tf.transpose(filling), indices)
        return tf.transpose(tf.tensor_scatter_nd_update(tf.transpose(filling), [[i] for i in indices], columns))
        
    def matvec(self, mat:Optional[tf.Tensor], vec:tf.Tensor, modes:List[int]) -> tf.Tensor:
        if mat is None:
            return vec
        N = vec.shape[-1] // 2
        indices = modes + [m+N for m in modes]
        updates = tf.linalg.matvec(mat, tf.gather(vec, indices))
        return tf.tensor_scatter_nd_update(vec, [[i] for i in indices], updates)

    def modsquare(self, array:tf.Tensor) -> tf.Tensor:
        return tf.abs(array)**2

    def all_diagonals(self, rho: tf.Tensor) -> tf.Tensor:
        cutoffs = rho.shape[:rho.ndim//2]
        rho = tf.reshape(rho, (np.prod(cutoffs), np.prod(cutoffs)))
        diag = tf.linalg.diag_part(rho)
        return tf.reshape(diag, cutoffs)

    def block(self, blocks:List[List]):
        rows = [tf.concat(row, axis=1) for row in blocks]
        return tf.concat(rows, axis=0)

    def make_symplectic_parameter(self, init_value: Optional[tf.Tensor] = None,
                                        trainable:bool = True,
                                        num_modes:int = 1, 
                                        name:str = 'symplectic') -> tf.Tensor:
        if init_value is None:
            if num_modes == 1:
                W = np.exp(1j*np.random.uniform(size=(1,1)))
                V = np.exp(1j*np.random.uniform(size=(1,1)))
            else:
                W = unitary_group.rvs(num_modes)
                V = unitary_group.rvs(num_modes)
            r = np.random.uniform(size=num_modes)
            OW = self.unitary_to_orthogonal(W)
            OV = self.unitary_to_orthogonal(V)
            dd = tf.concat([tf.math.exp(-r), tf.math.exp(r)], 0)
            val = tf.einsum('ij,j,jk->ik', OW,  dd,  OV)
        else:
            val = init_value
        if trainable:
            return tf.Variable(val, dtype=tf.float64, name = name)
        else:
            return tf.constant(val, dtype=tf.float64, name = name)

    def unitary_to_orthogonal(self, U):
        f"""Unitary to orthogonal mapping.
        Args:
            U (array): unitary matrix in U(n)
        Returns:
            array: Orthogonal matrix in O(2n)
        """
        X = tf.math.real(U)
        Y = tf.math.imag(U)
        return self._block([[X,-Y],[Y,X]])

    def make_parameter(self, init_value: Optional[float] = None,
                              trainable: bool = True,
                              bounds: Tuple[Optional[float], Optional[float]] = (None,None),
                              shape:Optional[Tuple[int,...]] = None,
                              name: str = '') -> tf.Tensor:
        bounds = (bounds[0] or -np.inf, bounds[1] or np.inf)

        if not bounds == (None, None):
            constraint = lambda x: tf.clip_by_value(x, bounds[0], bounds[1])
        else:
            constraint = None

        if init_value is None:
            val = truncnorm.rvs(*bounds, size=shape)
        else:
            val = init_value

        if trainable:
            return tf.Variable(val, dtype=tf.float64, name = name, constraint=constraint)
        else:
            return tf.constant(val, dtype=tf.float64, name = name)

