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

""" Classes for supporting tensor network functionalities."""

from __future__ import annotations

from typing import Iterable, Optional
import numpy as np

from mrmustard import settings

# pylint: disable=protected-access

__all__ = ["Wire", "Wires"]

Wire = int
r"""
An integer representing a wire in a tensor network.
"""


class Wires:
    r"""
    A class with wire functionality for tensor network applications.

    Wires are arranged into four groups, namely output bra, input bra, output ket, and input ket.
    Each of the groups can span multiple modes.

    .. code-block::

        >>> from mrmustard.lab_dev.wires import Wires

        >>> w = Wires([0, 1], [1, 2], [0,], [1, 2, 3])

        >>> # access the modes
        >>> modes = w.modes
        >>> assert w.modes == [0, 1, 2, 3]

        >>> # get input/output subsets
        >>> w_in = w.input
        >>> assert w_in.modes == [1, 2, 3]

        >>> # get ket/bra subsets
        >>> w_in_bra = w_in.bra
        >>> assert w_in_bra.modes == [1, 2]

    Every wire is assigned a numerical id, which is random and unique. The list of all the
    ids of a ``Wires`` can be accessed using the ``ids`` property. The standard order for this
    list is: ids for all the output bra wires, ids for all the input bra wires, ids for all the
    output ket wires, ids for all the input ket wires.

    .. code-block::

        >>> from mrmustard.lab_dev.wires import Wires

        >>> w = Wires([0, 1], [1, 2], [0,], [1, 2, 3])

        >>> # access the ids
        >>> ids = w.ids
        >>> assert len(ids) == 8

    Note that subsets return new ``Wires`` objects with the same ids as the original object.

    Args:
        modes_out_bra: The output modes on the bra side.
        modes_in_bra: The input modes on the bra side.
        modes_out_ket: The output modes on the ket side.
        modes_in_ket: The input modes on the ket side.

    Note that the order of the modes passed to initialize the object doesn't matter,
    as they get sorted at init time.
    """

    def __init__(
        self,
        modes_out_bra: Optional[Iterable[int]] = None,
        modes_in_bra: Optional[Iterable[int]] = None,
        modes_out_ket: Optional[Iterable[int]] = None,
        modes_in_ket: Optional[Iterable[int]] = None,
    ) -> None:
        modes_out_bra = modes_out_bra or []
        modes_in_bra = modes_in_bra or []
        modes_out_ket = modes_out_ket or []
        modes_in_ket = modes_in_ket or []

        self._modes = list(
            set(modes_out_bra) | set(modes_in_bra) | set(modes_out_ket) | set(modes_in_ket)
        )
        randint = settings.rng.integers  # MM random number generator
        ob = {m: randint(1, 2**62) if m in modes_out_bra else 0 for m in self._modes}
        ib = {m: randint(1, 2**62) if m in modes_in_bra else 0 for m in self._modes}
        ok = {m: randint(1, 2**62) if m in modes_out_ket else 0 for m in self._modes}
        ik = {m: randint(1, 2**62) if m in modes_in_ket else 0 for m in self._modes}
        self._id_array = np.array([[ob[m], ib[m], ok[m], ik[m]] for m in self._modes])
        self._mask = np.ones_like(self._id_array)  # multiplicative mask

    def _args(self):
        r"""
        Returns the input arguments needed to initialize the same ``Wires`` object
        (with different ids).
        """
        ob_modes = np.array(self._modes)[self._id_array[:, 0] > 0].tolist()
        ib_modes = np.array(self._modes)[self._id_array[:, 1] > 0].tolist()
        ok_modes = np.array(self._modes)[self._id_array[:, 2] > 0].tolist()
        ik_modes = np.array(self._modes)[self._id_array[:, 3] > 0].tolist()
        return tuple(ob_modes), tuple(ib_modes), tuple(ok_modes), tuple(ik_modes)

    @classmethod
    def _from_data(cls, id_array, modes, mask=None):
        r"""
        Initializes ``Wires`` object from its private attributes.
        """
        w = cls()
        w._id_array = id_array
        w._modes = modes
        w._mask = mask if mask is not None else np.ones_like(w._id_array)
        return w

    def _view(self, masked_rows: tuple[int, ...] = (), masked_cols: tuple[int, ...] = ()) -> Wires:
        r"""
        A masked view of this Wires object.
        """
        w = self._from_data(self._id_array, self._modes, self._mask.copy())
        w._mask[masked_rows, :] = -1
        w._mask[:, masked_cols] = -1
        return w

    def _mode(self, mode: int) -> np.ndarray:
        r"""
        A slice of the id_array matrix at the given mode.
        """
        return np.maximum(0, self.id_array[[self._modes.index(mode)]])[0]

    @property
    def id_array(self) -> np.ndarray:
        r"""
        The id_array of the available wires in a two-dimensional array, where line ``j`` contains
        the ids (in the standard order) for mode ``j``.
        """
        return self._id_array * self._mask

    @property
    def ids(self) -> list[int]:
        r"""
        The list of ids of the available wires in the standard order.
        """
        flat = self.id_array.T.ravel()
        return flat[flat > 0].tolist()

    @ids.setter
    def ids(self, ids: list[int]):
        r"""
        Sets the ids of the available wires.
        """
        if len(ids) != len(self.ids):
            raise ValueError(f"wrong number of ids (expected {len(self.ids)}, got {len(ids)})")
        self._id_array.flat[self.id_array.flatten() > 0] = ids

    @property
    def modes(self) -> list[int]:
        r"""
        The set of modes of the populated wires.
        """
        return [m for m in self._modes if any(self.id_array[self._modes.index(m)] > 0)]

    @property
    def indices(self) -> list[int]:
        r"""
        The array of indices of this subset in the standard order.
        """
        flat = self.id_array.T.ravel()
        flat = flat[flat != 0]
        return np.where(flat > 0)[0].tolist()

    @property
    def input(self) -> Wires:
        r"""
        A view of this ``Wires`` object without output wires.
        """
        return self._view(masked_cols=(0, 2))

    @property
    def output(self) -> Wires:
        r"""
        A view of this ``Wires`` object without input wires.
        """
        return self._view(masked_cols=(1, 3))

    @property
    def ket(self) -> Wires:
        r"""
        A view of this ``Wires`` object without bra wires.
        """
        return self._view(masked_cols=(0, 1))

    @property
    def bra(self) -> Wires:
        r"""
        A view of this ``Wires`` object without ket wires.
        """
        return self._view(masked_cols=(2, 3))

    @property
    def adjoint(self) -> Wires:
        r"""
        The adjoint of this wires object, obtained by swapping ket and bra wires, with new ids.
        """
        return self._from_data(self._id_array[:, [2, 3, 0, 1]], self._modes, self._mask)

    @property
    def dual(self) -> Wires:
        r"""
        The dual of this wires object, obtained by swapping input and output wires, with new ids.
        """
        return self._from_data(self._id_array[:, [1, 0, 3, 2]], self._modes, self._mask)

    def copy(self) -> Wires:
        r"""
        A copy of this wire with new ids.
        """
        w = Wires(*self._args())
        w._mask = self._mask.copy()
        return w

    def __add__(self, other: Wires) -> Wires:
        r"""
        A new ``Wires`` object with the wires of self and other combined.
        """
        modes_rows = {}
        all_modes = sorted(set(self.modes) | set(other.modes))
        for m in all_modes:
            self_row = self.id_array[self._modes.index(m)] if m in self.modes else np.zeros(4)
            other_row = other.id_array[other._modes.index(m)] if m in other.modes else np.zeros(4)
            if np.any(np.where(self_row > 0) == np.where(other_row > 0)):
                raise ValueError(f"wires overlap on mode {m}")
            modes_rows[m] = [s if s > 0 else o for s, o in zip(self_row, other_row)]
        combined_array = np.array([modes_rows[m] for m in sorted(modes_rows)])
        return self._from_data(combined_array, sorted(modes_rows), np.ones_like(combined_array))

    def __bool__(self) -> bool:
        r"""
        Returns ``True`` if this ``Wires`` object has ids, ``False`` otherwise.
        """
        return True if len(self.ids) > 0 else False

    def __getitem__(self, modes: Iterable[int] | int) -> Wires:
        r"""
        A view of this Wires object with wires only on the given modes.
        """
        modes = [modes] if isinstance(modes, int) else modes
        idxs = tuple(list(self._modes).index(m) for m in set(self._modes).difference(modes))
        return self._view(masked_rows=idxs)

    def __lshift__(self, other: Wires) -> Wires:
        return (other.dual >> self.dual).dual  # how cool is this

    def __rshift__(self, other: Wires) -> Wires:
        r"""
        A new Wires object with the wires of ``self`` and ``other`` combined as two
        components in a circuit: the output of self connects to the input of other wherever
        they match. All surviving wires are arranged in the standard order.
        A ValueError is raised if there are any surviving wires that overlap.
        """
        all_modes = sorted(set(self.modes) | set(other.modes))
        new_id_array = np.zeros((len(all_modes), 4), dtype=np.int64)
        for i, m in enumerate(all_modes):
            if m in self.modes and m in other.modes:
                # m-th row of self and other (self output bra = sob, etc...)
                sob, sib, sok, sik = self._mode(m)
                oob, oib, ook, oik = other._mode(m)
                errors = {
                    "output bra": sob and oob and not oib,
                    "output ket": sok and ook and not oik,
                    "input bra": oib and sib and not sob,
                    "input ket": oik and sik and not sok,
                }
                if any(errors.values()):
                    position = [k for k, v in errors.items() if v][0]
                    raise ValueError(f"wire overlap at {position} of mode {m}")
                if bool(sob) == bool(oib):  # if the inner wires are both there or both not there
                    new_id_array[i] += np.array([oob, sib, 0, 0])
                elif not sib and not sob:
                    new_id_array[i] += np.array([oob, oib, 0, 0])
                else:
                    new_id_array[i] += np.array([sob, sib, 0, 0])
                if bool(sok) == bool(oik):
                    new_id_array[i] += np.array([0, 0, ook, sik])
                elif not sik and not sok:
                    new_id_array[i] += np.array([0, 0, ook, oik])
                else:
                    new_id_array[i] += np.array([0, 0, sok, sik])
            elif m in self.modes and not m in other.modes:
                new_id_array[i] += self._mode(m)
            elif m in other.modes and not m in self.modes:
                new_id_array[i] += other._mode(m)
        return self._from_data(np.abs(new_id_array), all_modes)

    def __repr__(self) -> str:
        ob_modes, ib_modes, ok_modes, ik_modes = self._args()
        return f"Wires({ob_modes}, {ib_modes}, {ok_modes}, {ik_modes})"

    def _repr_html_(self):  # pragma: no cover
        "A matrix plot of the id_array."
        row_labels = map(str, self._modes)
        col_labels = ["bra-out", "bra-in", "ket-out", "ket-in"]
        array = np.abs(self.id_array) / (self.id_array + 1e-15)
        idxs = (i for i in self.indices)
        box_size = "60px"  # Set the size of the squares
        html = '<table style="border-collapse: collapse; border: 1px solid black;">'
        # colors
        active = "#5b9bd5"
        inactive = "#d6e8f7"

        # Add column headers
        html += "<tr>"
        for label in [""] + col_labels:  # Add an empty string for the top-left cell
            html += f'<th style="border: 1px solid black; padding: 5px;">{label}</th>'
        html += "</tr>"

        # Initialize rows with row labels
        rows_html = [
            f'<tr><td style="border: 1px solid black; padding: 5px;">{label}</td>'
            for label in row_labels
        ]

        # Add table cells (column by column)
        for label, col in zip(col_labels, array.T):
            for row_idx, value in enumerate(col):
                color = (
                    "white"
                    if np.isclose(value, 0)
                    else (active if np.isclose(value, 1) else inactive)
                )
                cell_html = f'<td style="border: 1px solid black; padding: 5px;\
                      width: {box_size}px; height: {box_size}px; background-color:\
                          {color}; box-sizing: border-box;'
                if color == active:
                    cell_html += (
                        f' text-align: center; vertical-align: middle;">{str(next(idxs))}</td>'
                    )
                else:
                    cell_html += '"></td>'
                rows_html[row_idx] += cell_html

        # Close the rows and add them to the HTML table
        for row_html in rows_html:
            row_html += "</tr>"
            html += row_html

        html += "</table>"

        try:
            from IPython.display import display, HTML  # pylint: disable=import-outside-toplevel

            display(HTML(html))
        except ImportError as e:
            raise ImportError(
                "To display the wires in a jupyter notebook you need to `pip install IPython`"
            ) from e
