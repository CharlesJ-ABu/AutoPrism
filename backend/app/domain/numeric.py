"""Versioned deterministic unit, currency and uncertainty contracts."""

from __future__ import annotations

from dataclasses import dataclass
from contextlib import contextmanager
from decimal import (
    Decimal,
    DecimalException,
    DivisionByZero,
    InvalidOperation,
    Overflow,
    ROUND_HALF_EVEN,
    localcontext,
)
from enum import Enum
from typing import Any

from app.domain.evidence import CalculationOperation, normalize_calculation_contract


UNIT_REGISTRY_VERSION = "unit-registry-v1"
NUMERIC_ENGINE_VERSION = "decimal-v2-bounded"
CONVERSION_ENGINE_VERSION = "conversion-v1-bounded"


class UncertaintyKind(str, Enum):
    EXACT = "exact"
    BOUNDED = "bounded"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class UnitDefinition:
    code: str
    dimension: str
    semantic_kind: str
    scale_to_base: Decimal


@dataclass(frozen=True)
class NumericInterval:
    value: Decimal
    absolute_error: Decimal

    @property
    def low(self) -> Decimal:
        with decimal_context():
            return self.value - self.absolute_error

    @property
    def high(self) -> Decimal:
        with decimal_context():
            return self.value + self.absolute_error


@dataclass(frozen=True)
class RoundedIntervalResult:
    value: Decimal
    absolute_error: Decimal
    low: Decimal
    high: Decimal
    quantum: Decimal


def _unit(
    code: str,
    dimension: str,
    semantic_kind: str,
    scale_to_base: str,
) -> UnitDefinition:
    return UnitDefinition(code, dimension, semantic_kind, Decimal(scale_to_base))


UNIT_REGISTRY: dict[str, UnitDefinition] = {
    item.code: item
    for item in (
        _unit("one", "dimensionless", "scalar", "1"),
        _unit("percent", "dimensionless", "ratio", "0.01"),
        _unit("basis_point", "dimensionless", "ratio", "0.0001"),
        _unit("record", "count", "record", "1"),
        _unit("vehicle", "count", "vehicle", "1"),
        _unit("thousand_vehicle", "count", "vehicle", "1000"),
        _unit("million_vehicle", "count", "vehicle", "1000000"),
        _unit("meter", "length", "length", "1"),
        _unit("kilometer", "length", "length", "1000"),
        _unit("mile", "length", "length", "1609.344"),
        _unit("gram", "mass", "mass", "0.001"),
        _unit("kilogram", "mass", "mass", "1"),
        _unit("tonne", "mass", "mass", "1000"),
        _unit("pound", "mass", "mass", "0.45359237"),
        _unit("Wh", "energy", "energy", "1"),
        _unit("kWh", "energy", "energy", "1000"),
        _unit("MWh", "energy", "energy", "1000000"),
        _unit("W", "power", "power", "1"),
        _unit("kW", "power", "power", "1000"),
        _unit("MW", "power", "power", "1000000"),
        _unit("second", "time", "duration", "1"),
        _unit("minute", "time", "duration", "60"),
        _unit("hour", "time", "duration", "3600"),
        _unit("currency_unit", "currency", "currency_amount", "1"),
        _unit("thousand_currency", "currency", "currency_amount", "1000"),
        _unit("million_currency", "currency", "currency_amount", "1000000"),
        _unit("billion_currency", "currency", "currency_amount", "1000000000"),
        _unit("currency_ratio", "dimensionless", "fx_rate", "1"),
        _unit("degree_latitude", "angle", "latitude", "1"),
        _unit("degree_longitude", "angle", "longitude", "1"),
    )
}


def decimal_value(value: Any) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float, str, Decimal)):
        raise ValueError("numeric value must be a finite decimal-compatible scalar")
    try:
        parsed = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("numeric value is not a valid decimal") from exc
    if not parsed.is_finite():
        raise ValueError("numeric value must be finite")
    return parsed


def canonical_decimal(value: Decimal | Any) -> str:
    parsed = decimal_value(value)
    if parsed == 0:
        return "0"
    with decimal_context():
        return format(parsed.normalize(), "f")


def make_interval(
    value: Any,
    *,
    uncertainty_kind: UncertaintyKind | str,
    absolute_error: Any | None,
) -> NumericInterval:
    kind = UncertaintyKind(uncertainty_kind)
    if kind is UncertaintyKind.UNKNOWN:
        raise ValueError("unknown uncertainty cannot enter deterministic derivation")
    parsed_value = decimal_value(value)
    if kind is UncertaintyKind.EXACT:
        if absolute_error not in (None, 0, "0", Decimal("0")):
            raise ValueError("exact values cannot declare non-zero uncertainty")
        error = Decimal("0")
    else:
        if absolute_error is None:
            raise ValueError("bounded uncertainty requires absolute_error")
        error = decimal_value(absolute_error)
        if error < 0:
            raise ValueError("absolute_error must not be negative")
    return NumericInterval(parsed_value, error)


@contextmanager
def decimal_context():
    """Isolate arithmetic from the process-global Decimal context."""

    with localcontext() as active:
        active.prec = 50
        active.rounding = ROUND_HALF_EVEN
        active.traps[InvalidOperation] = True
        active.traps[DivisionByZero] = True
        active.traps[Overflow] = True
        yield active


def _round_interval(
    *,
    center: Decimal,
    low: Decimal,
    high: Decimal,
    output_quantum: Any,
) -> RoundedIntervalResult:
    quantum = decimal_value(output_quantum)
    if quantum <= 0:
        raise ValueError("output_quantum must be positive")
    if low > high:
        low, high = high, low
    steps = (center / quantum).quantize(Decimal("1"), rounding=ROUND_HALF_EVEN)
    rounded = steps * quantum
    error = max(abs(rounded - low), abs(high - rounded))
    return RoundedIntervalResult(rounded, error, low, high, quantum)


def _multiply_bounds(
    first_low: Decimal,
    first_high: Decimal,
    second_low: Decimal,
    second_high: Decimal,
) -> tuple[Decimal, Decimal]:
    candidates = (
        first_low * second_low,
        first_low * second_high,
        first_high * second_low,
        first_high * second_high,
    )
    return min(candidates), max(candidates)


def _divide_bounds(
    numerator_low: Decimal,
    numerator_high: Decimal,
    denominator_low: Decimal,
    denominator_high: Decimal,
) -> tuple[Decimal, Decimal]:
    if denominator_low <= 0 <= denominator_high:
        raise ValueError("uncertain denominator interval contains zero")
    reciprocal_low = Decimal("1") / denominator_high
    reciprocal_high = Decimal("1") / denominator_low
    if reciprocal_low > reciprocal_high:
        reciprocal_low, reciprocal_high = reciprocal_high, reciprocal_low
    return _multiply_bounds(
        numerator_low,
        numerator_high,
        reciprocal_low,
        reciprocal_high,
    )


def unit_registry_payload() -> dict[str, Any]:
    return {
        "version": UNIT_REGISTRY_VERSION,
        "units": [
            {
                "code": item.code,
                "dimension": item.dimension,
                "semantic_kind": item.semantic_kind,
                "scale_to_base": canonical_decimal(item.scale_to_base),
            }
            for item in sorted(UNIT_REGISTRY.values(), key=lambda unit: unit.code)
        ],
    }


def convert_unit(
    value: NumericInterval,
    *,
    from_unit: str,
    to_unit: str,
    output_quantum: Any,
) -> tuple[RoundedIntervalResult, dict[str, Any]]:
    source = UNIT_REGISTRY.get(from_unit)
    target = UNIT_REGISTRY.get(to_unit)
    if source is None or target is None:
        raise ValueError("from_unit and to_unit must exist in the frozen registry")
    if (
        source.dimension != target.dimension
        or source.semantic_kind != target.semantic_kind
    ):
        raise ValueError("units do not share a compatible dimension and semantic kind")
    try:
        with decimal_context():
            factor = source.scale_to_base / target.scale_to_base
            low, high = _multiply_bounds(value.low, value.high, factor, factor)
            result = _round_interval(
                center=value.value * factor,
                low=low,
                high=high,
                output_quantum=output_quantum,
            )
    except (DecimalException, OverflowError) as exc:
        raise ValueError("unit conversion exceeds the supported decimal range") from exc
    return result, {
        "registry_version": UNIT_REGISTRY_VERSION,
        "from_unit": from_unit,
        "to_unit": to_unit,
        "factor": canonical_decimal(factor),
    }


def convert_currency(
    value: NumericInterval,
    rate: NumericInterval,
    *,
    from_currency: str,
    to_currency: str,
    rate_base_currency: str,
    rate_quote_currency: str,
    output_quantum: Any,
) -> tuple[RoundedIntervalResult, dict[str, Any]]:
    currencies = (
        from_currency,
        to_currency,
        rate_base_currency,
        rate_quote_currency,
    )
    if any(
        not isinstance(currency, str)
        or len(currency) != 3
        or currency.upper() != currency
        for currency in currencies
    ):
        raise ValueError("currency codes must be uppercase ISO-style three-letter codes")
    if from_currency == to_currency:
        raise ValueError("currency conversion requires different currencies")
    try:
        with decimal_context():
            if (
                from_currency == rate_base_currency
                and to_currency == rate_quote_currency
            ):
                low, high = _multiply_bounds(
                    value.low,
                    value.high,
                    rate.low,
                    rate.high,
                )
                center = value.value * rate.value
                direction = "direct"
            elif (
                from_currency == rate_quote_currency
                and to_currency == rate_base_currency
            ):
                low, high = _divide_bounds(
                    value.low,
                    value.high,
                    rate.low,
                    rate.high,
                )
                center = value.value / rate.value
                direction = "inverse"
            else:
                raise ValueError("fx rate does not match the requested currency pair")
            result = _round_interval(
                center=center,
                low=low,
                high=high,
                output_quantum=output_quantum,
            )
    except (DecimalException, OverflowError) as exc:
        raise ValueError("currency conversion exceeds the supported decimal range") from exc
    return result, {
        "registry_version": UNIT_REGISTRY_VERSION,
        "from_currency": from_currency,
        "to_currency": to_currency,
        "rate_base_currency": rate_base_currency,
        "rate_quote_currency": rate_quote_currency,
        "direction": direction,
    }


def calculate_interval(
    operation: CalculationOperation | str,
    inputs: list[NumericInterval],
    *,
    parameters: dict[str, Any] | None,
    output_quantum: Any,
) -> tuple[RoundedIntervalResult, dict[str, Any]]:
    contract = normalize_calculation_contract(
        operation,
        [canonical_decimal(item.value) for item in inputs],
        parameters,
    )
    if len(inputs) != len(contract.inputs):
        raise ValueError("numeric interval count does not match calculation inputs")
    try:
        with decimal_context():
            if contract.operation is CalculationOperation.ADD:
                center = sum((item.value for item in inputs), Decimal("0"))
                low = sum((item.low for item in inputs), Decimal("0"))
                high = sum((item.high for item in inputs), Decimal("0"))
            elif contract.operation is CalculationOperation.SUBTRACT:
                center = inputs[0].value - inputs[1].value
                low = inputs[0].low - inputs[1].high
                high = inputs[0].high - inputs[1].low
            elif contract.operation is CalculationOperation.MULTIPLY:
                center = Decimal("1")
                low = Decimal("1")
                high = Decimal("1")
                for item in inputs:
                    center *= item.value
                    low, high = _multiply_bounds(low, high, item.low, item.high)
            elif contract.operation is CalculationOperation.DIVIDE:
                center = inputs[0].value / inputs[1].value
                low, high = _divide_bounds(
                    inputs[0].low,
                    inputs[0].high,
                    inputs[1].low,
                    inputs[1].high,
                )
            elif contract.operation is CalculationOperation.PERCENT_CHANGE:
                old, new = inputs
                if old.low <= 0 <= old.high:
                    raise ValueError("percent-change baseline interval contains zero")
                difference_low = new.low - old.high
                difference_high = new.high - old.low
                low, high = _divide_bounds(
                    difference_low,
                    difference_high,
                    old.low,
                    old.high,
                )
                low *= Decimal("100")
                high *= Decimal("100")
                center = (new.value - old.value) / old.value * Decimal("100")
            else:
                assert contract.weights is not None
                total_weight = sum(contract.weights, Decimal("0"))
                center = Decimal("0")
                low = Decimal("0")
                high = Decimal("0")
                for item, weight in zip(inputs, contract.weights):
                    center += item.value * weight
                    term_low, term_high = _multiply_bounds(
                        item.low,
                        item.high,
                        weight,
                        weight,
                    )
                    low += term_low
                    high += term_high
                low, high = _divide_bounds(low, high, total_weight, total_weight)
                center /= total_weight
            result = _round_interval(
                center=center,
                low=low,
                high=high,
                output_quantum=output_quantum,
            )
    except (DecimalException, OverflowError) as exc:
        raise ValueError("bounded calculation exceeds the supported decimal range") from exc
    return result, {
        "engine_version": NUMERIC_ENGINE_VERSION,
        "operation": contract.operation.value,
        "parameters": contract.parameters,
    }
