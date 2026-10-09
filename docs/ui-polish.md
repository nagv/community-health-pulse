# UI polish and responsive layout

Changes:
- Replaced the broad sidebar descendant colour rule with scoped text, button, uploader and navigation styles.
- Restored readable secondary, primary and disabled button labels, including nested Markdown text.
- Added clearer white cards, borders, typography, spacing and focus outlines.
- Made navigation and form labels visible by default.
- Enabled value labels for line and bar charts; added explicit axes, label padding and category wrapping.
- Dense timelines show spaced value labels while retaining every data point and hover value.
- Added container breakpoints: filters/metrics wrap below 1050px workspace width; charts/chat stack below 850px; filters become one column below 480px.
- Mobile viewport spacing and automatic sidebar state are configured.
- Disabled Streamlit chart theming so it cannot override the specified chart colours and labels.

Verification:
- 41 tests passed, including five new chart regression tests and the existing Streamlit AppTests.
- Ruff lint and formatting checks passed.
- Existing API health: ok; frontend health: HTTP 200.
- Live browser visual verification remains unavailable: the browser tool rejected local-page access through its URL security policy. No alternate browser or policy workaround was attempted.

Refresh the application to load the updated UI. These changes do not require restarting the backend.

## Reference-inspired layout update

Reference: https://ad-campaign-analyzer.streamlit.app/

- Moved the three workspace options into a horizontal, wrapping navigation row below the heading and selection summary. Native radio behavior retains keyboard navigation and selected state.
- Moved dataset filters into the sidebar, retaining the same dataset-specific widget keys across sections.
- Added a summary of active dates, localities, ages, conditions, genders and calculated recorded visits to all three sections.
- Applied Source Sans typography, compact headings, lighter card styling and teal selected states.
- Retained chart value labels, responsive chart/chat stacking and distinct empty states.
- Navigation tests verify dataset, filters and conversation survive section changes; sidebar placement and summary updates are covered.

Validation: 44 deterministic tests pass; Ruff checks pass. Local visual and viewport verification remains unavailable under the previously reported browser restriction.

## Review follow-up (week 1)

Fixes:
- Chat chart clipping: the chat message body is a flex item beside the avatar; without `min-width: 0` it kept Plotly's earlier, wider SVG width after a resize, so bars and value labels were cut off. Verified in a browser by measuring element bounds at 279, 900 and 1280 px, and by removing the rule to reproduce the overflow.
- Agent timeouts: model timeout 15 s with one retry, so a retried call fits inside the 60 s request deadline (previously 25 s × 3 attempts could exceed it).
- Replaced deprecated `use_container_width` with `width="stretch"`.

UI:
- Filters are a sidebar form: quick range (All dates / Last 7, 30, 90 days / Custom range), From/To dates, locality, age band, condition and gender, applied with **Apply filters**; **Reset** restores the full dataset range. Edited dates switch the quick range to Custom.
- KPIs: recorded visits with change vs the equally long previous period, average visits per day, top condition with share, busiest locality. The always-100% completeness card is no longer a KPI; validation details moved to a sidebar "Dataset details" expander.
- Explore Data pages with Previous/Next and formats its table columns.
- Chat: suggestion chips only before the first message; a status indicator while the agent runs; the right panel shows the current selection instead of repeating each answer's steps.
- Overview exports the condition table as CSV (full JSON export kept).

Code:
- `frontend/app.py` split into `state.py`, `components/` (sidebar, filters, kpis, chart) and `views/` (overview, explore, chat).
- API responses are cached per dataset, filters and page; health is re-checked at most every 30 s per session; Ask the Data uses the lighter `POST /datasets/{id}/summary`.
- `Analysis` (with derived age bands) is built once per dataset at load time instead of on every request.
- Dashboard charts are looked up by `result_id`, not list position.
