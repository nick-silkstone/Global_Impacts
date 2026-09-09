# Severity Classification Addendum

Companion to the Impact Level schema (Very Low / Low / Medium / High) for the
Weather Impacts Viewer nightly trawl. This addendum covers two problems the
base schema doesn't solve on its own: incomplete information, and
country-relative calibration. It's meant to be pasted into the nightly
scheduled-task prompt alongside the schema itself.

## 1. Handling incomplete or early-stage reporting

Impacts logged within 10 days of an event will often be reported before firm
casualty counts, displacement figures, or cost estimates exist. Do not wait
for certainty, and do not silently invent a number. Instead:

- **Assess on whichever schema rows have information**, not just casualties.
  If a report says "government has requested international assistance" and
  "shelters are over capacity," that alone supports Medium/High under the
  Support Required and Displaced rows, even with no casualty figure yet.
- **Casualties are not the deciding factor by default.** The five rows
  (Casualties, Displaced, Support Required, Recovery Time, Costs) are read
  together. When they point to different levels, the impact level defaults to
  whichever level the *majority* of available rows support; if it's a genuine
  tie, take the higher of the two.
- **Tag confidence explicitly.** Every logged impact gets a
  `severity_confidence` field: `confirmed` (the report cites hard figures for
  most rows), `provisional` (based on qualitative language — evacuations,
  aid appeals, military deployment — with few or no hard numbers yet), or
  `estimated` (assessor's best judgement from fragmentary reporting). This
  keeps false precision visible on the dashboard rather than hidden inside a
  single confident-looking label.
- **Costs (% GDP) will usually be blank at first pass.** Reconstruction and
  insurance-loss estimates typically emerge weeks to months after an event.
  Leave this field blank rather than guessing, and treat it as revisable: a
  later trawl run may update an existing CSV row's cost field once real
  estimates appear, without changing the row's date or location.
- **Revise, don't duplicate.** If a later night's trawl finds firmer numbers
  for an already-logged event, update that row in place (matched on
  event date + location + hazard type) rather than adding a second entry.

## 2. Country-relative calibration

The schema's own worked examples (Caribbean island vs. USA/Western Europe)
make clear that severity is judged against a country's capacity to absorb
the impact, not against a fixed global casualty/cost scale. Two countries
with numerically similar rainfall totals and casualty counts can land at
different Impact Levels depending on the affected country's size, wealth,
and infrastructure.

`country_context.csv` (built by `build_country_context.R`, refreshed from
live World Bank data — see that script for details) provides the calibration
inputs:

| Field | Use |
|---|---|
| `income_group` | Proxy for infrastructure resilience and capacity for domestic-only recovery. Low/Lower-middle income countries reach Medium/High more readily on the same raw casualty or displacement numbers than High income countries, per the schema's own worked examples. |
| `small_state_flag` | Population ≤1.5M (World Bank's own small-states threshold). A flagged country reaching out for international support is a stronger High-impact signal than the same request from a large country, since it implies domestic capacity is genuinely exhausted rather than just slow to mobilise. |

**How to apply it:** treat `income_group` and `small_state_flag` as
*adjustments to which row of the schema an outcome maps to*, not as
separate scoring criteria. For example: "several hundred people
sheltering after river flooding" in a Low-income, small-population country
is consistent with Medium-to-High (strained local capacity is expected at
lower absolute numbers); the identical sentence about a High-income, large
country is more consistent with Low-to-Medium, since the same numbers
represent a much smaller share of national capacity.

This is a heuristic, not a formula — don't compute a weighted score. Use it
to sanity-check an initial read of the five schema rows, and note in the
event's rationale field when the country context shifted the assessment up
or down a level from what raw casualty/cost numbers alone would suggest.

**Known limitation:** `small_state_flag` is population-only and will
misclassify countries that are small in *area or exposure* but populous
(or vice versa). Where this looks wrong for a specific event, override it
and note why in the rationale field — the flag is a starting heuristic, not
a rule to apply mechanically.

## 3. Cross-border and multi-country events

Some events — long-track hurricanes are the clearest case, but also
widespread flooding, wind, or wildfire episodes — cause impacts in more
than one country, often on different days as the event tracks or spreads,
and with wildly different severity in each. A hurricane can be High impact
for a small Caribbean nation at landfall and Low impact days later as a
weakened system brushes a large, wealthy coastline.

**Log one row per country, not one row per event.** Each country a given
event affects gets its own row: its own date (or date range), its own
location/geolocation, its own severity assessment (using that country's
own `country_context.csv` entry per Section 2), and its own casualties/
displacement/support/cost figures. Do not average or roll these up into a
single severity level for the event as a whole — that would hide exactly
the contrast (small nation devastated, large nation barely touched) the
country-relative calibration in Section 2 exists to capture. This is also
what lets the dashboard colour each affected country on the map by its own
severity level, rather than one blended value smeared across all of them.

**Link the rows with a shared `event_id`.** Each country-level row also
carries a `parent_event_name` (e.g. "Hurricane Mirela") and an `event_id`
shared across every row that traces back to the same underlying event.
This is what lets the dashboard offer a "show full track" view — grouping
a hurricane's country-by-country impacts into one story — without forcing
severity itself to be a single event-wide number. Two fields carry this:

| Field | Purpose |
|---|---|
| `event_id` | Shared across all country-level rows belonging to one underlying event. Assign on first sighting of the event and reuse on later trawl nights as it continues to unfold — don't mint a new `event_id` each night for the same storm. |
| `impact_id` | Unique per row (per country per event) — this is the primary key the merge/prune/archive script keys off. |

**Dating a multi-day, multi-country event:** use the date impacts actually
materialised *in that country* for each row, not the event's overall start
date. A hurricane that forms on day 1 and makes landfall in Country A on
day 3 and Country B on day 6 produces two rows with two different dates,
both carrying the same `event_id`. This keeps the 10-day pruning window
(Section 1 / the CSV housekeeping script) correct per country, rather than
either pruning a country's row too early or keeping the whole event alive
past 10 days because one country's impact is more recent than another's.

**Naming consistency matters for linking.** Use the same `parent_event_name`
spelling/wording across all rows and all trawl nights for the same event
(don't let one night log "Hurricane Mirela" and a later night log "Storm
Mirela") — the merge script matches on this alongside `event_id`, and
inconsistent naming will silently create duplicate event threads.
