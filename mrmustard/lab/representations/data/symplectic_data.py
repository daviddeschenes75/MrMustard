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
import numpy as np
#from numba import njit
from typing import Union
from mrmustard.lab.representations.data.matvec_data import MatVecData
from mrmustard.typing import Scalar

class SymplecticData(MatVecData):

    def __init__(self, mat, vec, coeffs) -> None:
        super().__init__(mat=mat, vec=vec, coeffs=coeffs)


    @property
    def mean(self) -> np.array:
        return self.vec


    def __truediv__(self, other:Union[Scalar, SymplecticData]) -> SymplecticData: # TODO : implement
        r"""
        Divides a SymplecticData object by either another Data object of the same class or 
        by a scalar

        Args:
            other (Union[Scalar, SymplecticData]): the object or scalar to be divided by

        Returns:
            A SymplecticData object resulting form the division
        """
        raise NotImplementedError()



    #@njit(parallel=True)
    def __mul__(self, other:Union[Scalar, SymplecticData]) -> SymplecticData:
        r"""
        Multiplies two SymplecticData objects or a SymplecticData and a scalar

        Args:
            other (Union[Scalar, SymplecticData]): the object or scalar to multiply by

        Returns:
            An object of the common child Data class resulting form multiplying two objects
        """

        if isinstance(other, Scalar): # WARNING: this means we have to be very logical with our typing!
            c = super().scalar_mul(c=other)
            return self.__class__(mat=self.mat, vec=self.vec, coeffs=self.coeffs)
        
        else: # TODO : use MM's math module where possible
            raise NotImplementedError() # TODO : implement (is the below correct?)
            # try:
            #     return self.__class__(mat=np.matmul(self.mat, other.mat), 
            #                         mean=np.multiply(self.mean, other.mean),
            #                         coeff=np.multiply(self.coeff, other.coeff))
            
            # except AttributeError as e:
            # raise TypeError(f"Cannot tensor {self.__class__} and {other.__class__}.") from e
