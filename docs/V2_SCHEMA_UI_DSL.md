# AutoPrism V2 JSON Schema and Safe UI DSL

## Purpose

Every saved child panel freezes two related contracts:

1. a Draft 2020-12 JSON Schema describing stored INFO data;
2. a non-executable UI DSL describing how the trusted client may present it.

The UI DSL is deliberately bounded. Unknown node types and properties are
rejected by the API, not silently ignored, and no DSL field may reference data
absent from the frozen Schema.

## Required Schema semantics

A panel Schema must:

- have root type `object`;
- declare at least one property and an explicit `required` array;
- declare `x-unit` or `x-unitless: true` on every numeric property;
- use only a code from the frozen `unit-registry-v1` when `x-unit` is present;
- declare `x-currency` as an uppercase ISO-style three-letter code for money;
- declare numeric `x-uncertainty` as `exact`, `source_absolute_field`, or
  `unknown` (absence is treated as unknown, never zero);
- provide `x-autoprism.time_dimension`;
- provide `x-autoprism.geographic_dimension`;
- provide `x-autoprism.aggregation`;
- provide `x-autoprism.visualization_mapping`.

Units, time basis, geography and aggregation are data semantics. They are not
visual labels and must not be inferred by the renderer.

Example bounded numeric claim:

```json
{
  "revenue": {
    "type": "number",
    "x-unit": "million_currency",
    "x-currency": "USD",
    "x-uncertainty": {
      "kind": "source_absolute_field",
      "field": "revenue_error"
    }
  },
  "revenue_error": {
    "type": "number",
    "x-unit": "million_currency",
    "x-currency": "USD",
    "x-uncertainty": {"kind": "exact"}
  }
}
```

The referenced error field must exist and be required. Conversion targets are
also frozen Schema fields; the caller cannot rename a unit, currency or metric
outside that contract.

An executable conversion time basis uses `time-scope-v1` rather than a
descriptive label:

```json
{
  "x-autoprism": {
    "time_dimension": {
      "contract_version": "time-scope-v1",
      "kind": "instant",
      "field": "reported_at"
    }
  }
}
```

The named field must be a required string containing ISO-8601 time with an
explicit UTC offset. `period_end` uses `field`; `period_average` uses required
`start_field` and `end_field`. Legacy descriptive strings remain display
metadata and provide no currency-conversion authority.

### Executable geography for the Shell map

A descriptive string such as `"US"` remains valid legacy metadata but grants
no map authority. A new feature may be mapped only with `geo-scope-v1`:

```json
{
  "x-autoprism": {
    "geographic_dimension": {
      "contract_version": "geo-scope-v1",
      "display_type": "HOTSPOT",
      "label_field": "location",
      "latitude_field": "latitude",
      "longitude_field": "longitude"
    }
  }
}
```

Every referenced field must exist and be required. Latitude and longitude are
finite JSON numbers with `x-unit: degree_latitude` and
`x-unit: degree_longitude`. Flow-style nodes additionally bind required end
coordinates. Zone geometry binds a required closed `[longitude, latitude]`
ring with 4–500 positions. `MARKER`, `HOTSPOT`, `RIPPLE`, `FLOW`,
`COMPARISON`, `SHIELD_UP` and `ZONE` are the only display types.

Extraction freezes all geographic claim citations separately from the metric
citation. Missing fields, invalid ranges, missing citations or unsupported
geometry make the extraction invalid; neither the client nor L2 geocodes a
label or supplies coordinates.

## Supported UI DSL nodes

### `stack`

Groups one or more child nodes. Maximum nesting depth is eight.

```json
{
  "type": "stack",
  "children": []
}
```

An empty stack is invalid.

### `metric`

Displays one field that exists in the root Schema.

```json
{
  "type": "metric",
  "field": "record_count",
  "label": "官方记录数",
  "unit": "record"
}
```

The renderer never replaces a missing metric with zero or a generated value.
When `unit` is present it must exactly match the field's frozen Schema
`x-unit`; it is not a free-form display label.

### `table`

Displays an array field. Every named column must exist in the array item
Schema.

```json
{
  "type": "table",
  "field": "records",
  "columns": ["Make_Name", "Model_Name", "Model_ID"],
  "page_size": 20
}
```

### `chart`

Displays a single real series from an array field as a line, bar or area chart.
The Y field must be numeric and declare exactly one of `x-unit` or
`x-unitless: true`. The X field must be a string or numeric item property.

```json
{
  "type": "chart",
  "field": "records",
  "variant": "line",
  "x_field": "reported_at",
  "y_field": "value",
  "label": "已报告数值",
  "max_points": 80
}
```

`max_points` is bounded to 2–200. The renderer preserves stored row order,
rejects non-finite values and reports an empty state rather than interpolating,
extrapolating or adding trend points. Multi-series grouping is not accepted in
this contract version.

### `timeline`

Displays stored events from an array field. The time field must be a Schema
string with `format: date-time`; the title must be a string and an optional
value field must be numeric.

```json
{
  "type": "timeline",
  "field": "records",
  "time_field": "reported_at",
  "title_field": "event_name",
  "value_field": "value",
  "label": "公告时间线",
  "max_items": 20
}
```

Events are sorted only from their stored timestamps. Invalid or missing dates
are not repaired, and the renderer never creates placeholder events.

### `provenance`

Requests the trusted provenance footer and evidence terminal.

```json
{
  "type": "provenance",
  "show_source": true,
  "show_locator": true,
  "show_retrieved_at": true,
  "show_artifact_hash": true
}
```

The server remains authoritative for evidence content. UI flags cannot create
or elevate trust.

## Unsupported nodes

`map`, `heatmap`, `radar`, `ticker`, `network` and multi-series charts remain
explicitly unavailable until they have:

- a versioned data contract;
- deterministic renderer behavior;
- empty/error/loading rules;
- accessibility and responsive tests;
- evidence-aware labels and unit handling.

The situation map in the V2 Shell is not a general panel DSL node. It consumes
only `trusted-insight-map-v1` features built from `geo-scope-v1`, current
ELIGIBLE inputs and replayable claim citations. A panel-level `map` node remains
unsupported until the richer DSL milestone.

## Custom React

Panel versions may use `custom_react` only with frozen source, SHA-256,
`visualization_contract.runtime = "custom-react-sandbox-v1"` and an empty
dependency array. Imports, dynamic imports and `require` are rejected.

The client verifies the source hash, compiles in a dedicated worker, and sends
the result to a worker inside a sandboxed iframe with an opaque origin and CSP
`connect-src 'none'`. Network and nested-worker APIs are disabled. Output is
serialized through an allowlist of text and basic semantic/table elements;
attributes, scripts, event handlers and raw HTML never cross into the host DOM.
Compilation has a separate cold-start budget; component execution remains
limited to 250 ms plus depth/node/text quotas. The runtime is presentation-only
and cannot upgrade input trust state.

## Version lifecycle

- Existing `DashboardVersion` and `PanelVersion` rows are read-only.
- Editing begins from a complete historical payload.
- Saving creates a new dashboard version and new child-panel versions.
- A draft and a published version are different immutable rows.
- Publishing requires explicit UI confirmation.
- Errors create another revision; no historical contract is overwritten.
