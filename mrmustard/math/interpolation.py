from __future__ import annotations

import numpy as np
from scipy.interpolate import interp1d

from mrmustard import settings
from mrmustard.math import Math
from mrmustard.typing import ComplexVector, RealVector
from mrmustard.utils.graphics import wave_function_cartesian, wave_function_polar

np.set_printoptions(suppress=True, linewidth=250)


math = Math()


class ComplexFunction1D:
    r"""A complex function of a real variable."""

    def __init__(self, x: RealVector, y: ComplexVector):
        r"""Initialize the function with a set of points.
        Supports interpolation, plotting, and resampling.
        Args:
            x (Vector): the domain of the function
            y (Vector): the values of the function
        """
        self.interp_real = interp1d(x, np.real(y))
        self.interp_imag = interp1d(x, np.imag(y))

    def intersect_domains(self, other: ComplexFunction1D) -> RealVector:
        x = np.union1d(self.domain, other.domain)
        # find intersection of x ranges
        x_min = max(self.domain.min(), other.domain.min())
        x_max = min(self.domain.max(), other.domain.max())
        # keep only the intersection
        x = x[(x >= x_min) & (x <= x_max)]
        return x

    @property
    def domain(self) -> RealVector:
        return self.interp_real.x

    @property
    def values(self) -> ComplexVector:
        return self.interp_real.y + 1j * self.interp_imag.y

    def plot(self):
        r"""
        Plots the magnitude of the wave function for each value of x in cartesian coordinates.
        The filling at x is colored by the phase angle of f(x) using HUE colors.
        """
        return wave_function_cartesian(self.domain, self.values)

    def plot_polar(self):
        r"""
        Plots the complex values of the wave function for each value of x on the y-z plane at x,
        in polar coordinates. The points are colored by their phase angle using HUE colors.
        """
        return wave_function_polar(self.domain, self.values)

    def resample(self) -> None:
        """Resample the domain to have at most max_dom_points points.
        Sample more points where the derivative is large.
        """
        min_, max_ = self.domain.min(), self.domain.max()
        dom = np.linspace(min_, max_, settings.MAX_DOM_POINTS)
        real_grad = np.gradient(self.interp_real(dom), dom)
        imag_grad = np.gradient(self.interp_imag(dom), dom)
        dy = np.abs(real_grad - 1j * imag_grad)  # Warning: unverified
        dy = interp1d(dom, dy)
        # we have a budget of max_dom_points,
        # we sample them between x.min() and x.max()
        # using dy as probability distribution
        a = np.linspace(self.domain.min(), self.domain.max(), 10000)
        x = np.random.choice(
            a=a,
            size=settings.MAX_DOM_POINTS,
            p=dy(a) / dy(a).sum(),
        )
        self.interp_real = interp1d(x, self.interp_real(x))
        self.interp_imag = interp1d(x, self.interp_imag(x))

    def __call__(self, x) -> complex:
        return self.interp_real(x) + 1j * self.interp_imag(x)

    def __add__(self, other: ComplexFunction1D | int | float | complex) -> ComplexFunction1D:
        if isinstance(other, self.__class__):
            x = self.intersect_domains(other)
            y = self(x) + other(x)
            f = ComplexFunction1D(x, y)
        elif isinstance(other, (int, float, complex)):
            x = self.domain
            y = self(x) + other
            f = ComplexFunction1D(x, y)
        else:
            raise TypeError(f"Cannot add {type(self)} and {type(other)}")
        if len(x) > settings.MAX_DOM_POINTS:
            f.resample()
        return f

    def __radd__(self, other: int | float | complex) -> ComplexFunction1D:
        return self + other

    def __mul__(self, other: ComplexFunction1D | int | float | complex) -> ComplexFunction1D:
        if isinstance(other, ComplexFunction1D):
            x = self.intersect_domains(other)
            f = ComplexFunction1D(x, self(x) * other(x))
        elif isinstance(other, (int, float, complex)):
            x = self.domain
            f = ComplexFunction1D(x, self(x) * other)
        if len(x) > settings.MAX_DOM_POINTS:
            f.resample()
        return f

    def __rmul__(self, other: int | float | complex) -> ComplexFunction1D:
        return self * other

    def __neg__(self) -> ComplexFunction1D:
        return ComplexFunction1D(self.domain, -self.interp_real.y - 1j * self.interp_imag.y)

    def __sub__(self, other: ComplexFunction1D | int | float | complex) -> ComplexFunction1D:
        return self + (-other)

    def __rsub__(self, other: int | float | complex) -> ComplexFunction1D:
        return other + (-self)

    def __truediv__(self, other: ComplexFunction1D | int | float | complex) -> ComplexFunction1D:
        if isinstance(other, ComplexFunction1D):
            x = self.intersect_domains(other)
            y = self(x) / other(x)
            f = ComplexFunction1D(x, y)
        elif isinstance(other, (int, float, complex)):
            x = self.domain
            y = self(x) / other
            f = ComplexFunction1D(x, y)
        if len(x) > self.settings.MAX_DOM_POINTS:
            f.resample()
        return f

    def __rtruediv__(self, other: int | float | complex) -> ComplexFunction1D:
        if isinstance(other, (int, float, complex)):
            x = self.domain
            y = other / self(x)
            return ComplexFunction1D(x, y)

    def __array_ufunc__(self, ufunc, method, *inputs, **kwargs) -> ComplexFunction1D:
        if method == "__call__":
            x = inputs[0].domain
            y = ufunc(*(input(x) for input in inputs), **kwargs)
            return ComplexFunction1D(x, y)
        else:
            raise NotImplementedError

    def __array__(self, dtype=None) -> np.ndarray:
        return np.array(self.values, dtype=dtype)
