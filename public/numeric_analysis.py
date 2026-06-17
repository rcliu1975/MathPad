from __future__ import annotations

import ast
import cmath
import contextlib
import dataclasses
import io
import json
import math
import sys
import traceback
from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from typing import Any, NotRequired, TypedDict, cast

import numpy as np
from scipy import integrate, interpolate, optimize, linalg

try:
    import CoolProp.CoolProp as coolprop
except Exception:  # pragma: no cover - optional dependency
    coolprop = None  # type: ignore[assignment]


sys.setrecursionlimit(2000)

DIM_COUNT = 9
ZERO_DIMS = (0.0,) * DIM_COUNT
ANGLE_DIMS = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0)
EXP_NUM_DIGITS = 12
EXP_INT_THRESHOLD = 1e-12


def round_dims(dims: tuple[float, ...]) -> tuple[float, ...]:
    return tuple(round(float(value), EXP_NUM_DIGITS) for value in dims)


def dims_close(a: tuple[float, ...], b: tuple[float, ...]) -> bool:
    return all(abs(x - y) < EXP_INT_THRESHOLD for x, y in zip(a, b))


def add_dims(a: tuple[float, ...], b: tuple[float, ...]) -> tuple[float, ...]:
    return round_dims(tuple(x + y for x, y in zip(a, b)))


def sub_dims(a: tuple[float, ...], b: tuple[float, ...]) -> tuple[float, ...]:
    return round_dims(tuple(x - y for x, y in zip(a, b)))


def scale_dims(dims: tuple[float, ...], factor: float) -> tuple[float, ...]:
    return round_dims(tuple(value * factor for value in dims))


def negate_dims(dims: tuple[float, ...]) -> tuple[float, ...]:
    return round_dims(tuple(-value for value in dims))


def format_number(value: Any) -> str:
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, complex):
        if abs(value.imag) < 1e-15:
            return str(float(value.real))
        return str(value)
    if isinstance(value, (int, float)):
        return str(float(value))
    return str(value)


def format_symbolic_number(value: Any) -> str:
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, complex):
        if abs(value.imag) < 1e-15:
            value = value.real
        else:
            return str(value)
    if isinstance(value, (int, float)):
        if abs(value - round(value)) < EXP_INT_THRESHOLD:
            return str(int(round(value)))
        return str(value)
    return str(value)


def format_units_latex(units: str) -> str:
    if not units:
        return ""
    return rf"\left\lbrack {units}\right\rbrack"


def normalize_unit_power(power: float) -> str:
    if abs(power - round(power)) < EXP_INT_THRESHOLD:
        return str(int(round(power)))
    return format_number(power)


def dims_to_units(dims: tuple[float, ...], custom_base_units: dict[str, str] | None = None) -> str:
    dims = round_dims(dims)
    units = {
        (0.0,) * DIM_COUNT: "",
        (1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0): "kg",
        (0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0): "m",
        (0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0): "s",
        (0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0): "A",
        (0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0): "K",
        (0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0): "cd",
        (0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0): "mol",
        (1.0, 1.0, -2.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0): "N",
        (0.0, 2.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0): "m^2",
        (0.0, 3.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0): "m^3",
        (1.0, 2.0, -2.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0): "J",
        (1.0, 2.0, -3.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0): "W",
        (1.0, -1.0, -2.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0): "Pa",
        (0.0, 0.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0): "C",
        (-1.0, -2.0, 4.0, 2.0, 0.0, 0.0, 0.0, 0.0, 0.0): "F",
        (1.0, 2.0, -3.0, -1.0, 0.0, 0.0, 0.0, 0.0, 0.0): "V",
        (1.0, 2.0, -3.0, -2.0, 0.0, 0.0, 0.0, 0.0, 0.0): "ohm",
        (1.0, 2.0, -2.0, -2.0, 0.0, 0.0, 0.0, 0.0, 0.0): "H",
        (-1.0, -2.0, 3.0, 2.0, 0.0, 0.0, 0.0, 0.0, 0.0): "S",
        (1.0, 2.0, -2.0, -1.0, 0.0, 0.0, 0.0, 0.0, 0.0): "Wb",
        (1.0, 0.0, -2.0, -1.0, 0.0, 0.0, 0.0, 0.0, 0.0): "T",
        (0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0): "rad",
        (0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0): "b",
    }

    if custom_base_units:
        units[(1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)] = custom_base_units.get("mass", "kg")
        units[(0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)] = custom_base_units.get("length", "m")
        units[(0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)] = custom_base_units.get("time", "s")
        units[(0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0)] = custom_base_units.get("current", "A")
        units[(0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0)] = custom_base_units.get("temperature", "K")
        units[(0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0)] = custom_base_units.get("luminous_intensity", "cd")
        units[(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0)] = custom_base_units.get("amount_of_substance", "mol")
        units[(1.0, 1.0, -2.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)] = custom_base_units.get("force", "N")
        units[(0.0, 2.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)] = custom_base_units.get("area", "m^2")
        units[(0.0, 3.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)] = custom_base_units.get("volume", "m^3")
        units[(1.0, 2.0, -2.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)] = custom_base_units.get("energy", "J")
        units[(1.0, 2.0, -3.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)] = custom_base_units.get("power", "W")
        units[(1.0, -1.0, -2.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)] = custom_base_units.get("pressure", "Pa")
        units[(0.0, 0.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0)] = custom_base_units.get("charge", "C")
        units[(-1.0, -2.0, 4.0, 2.0, 0.0, 0.0, 0.0, 0.0, 0.0)] = custom_base_units.get("capacitance", "F")
        units[(1.0, 2.0, -3.0, -1.0, 0.0, 0.0, 0.0, 0.0, 0.0)] = custom_base_units.get("electric_potential", "V")
        units[(1.0, 2.0, -3.0, -2.0, 0.0, 0.0, 0.0, 0.0, 0.0)] = custom_base_units.get("resistance", "ohm")
        units[(1.0, 2.0, -2.0, -2.0, 0.0, 0.0, 0.0, 0.0, 0.0)] = custom_base_units.get("inductance", "H")
        units[(-1.0, -2.0, 3.0, 2.0, 0.0, 0.0, 0.0, 0.0, 0.0)] = custom_base_units.get("conductance", "S")
        units[(1.0, 2.0, -2.0, -1.0, 0.0, 0.0, 0.0, 0.0, 0.0)] = custom_base_units.get("magnetic_flux", "Wb")
        units[(1.0, 0.0, -2.0, -1.0, 0.0, 0.0, 0.0, 0.0, 0.0)] = custom_base_units.get("magnetic_flux_density", "T")
        units[(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0)] = custom_base_units.get("angle", "rad")
        units[(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0)] = custom_base_units.get("information", "b")

    if dims in units:
        return units[dims]

    parts: list[str] = []
    symbols = [
        units[(1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)],
        units[(0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)],
        units[(0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)],
        units[(0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0)],
        units[(0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0)],
        units[(0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0)],
        units[(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0)],
        units[(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0)],
        units[(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0)],
    ]
    for symbol, exponent in zip(symbols, dims):
        if abs(exponent) < EXP_INT_THRESHOLD:
            continue
        if exponent == 1:
            parts.append(symbol)
        else:
            parts.append(f"{symbol}^{normalize_unit_power(exponent)}")
    return " ".join(parts)


@dataclass
class Quantity:
    value: Any
    dims: tuple[float, ...] = ZERO_DIMS

    __array_priority__ = 1000

    def _binary(self, other: Any, op: Callable[[Any, Any], Any], dims_op: Callable[[tuple[float, ...], tuple[float, ...]], tuple[float, ...]]) -> "Quantity":
        other_q = ensure_quantity(other)
        if not dims_close(self.dims, other_q.dims):
            raise ValueError("Dimension mismatch")
        return Quantity(op(self.value, other_q.value), dims_op(self.dims, other_q.dims))

    def __add__(self, other: Any) -> "Quantity":
        other_q = ensure_quantity(other)
        if not dims_close(self.dims, other_q.dims):
            raise ValueError("Dimension mismatch")
        return Quantity(self.value + other_q.value, self.dims)

    def __radd__(self, other: Any) -> "Quantity":
        return self.__add__(other)

    def __sub__(self, other: Any) -> "Quantity":
        other_q = ensure_quantity(other)
        if not dims_close(self.dims, other_q.dims):
            raise ValueError("Dimension mismatch")
        return Quantity(self.value - other_q.value, self.dims)

    def __rsub__(self, other: Any) -> "Quantity":
        other_q = ensure_quantity(other)
        if not dims_close(self.dims, other_q.dims):
            raise ValueError("Dimension mismatch")
        return Quantity(other_q.value - self.value, self.dims)

    def __mul__(self, other: Any) -> "Quantity":
        other_q = ensure_quantity(other)
        return Quantity(self.value * other_q.value, add_dims(self.dims, other_q.dims))

    def __rmul__(self, other: Any) -> "Quantity":
        return self.__mul__(other)

    def __truediv__(self, other: Any) -> "Quantity":
        other_q = ensure_quantity(other)
        return Quantity(self.value / other_q.value, sub_dims(self.dims, other_q.dims))

    def __rtruediv__(self, other: Any) -> "Quantity":
        other_q = ensure_quantity(other)
        return Quantity(other_q.value / self.value, sub_dims(other_q.dims, self.dims))

    def __pow__(self, other: Any) -> "Quantity":
        other_q = ensure_quantity(other)
        if not dims_close(other_q.dims, ZERO_DIMS):
            raise ValueError("Exponent must be dimensionless")
        exponent = other_q.value
        if isinstance(exponent, np.ndarray):
            raise ValueError("Unsupported exponent")
        return Quantity(self.value ** exponent, scale_dims(self.dims, float(exponent)))

    def __rpow__(self, other: Any) -> "Quantity":
        other_q = ensure_quantity(other)
        return other_q.__pow__(self)

    def __neg__(self) -> "Quantity":
        return Quantity(-self.value, self.dims)

    def __abs__(self) -> "Quantity":
        return Quantity(abs(self.value), self.dims)

    def __float__(self) -> float:
        if isinstance(self.value, np.ndarray):
            raise TypeError("Matrix cannot be converted to float")
        return float(self.value)

    def __complex__(self) -> complex:
        if isinstance(self.value, np.ndarray):
            raise TypeError("Matrix cannot be converted to complex")
        return complex(self.value)

    def item(self) -> Any:
        return self.value.item() if isinstance(self.value, np.generic) else self.value


@dataclass
class RenderExpr:
    render_type: str
    render_value: str


@dataclass
class SymbolicValue:
    latex: str
    dims: tuple[float, ...] = ZERO_DIMS

    def __str__(self) -> str:
        return self.latex


def is_symbolic(value: Any) -> bool:
    return isinstance(value, SymbolicValue)


def symbolic_name(name: str) -> str:
    suffix = "_as_variable"
    return name[:-len(suffix)] if name.endswith(suffix) else name


def symbolic_latex(value: Any) -> str:
    if isinstance(value, SymbolicValue):
        return value.latex
    if isinstance(value, Quantity):
        return format_symbolic_number(value.value)
    if isinstance(value, np.generic):
        return format_symbolic_number(value.item())
    if isinstance(value, complex):
        return format_symbolic_number(value)
    if isinstance(value, (int, float, bool)):
        return format_symbolic_number(value)
    return str(value)


def symbolic_dims(value: Any) -> tuple[float, ...]:
    if isinstance(value, SymbolicValue):
        return value.dims
    if isinstance(value, Quantity):
        return value.dims
    return ZERO_DIMS


def make_symbolic(latex: str, dims: tuple[float, ...] = ZERO_DIMS) -> SymbolicValue:
    return SymbolicValue(latex, dims)


def maybe_symbolic_binary(
    lhs: Any,
    rhs: Any,
    op: str,
    numeric_fn: Callable[[Any, Any], Any],
    dims_fn: Callable[[tuple[float, ...], tuple[float, ...]], tuple[float, ...]],
) -> Any:
    if isinstance(lhs, np.ndarray) or isinstance(rhs, np.ndarray):
        lhs_matrix = matrix_value(lhs)
        rhs_matrix = matrix_value(rhs)
        if lhs_matrix.shape == rhs_matrix.shape:
            return np.vectorize(lambda a, b: maybe_symbolic_binary(a, b, op, numeric_fn, dims_fn), otypes=[object])(lhs_matrix, rhs_matrix)
        if lhs_matrix.size == 1:
            scalar = lhs_matrix.item()
            return np.vectorize(lambda b: maybe_symbolic_binary(scalar, b, op, numeric_fn, dims_fn), otypes=[object])(rhs_matrix)
        if rhs_matrix.size == 1:
            scalar = rhs_matrix.item()
            return np.vectorize(lambda a: maybe_symbolic_binary(a, scalar, op, numeric_fn, dims_fn), otypes=[object])(lhs_matrix)
        return numeric_fn(lhs_matrix, rhs_matrix)

    if is_symbolic(lhs) or is_symbolic(rhs):
        lhs_dims = symbolic_dims(lhs)
        rhs_dims = symbolic_dims(rhs)
        if op in {"+", "-"} and not dims_close(lhs_dims, rhs_dims):
            raise ValueError("Dimension mismatch")
        dims = dims_fn(lhs_dims, rhs_dims)
        return make_symbolic(f"{symbolic_latex(lhs)} {op} {symbolic_latex(rhs)}", dims)

    return numeric_fn(lhs, rhs)


def ensure_quantity(value: Any) -> Quantity:
    if isinstance(value, Quantity):
        return value
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, bool):
        return Quantity(value, ZERO_DIMS)
    if isinstance(value, (int, float, complex)):
        return Quantity(value, ZERO_DIMS)
    raise TypeError(f"Unsupported value type {type(value).__name__}")


def is_matrix(value: Any) -> bool:
    return isinstance(value, np.ndarray)


def matrix_value(value: Any) -> np.ndarray:
    if isinstance(value, np.ndarray):
        return value.astype(object, copy=False)
    if isinstance(value, (list, tuple)):
        array = np.array(value, dtype=object)
        if array.ndim == 1:
            return array.reshape((-1, 1))
        return array
    raise TypeError("Matrix value expected")


def elementwise(value: Any, fn: Callable[[Any], Any]) -> Any:
    if isinstance(value, np.ndarray):
        return np.vectorize(fn, otypes=[object])(value)
    if isinstance(value, list):
        return [elementwise(item, fn) for item in value]
    return fn(value)


def array_dims(value: Any) -> tuple[int, ...]:
    if isinstance(value, np.ndarray):
        return tuple(value.shape)
    return ()


def quantity_value(value: Any) -> Any:
    if isinstance(value, Quantity):
        return value.value
    if isinstance(value, np.generic):
        return value.item()
    return value


def quantity_dims(value: Any) -> tuple[float, ...]:
    if isinstance(value, Quantity):
        return value.dims
    return ZERO_DIMS


def quantity_to_result_parts(value: Any, custom_base_units: dict[str, str] | None = None) -> tuple[str, str]:
    if isinstance(value, SymbolicValue):
        return value.latex, format_units_latex(dims_to_units(value.dims, custom_base_units))
    if isinstance(value, Quantity):
        units = dims_to_units(value.dims, custom_base_units)
        return format_number(value.value), format_units_latex(units)
    if isinstance(value, np.generic):
        return format_number(value.item()), ""
    if isinstance(value, complex):
        return format_number(value), ""
    if isinstance(value, (int, float, bool)):
        return format_number(value), ""
    return str(value), ""


def apply_unary_numeric(value: Any, fn: Callable[[Any], Any], dims_fn: Callable[[tuple[float, ...]], tuple[float, ...]] | None = None) -> Any:
    if isinstance(value, np.ndarray):
        return np.vectorize(lambda item: apply_unary_numeric(item, fn, dims_fn), otypes=[object])(value)
    if isinstance(value, Quantity):
        return Quantity(fn(value.value), dims_fn(value.dims) if dims_fn else value.dims)
    return fn(value)


def apply_dimensionless_numeric(value: Any, fn: Callable[[Any], Any]) -> Any:
    if isinstance(value, np.ndarray):
        return np.vectorize(lambda item: apply_dimensionless_numeric(item, fn), otypes=[object])(value)
    if isinstance(value, SymbolicValue):
        return make_symbolic(fn(value.latex), ZERO_DIMS)
    q = ensure_quantity(value)
    if not (dims_close(q.dims, ZERO_DIMS) or dims_close(q.dims, ANGLE_DIMS)):
        raise ValueError("Argument must be dimensionless")
    return Quantity(fn(q.value), ZERO_DIMS)


def apply_preserve_dims_numeric(value: Any, fn: Callable[[Any], Any]) -> Any:
    if isinstance(value, np.ndarray):
        return np.vectorize(lambda item: apply_preserve_dims_numeric(item, fn), otypes=[object])(value)
    if isinstance(value, SymbolicValue):
        return make_symbolic(fn(value.latex), value.dims)
    q = ensure_quantity(value)
    return Quantity(fn(q.value), q.dims)


def apply_two_arg_dimensionless(a: Any, b: Any, fn: Callable[[Any, Any], Any]) -> Any:
    qa = ensure_quantity(a)
    qb = ensure_quantity(b)
    if not dims_close(qa.dims, qb.dims):
        raise ValueError("Dimension mismatch")
    if not dims_close(qa.dims, ZERO_DIMS):
        raise ValueError("Arguments must be dimensionless")
    return Quantity(fn(qa.value, qb.value), ZERO_DIMS)


def custom_abs(value: Any) -> Any:
    if isinstance(value, SymbolicValue):
        return make_symbolic(rf"\left|{value.latex}\right|", value.dims)
    return apply_preserve_dims_numeric(value, abs)


def custom_floor(value: Any) -> Any:
    if isinstance(value, SymbolicValue):
        return make_symbolic(rf"\left\lfloor {value.latex} \right\rfloor", value.dims)
    return apply_preserve_dims_numeric(value, math.floor)


def custom_ceiling(value: Any) -> Any:
    if isinstance(value, SymbolicValue):
        return make_symbolic(rf"\left\lceil {value.latex} \right\rceil", value.dims)
    return apply_preserve_dims_numeric(value, math.ceil)


def custom_sign(value: Any) -> Any:
    if isinstance(value, SymbolicValue):
        return make_symbolic(rf"\operatorname{{sign}}\left({value.latex}\right)", value.dims)
    def _sign(x: Any) -> Any:
        return -1 if x < 0 else 1 if x > 0 else 0

    return apply_preserve_dims_numeric(value, _sign)


def custom_re(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return np.vectorize(custom_re, otypes=[object])(value)
    if isinstance(value, SymbolicValue):
        return make_symbolic(rf"\operatorname{{Re}}\left({value.latex}\right)", value.dims)
    q = ensure_quantity(value)
    return Quantity(np.real(q.value), q.dims)


def custom_im(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return np.vectorize(custom_im, otypes=[object])(value)
    if isinstance(value, SymbolicValue):
        return make_symbolic(rf"\operatorname{{Im}}\left({value.latex}\right)", value.dims)
    q = ensure_quantity(value)
    return Quantity(np.imag(q.value), q.dims)


def custom_conjugate(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return np.vectorize(custom_conjugate, otypes=[object])(value)
    if isinstance(value, SymbolicValue):
        return make_symbolic(rf"\overline{{{value.latex}}}", value.dims)
    q = ensure_quantity(value)
    return Quantity(np.conjugate(q.value), q.dims)


def custom_arg(value: Any) -> Any:
    if isinstance(value, SymbolicValue):
        return make_symbolic(rf"\arg\left({value.latex}\right)", ANGLE_DIMS)
    return Quantity(apply_dimensionless_numeric(value, cmath.phase).value, ANGLE_DIMS)


def custom_sqrt(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return np.vectorize(custom_sqrt, otypes=[object])(value)
    if isinstance(value, SymbolicValue):
        return make_symbolic(rf"\sqrt{{{value.latex}}}", scale_dims(value.dims, 0.5))
    q = ensure_quantity(value)
    return Quantity(np.sqrt(q.value), scale_dims(q.dims, 0.5))


def custom_exp(value: Any) -> Any:
    if isinstance(value, SymbolicValue):
        return make_symbolic(rf"e^{{{value.latex}}}")
    return apply_dimensionless_numeric(value, np.exp)


def custom_log(value: Any, base: Any | None = None) -> Any:
    if isinstance(value, SymbolicValue) or isinstance(base, SymbolicValue):
        if base is None:
            return make_symbolic(rf"\log\left({symbolic_latex(value)}\right)")
        return make_symbolic(rf"\log_{{{symbolic_latex(base)}}}\left({symbolic_latex(value)}\right)")
    if base is None:
        return apply_dimensionless_numeric(value, np.log)
    return apply_two_arg_dimensionless(value, base, lambda x, y: np.log(x) / np.log(y))


def custom_trig(fn: Callable[[Any], Any]) -> Callable[[Any], Any]:
    def wrapper(value: Any) -> Any:
        if isinstance(value, SymbolicValue):
            name = getattr(fn, "__name__", "f")
            latex_name = {
                "sin": "\\sin",
                "cos": "\\cos",
                "tan": "\\tan",
                "sinh": "\\sinh",
                "cosh": "\\cosh",
                "tanh": "\\tanh",
            }.get(name, name)
            return make_symbolic(rf"{latex_name}\left({value.latex}\right)")
        return apply_dimensionless_numeric(value, fn)

    return wrapper


def custom_inverse_trig(fn: Callable[[Any], Any]) -> Callable[[Any], Any]:
    def wrapper(value: Any) -> Any:
        if isinstance(value, SymbolicValue):
            name = getattr(fn, "__name__", "f")
            latex_name = {
                "arcsin": "\\asin",
                "arccos": "\\acos",
                "arctan": "\\atan",
            }.get(name, name)
            return make_symbolic(rf"{latex_name}\left({value.latex}\right)", ANGLE_DIMS)
        result = apply_dimensionless_numeric(value, fn)
        return Quantity(result.value, ANGLE_DIMS)

    return wrapper


def custom_max(*args: Any) -> Any:
    quantities = [ensure_quantity(arg) for arg in args]
    if not quantities:
        raise ValueError("max() requires at least one argument")
    base_dims = quantities[0].dims
    if not all(dims_close(quantity.dims, base_dims) for quantity in quantities[1:]):
        raise ValueError("Dimension mismatch")
    return Quantity(max(quantity.value for quantity in quantities), base_dims)


def custom_min(*args: Any) -> Any:
    quantities = [ensure_quantity(arg) for arg in args]
    if not quantities:
        raise ValueError("min() requires at least one argument")
    base_dims = quantities[0].dims
    if not all(dims_close(quantity.dims, base_dims) for quantity in quantities[1:]):
        raise ValueError("Dimension mismatch")
    return Quantity(min(quantity.value for quantity in quantities), base_dims)


def custom_factorial(value: Any) -> Any:
    quantity = ensure_quantity(value)
    if not dims_close(quantity.dims, ZERO_DIMS):
        raise ValueError("factorial() argument must be dimensionless")
    return Quantity(math.factorial(int(round(float(quantity.value)))), ZERO_DIMS)


def custom_matrix(*args: Any) -> Any:
    if len(args) == 1:
        value = args[0]
        if isinstance(value, np.ndarray):
            return value.astype(object, copy=False)
        if isinstance(value, (list, tuple)):
            if value and not isinstance(value[0], (list, tuple, np.ndarray)):
                return np.array([[item] for item in value], dtype=object)
            return np.array(value, dtype=object)
    return np.array(args, dtype=object)


def custom_ones(*args: Any) -> Any:
    shape = tuple(int(round(float(ensure_quantity(arg).value))) for arg in args)
    return np.ones(shape, dtype=object)


def custom_zeros(*args: Any) -> Any:
    shape = tuple(int(round(float(ensure_quantity(arg).value))) for arg in args)
    return np.zeros(shape, dtype=object)


def custom_eye(n: Any) -> Any:
    size = int(round(float(ensure_quantity(n).value)))
    return np.eye(size, dtype=object)


def custom_transpose(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.T
    if isinstance(value, (list, tuple)):
        return np.array(value, dtype=object).T
    raise TypeError("Transpose expects a matrix")


def custom_piecewise(*args: Any) -> Any:
    if len(args) % 2 == 1:
        default_value = args[-1]
        pairs = list(zip(args[0:-1:2], args[1:-1:2]))
    else:
        default_value = Quantity(float("nan"), ZERO_DIMS)
        pairs = list(zip(args[0::2], args[1::2]))
    for value, condition in pairs:
        if bool(condition):
            return value
    return default_value


def custom_eq(lhs: Any, rhs: Any) -> bool:
    if is_symbolic(lhs) or is_symbolic(rhs):
        if is_symbolic(lhs) and is_symbolic(rhs):
            return lhs.latex == rhs.latex
        return False
    qlhs = ensure_quantity(lhs)
    qrhs = ensure_quantity(rhs)
    if not dims_close(qlhs.dims, qrhs.dims):
        raise ValueError("Dimension mismatch")
    return bool(np.allclose(qlhs.value, qrhs.value))


def custom_compare(lhs: Any, rhs: Any, op: Callable[[Any, Any], bool]) -> bool:
    if is_symbolic(lhs) or is_symbolic(rhs):
        return False
    qlhs = ensure_quantity(lhs)
    qrhs = ensure_quantity(rhs)
    if not dims_close(qlhs.dims, qrhs.dims):
        raise ValueError("Dimension mismatch")
    return bool(op(qlhs.value, qrhs.value))


def custom_summation(expr_node: ast.AST, var_node: ast.AST, start_node: ast.AST, end_node: ast.AST, env: dict[str, Any], file_name: str) -> Any:
    var_name = ast_name(var_node)
    start_value = ensure_quantity(evaluate_expression_in_env(ast.unparse(start_node), env, file_name))
    end_value = ensure_quantity(evaluate_expression_in_env(ast.unparse(end_node), env, file_name))
    if not dims_close(start_value.dims, end_value.dims):
        raise ValueError("Summation limits must have matching dimensions")
    if not dims_close(start_value.dims, ZERO_DIMS):
        raise ValueError("Summation limits must be dimensionless")
    start = int(round(float(start_value.value)))
    end = int(round(float(end_value.value)))
    step = 1 if end >= start else -1
    total: Any = Quantity(0.0, ZERO_DIMS)
    for idx in range(start, end + step, step):
        env[var_name] = Quantity(idx, ZERO_DIMS)
        total = total + ensure_quantity(evaluate_expression_in_env(ast.unparse(expr_node), env, file_name))
    env.pop(var_name, None)
    return total


def custom_product(expr_node: ast.AST, var_node: ast.AST, start_node: ast.AST, end_node: ast.AST, env: dict[str, Any], file_name: str) -> Any:
    var_name = ast_name(var_node)
    start_value = ensure_quantity(evaluate_expression_in_env(ast.unparse(start_node), env, file_name))
    end_value = ensure_quantity(evaluate_expression_in_env(ast.unparse(end_node), env, file_name))
    if not dims_close(start_value.dims, end_value.dims):
        raise ValueError("Product limits must have matching dimensions")
    if not dims_close(start_value.dims, ZERO_DIMS):
        raise ValueError("Product limits must be dimensionless")
    start = int(round(float(start_value.value)))
    end = int(round(float(end_value.value)))
    step = 1 if end >= start else -1
    total: Any = Quantity(1.0, ZERO_DIMS)
    for idx in range(start, end + step, step):
        env[var_name] = Quantity(idx, ZERO_DIMS)
        total = total * ensure_quantity(evaluate_expression_in_env(ast.unparse(expr_node), env, file_name))
    env.pop(var_name, None)
    return total


def custom_integral(expr_node: ast.AST, lower_node: ast.AST, upper_node: ast.AST, var_node: ast.AST, env: dict[str, Any], file_name: str) -> Any:
    var_name = ast_name(var_node)
    lower = ensure_quantity(evaluate_expression_in_env(ast.unparse(lower_node), env, file_name))
    upper = ensure_quantity(evaluate_expression_in_env(ast.unparse(upper_node), env, file_name))
    if not dims_close(lower.dims, upper.dims):
        raise ValueError("Integration limits must have matching dimensions")
    variable_dims = lower.dims

    def integrand(x: float) -> Any:
        env[var_name] = Quantity(x, variable_dims)
        result = ensure_quantity(evaluate_expression_in_env(ast.unparse(expr_node), env, file_name))
        return result.value

    result_value, _ = integrate.quad(lambda x: float(np.real(integrand(x))), float(lower.value), float(upper.value), limit=200)
    sample = ensure_quantity(evaluate_expression_in_env(ast.unparse(expr_node), {**env, var_name: Quantity(float(lower.value), variable_dims)}, file_name))
    return Quantity(result_value, add_dims(sample.dims, variable_dims))


def custom_derivative(expr_node: ast.AST, var_node: ast.AST, env: dict[str, Any], file_name: str, order: int = 1) -> Any:
    var_name = ast_name(var_node)
    current = env.get(var_name, Quantity(0.0, ZERO_DIMS))
    current_q = ensure_quantity(current)
    step = 1e-8 * max(1.0, abs(float(current_q.value)))
    dims = current_q.dims

    def f(x: float) -> Quantity:
        env[var_name] = Quantity(x, dims)
        return ensure_quantity(evaluate_expression_in_env(ast.unparse(expr_node), env, file_name))

    if order <= 0:
        return ensure_quantity(evaluate_expression_in_env(ast.unparse(expr_node), env, file_name))

    if order == 1:
        upper = f(float(current_q.value) + step)
        lower = f(float(current_q.value) - step)
        return Quantity((upper.value - lower.value) / (2 * step), sub_dims(upper.dims, dims))

    # recursive central differences for higher order derivatives
    def recurse(level: int, value: float) -> Quantity:
        if level == 1:
            upper = f(value + step)
            lower = f(value - step)
            return Quantity((upper.value - lower.value) / (2 * step), sub_dims(upper.dims, dims))
        upper = recurse(level - 1, value + step)
        lower = recurse(level - 1, value - step)
        return Quantity((upper.value - lower.value) / (2 * step), sub_dims(upper.dims, dims))

    return recurse(order, float(current_q.value))


def ast_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    raise ValueError("Expected a variable name")


def custom_add(lhs: Any, rhs: Any) -> Any:
    return maybe_symbolic_binary(lhs, rhs, "+", lambda a, b: a + b, add_dims)


def custom_multiply(lhs: Any, rhs: Any) -> Any:
    return maybe_symbolic_binary(lhs, rhs, "\\cdot", lambda a, b: a * b, add_dims)


def custom_mat_multiply(lhs: Any, rhs: Any) -> Any:
    if isinstance(lhs, np.ndarray) or isinstance(rhs, np.ndarray) or is_symbolic(lhs) or is_symbolic(rhs):
        left = matrix_value(lhs)
        right = matrix_value(rhs)
        if left.ndim == 0 or right.ndim == 0:
            return custom_multiply(left.item() if left.ndim == 0 else left, right.item() if right.ndim == 0 else right)
        if left.shape[1] != right.shape[0]:
            raise ValueError("Matrix dimension mismatch")
        result: list[list[Any]] = []
        for i in range(left.shape[0]):
            row: list[Any] = []
            for j in range(right.shape[1]):
                total: Any = None
                for k in range(left.shape[1]):
                    term = custom_multiply(left[i, k], right[k, j])
                    total = term if total is None else custom_add(total, term)
                row.append(total if total is not None else Quantity(0.0, ZERO_DIMS))
            result.append(row)
        return np.array(result, dtype=object)
    return lhs @ rhs


def get_eval_namespace(env: dict[str, Any], file_name: str) -> dict[str, Any]:
    namespace: dict[str, Any] = {
        "Quantity": Quantity,
        "Matrix": custom_matrix,
        "ones": custom_ones,
        "zeros": custom_zeros,
        "eye": custom_eye,
        "transpose": custom_transpose,
        "_Transpose": custom_transpose,
        "_Piecewise": custom_piecewise,
        "_Abs": custom_abs,
        "_factorial": custom_factorial,
        "_add": custom_add,
        "_multiply": custom_multiply,
        "_mat_multiply": custom_mat_multiply,
        "_summation": lambda expr, var, start, end: custom_summation(expr, var, start, end, env, file_name),
        "_product": lambda expr, var, start, end: custom_product(expr, var, start, end, env, file_name),
        "_Integral": lambda expr, lower, upper, var: custom_integral(expr, lower, upper, var, env, file_name),
        "_Derivative": lambda expr, var, order=1: custom_derivative(expr, var, env, file_name, int(round(float(order)))) if order is not None else custom_derivative(expr, var, env, file_name),
        "_IndefiniteIntegral": lambda expr, var: Quantity(float("nan"), ZERO_DIMS),
        "_Eq": custom_eq,
        "_StrictLessThan": lambda lhs, rhs: custom_compare(lhs, rhs, lambda a, b: a < b),
        "_LessThan": lambda lhs, rhs: custom_compare(lhs, rhs, lambda a, b: a <= b),
        "_StrictGreaterThan": lambda lhs, rhs: custom_compare(lhs, rhs, lambda a, b: a > b),
        "_GreaterThan": lambda lhs, rhs: custom_compare(lhs, rhs, lambda a, b: a >= b),
        "_aasin": custom_inverse_trig(np.arcsin),
        "_aacos": custom_inverse_trig(np.arccos),
        "_aatan": custom_inverse_trig(np.arctan),
        "_aacsc": custom_inverse_trig(lambda x: np.arcsin(1 / x)),
        "_aacot": custom_inverse_trig(lambda x: np.arctan(1 / x)),
        "_aasec": custom_inverse_trig(lambda x: np.arccos(1 / x)),
        "sin": custom_trig(np.sin),
        "cos": custom_trig(np.cos),
        "tan": custom_trig(np.tan),
        "sinh": custom_trig(np.sinh),
        "cosh": custom_trig(np.cosh),
        "tanh": custom_trig(np.tanh),
        "asin": custom_inverse_trig(np.arcsin),
        "acos": custom_inverse_trig(np.arccos),
        "atan": custom_inverse_trig(np.arctan),
        "acsc": custom_inverse_trig(lambda x: np.arcsin(1 / x)),
        "acot": custom_inverse_trig(lambda x: np.arctan(1 / x)),
        "asec": custom_inverse_trig(lambda x: np.arccos(1 / x)),
        "exp": custom_exp,
        "log": custom_log,
        "sqrt": custom_sqrt,
        "_factorial": custom_factorial,
        "floor": custom_floor,
        "ceiling": custom_ceiling,
        "sign": custom_sign,
        "Abs": custom_abs,
        "abs": custom_abs,
        "re": custom_re,
        "im": custom_im,
        "conjugate": custom_conjugate,
        "arg": custom_arg,
        "max": custom_max,
        "min": custom_min,
        "pi": math.pi,
        "E": math.e,
        "e": math.e,
        "I": 1j,
        "nan": float("nan"),
        "inf": float("inf"),
        "linalg": linalg,
        "np": np,
        "numpy": np,
        "interpolate": interpolate,
        "integrate": integrate,
        "optimize": optimize,
        "math": math,
        "cmath": cmath,
    }
    namespace.update(env)
    for name, value in env.items():
        if not name.endswith("_as_variable"):
            namespace[f"{name}_as_variable"] = value
    return namespace


def eval_node(node: ast.AST, env: dict[str, Any], file_name: str) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        if node.id in env:
            return env[node.id]
        alias = symbolic_name(node.id)
        if alias in env:
            return env[alias]
        if node.id == "pi":
            return Quantity(math.pi, ZERO_DIMS)
        if node.id == "E":
            return Quantity(math.e, ZERO_DIMS)
        if node.id == "I":
            return Quantity(1j, ZERO_DIMS)
        if node.id == "True":
            return True
        if node.id == "False":
            return False
        if node.id == "None":
            return None
        return make_symbolic(symbolic_name(node.id))
    if isinstance(node, ast.Tuple):
        return tuple(eval_node(elt, env, file_name) for elt in node.elts)
    if isinstance(node, ast.List):
        values = [eval_node(elt, env, file_name) for elt in node.elts]
        if any(isinstance(value, (list, tuple, np.ndarray)) for value in values):
            return np.array(values, dtype=object)
        return np.array(values, dtype=object)
    if isinstance(node, ast.Dict):
        return {eval_node(key, env, file_name): eval_node(value, env, file_name) for key, value in zip(node.keys, node.values)}
    if isinstance(node, ast.UnaryOp):
        operand = eval_node(node.operand, env, file_name)
        if isinstance(node.op, ast.USub):
            return -ensure_quantity(operand) if not isinstance(operand, bool) else -operand
        if isinstance(node.op, ast.UAdd):
            return operand
        if isinstance(node.op, ast.Not):
            return not bool(operand)
        if isinstance(node.op, ast.Invert):
            return ~operand
        raise NotImplementedError(type(node.op).__name__)
    if isinstance(node, ast.BinOp):
        left = eval_node(node.left, env, file_name)
        right = eval_node(node.right, env, file_name)
        if is_symbolic(left) or is_symbolic(right):
            if isinstance(node.op, ast.Add):
                return maybe_symbolic_binary(left, right, "+", lambda a, b: a + b, add_dims)
            if isinstance(node.op, ast.Sub):
                return maybe_symbolic_binary(left, right, "-", lambda a, b: a - b, subtract_dims)
            if isinstance(node.op, ast.Mult):
                return maybe_symbolic_binary(left, right, "\\cdot", lambda a, b: a * b, add_dims)
            if isinstance(node.op, ast.Div):
                return maybe_symbolic_binary(left, right, "/", lambda a, b: a / b, subtract_dims)
            if isinstance(node.op, ast.Pow):
                if is_symbolic(right):
                    return make_symbolic(rf"{symbolic_latex(left)}^{{{symbolic_latex(right)}}}")
                exponent = ensure_quantity(right).value if isinstance(right, Quantity) else right
                return make_symbolic(rf"{symbolic_latex(left)}^{{{symbolic_latex(right)}}}", scale_dims(symbolic_dims(left), float(exponent)))
            if isinstance(node.op, ast.MatMult):
                return custom_mat_multiply(left, right)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / right
        if isinstance(node.op, ast.Pow):
            return left ** right
        if isinstance(node.op, ast.Mod):
            return ensure_quantity(left).value % ensure_quantity(right).value
        if isinstance(node.op, ast.MatMult):
            return matrix_value(left) @ matrix_value(right)
        raise NotImplementedError(type(node.op).__name__)
    if isinstance(node, ast.BoolOp):
        values = [bool(eval_node(value, env, file_name)) for value in node.values]
        if isinstance(node.op, ast.And):
            return all(values)
        if isinstance(node.op, ast.Or):
            return any(values)
        raise NotImplementedError(type(node.op).__name__)
    if isinstance(node, ast.Compare):
        left = eval_node(node.left, env, file_name)
        for op, comparator in zip(node.ops, node.comparators):
            right = eval_node(comparator, env, file_name)
            if isinstance(op, ast.Eq):
                if not custom_eq(left, right):
                    return False
            elif isinstance(op, ast.NotEq):
                if custom_eq(left, right):
                    return False
            elif isinstance(op, ast.Lt):
                if not custom_compare(left, right, lambda a, b: a < b):
                    return False
            elif isinstance(op, ast.LtE):
                if not custom_compare(left, right, lambda a, b: a <= b):
                    return False
            elif isinstance(op, ast.Gt):
                if not custom_compare(left, right, lambda a, b: a > b):
                    return False
            elif isinstance(op, ast.GtE):
                if not custom_compare(left, right, lambda a, b: a >= b):
                    return False
            else:
                raise NotImplementedError(type(op).__name__)
            left = right
        return True
    if isinstance(node, ast.IfExp):
        return eval_node(node.body, env, file_name) if bool(eval_node(node.test, env, file_name)) else eval_node(node.orelse, env, file_name)
    if isinstance(node, ast.Subscript):
        value = eval_node(node.value, env, file_name)
        index = eval_slice(node.slice, env, file_name)
        return value[index]
    if isinstance(node, ast.Attribute):
        value = eval_node(node.value, env, file_name)
        return getattr(value, node.attr)
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            if func_name == "_Integral":
                return custom_integral(node.args[0], node.args[1], node.args[2], node.args[3], env, file_name)
            if func_name == "_Derivative":
                if len(node.args) == 2:
                    return custom_derivative(node.args[0], node.args[1], env, file_name, 1)
                order = int(round(float(ensure_quantity(eval_node(node.args[2], env, file_name)).value)))
                return custom_derivative(node.args[0], node.args[1], env, file_name, order)
            if func_name == "_IndefiniteIntegral":
                return Quantity(float("nan"), ZERO_DIMS)
            if func_name == "_summation":
                return custom_summation(node.args[0], node.args[1], node.args[2], node.args[3], env, file_name)
            if func_name == "_product":
                return custom_product(node.args[0], node.args[1], node.args[2], node.args[3], env, file_name)
            if func_name == "_Piecewise":
                return custom_piecewise(*[eval_node(arg, env, file_name) for arg in node.args])
            if func_name == "_Eq":
                return custom_eq(eval_node(node.args[0], env, file_name), eval_node(node.args[1], env, file_name))
            if func_name in {"_StrictLessThan", "_LessThan", "_StrictGreaterThan", "_GreaterThan"}:
                comparator = {
                    "_StrictLessThan": lambda a, b: a < b,
                    "_LessThan": lambda a, b: a <= b,
                    "_StrictGreaterThan": lambda a, b: a > b,
                    "_GreaterThan": lambda a, b: a >= b,
                }[func_name]
                return custom_compare(eval_node(node.args[0], env, file_name), eval_node(node.args[1], env, file_name), comparator)
        func = eval_node(node.func, env, file_name)
        args = [eval_node(arg, env, file_name) for arg in node.args]
        kwargs = {kw.arg: eval_node(kw.value, env, file_name) for kw in node.keywords}
        if is_symbolic(func) or not callable(func):
            arg_text = ", ".join(symbolic_latex(arg) for arg in args)
            if kwargs:
                kw_text = ", ".join(f"{key}={symbolic_latex(value)}" for key, value in kwargs.items())
                arg_text = ", ".join(filter(None, [arg_text, kw_text]))
            return make_symbolic(rf"{symbolic_latex(func)}\left({arg_text}\right)")
        return func(*args, **kwargs)
    raise NotImplementedError(type(node).__name__)


def eval_slice(node: ast.AST, env: dict[str, Any], file_name: str) -> Any:
    if isinstance(node, ast.Slice):
        return slice(
            eval_node(node.lower, env, file_name) if node.lower else None,
            eval_node(node.upper, env, file_name) if node.upper else None,
            eval_node(node.step, env, file_name) if node.step else None,
        )
    if isinstance(node, ast.Tuple):
        return tuple(eval_node(elt, env, file_name) for elt in node.elts)
    return eval_node(node, env, file_name)


def eval_expression(expr: str, env: dict[str, Any], file_name: str = "<expr>") -> Any:
    parsed = ast.parse(expr, mode="eval")
    return eval_node(parsed.body, env, file_name)


def convert_from_SI(dims: dict[str, Any], value: Any) -> Any:
    if dims["type"] in {"any", "dummy", "render"}:
        return value
    offset = float(dims["offset"])
    scale_factor = float(dims["scaleFactor"])
    if isinstance(value, np.ndarray):
        if offset == 0.0:
            return value / scale_factor
        return (value / scale_factor) - offset
    if offset == 0.0:
        return value / scale_factor
    return (value / scale_factor) - offset


def convert_to_SI(dims: dict[str, Any], value: Any) -> Any:
    if dims["type"] in {"any", "dummy", "render"}:
        return value
    offset = float(dims["offset"])
    scale_factor = float(dims["scaleFactor"])
    if isinstance(value, np.ndarray):
        if offset == 0.0:
            return value * scale_factor
        return (value + offset) * scale_factor
    if offset == 0.0:
        return value * scale_factor
    return (value + offset) * scale_factor


class ImplicitParameter(TypedDict):
    name: str
    units: str
    dimensions: list[float]
    original_value: str
    si_value: str


class BaseUserFunction(TypedDict):
    type: str
    name: str
    expression: str
    params: list[str]
    isFunctionArgument: bool
    isFunction: bool
    functionParameters: list[str]
    index: int


class UserFunction(BaseUserFunction):
    isRange: bool


class UserFunctionRange(BaseUserFunction):
    isRange: bool
    freeParameter: str
    lowerLimitArgument: str
    lowerLimitInclusive: bool
    upperLimitArgument: str
    upperLimitInclusive: bool
    unitsQueryFunction: str


class FunctionUnitsQuery(TypedDict):
    type: str
    expression: str
    params: list[str]
    units: str
    isFunctionArgument: bool
    isFunction: bool
    isUnitsQuery: bool
    isRange: bool
    isDataTableQuery: bool
    isCodeFunctionQuery: bool
    isCodeFunctionRawQuery: bool
    index: int


class LocalSubstitution(TypedDict):
    type: str
    parameter: str
    argument: str
    isRange: bool
    function: str


class QueryAssignmentCommon(TypedDict):
    expression: str
    implicitParams: list[ImplicitParameter]
    functions: list[UserFunction | UserFunctionRange | FunctionUnitsQuery]
    arguments: list[Any]
    localSubs: list[Any]
    params: list[str]
    variableNameMap: dict[str, str]
    index: int


class AssignmentStatement(QueryAssignmentCommon):
    type: str
    name: str
    isFunctionArgument: bool
    isFunction: bool
    isFromPlotCell: bool
    isDataTableQuery: bool
    isCodeFunctionQuery: bool
    isCodeFunctionRawQuery: bool
    isRange: bool


class SystemSolutionAssignmentStatement(AssignmentStatement):
    display: str
    displayName: str


class BaseQueryStatement(QueryAssignmentCommon):
    type: str
    isFunctionArgument: bool
    isFunction: bool
    isUnitsQuery: bool
    isEqualityUnitsQuery: bool
    isFromPlotCell: bool
    units: str
    unitsLatex: str


class QueryStatement(BaseQueryStatement):
    isRange: bool
    isDataTableQuery: bool
    isCodeFunctionQuery: bool
    isCodeFunctionRawQuery: bool
    isSubQuery: bool


class RangeQueryStatement(BaseQueryStatement):
    isRange: bool
    isParametric: bool
    isDataTableQuery: bool
    isCodeFunctionQuery: bool
    isCodeFunctionRawQuery: bool
    isSubQuery: bool
    cellNum: int
    numPoints: int
    freeParameter: str
    lowerLimitArgument: str
    lowerLimitInclusive: bool
    upperLimitArgument: str
    upperLimitInclusive: bool
    logX: bool
    unitsQueryFunction: str
    inputUnits: str
    inputUnitsLatex: str
    outputName: str


class ScatterQueryStatement(TypedDict):
    type: str
    asLines: bool
    equationIndex: int
    cellNum: int
    isFromPlotCell: bool
    params: list[str]
    variableNameMap: dict[str, str]
    functions: list[Any]
    arguments: list[Any]
    localSubs: list[Any]
    implicitParams: list[ImplicitParameter]
    xValuesQuery: Any
    yValuesQuery: Any
    xName: str
    yName: str
    units: str
    unitsLatex: str
    inputUnits: str
    inputUnitsLatex: str
    index: int


class CodeFunctionRawQuery(BaseQueryStatement):
    isRange: bool
    isDataTableQuery: bool
    isCodeFunctionQuery: bool
    isCodeFunctionRawQuery: bool


class CodeFunctionQueryStatement(BaseQueryStatement):
    isRange: bool
    isDataTableQuery: bool
    isCodeFunctionQuery: bool
    isCodeFunctionRawQuery: bool
    functionName: str
    parameterNames: list[str]
    parameterValues: list[str]
    parameterUnits: list[str]
    generateCode: bool
    codeFunctionRawQuery: CodeFunctionRawQuery


class EqualityUnitsQueryStatement(QueryAssignmentCommon):
    type: str
    isRange: bool
    isDataTableQuery: bool
    isCodeFunctionQuery: bool
    isCodeFunctionRawQuery: bool
    isFunctionArgument: bool
    isFunction: bool
    isUnitsQuery: bool
    isEqualityUnitsQuery: bool
    isFromPlotCell: bool
    units: str
    equationIndex: int


class EqualityStatement(QueryAssignmentCommon):
    type: str
    isFunctionArgument: bool
    isFunction: bool
    isFromPlotCell: bool
    isRange: bool
    isDataTableQuery: bool
    isCodeFunctionQuery: bool
    isCodeFunctionRawQuery: bool
    equationIndex: int
    equalityUnitsQueries: list[EqualityUnitsQueryStatement]


class GuessAssignmentStatement(AssignmentStatement):
    guess: str


class ExactSystemDefinition(TypedDict):
    statements: list[EqualityStatement]
    variables: list[str]
    selectedSolution: int
    numericalSolve: bool


class NumericalSystemDefinition(TypedDict):
    statements: list[EqualityStatement]
    variables: list[str]
    selectedSolution: int
    numericalSolve: bool
    guesses: list[str]
    guessStatements: list[GuessAssignmentStatement]


class FluidFunction(TypedDict):
    name: str
    fluid: str
    output: str
    outputDims: list[float]
    input1: str
    input1Dims: list[float]
    input2: str
    input2Dims: list[float]
    input3: NotRequired[str]
    input3Dims: NotRequired[list[float]]


class InterpolationFunction(TypedDict):
    type: str
    name: str
    numInputs: int
    inputValues: list[list[float]]
    outputValues: list[float]
    inputDims: list[list[float]]
    outputDims: list[float]
    order: int


class GridInterpolationFunction(TypedDict):
    type: str
    name: str
    numInputs: int
    inputValues: list[list[float]]
    outputValues: list[list[float]]
    inputDims: list[list[float]]
    outputDims: list[float]
    order: int


class CustomBaseUnits(TypedDict):
    mass: str
    length: str
    time: str
    current: str
    temperature: str
    luminous_intensity: str
    amount_of_substance: str
    force: str
    area: str
    volume: str
    energy: str
    power: str
    pressure: str
    charge: str
    capacitance: str
    electric_potential: str
    resistance: str
    inductance: str
    conductance: str
    magnetic_flux: str
    magnetic_flux_density: str
    angle: str
    information: str


class CodeCellDimsAny(TypedDict):
    type: str


class CodeCellDimsDummy(TypedDict):
    type: str


class CodeCellDimsRender(TypedDict):
    type: str
    renderType: str


class CodeCellDimsSpecific(TypedDict):
    type: str
    dims: list[float]
    offset: float
    scaleFactor: float


CodeCellDims = CodeCellDimsSpecific | CodeCellDimsAny | CodeCellDimsRender | CodeCellDimsDummy


class ScalarCodeCellDims(TypedDict):
    type: str
    dims: CodeCellDims


class MatrixCodeCellDims(TypedDict):
    type: str
    dims: list[list[CodeCellDimsSpecific | CodeCellDimsAny]]


CodeCellInputOutputDims = ScalarCodeCellDims | MatrixCodeCellDims


class CodeCellFunction(TypedDict):
    name: str
    code: str
    inputDims: list[CodeCellInputOutputDims]
    outputDims: CodeCellInputOutputDims
    neededPyodidePackages: list[str]


class CodeCellError(TypedDict):
    message: str
    startLine: int | None
    endLine: int | None
    startCol: int | None
    endCol: int | None


class CodeCellResult(TypedDict):
    stdout: str
    errors: list[CodeCellError]


class Result(TypedDict):
    value: str
    symbolicValue: NotRequired[str]
    units: str
    unitsLatex: str
    customUnitsDefined: bool
    customUnits: str
    customUnitsLatex: str
    numeric: bool
    real: bool
    finite: bool
    generatedCode: NotRequired[str]
    isSubResult: NotRequired[bool]
    subQueryName: NotRequired[str]


class FiniteImagResult(TypedDict):
    value: str
    symbolicValue: NotRequired[str]
    realPart: str
    imagPart: str
    units: str
    unitsLatex: str
    customUnitsDefined: bool
    customUnits: str
    customUnitsLatex: str
    numeric: bool
    real: bool
    finite: bool
    generatedCode: NotRequired[str]
    isSubResult: NotRequired[bool]
    subQueryName: NotRequired[str]


class MatrixResult(TypedDict):
    matrixResult: bool
    results: list[list[Result | FiniteImagResult]]
    generatedCode: NotRequired[str]
    isSubResult: NotRequired[bool]
    subQueryName: NotRequired[str]


class DataTableResult(TypedDict):
    dataTableResult: bool
    colData: dict[int, MatrixResult]


class PlotData(TypedDict):
    numericOutput: bool
    numericInput: bool
    limitsUnitsMatch: bool
    input: list[float]
    output: list[float]
    inputReversed: bool
    inputUnits: str
    inputUnitsLatex: str
    inputName: str
    outputUnits: str
    outputUnitsLatex: str
    outputName: str
    isScatter: bool


class PlotResult(TypedDict):
    plot: bool
    data: list[PlotData]


class SystemResult(TypedDict):
    error: str | None
    solutions: dict[str, list[str]]
    selectedSolution: int


class RenderResult(TypedDict):
    renderResult: bool
    type: str
    value: str
    dimensionError: str


class Results(TypedDict):
    error: str | None
    results: list[Any]
    systemResults: list[SystemResult]
    codeCellResults: dict[str, CodeCellResult]


class StatementsAndSystems(TypedDict):
    statements: list[Any]
    systemDefinitions: list[Any]
    fluidFunctions: list[FluidFunction]
    codeCellFunctions: list[CodeCellFunction]
    interpolationFunctions: list[Any]
    customBaseUnits: NotRequired[CustomBaseUnits]


class CodeCellResultCollector(TypedDict):
    buffer: io.StringIO
    exceptions: list[Exception]


def make_error(message: str) -> Results:
    return {
        "error": message,
        "results": [],
        "systemResults": [],
        "codeCellResults": {},
    }


def wrap_code_cell_function(func: Callable, buffer: io.StringIO, exceptions: list[Exception]) -> Callable:
    def wrapped_func(*args: Any, **kwargs: Any):
        stdout = sys.stdout
        sys.stdout = buffer
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            exceptions.append(exc)
            raise
        finally:
            sys.stdout = stdout

    return wrapped_func


def compile_code_cell_function(code_cell_function: CodeCellFunction,
                               code_cell_result_store: dict[str, CodeCellResultCollector]) -> Callable:
    name = code_cell_function["name"]
    exceptions: list[Exception] = []
    buffer = io.StringIO()
    code_cell_result_store[name] = {"buffer": buffer, "exceptions": exceptions}

    code_globals: dict[str, Any] = {
        "__builtins__": {
            "abs": abs,
            "min": min,
            "max": max,
            "sum": sum,
            "range": range,
            "len": len,
            "enumerate": enumerate,
            "zip": zip,
            "float": float,
            "int": int,
            "bool": bool,
            "complex": complex,
            "list": list,
            "tuple": tuple,
            "dict": dict,
            "set": set,
            "print": print,
        },
        "np": np,
        "numpy": np,
        "math": math,
        "cmath": cmath,
        "linalg": linalg,
        "interpolate": interpolate,
        "integrate": integrate,
        "optimize": optimize,
        "coolprop": coolprop,
    }

    try:
        code_object = compile(code_cell_function["code"], name, "exec")
        with contextlib.redirect_stdout(buffer):
            exec(code_object, code_globals)
        code_func = code_globals.get("calculate")
        if not callable(code_func):
            raise ValueError('The code cell must define a function called "calculate"')
    except Exception as exc:
        exceptions.append(exc)
        raise

    return wrap_code_cell_function(code_func, buffer, exceptions)


def check_code_cell_input(value: Any, input_num: int, dims: CodeCellInputOutputDims, name: str) -> None:
    if dims["type"] == "scalar":
        if dims["dims"]["type"] == "specific":
            if is_matrix(value):
                values = value.flat
            else:
                values = [value]
            expected_dims = tuple(float(x) for x in dims["dims"]["dims"])
            for item in values:
                quantity = ensure_quantity(item)
                if not dims_close(quantity.dims, expected_dims):
                    raise ValueError(f"Incorrect units for input number {input_num + 1} of code cell function {name}")
    else:
        if not is_matrix(value):
            raise TypeError(f"Matrix or vector expected for input number {input_num + 1} of code cell function {name}")
        expected_shape = (len(dims["dims"]), len(dims["dims"][0]))
        if value.shape == expected_shape:
            for i, row in enumerate(dims["dims"]):
                for j, dim in enumerate(row):
                    if dim["type"] == "specific":
                        if not dims_close(ensure_quantity(value[i, j]).dims, tuple(float(x) for x in dim["dims"])):
                            raise ValueError(f"Incorrect units at (row={i + 1}, col={j + 1}) for input number {input_num + 1} of code cell function {name}")
        else:
            if expected_shape[1] == 1 and expected_shape[0] == value.shape[0]:
                for i, row in enumerate(dims["dims"]):
                    dim = row[0]
                    if dim["type"] == "specific":
                        for item in value[i, :]:
                            if not dims_close(ensure_quantity(item).dims, tuple(float(x) for x in dim["dims"])):
                                raise ValueError(f"Incorrect units for input number {input_num + 1} of code cell function {name}")
            elif expected_shape[0] == 1 and expected_shape[1] == value.shape[1]:
                for j, row in enumerate(dims["dims"][0]):
                    if row["type"] == "specific":
                        for item in value[:, j]:
                            if not dims_close(ensure_quantity(item).dims, tuple(float(x) for x in row["dims"])):
                                raise ValueError(f"Incorrect units for input number {input_num + 1} of code cell function {name}")
            else:
                raise TypeError(f"Incorrect matrix or vector size for input number {input_num + 1} of code cell function {name}")


def code_cell_dims_check(*inputs: Any, code_cell_function: CodeCellFunction) -> tuple[float, ...] | np.ndarray:
    dims = code_cell_function["outputDims"]
    name = code_cell_function["name"]
    num_spec_dims = len(code_cell_function["inputDims"])
    for i, value in enumerate(inputs):
        if num_spec_dims == 1:
            check_code_cell_input(value, i, code_cell_function["inputDims"][0], name)
        else:
            check_code_cell_input(value, i, code_cell_function["inputDims"][i], name)

    if dims["type"] == "scalar":
        if dims["dims"]["type"] == "render":
            return ZERO_DIMS
        if dims["dims"]["type"] == "specific":
            return tuple(float(x) for x in dims["dims"]["dims"])
        return ZERO_DIMS

    output_rows: list[list[tuple[float, ...]]] = []
    for row in dims["dims"]:
        current_row: list[tuple[float, ...]] = []
        for dim in row:
            if dim["type"] != "specific":
                raise TypeError(f"Return type of [any], [text], [html], or [markdown] cannot be used within a matrix output specification, the code cell function {name}")
            current_row.append(tuple(float(x) for x in dim["dims"]))
        output_rows.append(current_row)
    return np.array(output_rows, dtype=object)


def to_numeric_matrix(value: Any) -> np.ndarray:
    if isinstance(value, np.ndarray):
        return value.astype(object, copy=False)
    if isinstance(value, (list, tuple)):
        return np.array(value, dtype=object)
    return np.array([[value]], dtype=object)


def convert_input_value(dims: CodeCellDims, value: Any) -> Any:
    if dims["type"] in {"any", "dummy"}:
        return value
    if dims["type"] == "render":
        raise ValueError("[text], [html], or [markdown] types not allowed for input arguments of code cell")
    return convert_from_SI(dims, value)


def wrap_output_value(dims: CodeCellDims, value: Any) -> Any:
    if dims["type"] in {"any", "dummy"}:
        return value
    if dims["type"] == "render":
        raise ValueError("[text], [html], or [markdown] types not allowed for input arguments of code cell")
    return convert_to_SI(dims, value)


def get_code_cell_wrapper(code_cell_function: CodeCellFunction,
                          code_cell_result_store: dict[str, CodeCellResultCollector]) -> Callable:
    code_func = compile_code_cell_function(code_cell_function, code_cell_result_store)
    name = code_cell_function["name"]

    def implementation(*args: Any) -> Any:
        if len(args) != len(code_cell_function["inputDims"]):
            raise ValueError(
                f'Number of input arguments provided to code function "{name}" ({len(args)}) differs from the number of arguments specified in the code function definition ({len(code_cell_function["inputDims"])})'
            )
        converted_args: list[Any] = []
        for input_num, arg in enumerate(args):
            input_dims = code_cell_function["inputDims"][input_num]
            if input_dims["type"] == "scalar":
                converted_args.append(convert_input_value(input_dims["dims"], arg))
            else:
                matrix = to_numeric_matrix(arg)
                converted_matrix = np.array(matrix, dtype=object)
                for i, row in enumerate(input_dims["dims"]):
                    for j, dim in enumerate(row):
                        if dim["type"] == "specific":
                            converted_matrix[i, j] = convert_from_SI({"type": "specific", "offset": dim["offset"], "scaleFactor": dim["scaleFactor"]}, converted_matrix[i, j])
                converted_args.append(converted_matrix)
        result = code_func(*converted_args)
        output_dims = code_cell_function["outputDims"]
        if isinstance(result, str):
            if output_dims["type"] == "scalar" and output_dims["dims"]["type"] == "render":
                return RenderExpr(output_dims["dims"]["renderType"], result)
            raise ValueError(
                f"The code cell function {name} returns a string value where a numerical value is expected. Specify an output type of [text], [html], or [markdown] to render string output."
            )

        if output_dims["type"] == "scalar":
            if isinstance(result, (list, tuple, np.ndarray)):
                array = np.array(result, dtype=object)
                if array.ndim == 1:
                    array = array.reshape((-1, 1))
                if array.ndim != 2:
                    raise ValueError(f"Output of code cell function {name} must be scalar value or a 2D matrix.")
                converted = np.array(array, dtype=object)
                for index, item in np.ndenumerate(converted):
                    converted[index] = Quantity(convert_to_SI(output_dims["dims"], item), tuple(float(x) for x in output_dims["dims"]["dims"])) if output_dims["dims"]["type"] == "specific" else convert_to_SI(output_dims["dims"], item)
                return converted
            converted_scalar = wrap_output_value(output_dims["dims"], result)
            if output_dims["dims"]["type"] == "specific":
                return Quantity(converted_scalar, tuple(float(x) for x in output_dims["dims"]["dims"]))
            return converted_scalar

        array_result = to_numeric_matrix(result)
        if array_result.ndim == 1:
            array_result = array_result.reshape((-1, 1))
        expected_shape = (len(output_dims["dims"]), len(output_dims["dims"][0]))
        if array_result.shape != expected_shape:
            if expected_shape[1] == 1 and expected_shape[0] == array_result.shape[0]:
                array_result = array_result.reshape(expected_shape)
            elif expected_shape[0] == 1 and expected_shape[1] == array_result.shape[1]:
                array_result = array_result.reshape(expected_shape)
            else:
                raise ValueError(f"Incorrect matrix or vector size for output of code cell function {name}")
        wrapped = np.array(array_result, dtype=object)
        for i, row in enumerate(output_dims["dims"]):
            for j, dim in enumerate(row):
                if dim["type"] != "specific":
                    raise ValueError(f"Return type of [any], [text], [html], or [markdown] cannot be used within a matrix output specification, the code cell function {name}")
                wrapped[i, j] = Quantity(convert_to_SI(dim, wrapped[i, j]), tuple(float(x) for x in dim["dims"]))
        return wrapped

    return implementation


def get_code_cell_result_store(code_cell_functions: list[CodeCellFunction]) -> tuple[dict[str, Callable], dict[str, CodeCellResultCollector]]:
    result_store: dict[str, CodeCellResultCollector] = {}
    wrappers: dict[str, Callable] = {}
    for code_cell_function in code_cell_functions:
        wrappers[code_cell_function["name"]] = get_code_cell_wrapper(code_cell_function, result_store)
    return wrappers, result_store


def collect_code_cell_results(code_cell_result_store: dict[str, CodeCellResultCollector]) -> dict[str, CodeCellResult]:
    result: dict[str, CodeCellResult] = {}
    for code_function, collection in code_cell_result_store.items():
        stdout = collection["buffer"].getvalue()
        collection["buffer"].close()
        errors: list[CodeCellError] = []
        for error in collection["exceptions"]:
            if isinstance(error, SyntaxError):
                errors.append({
                    "message": str(error),
                    "startLine": error.lineno,
                    "endLine": error.end_lineno,
                    "startCol": error.offset - 1 if error.offset else None,
                    "endCol": error.end_offset - 1 if error.end_offset else None,
                })
            else:
                tb = traceback.extract_tb(error.__traceback__)
                matching = [frame for frame in tb if frame.filename == code_function]
                if matching:
                    frame = matching[-1]
                    errors.append({
                        "message": f"{type(error).__name__}: {error}",
                        "startLine": frame.lineno,
                        "endLine": frame.end_lineno,
                        "startCol": frame.colno,
                        "endCol": frame.end_colno,
                    })
                else:
                    errors.append({
                        "message": f"{type(error).__name__}: {error}",
                        "startLine": None,
                        "endLine": None,
                        "startCol": None,
                        "endCol": None,
                    })
        result[code_function] = {"stdout": stdout, "errors": errors}
    return result


def make_result_from_value(value: Any, custom_base_units: dict[str, str] | None = None) -> Result | FiniteImagResult | MatrixResult | RenderResult:
    if isinstance(value, RenderExpr):
        return {
            "renderResult": True,
            "type": value.render_type,
            "value": value.render_value,
            "dimensionError": "",
        }
    if isinstance(value, SymbolicValue):
        units = dims_to_units(value.dims, custom_base_units)
        units_latex = format_units_latex(units)
        return {
            "value": value.latex,
            "symbolicValue": value.latex,
            "units": units,
            "unitsLatex": units_latex,
            "customUnitsDefined": False,
            "customUnits": "",
            "customUnitsLatex": "",
            "numeric": False,
            "real": True,
            "finite": True,
        }

    if isinstance(value, np.ndarray):
        matrix = value.astype(object, copy=False)
        if matrix.ndim == 1:
            matrix = matrix.reshape((-1, 1))
        rows: list[list[Result | FiniteImagResult]] = []
        for row in matrix:
            current_row: list[Result | FiniteImagResult] = []
            for cell in row:
                current_row.append(cast(Result | FiniteImagResult, make_result_from_value(cell, custom_base_units)))
            rows.append(current_row)
        return {"matrixResult": True, "results": rows}

    if isinstance(value, Quantity):
        numeric_value = value.value
        units = dims_to_units(value.dims, custom_base_units)
        units_latex = format_units_latex(units)
    else:
        numeric_value = value
        units = ""
        units_latex = ""

    if isinstance(numeric_value, np.generic):
        numeric_value = numeric_value.item()

    if isinstance(numeric_value, bool):
        return {
            "value": "True" if numeric_value else "False",
            "units": units,
            "unitsLatex": units_latex,
            "customUnitsDefined": False,
            "customUnits": "",
            "customUnitsLatex": "",
            "numeric": False,
            "real": True,
            "finite": True,
        }

    if isinstance(numeric_value, complex):
        if abs(numeric_value.imag) < 1e-15:
            numeric_value = float(numeric_value.real)
        else:
            return {
                "value": format_number(numeric_value),
                "realPart": format_number(numeric_value.real),
                "imagPart": format_number(numeric_value.imag),
                "units": units,
                "unitsLatex": units_latex,
                "customUnitsDefined": False,
                "customUnits": "",
                "customUnitsLatex": "",
                "numeric": True,
                "real": False,
                "finite": True,
            }

    if isinstance(numeric_value, (int, float, np.floating)):
        finite = bool(np.isfinite(numeric_value))
        return {
            "value": format_number(numeric_value),
            "units": units,
            "unitsLatex": units_latex,
            "customUnitsDefined": False,
            "customUnits": "",
            "customUnitsLatex": "",
            "numeric": True,
            "real": True,
            "finite": finite,
        }

    return {
        "value": str(numeric_value),
        "units": units,
        "unitsLatex": units_latex,
        "customUnitsDefined": False,
        "customUnits": "",
        "customUnitsLatex": "",
        "numeric": False,
        "real": True,
        "finite": True,
    }


def evaluate_expression_in_env(expression: str, env: dict[str, Any], file_name: str = "<expr>") -> Any:
    namespace = get_eval_namespace(env, file_name)
    parsed = ast.parse(expression, mode="eval")
    return eval_node(parsed.body, namespace, file_name)


def prepare_statement_env(statement: dict[str, Any], base_env: dict[str, Any]) -> dict[str, Any]:
    statement_env = dict(base_env)

    for implicit_param in statement.get("implicitParams", []):
        dims = tuple(float(x) for x in implicit_param["dimensions"])
        statement_env[implicit_param["name"]] = Quantity(float(implicit_param["si_value"]), dims)

    for function_def in statement.get("functions", []):
        function_name = function_def["name"]
        parameter_names = list(function_def.get("functionParameters", []))

        def function_wrapper(*args: Any, _function=function_def, _parameter_names=parameter_names) -> Any:
            if len(args) != len(_parameter_names):
                raise ValueError(
                    f'Number of input arguments provided to function "{function_name}" ({len(args)}) differs from the number of arguments specified in the function definition ({len(_parameter_names)})'
                )
            local_env = dict(statement_env)
            for parameter_name, argument in zip(_parameter_names, args):
                local_env[parameter_name] = argument if isinstance(argument, (Quantity, np.ndarray, RenderExpr)) else ensure_quantity(argument)
            return evaluate_expression_in_env(_function["expression"], local_env, function_name)

        statement_env[function_name] = function_wrapper

    for argument_def in statement.get("arguments", []):
        if argument_def.get("type") == "assignment" and "name" in argument_def:
            try:
                statement_env[argument_def["name"]] = evaluate_expression_in_env(argument_def["expression"], statement_env, argument_def["name"])
            except Exception:
                pass

    for local_sub in statement.get("localSubs", []):
        parameter = local_sub.get("parameter")
        argument = local_sub.get("argument")
        if parameter and argument and argument in statement_env:
            statement_env[parameter] = statement_env[argument]

    return statement_env


def solve_linear_system_from_equations(
    statements: list[EqualityStatement],
    variables: list[str],
    env: dict[str, Any],
    file_name: str,
) -> tuple[str | None, list[dict[str, Any]], dict[str, list[str]]]:
    def residuals(values: np.ndarray) -> np.ndarray:
        local_env = dict(env)
        for name, value in zip(variables, values):
            local_env[name] = Quantity(float(value), ZERO_DIMS)
        residual_list: list[float] = []
        for statement in statements:
            statement_env = prepare_statement_env(cast(dict[str, Any], statement), local_env)
            expr = statement["expression"]
            if expr.startswith("_Eq(") and expr.endswith(")"):
                inner = expr[4:-1]
                lhs_expr, rhs_expr = split_top_level_args(inner)
                lhs = ensure_quantity(evaluate_expression_in_env(lhs_expr, statement_env, file_name))
                rhs = ensure_quantity(evaluate_expression_in_env(rhs_expr, statement_env, file_name))
                if not dims_close(lhs.dims, rhs.dims):
                    raise ValueError("Units mismatch in system of equations")
                residual_list.append(float(lhs.value - rhs.value))
            else:
                value = ensure_quantity(evaluate_expression_in_env(expr, statement_env, file_name))
                residual_list.append(float(value.value))
        return np.array(residual_list, dtype=float)

    guesses = np.ones(len(variables), dtype=float)
    try:
        root = optimize.root(residuals, guesses)
        if not root.success:
            least_squares = optimize.least_squares(residuals, guesses)
            if not least_squares.success:
                return "Unable to solve system of equations", [], {}
            solution_values = least_squares.x
        else:
            solution_values = root.x
    except Exception as exc:
        return f"Solve error: {type(exc).__name__}, {exc}", [], {}

    local_env = dict(env)
    for name, value in zip(variables, solution_values):
        local_env[name] = Quantity(float(value), ZERO_DIMS)

    display_solutions = {name: [format_number(value)] for name, value in zip(variables, solution_values)}
    assignments = [{"type": "assignment", "name": name, "value": float(value)} for name, value in zip(variables, solution_values)]
    for name, value in zip(variables, solution_values):
        env[name] = Quantity(float(value), ZERO_DIMS)
    return None, assignments, display_solutions


def split_top_level_args(expression: str) -> tuple[str, str]:
    depth = 0
    start = 0
    parts: list[str] = []
    for index, char in enumerate(expression):
        if char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
        elif char == "," and depth == 0:
            parts.append(expression[start:index].strip())
            start = index + 1
    parts.append(expression[start:].strip())
    if len(parts) != 2:
        raise ValueError("Expected two arguments")
    return parts[0], parts[1]


def build_interpolation_wrappers(interpolation_definitions: list[Any]) -> dict[str, Callable]:
    wrappers: dict[str, Callable] = {}
    for definition in interpolation_definitions:
        name = definition["name"]
        input_values = np.array(definition["inputValues"], dtype=float)
        output_values = np.array(definition["outputValues"], dtype=float)
        order = int(definition["order"])
        output_dims = tuple(float(x) for x in definition["outputDims"])
        if definition["type"] == "gridInterpolation":
            if definition["numInputs"] != input_values.shape[0]:
                continue
            grid = [np.unique(column) for column in input_values]
            values = output_values.reshape([len(axis) for axis in grid])
            interpolator = interpolate.RegularGridInterpolator(grid, values, bounds_error=False, fill_value=None)

            def wrapper(*args: Any, _interpolator=interpolator) -> Quantity:
                point = np.array([float(ensure_quantity(arg).value) for arg in args], dtype=float)
                return Quantity(float(_interpolator(point)), output_dims)

            wrappers[name] = wrapper
            continue

        if definition["numInputs"] == 1:
            x = input_values[0]
            y = output_values
            kind = "cubic" if order >= 3 and len(x) >= 4 else "linear"
            interpolator = interpolate.interp1d(x, y, kind=kind, fill_value="extrapolate", bounds_error=False)

            def wrapper(value: Any, _interpolator=interpolator) -> Quantity:
                x_value = float(ensure_quantity(value).value)
                return Quantity(float(_interpolator(x_value)), output_dims)

            wrappers[name] = wrapper
        else:
            coeffs = np.polyfit(input_values.T, output_values, deg=order)

            def wrapper(*args: Any, _coeffs=coeffs) -> Quantity:
                values = np.array([float(ensure_quantity(arg).value) for arg in args], dtype=float)
                return Quantity(float(np.polyval(_coeffs, values)), output_dims)

            wrappers[name] = wrapper
    return wrappers


def build_fluid_wrappers(fluid_definitions: list[FluidFunction]) -> dict[str, Callable]:
    wrappers: dict[str, Callable] = {}
    if coolprop is None:
        return wrappers
    for definition in fluid_definitions:
        def wrapper(*args: Any, _definition=definition) -> Quantity:
            values = [float(ensure_quantity(arg).value) for arg in args]
            input_names = [_definition["input1"], _definition["input2"]]
            input_names.extend([_definition["input3"]] if "input3" in _definition else [])
            outputs = [values[0], values[1]]
            if len(values) > 2:
                outputs.append(values[2])
            result = coolprop.PropsSI(_definition["output"], input_names[0], outputs[0], input_names[1], outputs[1], _definition["fluid"])
            return Quantity(float(result), tuple(float(x) for x in _definition["outputDims"]))

        wrappers[definition["name"]] = wrapper
    return wrappers


def solve_sheet(statements_and_systems: str) -> str:
    try:
        data = cast(StatementsAndSystems, json.loads(statements_and_systems))
        statements = cast(list[Any], data["statements"])
        system_definitions = cast(list[Any], data["systemDefinitions"])
        fluid_definitions = cast(list[FluidFunction], data.get("fluidFunctions", []))
        code_cell_definitions = cast(list[CodeCellFunction], data["codeCellFunctions"])
        interpolation_definitions = cast(list[Any], data["interpolationFunctions"])
        custom_base_units = data.get("customBaseUnits")
        env: dict[str, Any] = {}

        code_cell_wrappers, code_cell_result_store = get_code_cell_result_store(code_cell_definitions)
        env.update(code_cell_wrappers)
        env.update(build_interpolation_wrappers(interpolation_definitions))
        env.update(build_fluid_wrappers(fluid_definitions))

        system_results: list[SystemResult] = []
        for system_definition in system_definitions:
            variables = cast(list[str], system_definition["variables"])
            statements_for_system = cast(list[EqualityStatement], system_definition["statements"])
            if system_definition.get("numericalSolve", True):
                error, assignments, display_solutions = solve_linear_system_from_equations(statements_for_system, variables, env, "<system>")
                if error is not None:
                    system_results.append({"error": error, "solutions": {}, "selectedSolution": 0})
                else:
                    system_results.append({"error": None, "solutions": display_solutions, "selectedSolution": int(system_definition.get("selectedSolution", 0))})
            else:
                error, assignments, display_solutions = solve_linear_system_from_equations(statements_for_system, variables, env, "<system>")
                if error is not None:
                    system_results.append({"error": error, "solutions": {}, "selectedSolution": 0})
                else:
                    system_results.append({"error": None, "solutions": display_solutions, "selectedSolution": int(system_definition.get("selectedSolution", 0))})

        # Build the full environment first so later assignment cells can
        # contribute values used by earlier visible expressions.
        for statement in statements:
            if isinstance(statement, dict) and statement.get("isSubQuery"):
                continue
            stmt_type = statement.get("type")
            try:
                statement_env = prepare_statement_env(cast(dict[str, Any], statement), env)
                if stmt_type == "assignment":
                    value = evaluate_expression_in_env(statement["expression"], statement_env, "<assignment>")
                    if statement.get("name"):
                        env[statement["name"]] = value if isinstance(value, (Quantity, np.ndarray, RenderExpr)) else ensure_quantity(value)
            except Exception:
                continue

        results: list[Any] = []
        sheet_error: str | None = None

        for statement in statements:
            if isinstance(statement, dict) and statement.get("isSubQuery"):
                continue
            stmt_type = statement.get("type")
            try:
                statement_env = prepare_statement_env(cast(dict[str, Any], statement), env)
                if stmt_type == "assignment":
                    value = evaluate_expression_in_env(statement["expression"], statement_env, "<assignment>")
                    if statement.get("name"):
                        env[statement["name"]] = value if isinstance(value, (Quantity, np.ndarray, RenderExpr)) else ensure_quantity(value)
                    results.append(make_result_from_value(value, custom_base_units))
                elif stmt_type == "query" and statement.get("isCodeFunctionQuery"):
                    value = evaluate_expression_in_env(statement["codeFunctionRawQuery"]["expression"], statement_env, "<code-function>")
                    results.append(make_result_from_value(value, custom_base_units))
                elif stmt_type == "query":
                    value = evaluate_expression_in_env(statement["expression"], statement_env, "<query>")
                    results.append(make_result_from_value(value, custom_base_units))
                elif stmt_type == "equality":
                    value = evaluate_expression_in_env(statement["expression"], statement_env, "<equality>")
                    results.append(make_result_from_value(value, custom_base_units))
                elif stmt_type == "scatterQuery":
                    x_value = evaluate_expression_in_env(statement["xValuesQuery"]["expression"], statement_env, "<scatter>")
                    y_value = evaluate_expression_in_env(statement["yValuesQuery"]["expression"], statement_env, "<scatter>")
                    results.append({
                        "plot": True,
                        "data": [{
                            "numericOutput": True,
                            "numericInput": True,
                            "limitsUnitsMatch": True,
                            "input": [float(ensure_quantity(x_value).value)],
                            "output": [float(ensure_quantity(y_value).value)],
                            "inputReversed": False,
                            "inputUnits": statement.get("inputUnits", ""),
                            "inputUnitsLatex": statement.get("inputUnitsLatex", ""),
                            "inputName": statement.get("xName", ""),
                            "outputUnits": statement.get("units", ""),
                            "outputUnitsLatex": statement.get("unitsLatex", ""),
                            "outputName": statement.get("yName", ""),
                            "isScatter": True,
                        }],
                    })
                elif stmt_type == "query" and statement.get("isRange"):
                    value = evaluate_expression_in_env(statement["expression"], statement_env, "<range>")
                    results.append(make_result_from_value(value, custom_base_units))
                elif stmt_type == "blank":
                    continue
            except Exception as exc:
                sheet_error = f"{type(exc).__name__}: {exc}"
                break

        return json.dumps({
            "error": sheet_error,
            "results": results if sheet_error is None else [],
            "systemResults": system_results,
            "codeCellResults": collect_code_cell_results(code_cell_result_store),
        })
    except Exception as exc:
        return json.dumps(make_error(f"Unhandled exception occurred during Python call. {exc}"))


class FuncContainer:
    pass


py_funcs = FuncContainer()
py_funcs.solveSheet = solve_sheet  # type: ignore[attr-defined]
py_funcs
