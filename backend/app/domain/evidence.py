"""Deterministic helpers for AutoPrism's evidence chain."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from decimal import Decimal, DecimalException, InvalidOperation
from enum import Enum
from typing import Any, Mapping


class LocatorType(str, Enum):
    PDF_PAGE = "pdf_page"
    TABLE_CELL = "table_cell"
    CSS_SELECTOR = "css_selector"
    XPATH = "xpath"
    JSON_POINTER = "json_pointer"
    TEXT_SPAN = "text_span"


class CalculationOperation(str, Enum):
    ADD = "add"
    SUBTRACT = "subtract"
    MULTIPLY = "multiply"
    DIVIDE = "divide"
    PERCENT_CHANGE = "percent_change"
    WEIGHTED_AVERAGE = "weighted_average"


@dataclass(frozen=True)
class CalculationResult:
    value: Decimal
    operation: CalculationOperation
    inputs: tuple[Decimal, ...]


@dataclass(frozen=True)
class NormalizedCalculationContract:
    """Validated calculation inputs and canonical JSON parameters."""

    operation: CalculationOperation
    inputs: tuple[Decimal, ...]
    parameters: dict[str, Any]
    weights: tuple[Decimal, ...] | None


@dataclass(frozen=True)
class NumericValidationResult:
    state: str
    minimum: Decimal | None
    maximum: Decimal | None
    spread: Decimal | None
    relative_spread: Decimal | None


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def sha256_json(value: Any) -> str:
    return sha256_bytes(canonical_json(value).encode("utf-8"))


def validate_sha256(value: str) -> str:
    normalized = value.lower()
    if len(normalized) != 64 or any(c not in "0123456789abcdef" for c in normalized):
        raise ValueError("sha256 must contain exactly 64 hexadecimal characters")
    return normalized


def validate_locator(locator_type: LocatorType | str, locator: Mapping[str, Any]) -> None:
    kind = LocatorType(locator_type)
    required = {
        LocatorType.PDF_PAGE: {"page"},
        LocatorType.TABLE_CELL: {"sheet", "cell"},
        LocatorType.CSS_SELECTOR: {"selector"},
        LocatorType.XPATH: {"xpath"},
        LocatorType.JSON_POINTER: {"pointer"},
        LocatorType.TEXT_SPAN: {"start", "end"},
    }[kind]
    missing = sorted(key for key in required if key not in locator)
    if missing:
        raise ValueError(f"{kind.value} locator is missing: {', '.join(missing)}")

    if kind is LocatorType.PDF_PAGE and int(locator["page"]) < 1:
        raise ValueError("PDF pages are 1-based")
    if kind is LocatorType.TEXT_SPAN:
        start, end = int(locator["start"]), int(locator["end"])
        if start < 0 or end <= start:
            raise ValueError("text span must satisfy 0 <= start < end")


def _decimal(value: Any) -> Decimal:
    if isinstance(value, bool):
        raise ValueError("boolean is not a numeric input")
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"invalid numeric input: {value!r}") from exc
    if not parsed.is_finite():
        raise ValueError(f"numeric input must be finite: {value!r}")
    return parsed


def _is_finite_json_number(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return not isinstance(value, float) or math.isfinite(value)


def normalize_calculation_contract(
    operation: CalculationOperation | str,
    raw_inputs: list[Any] | tuple[Any, ...],
    parameters: dict[str, Any] | None = None,
) -> NormalizedCalculationContract:
    """Fail closed on every operation/parameter shape before calculation.

    Observation values may be canonical decimal strings, but weights are API
    parameters and therefore must be finite JSON numbers rather than strings
    that happen to parse as numbers.
    """

    try:
        normalized_operation = CalculationOperation(operation)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"unsupported calculation operation: {operation!r}") from exc
    if not isinstance(raw_inputs, (list, tuple)):
        raise ValueError("raw_inputs must be an array")
    inputs = tuple(_decimal(value) for value in raw_inputs)
    if not inputs:
        raise ValueError("at least one input is required")
    if normalized_operation in {
        CalculationOperation.SUBTRACT,
        CalculationOperation.DIVIDE,
        CalculationOperation.PERCENT_CHANGE,
    } and len(inputs) != 2:
        raise ValueError(f"{normalized_operation.value} requires exactly two inputs")

    if parameters is None:
        raw_parameters: dict[str, Any] = {}
    elif isinstance(parameters, dict):
        raw_parameters = dict(parameters)
    else:
        raise ValueError("calculation parameters must be an object")
    if any(not isinstance(key, str) for key in raw_parameters):
        raise ValueError("calculation parameter keys must be strings")

    allowed_keys = (
        {"weights"}
        if normalized_operation is CalculationOperation.WEIGHTED_AVERAGE
        else {"unit_plan"}
        if normalized_operation
        in {CalculationOperation.MULTIPLY, CalculationOperation.DIVIDE}
        else set()
    )
    unknown_keys = sorted(set(raw_parameters) - allowed_keys)
    if unknown_keys:
        raise ValueError(
            "unsupported calculation parameters: " + ", ".join(unknown_keys)
        )

    normalized_parameters: dict[str, Any] = {}
    decimal_weights: tuple[Decimal, ...] | None = None
    if normalized_operation is CalculationOperation.WEIGHTED_AVERAGE:
        weights = raw_parameters.get("weights")
        if not isinstance(weights, (list, tuple)):
            raise ValueError("weighted_average weights must be an array")
        if len(weights) != len(inputs):
            raise ValueError("weighted_average requires one weight per input")
        if any(not _is_finite_json_number(value) for value in weights):
            raise ValueError(
                "weighted_average weights must be finite JSON numbers"
            )
        decimal_weights = tuple(_decimal(value) for value in weights)
        try:
            total_weight = sum(decimal_weights, Decimal("0"))
        except (DecimalException, OverflowError) as exc:
            raise ValueError("calculation parameters exceed the supported range") from exc
        if total_weight == 0:
            raise ValueError("weight total must not be zero")
        normalized_parameters["weights"] = list(weights)
    elif normalized_operation in {
        CalculationOperation.MULTIPLY,
        CalculationOperation.DIVIDE,
    }:
        unit_plan = raw_parameters.get("unit_plan")
        if not isinstance(unit_plan, dict) or not unit_plan:
            raise ValueError(
                f"{normalized_operation.value} requires a non-empty unit_plan object"
            )
        try:
            canonical_json(unit_plan)
        except (TypeError, ValueError) as exc:
            raise ValueError("unit_plan must be a non-empty JSON object") from exc
        normalized_parameters["unit_plan"] = dict(unit_plan)

    return NormalizedCalculationContract(
        operation=normalized_operation,
        inputs=inputs,
        parameters=normalized_parameters,
        weights=decimal_weights,
    )


def _execute_calculation(
    operation: CalculationOperation | str,
    raw_inputs: list[Any] | tuple[Any, ...],
    *,
    weights: list[Any] | tuple[Any, ...] | None = None,
) -> CalculationResult:
    op = CalculationOperation(operation)
    inputs = tuple(_decimal(value) for value in raw_inputs)
    if not inputs:
        raise ValueError("at least one input is required")

    if op is CalculationOperation.ADD:
        result = sum(inputs, Decimal("0"))
    elif op is CalculationOperation.SUBTRACT:
        if len(inputs) != 2:
            raise ValueError("subtract requires exactly two inputs")
        result = inputs[0] - inputs[1]
    elif op is CalculationOperation.MULTIPLY:
        result = Decimal("1")
        for value in inputs:
            result *= value
    elif op is CalculationOperation.DIVIDE:
        if len(inputs) != 2:
            raise ValueError("divide requires exactly two inputs")
        if inputs[1] == 0:
            raise ValueError("division by zero")
        result = inputs[0] / inputs[1]
    elif op is CalculationOperation.PERCENT_CHANGE:
        if len(inputs) != 2:
            raise ValueError("percent_change requires old and new values")
        if inputs[0] == 0:
            raise ValueError("percent change from zero is undefined")
        result = (inputs[1] - inputs[0]) / inputs[0] * Decimal("100")
    else:
        if weights is None or len(weights) != len(inputs):
            raise ValueError("weighted_average requires one weight per input")
        decimal_weights = tuple(_decimal(weight) for weight in weights)
        total_weight = sum(decimal_weights, Decimal("0"))
        if total_weight == 0:
            raise ValueError("weight total must not be zero")
        result = sum(
            (value * weight for value, weight in zip(inputs, decimal_weights)),
            Decimal("0"),
        ) / total_weight

    return CalculationResult(value=result, operation=op, inputs=inputs)


def execute_calculation(
    operation: CalculationOperation | str,
    raw_inputs: list[Any] | tuple[Any, ...],
    *,
    parameters: dict[str, Any] | None = None,
    weights: list[Any] | tuple[Any, ...] | None = None,
) -> CalculationResult:
    if parameters is not None and weights is not None:
        raise ValueError("pass calculation weights through parameters only")
    if weights is not None:
        parameters = {"weights": weights}
    contract = normalize_calculation_contract(operation, raw_inputs, parameters)
    return execute_normalized_calculation(contract)


def execute_normalized_calculation(
    contract: NormalizedCalculationContract,
) -> CalculationResult:
    try:
        return _execute_calculation(
            contract.operation,
            contract.inputs,
            weights=contract.weights,
        )
    except (DecimalException, OverflowError) as exc:
        raise ValueError("decimal calculation exceeds the supported range") from exc


def _validate_numeric_sources(
    raw_values: list[Any] | tuple[Any, ...],
    *,
    absolute_tolerance: Any = 0,
    relative_tolerance: Any = 0,
) -> NumericValidationResult:
    """Compare independently sourced values using explicit tolerances."""
    values = tuple(_decimal(value) for value in raw_values)
    if len(values) < 2:
        return NumericValidationResult("needs_review", None, None, None, None)

    absolute_limit = _decimal(absolute_tolerance)
    relative_limit = _decimal(relative_tolerance)
    if absolute_limit < 0 or relative_limit < 0:
        raise ValueError("validation tolerances must not be negative")

    minimum, maximum = min(values), max(values)
    spread = maximum - minimum
    denominator = max(abs(value) for value in values)
    relative_spread = Decimal("0") if denominator == 0 else spread / denominator
    passed = spread <= absolute_limit or relative_spread <= relative_limit
    return NumericValidationResult(
        "passed" if passed else "conflict",
        minimum,
        maximum,
        spread,
        relative_spread,
    )


def validate_numeric_sources(
    raw_values: list[Any] | tuple[Any, ...],
    *,
    absolute_tolerance: Any = 0,
    relative_tolerance: Any = 0,
) -> NumericValidationResult:
    try:
        return _validate_numeric_sources(
            raw_values,
            absolute_tolerance=absolute_tolerance,
            relative_tolerance=relative_tolerance,
        )
    except (DecimalException, OverflowError) as exc:
        raise ValueError("numeric validation exceeds the supported range") from exc
