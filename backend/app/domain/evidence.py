"""Deterministic helpers for AutoPrism's evidence chain."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
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
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"invalid numeric input: {value!r}") from exc


def execute_calculation(
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


def validate_numeric_sources(
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
