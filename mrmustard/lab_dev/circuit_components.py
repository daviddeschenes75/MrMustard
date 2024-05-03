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

"""
A base class for the components of quantum circuits.

``CircuitComponent``\s bring together two types of information:

* That contained in the ``Wires`` object, which identifies the modes spanned by a component.
* That contained in the ``Representation``, which provides a mathematical description of a
  component.
Together, wires and representation uniquely define individual components, as well as their
interaction with other components.

This example shows how to define components with the same wires and representations as popular
states and gates.

.. code-block ::

    >>> from mrmustard.lab_dev import *
    >>> from mrmustard.physics.triples import vacuum_state_Abc, beamsplitter_gate_Abc, attenuator_Abc
    >>> from mrmustard.physics.fock import fock_state
    >>> from mrmustard.physics.representations import Bargmann, Fock
    >>> import numpy as np

    >>> # the vacuum state on mode `0`
    >>> vac_rep = Bargmann(*vacuum_state_Abc(n_modes=1))
    >>> vac_modes = (0,)
    >>> vac = CircuitComponent("my_vac", vac_rep, modes_out_ket=vac_modes)

    >>> # the number state on mode `3`
    >>> num_rep = Fock(fock_state(n=1))
    >>> num_modes = (3,)
    >>> number = CircuitComponent("my_num", num_rep, modes_out_ket=num_modes)

    >>> # the 50/50 beam splitter on modes `(8, 19)`
    >>> bs_rep = Bargmann(*beamsplitter_gate_Abc(theta=np.pi/4))
    >>> bs_modes = (8, 19)
    >>> bs = CircuitComponent("my_bs", bs_rep, modes_out_ket=bs_modes, modes_in_ket=bs_modes)

    >>> # the attenuator on mode `16`
    >>> att_rep = Bargmann(*attenuator_Abc(0.9))
    >>> att_modes = (16,)
    >>> att = CircuitComponent("my_att", att_rep, att_modes, att_modes, att_modes, att_modes)

By accessing the information about wires and representations, ``CircuitComponent``\s can be easily
concatenated via the ``@`` and ``>>`` operators. 

.. code-block ::

    >>> from mrmustard.lab_dev import *
    >>> from mrmustard.physics.triples import attenuator_Abc
    >>> from mrmustard.physics.fock import fock_state
    >>> from mrmustard.physics.representations import Bargmann, Fock
    >>> import numpy as np

    >>> # the number state on mode `3` with `n=1` photons
    >>> num_rep = Fock(fock_state(n=1))
    >>> num_modes = (3,)
    >>> number = CircuitComponent("my_num", num_rep, modes_out_ket=num_modes)

    >>> # the attenuator on mode `3`
    >>> att_rep = Bargmann(*attenuator_Abc(0.5))
    >>> att_modes = (3,)
    >>> att = CircuitComponent("my_att", att_rep, att_modes, att_modes, att_modes, att_modes)

    >>> # `@` is a "lower-level" operator that simply contracts the two given components,
    >>> # without adding adjoints. in general, it returns "unphysical" components, like the
    >>> # following one
    >>> res1 = number @ att
    >>> assert res1.wires == Wires(modes_out_bra={3,}, modes_in_bra={3,}, modes_out_ket={3,})

    >>> # `>>` is "higher-level" and is designed to be more user-friendly. by adding the missing
    >>> # adjoints, it is guaranteed map any two physical components into another component that
    >>> # also physical.
    >>> res2 = number >> att
    >>> assert res2.wires == Wires(modes_out_bra={3,}, modes_out_ket={3,})
    >>> assert res2 == number @ number.adjoint @ att

By accessing the information about wires and representations, ``CircuitComponent``\s can be easily
concatenated via the ``@`` and ``>>`` operators. 
"""

# pylint: disable=super-init-not-called, protected-access

from __future__ import annotations

from typing import Iterable, Optional, Sequence, Union

import numpy as np
from ..utils.typing import Scalar
from ..physics.converters import to_fock
from ..physics.representations import Representation, Bargmann, Fock
from ..math.parameter_set import ParameterSet
from ..math.parameters import Constant, Variable
from .wires import Wires

__all__ = ["CircuitComponent", "AdjointView", "DualView"]


class CircuitComponent:
    r"""
    A base class for the components (states, transformations, and measurements, or potentially
    unphysical "wired" objects) that can be placed in Mr Mustard's quantum circuits.

    Args:
        name: The name of this component.
        representation: A representation for this circuit component.
        modes_out_bra: The output modes on the bra side of this component.
        modes_in_bra: The input modes on the bra side of this component.
        modes_out_ket: The output modes on the ket side of this component.
        modes_in_ket: The input modes on the ket side of this component.
    """

    def __init__(
        self,
        name: Optional[str] = None,
        representation: Optional[Bargmann | Fock] = None,
        modes_out_bra: Optional[Sequence[int]] = None,
        modes_in_bra: Optional[Sequence[int]] = None,
        modes_out_ket: Optional[Sequence[int]] = None,
        modes_in_ket: Optional[Sequence[int]] = None,
    ) -> None:
        modes_out_bra = modes_out_bra or ()
        modes_in_bra = modes_in_bra or ()
        modes_out_ket = modes_out_ket or ()
        modes_in_ket = modes_in_ket or ()

        self._wires = Wires(
            set(modes_out_bra), set(modes_in_bra), set(modes_out_ket), set(modes_in_ket)
        )
        self._name = name or "CC" + "".join(str(m) for m in sorted(self.wires.modes))
        self._parameter_set = ParameterSet()
        self._representation = representation

        # handle out-of-order modes
        ob = tuple(sorted(modes_out_bra))
        ib = tuple(sorted(modes_in_bra))
        ok = tuple(sorted(modes_out_ket))
        ik = tuple(sorted(modes_in_ket))
        if ob != modes_out_bra or ib != modes_in_bra or ok != modes_out_ket or ik != modes_in_ket:
            offsets = [len(ob), len(ob) + len(ib), len(ob) + len(ib) + len(ok)]
            perm = (
                tuple(np.argsort(modes_out_bra))
                + tuple(np.argsort(modes_in_bra) + offsets[0])
                + tuple(np.argsort(modes_out_ket) + offsets[1])
                + tuple(np.argsort(modes_in_ket) + offsets[2])
            )
            if self._representation:
                self._representation = self._representation.reorder(tuple(perm))

    @classmethod
    def _from_attributes(
        cls, name: str, representation: Representation, wires: Wires
    ) -> CircuitComponent:
        r"""
        Initializes a circuit component from its attributes (a name, a ``Wires``,
        and a ``Representation``).

        If the Method Resolution Order (MRO) of ``cls`` contains one between ``Ket``, ``DM``,
        ``Unitary``, and ``Channel``, then the returned component is of that type. Otherwise,
        it is of type ``CircuitComponent``.

        This function needs to be used with caution, as it does not check that the attributes
        provided are consistent with the type of the returned component. If used improperly it
        may initialize, e.g., ``Ket``s with both input and output wires or ``Unitary``s with
        wires on the bra side.

        Args:
            name: The name of this component.
            representation: A representation for this circuit component.
            wires: The wires of this component.

        Returns:
            A circuit component of type ``cls`` with the given attributes.
        """
        types = {"Ket", "DM", "Unitary", "Channel"}
        for tp in cls.mro():
            if tp.__name__ in types:
                ret = tp()
                break
        else:
            ret = CircuitComponent()

        ret._name = name
        ret._representation = representation
        ret._wires = wires

        return ret

    def _add_parameter(self, parameter: Union[Constant, Variable]):
        r"""
        Adds a parameter to this circuit component.

        Args:
            parameter: The parameter to add.

        Raises:
            ValueError: If the length of the given parameter is incompatible with the number
                of modes.
        """
        if parameter.value.shape != ():
            if len(parameter.value) != 1 and len(parameter.value) != len(self.modes):
                msg = f"Length of ``{parameter.name}`` must be 1 or {len(self.modes)}."
                raise ValueError(msg)
        self.parameter_set.add_parameter(parameter)
        self.__dict__[parameter.name] = parameter

    @property
    def bargmann(self) -> tuple:
        r"""
        The Bargmann parametrization of this circuit component, if available.
        """
        if not isinstance(self.representation, Bargmann):
            raise ValueError(
                f"Cannot compute triple from representation of type ``{self.representation.__class__.__qualname__}``."
            )
        return self.representation.triple

    @property
    def representation(self) -> Representation | None:
        r"""
        A representation of this circuit component.
        """
        return self._representation

    @property
    def modes(self) -> list[int]:
        r"""
        The sorted list of modes of this component.
        """
        return sorted(self.wires.modes)

    @property
    def n_modes(self) -> list[int]:
        r"""
        The number of modes in this component.
        """
        return len(self.modes)

    @property
    def name(self) -> str:
        r"""
        The name of this component.
        """
        return self._name

    @property
    def parameter_set(self) -> ParameterSet:
        r"""
        The set of parameters characterizing this component.
        """
        return self._parameter_set

    @property
    def wires(self) -> Wires:
        r"""
        The wires of this component.
        """
        return self._wires

    @property
    def adjoint(self) -> AdjointView:
        r"""
        The ``AdjointView`` of this component.
        """
        return AdjointView(self)

    @property
    def dual(self) -> DualView:
        r"""
        The ``DualView`` of this component.
        """
        return DualView(self)

    def light_copy(self) -> CircuitComponent:
        r"""
        Creates a copy of this component by copying every data stored in memory for
        it by reference, except for its wires, which are copied by value.
        """
        instance = super().__new__(self.__class__)
        instance.__dict__ = self.__dict__.copy()
        instance.__dict__["_wires"] = Wires(*self.wires.args)
        return instance

    def on(self, modes: Sequence[int]) -> CircuitComponent:
        r"""
        Creates a copy of this component that acts on the given ``modes`` instead of on the
        original modes.

        Args:
            modes: The new modes that this component acts on.

        Returns:
            The component acting on the specified modes.

        Raises:
            ValueError: If ``modes`` contains more or less modes than the original component.
        """
        modes = set(modes)

        ob = self.wires.output.bra
        ib = self.wires.input.bra
        ok = self.wires.output.ket
        ik = self.wires.input.ket
        for subset in [ob, ib, ok, ik]:
            if subset and len(subset.modes) != len(modes):
                msg = f"Expected ``{len(modes)}`` modes, found ``{len(subset.modes)}``."
                raise ValueError(msg)

        wires = Wires(
            modes_out_bra=modes if ob else set(),
            modes_in_bra=modes if ib else set(),
            modes_out_ket=modes if ok else set(),
            modes_in_ket=modes if ik else set(),
        )

        ret = self.light_copy()
        ret._wires = wires

        return ret

    def to_fock_component(
        self, shape: Optional[Union[int, Iterable[int]]] = None
    ) -> CircuitComponent:
        r"""
        Returns a circuit component with the same attributes as this component, but
        with ``Fock`` representation.

        Uses the :meth:`mrmustard.physics.converters.to_fock` method to convert the internal
        representation.

        .. code-block::

            >>> from mrmustard.physics.converters import to_fock
            >>> from mrmustard.lab_dev import Dgate

            >>> d = Dgate([1], x=0.1, y=0.1)
            >>> d_fock = d.to_fock_component(shape=3)

            >>> assert d_fock.name == d.name
            >>> assert d_fock.wires == d.wires
            >>> assert d_fock.representation == to_fock(d.representation, shape=3)

        Args:
            shape: The shape of the returned representation. If ``shape``is given as
                an ``int``, it is broadcasted to all the dimensions. If ``None``, it
                defaults to the value of ``AUTOCUTOFF_MAX_CUTOFF`` in the settings.
        """
        cls = self.__class__
        return cls._from_attributes(
            self.name,
            to_fock(self.representation, shape=shape),
            self.wires,
        )

    def __add__(self, other: CircuitComponent) -> CircuitComponent:
        r"""
        Implements the addition between circuit components.
        """
        if self.wires != other.wires:
            msg = "Cannot add components with different wires."
            raise ValueError(msg)
        rep = self.representation + other.representation
        name = self.name if self.name == other.name else ""
        return self._from_attributes(name, rep, self.wires)

    def __sub__(self, other: CircuitComponent) -> CircuitComponent:
        r"""
        Implements the subtraction between circuit components.
        """
        if self.wires != other.wires:
            msg = "Cannot subtract components with different wires."
            raise ValueError(msg)
        rep = self.representation - other.representation
        name = self.name if self.name == other.name else ""
        return self._from_attributes(name, rep, self.wires)

    def __mul__(self, other: Scalar) -> CircuitComponent:
        r"""
        Implements the multiplication by a scalar on the right.
        """
        return self._from_attributes(self.name, other * self.representation, self.wires)

    def __rmul__(self, other: Scalar) -> CircuitComponent:
        r"""
        Implements the multiplication by a scalar on the left.
        """
        return self.__mul__(other)

    def __truediv__(self, other: Scalar) -> CircuitComponent:
        r"""
        Implements the division by a scalar for circuit components.
        """
        return self._from_attributes(self.name, self.representation / other, self.wires)

    def __eq__(self, other) -> bool:
        r"""
        Whether this component is equal to another component.

        Compares representations and wires, but not the other attributes (including name and parameter set).
        """
        return self.representation == other.representation and self.wires == other.wires

    def __matmul__(self, other: CircuitComponent) -> CircuitComponent:
        r"""
        Contracts ``self`` and ``other``, without adding adjoints.
        """
        # initialized the ``Wires`` of the returned component
        wires_ret, perm = self.wires @ other.wires

        # find the indices of the wires being contracted on the bra side
        bra_modes = tuple(self.wires.bra.output.modes & other.wires.bra.input.modes)
        idx_z = self.wires.bra.output[bra_modes].indices
        idx_zconj = other.wires.bra.input[bra_modes].indices

        # find the indices of the wires being contracted on the ket side
        ket_modes = tuple(self.wires.ket.output.modes & other.wires.ket.input.modes)
        idx_z += self.wires.ket.output[ket_modes].indices
        idx_zconj += other.wires.ket.input[ket_modes].indices

        # calculate the representation of the returned component
        representation_ret = self.representation[idx_z] @ other.representation[idx_zconj]

        # reorder the representation
        representation_ret = representation_ret.reorder(perm) if perm else representation_ret
        return CircuitComponent._from_attributes(None, representation_ret, wires_ret)

    def __rshift__(self, other: CircuitComponent) -> CircuitComponent:
        r"""
        Contracts ``self`` and ``other`` as it would in a circuit, adding the adjoints when
        they are missing.
        """
        msg = f"``>>`` not supported between {self} and {other}, use ``@``."

        wires_s = self.wires
        wires_o = other.wires

        if wires_s.ket and wires_s.bra:
            if wires_o.ket and wires_o.bra:
                return self @ other
            return self @ other @ other.adjoint

        if wires_s.ket:
            if wires_o.ket and wires_o.bra:
                return self @ self.adjoint @ other
            if wires_o.ket:
                return self @ other
            raise ValueError(msg)

        if wires_s.bra:
            if wires_o.ket and wires_o.bra:
                return self @ self.adjoint @ other
            if wires_o.bra:
                return self @ other
            raise ValueError(msg)

        raise ValueError(msg)

    def __repr__(self) -> str:
        return f"CircuitComponent(name={self.name or None}, modes={self.modes})"


class CCView(CircuitComponent):
    r"""A base class for views of circuit components.
    Args:
        component: The circuit component to take the view of.
    """

    def __init__(self, component: CircuitComponent) -> None:
        self.__dict__ = component.__dict__.copy()
        self._component = component.light_copy()

    def __getattr__(self, name):
        r"""send calls to the component"""
        return getattr(self._component, name)

    def __repr__(self) -> str:
        return repr(self._component)


class AdjointView(CCView):
    r"""
    Adjoint view of a circuit component.

    Args:
        component: The circuit component to take the view of.
    """

    @property
    def adjoint(self) -> CircuitComponent:
        r"""
        Returns a light-copy of the component that was used to generate the view.
        """
        return self._component.light_copy()

    @property
    def representation(self):
        r"""
        A representation of this circuit component.
        """
        bras = self._component.wires.bra.indices
        kets = self._component.wires.ket.indices
        return self._component.representation.reorder(kets + bras).conj()

    @property
    def wires(self):
        r"""
        The ``Wires`` in this component.
        """
        return self._component.wires.adjoint


class DualView(CCView):
    r"""
    Dual view of a circuit component.

    Args:
        component: The circuit component to take the view of.
    """

    @property
    def dual(self) -> CircuitComponent:
        r"""
        Returns a light-copy of the component that was used to generate the view.
        """
        return self._component.light_copy()

    @property
    def representation(self):
        r"""
        A representation of this circuit component.
        """
        ok = self._component.wires.ket.output.indices
        ik = self._component.wires.ket.input.indices
        ib = self._component.wires.bra.input.indices
        ob = self._component.wires.bra.output.indices
        return self._component.representation.reorder(ib + ob + ik + ok).conj()

    @property
    def wires(self):
        r"""
        The ``Wires`` in this component.
        """
        return self._component.wires.dual
