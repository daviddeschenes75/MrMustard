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

"""This module contains the interface for Representations."""

from __future__ import annotations

from abc import abstractproperty


class Representation:

    @abstractproperty
    def dimension(self):
        r"""Returns the dimension of the representation."""

    def __getattr__(self, name):
        r"""Returns the attribute of the data object and wraps it in a function if it is callable.
        In particular this will work with any method the State or Transformation class calls on the
        Representation object, which will be passed through to the data object if not implemented
        on the Representation object.
        """
        attr = getattr(self.data, name)
        if callable(attr):

            def wrapper(*args, **kwargs):
                return attr(*args, **kwargs)

            return wrapper
        return attr

    def id_position(self, id):
        r"""
        It returns the position of the id in the list of not-None ids for this Tensor.
        Warning: use only when len(ids) matches the number of wires of the object.
        """
        not_none = [i for i in self.wires.ids if i is not None]
        return not_none.index(id)





class FockArray(Representation):
    def __init__(self, fock_array):
        self.data = fock_array