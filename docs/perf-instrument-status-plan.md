# Performance Fix Plan: Instrument Status Tab

## Problem

When navigating to the Instrument Status (CSS Status) tab, the app becomes very slow to respond to clicks, inputs, and selects.

### Root Cause

A cascade of redundant re-renders in `PVPlot` from `nova.epics.trame`:

1. **All 7 PVPlot instances re-render on ANY PV change** — each registers `@self.server.state.change("epics")`, which fires for all ~51 PVs, not just its own.
2. **No debouncing on PV flush** — each PV subscription calls `dirty("epics"); flush()` immediately in JS.
3. **The 2D heatmap (data_width=1105) is expensive** — numpy resize + full Plotly figure on every call.
4. **All 5 sub-tab plot panels render simultaneously** — uses `v_show` (CSS hidden) instead of `v_if` (conditional DOM), so hidden PVPlots still respond to state changes.
5. **51 DisconnectedAlert instances** — each PVInput creates one.

Multiplication effect: `N PV updates/sec x 7 PVPlot re-renders = 7N Plotly figure rebuilds/sec`, saturating both the Python event loop and the browser main thread.

---

## Plan

### Phase 1: App-level quick wins — v_show to v_if (DONE)

| Step | Change | File | Impact |
|------|--------|------|--------|
| 1.1 | Outer tab: `v_show` -> `v_if` | `views/tab_content_panel.py:33` | **Very High** — zero PVPlot callbacks when on other tabs |
| 1.2 | Inner sub-tabs: `v_show` -> `v_if` | `views/css_status.py` (lines 61,78,95,112,129) | **High** — only active sub-tab's PVPlot fires |

**Effect:** When user is on another tab, the entire Instrument Status DOM is destroyed — zero server-side callbacks. When on the tab, only the active sub-tab's PVPlot exists, reducing renders from 7 to ~3 per PV change.

**Trade-off:** Switching to/from the tab has a brief initialization cost as components are created/destroyed. Acceptable for a monitoring tab.

### Phase 2: JS-side debouncing (NOT YET DONE)

Inject a debounced `flush()` after EPICS `connect()` call in `main_view.py` to collapse N rapid PV updates into 1 batched state change (~200ms window).

**Risk:** Global flush monkey-patch could affect other widgets' responsiveness. Safer variant: EPICS-only debounce via subclassed `TrameEPICS.connect()`.

### Phase 3: Guarded PVPlot subclass (NOT YET DONE)

Subclass `PVPlot` with per-PV change detection to skip `render_figure()` + `figure.update()` when this PV's data hasn't changed. Avoids expensive numpy/plotly rebuild and Trame push for unchanged plots.

**Risk:** Couples app to library internals. Pin `nova-epics` version.

### Phase 4: Upstream library fixes (NOT YET DONE)

- Per-PV state keys instead of single `"epics"` blob
- Built-in JS debounce in `connect()`
- Consolidate `DisconnectedAlert` (58 instances -> 1)

---

## Status

- [x] Phase 1 — completed 2026-03-31
- [ ] Phase 2
- [ ] Phase 3
- [ ] Phase 4
