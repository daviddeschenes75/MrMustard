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
""" This class corresponds to test child class for the MatVecData class.

Unlike some of its -abstract- parent test classes, this class is meant to be run with pytest.

Check parents test classe-s for more details on the rationale.

The fixtures must correspond to the concrete class being tested, here MatVecData.
"""

import numpy as np
import operator as op
import pytest

from copy import deepcopy

from mrmustard.lab.representations.data.matvec_data import MatVecData
from mrmustard.typing import Batch, Matrix, Scalar, Vector
from mrmustard.utils.misc_tools import general_factory
#from tests.test_lab.test_representations.test_data.test_data import TestData
from tests.test_lab.test_representations.test_data.tools_for_tests import (
    helper_mat_vec_unchanged_computed_coeffs_are_correct,
)

np.random.seed(42)
D = 10 #dimension, matrix will be DxD while means will be D
N = 3 #number of elements in the batch


##################   FIXTURES  ###################
@pytest.fixture
def D():
    """The dimension: matrices will be DxD and vectors will be D."""
    return 5

@pytest.fixture
def N():
    """The number of elements in the batch."""
    return 3

@pytest.fixture
def TYPE():
    r"""Type of the object under test."""
    return MatVecData

@pytest.fixture
def MAT(D,N) -> Batch[Matrix]:
    r"""Some batch of matrices for the object's parameterization."""
    mats = []
    for _ in range(N):
        m = np.random.normal(size=(D,D)) + 1j*np.random.normal(size=(D,D))
        m = m + m.T  # symmetrize A
        mats.append(m)
    return np.array(mats)


@pytest.fixture
def VEC(D,N) -> Batch[Vector]:
    r"""Some batch of vectors for the object's parameterization."""
    return np.array([np.random.normal(size=D) + 1j*np.random.normal(size=D) for _ in range(N)])


@pytest.fixture
def COEFFS(N) -> Batch[Scalar]:
    r"""Some batch of scalars for the object's parameterization."""
    return np.array([np.random.normal() + 1j*np.random.normal() for _ in range(N)])


@pytest.fixture
def PARAMS(MAT, VEC, COEFFS) -> dict:
    r"""Parameters for the class instance which is created."""
    params_dict = {"mat": MAT, "vec": VEC, "coeffs": COEFFS}
    return params_dict


@pytest.fixture()
def DATA(TYPE, PARAMS) -> MatVecData:
    r"""Instance of the class that must be tested."""
    return general_factory(TYPE, **PARAMS)


@pytest.fixture()
def OTHER(DATA) -> MatVecData:
    r"""Another instance of the class that must be tested."""
    return deepcopy(DATA)


class TestMatVecData(): #TestData
    ####################  Init  ######################
    def if_coeffs_not_given_they_are_equal_to_1(self, TYPE, PARAMS):
        params_without_coeffs = deepcopy(PARAMS)
        del params_without_coeffs["coeffs"]
        new_data = general_factory(TYPE, **params_without_coeffs)
        n = len(new_data.coeffs)
        assert np.allclose(new_data.coeffs, np.ones(n))

    ##################  Negative  ####################
    def test_negative_returns_new_object_with_neg_coeffs_and_unaltered_mat_and_vec(self, DATA):
        pre_op_data = deepcopy(DATA)
        neg_data = -DATA
        manual_neg_coeffs = [-c for c in pre_op_data.coeffs]
        assert manual_neg_coeffs == neg_data.coeffs
        assert np.allclose(neg_data.mat, pre_op_data.mat)
        assert np.allclose(neg_data.vec, pre_op_data.vec)

    # ##################  Equality  ####################
    # # NOTE: tested in parent

    # ###########  Addition / subtraction  #############
    # # TODO: more complex tests of the general concat case!
    # @pytest.mark.parametrize("operator", [op.add, op.sub])
    # def test_when_mat_and_vec_same_coefs_get_element_wise_operation(self, operator, DATA, OTHER):
    #     pre_op_data = deepcopy(DATA)
    #     processed_data = operator(DATA, OTHER)
    #     s0 = set(processed_data.coeffs)
    #     cs = []
    #     for c0 in DATA.coeffs:
    #         for c1 in OTHER.coeffs:
    #             cs.append(operator(c0, c1))
    #     s1 = set(cs)
    #     assert s0.symmetric_difference(s1) == set()
    #     # assert np.allclose(DATA.mat, pre_op_data.mat)
    #     # assert np.allclose(DATA.vec, pre_op_data.vec)

    #######  Scalar division / multiplication ########
    # @pytest.mark.parametrize("operator", [op.truediv, op.mul])
    # @pytest.mark.parametrize("x", [0.00001, 7, 100])
    # def test_scalar_mul_or_div_if_mat_vec_same_change_only_coeffs(self, DATA, operator, x):
    #     pre_op_data = deepcopy(DATA)
    #     divided_data = operator(DATA, x)
    #     helper_mat_vec_unchanged_computed_coeffs_are_correct(divided_data, pre_op_data, operator, x)

    # ###############  Multiplication  ##################
    # # #TODO : write more tests (other than the generic ones from the parents)

    # ###############  Outer product  ##################
    # # NOTE: not implented yet so no tests