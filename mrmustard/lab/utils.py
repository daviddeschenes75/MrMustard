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

# pylint: disable=no-member

"""
This module contains the utility functions used by the classes in ``mrmustard.lab``.
"""
from typing import Callable, Optional, Tuple
from mrmustard.math.parameters import update_euclidean
from mrmustard import settings
from mrmustard.math import Math
from mrmustard.math.parameters import Constant, Variable

math = Math()


def make_parameter(
    is_trainable: bool,
    value: any,
    name: str,
    bounds: Tuple[Optional[float], Optional[float]],
    update_fn: Callable = update_euclidean,
):
    r"""
    Returns a constant or variable parameter with given name, value, bounds, and update function.

    Args:
        is_trainable: Whether to return a variable (``True``) or constant (``False``) parameter.
        value: The value of the returned parameter.
        name: The name of the returned parameter.
        bounds: The bounds of the returned parameter (ignored if ``is_trainable`` is ``False``).
        update_fn: The update_fn of the returned parameter (ignored if ``is_trainable`` is ``False``).
    """
    if isinstance(value, (Constant, Variable)):
        return value
    if not is_trainable:
        return Constant(value=value, name=name)
    return Variable(value=value, name=name, bounds=bounds, update_fn=update_fn)


def trainable_property(func):
    r"""
    Decorator that makes a property lazily evaluated or not depending on the settings.BACKEND flag.
    If settings.BACKEND is tensorflow, we need the property to be re-evaluated every time it is accessed
    for the computation of the gradient. If settings.BACKEND is numpy, we want to avoid re-computing
    the property every time it is accessed, so we make it lazy.

    Arguments:
        func (callable): The function to be made into a trainable property.

    Returns:
        callable: The decorated function.
    """
    attr_name = "_" + func.__name__

    if settings.BACKEND == "numpy":
        import functools  # pylint: disable=import-outside-toplevel

        @functools.wraps(func)
        @property
        def _trainable_property(self):
            r"""
            Property getter that lazily evaluates its value. Computes the value only on the first
            call and caches the result in a private attribute for future access.

            Returns:
                any: The value of the lazy property.
            """
            if not hasattr(self, attr_name):
                setattr(self, attr_name, func(self))
            return getattr(self, attr_name)

    else:
        _trainable_property = property(func)

    return _trainable_property
