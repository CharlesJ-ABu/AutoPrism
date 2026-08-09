# AutoPrism V2 JSON Schema and Safe UI DSL

## Purpose

Every saved child panel freezes two related contracts:

1. a Draft 2020-12 JSON Schema describing stored INFO data;
2. a non-executable UI DSL describing how the trusted client may present it.

The UI DSL is deliberately small. Unknown node types are rejected by the API,
not silently ignored, and no DSL field may reference data absent from the
frozen Schema.

## Required Schema semantics

A panel Schema must:

- have root type `object`;
- declare at least one property and an explicit `required` array;
- declare `x-unit` or `x-unitless: true` on every numeric property;
- provide `x-autoprism.time_dimension`;
- provide `x-autoprism.geographic_dimension`;
- provide `x-autoprism.aggregation`;
- provide `x-autoprism.visualization_mapping`.

Units, time basis, geography and aggregation are data semantics. They are not
visual labels and must not be inferred by the renderer.

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

`chart`, `timeline`, `map`, `heatmap`, `radar`, `ticker` and `network` remain
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

Panel versions may retain `custom_react` source and its SHA-256 for future
portability, but the V2 client does not compile or execute it. Enabling it
requires an isolated origin/runtime, dependency allowlist, CSP, resource limits
and zero ambient credentials. Until then, the version editor shows a visible
unavailable notice.

## Version lifecycle

- Existing `DashboardVersion` and `PanelVersion` rows are read-only.
- Editing begins from a complete historical payload.
- Saving creates a new dashboard version and new child-panel versions.
- A draft and a published version are different immutable rows.
- Publishing requires explicit UI confirmation.
- Errors create another revision; no historical contract is overwritten.
