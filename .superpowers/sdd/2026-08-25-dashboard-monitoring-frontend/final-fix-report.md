# Final whole-branch fix report

Base reviewed HEAD: `5967531402cb1a833505483ccb5f167f98abe16e`

Worktree: `C:\Users\nurch\OneDrive\Documents\project\sparingV1.1\.worktrees\dashboard-monitoring-charts`

Branch: `feature/dashboard-monitoring-charts`

Final commit: created after this report and provided in the final handoff. The report is included in that commit, so the exact self-referential commit hash is not embedded here.

## Scope

Addressed all six Important findings from `final-fix-brief.md` with regression tests first, then the smallest compatible implementation changes. Non-blocking scope was not changed.

No merge, push, browser visual verification, or external side effect was performed.

## Files changed

- `sparing_api/app/tests/test_timeseries_api.py`
- `sparing_api/app/tests/test_anomaly_engine.py`
- `sparing_api/app/tests/test_getdata_api.py`
- `sparing_api/app/utils/timeseries_helpers.py`
- `sparing_api/app/utils/timeseries_service.py`
- `sparing_api/app/utils/anomaly_engine.py`
- `sparing_front/tests/dashboard-timeseries.test.mjs`
- `sparing_front/tests/dashboard-chart.test.mjs`
- `sparing_front/resources/js/Composables/useDashboardTimeseries.js`
- `sparing_front/resources/js/Components/Dashboard/WaterQualityTrendChart.vue`
- `sparing_front/resources/js/Components/Dashboard/DebitTrendChart.vue`

## Finding 1: custom range shifts for non-UTC sites

Test added:

- `test_timeseries_interprets_naive_custom_range_in_site_timezone`

Implementation:

- Added `_coerce_custom_boundary_dt()` in `timeseries_helpers.py`.
- `resolve_timeseries_window()` now interprets naive custom/range boundaries in the selected site's IANA timezone before converting to UTC.
- Explicit aware datetimes continue to be normalized as instants.

RED evidence against reviewed behavior:

```text
Command: python -m pytest app/tests/test_timeseries_api.py -q -k naive_custom_range
Result: 1 failed, 47 deselected, 5 warnings
Failure: meta.date_from was 2026-08-25T00:00:00Z; expected 2026-08-24T17:00:00Z for Asia/Jakarta local midnight.
```

GREEN evidence:

```text
Command: python -m pytest app/tests/test_timeseries_api.py -q -k naive_custom_range
Result: 1 passed, 47 deselected, 5 warnings in 0.17s
```

## Finding 2: stale snapshot from one selection remains visible under another

Tests added:

- `clears a successful snapshot when a changed preset request fails`
- `clears a successful custom snapshot when custom boundaries change and fail`

Existing same-key refresh regression retained:

- `preserves the last successful snapshot as stale when a refresh fails`

Implementation:

- Added complete request identity key in `useDashboardTimeseries.js` using `siteUid`, preset/custom boundaries, and fields.
- Successful snapshots store their identity.
- Snapshot is cleared when identity changes before a request resolves.
- Stale-on-failure is allowed only when the failed request matches the stored snapshot identity.
- Incomplete custom selection now clears the old snapshot and returns to idle/error state instead of displaying stale data from a different selection.

RED evidence against reviewed behavior:

```text
Command: node --test tests/dashboard-timeseries.test.mjs
Result: 25 passed, 2 failed
Failure: changed preset/custom-boundary failure kept the previous snapshot; expected null snapshot and initial-load error state.
```

GREEN evidence:

```text
Command: node --test tests/dashboard-timeseries.test.mjs
Result: 27 passed, 0 failed, duration_ms 170.3714
```

## Finding 3: chart x-axis timezone differs from tooltip/site timezone

Tests added:

- `WaterQualityTrendChart formats x-axis labels in the response timezone`
- `DebitTrendChart formats x-axis labels in the response timezone`

Implementation:

- Added explicit `formatXAxisLabel()` in both dashboard Apex chart components.
- X-axis labels now use `formatDashboardTimestamp(..., meta.timezone, true)`.
- `datetimeUTC` is set true and custom formatter owns the displayed site-time label.
- Responsive x-axis options preserve the same deterministic formatter.

RED evidence against reviewed behavior:

```text
Command: node --test tests/dashboard-chart.test.mjs
Result: 18 passed, 2 failed
Failure: Apex probe found no explicit x-axis formatter; expected Pacific/Auckland 12:00 label for 2026-08-25T00:00:00Z.
```

GREEN evidence:

```text
Command: node --test tests/dashboard-chart.test.mjs
Result: 20 passed, 0 failed, duration_ms 1663.5667
```

## Finding 4: sparse predecessor rows create false threshold-entry event at window start

Test added:

- `test_timeseries_uses_sparse_field_predecessor_for_threshold_continuity`

Implementation:

- Replaced the single global predecessor row with `_load_sensor_predecessors()`.
- Loads the latest valid predecessor per requested monitored field.
- Excludes predecessor rows with `op_status` and `sensor_error`, preserving sensor-error exclusion semantics.
- Deduplicates rows that serve as predecessor for multiple fields.
- Threshold continuity now receives field-specific predecessor samples.

RED evidence against reviewed behavior:

```text
Command: python -m pytest app/tests/test_timeseries_api.py -q -k sparse_field_predecessor
Result: 1 failed, 47 deselected, 5 warnings
Failure: emitted a false ph threshold_warning event at 2026-08-01T00:00:00Z.
```

GREEN evidence:

```text
Command: python -m pytest app/tests/test_timeseries_api.py -q -k sparse_field_predecessor
Result: 1 passed, 47 deselected, 5 warnings in 0.17s
```

## Finding 5: multi-field anomaly quality precedence is order-dependent

Test added:

- `test_getdata_keeps_row_quality_sensor_error_when_later_field_spike_shares_timestamp`

Implementation:

- Added `_QUALITY_FLAG_SEVERITY`.
- Added `_mark_sensor_quality()` and `_quality_guard()`.
- `sensor_error` may replace `anomaly`; `anomaly` cannot replace `sensor_error`.
- Implausible/spike/flatline row-quality writes now go through the monotonic guard.

RED evidence against reviewed behavior:

```text
Command: python -m pytest app/tests/test_getdata_api.py -q -k quality_sensor_error
Result: 1 failed, 13 deselected, 4 warnings
Failure: latest row quality_flag was anomaly; expected sensor_error when implausible pH and later TSS spike shared the timestamp.
```

GREEN evidence:

```text
Command: python -m pytest app/tests/test_getdata_api.py -q -k quality_sensor_error
Result: 1 passed, 13 deselected, 5 warnings in 0.17s
```

## Finding 6: SensorHealth writes are not measurement-time monotonic

Test added:

- `test_sensor_health_ignores_older_measurement_after_newer_state`

Implementation:

- `_upsert_health()` now uses the measurement timestamp, normalized as DB UTC, as the write guard.
- Existing rows update only when `SensorHealth.updated_at <= incoming_measurement_at`.
- SQLite uses `ON CONFLICT DO UPDATE ... WHERE updated_at <= incoming`.
- MySQL uses `ON DUPLICATE KEY UPDATE` with CASE guards, preserving atomic insert/upsert behavior for the production-style unique key.
- Generic fallback avoids overwriting an existing newer row.

RED evidence against reviewed behavior:

```text
Command: python -m pytest app/tests/test_anomaly_engine.py -q -k health_ignores_older
Result: 1 failed, 32 deselected, 4 warnings
Failure: older 00:05 bad measurement overwrote newer 00:10 ok health state.
```

GREEN evidence:

```text
Command: python -m pytest app/tests/test_anomaly_engine.py -q -k health_ignores_older
Result: 1 passed, 32 deselected, 4 warnings in 0.07s
```

## Focused verification summary

Backend focused:

```text
python -m pytest app/tests/test_timeseries_api.py -q -k naive_custom_range
1 passed, 47 deselected, 5 warnings in 0.17s

python -m pytest app/tests/test_timeseries_api.py -q -k sparse_field_predecessor
1 passed, 47 deselected, 5 warnings in 0.17s

python -m pytest app/tests/test_anomaly_engine.py -q -k health_ignores_older
1 passed, 32 deselected, 4 warnings in 0.07s

python -m pytest app/tests/test_getdata_api.py -q -k quality_sensor_error
1 passed, 13 deselected, 5 warnings in 0.17s
```

Frontend focused:

```text
node --test tests/dashboard-timeseries.test.mjs
27 passed, 0 failed, duration_ms 170.3714

node --test tests/dashboard-chart.test.mjs
20 passed, 0 failed, duration_ms 1663.5667
```

## Full verification

Backend full suite:

```text
Command: python -m pytest -q
Result: 277 passed, 5 warnings in 14.18s
Warnings: FastAPI on_event deprecations; passlib argon2.__version__ deprecation.
```

Frontend full suite:

```text
Command: npm.cmd test
Result: 75 passed, 0 failed, duration_ms 1706.8949
```

Frontend production build:

```text
Command: npm.cmd run build
Initial sandboxed result: failed because Vite/esbuild could not read the worktree config path; access denied while reading parent directories.
Escalated retry result: built successfully in 3.40s.
Warnings: Browserslist/caniuse-lite data is 8 months old; analysis.js is both dynamically and statically imported; final bundle chunk exceeds 500 kB.
```

Graphify:

```text
Command: graphify update .
Result: exit 0
Output: fail-closed kept 54 nodes from 1 file that left the scan corpus; rebuilt 0 nodes, 0 edges, 0 communities; graph.json, graph.html, and GRAPH_REPORT.md updated in graphify-out.
Git status after graphify showed no tracked graphify-out changes.
```

Whitespace:

```text
Command: git diff --check
Result: exit 0
Warnings: Git reported LF will be replaced by CRLF the next time Git touches the changed files.
```

Status before commit:

```text
Command: git status --short --branch
Result: branch feature/dashboard-monitoring-charts with modified fix/test files only.
```

## Diff summary before commit

```text
11 files changed, 524 insertions(+), 67 deletions(-)
```

## Concerns

- No unresolved functional concerns.
- Production build required an escalated retry because the sandbox denied Vite/esbuild access to the worktree config path. The same command passed after escalation.
- Existing non-blocking warnings remain: FastAPI `on_event`, passlib argon2 metadata access, stale Browserslist database, mixed static/dynamic import of `analysis.js`, and large frontend bundle chunk.
