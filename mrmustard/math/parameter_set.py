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

"""This module contains the classes to describe sets of parameters."""

from typing import Sequence, Union
import numpy as np

from .parameters import Constant, Variable
from mrmustard.math import Math

math = Math()

__all__ = [
    "ParameterSet",
]


class ParameterSet:
    r"""
    A set of parameters.
    """

    def __init__(self):
        self._names: list[str] = []
        self._constants: dict[str, Constant] = {}
        self._variables: dict[str, Variable] = {}

    @property
    def constants(self) -> dict[str, Constant]:
        r"""
        The constant parameters in this parameter set.
        """
        return self._constants

    @property
    def variables(self) -> dict[str, Variable]:
        r"""
        The variable parameters in this parameter set.
        """
        return self._variables

    @property
    def names(self) -> Sequence[str]:
        r"""
        The names of all the parameters in this parameter set, in the order in which they
        were added.
        """
        return self._names

    def add_parameter(self, parameter: Union[Constant, Variable]) -> None:
        r"""
        Adds a parameter to this parameter set.

        Args:
            parameter: A constant or variable parameter.

        Raises:
            ValueError: If this parameter set already contains a parameter with the same
                name as that of the given parameter.
        """
        name = parameter.name

        if name in self.names:
            msg = f"A parameter with name ``{name}`` is already part of this parameter set."
            raise ValueError(msg)
        self._names.append(name)

        # updates dictionary and dynamically creates an attribute
        if isinstance(parameter, Constant):
            self.constants[name] = parameter
            self.__dict__[name] = self.constants[name]
        elif isinstance(parameter, Variable):
            self.variables[parameter.name] = parameter
            self.__dict__[name] = self.variables[name]

    def tagged_variables(self, tag: str) -> dict[str, Variable]:
        r"""
        Tags the variables in this parameter set by prepending the given  ``tag`` to their names.
        """
        ret = {}
        for k, v in self.variables.items():
            ret[f"{tag}/{k}"] = v
        return ret

    def to_string(self, decimals: int) -> str:
        r"""
        Returns a string representation of the parameter values, separated by commas and rounded
        to the specified number of decimals.

        Args:
            decimals (int): number of decimals to round to

        Returns:
            str: string representation of the parameter values
        """
        strings = []
        for name in self.names:
            param = self.constants.get(name) or self.variables.get(name)
            value = math.asnumpy(param.value)
            if value.ndim == 0:  # don't show arrays
                sign = "-" if value < 0 else ""
                value = np.abs(np.round(value, decimals))
                int_part = int(value)
                decimal_part = np.round(value - int_part, decimals)
                string = sign + str(int_part) + f"{decimal_part:.{decimals}g}".lstrip("0")
            else:
                string = f"{name}"
            strings.append(string)
        return ", ".join(strings)
