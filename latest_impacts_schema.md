# latest_impacts.csv — Schema

One row = one country's impacts from one event. Multi-country events (see
Section 3 of the severity addendum) produce multiple rows sharing an
`event_id`. Assessed against the Impact Level schema + addendum.

| # | Column | Type | Allowed values / format | Notes |
|---|---|---|---|---|
| 1 | `impact_id` | text | e.g. `2026-09-08-001` | Unique per row. Primary key — this is what the merge/prune/archive script keys off for dedupe. |
| 2 | `event_id` | text | e.g. `EVT-2026-014` | Shared across every row belonging to the same underlying event. Assigned once, reused on later trawl nights as the event continues to unfold. |
| 3 | `parent_event_name` | text | e.g. `Hurricane Mirela` | Keep spelling/wording identical across all rows and all nights for the same event — the merge script matches on this plus `event_id`. |
| 4 | `hazard_category` | text | `Weather` \| `Geophysical` | Top-level split. |
| 5 | `hazard_type` | text | See hazard type list below | Specific cause. |
| 6 | `country` | text | Must match `country` in `country_context.csv` exactly | Join key for severity calibration and for the dashboard's country lookup. |
| 7 | `iso3c` | text | 3-letter ISO code, e.g. `NPL` | Join key for the map choropleth colouring. |
| 8 | `locality` | text | e.g. `Sindhupalchok District` | Sub-national detail for the map popup/description — not used for colouring. |
| 9 | `lat` | number | decimal degrees | See geolocation_confidence — this may be a district/region centroid, not a precise point. |
| 10 | `lon` | number | decimal degrees | As above. |
| 11 | `geolocation_confidence` | text | `precise` \| `locality` \| `region` \| `country` | How tightly the lat/lon is actually known, per the source reporting. |
| 12 | `date_occurred` | date | `YYYY-MM-DD` | Last date the **physical hazard itself** was actively occurring at this location — not the event's overall start date for multi-country cases, and not the date of the most recent casualty/damage-report update. Moves forward only if the hazard genuinely continues or recurs (another day of a heatwave, a storm still tracking through); never moves forward for revised casualty figures or rescue-effort news alone. See addendum Section 3. |
| 13 | `date_logged` | date | `YYYY-MM-DD` | Date this row was first written by the trawl. |
| 14 | `date_last_updated` | date | `YYYY-MM-DD` | Date this row's fields were last revised (e.g. a casualty figure firmed up on a later night). Equals `date_logged` on first write. |
| 15 | `severity_level` | text | `Low` \| `Medium` \| `High` | Very Low is out of scope by design — your own schema doc excludes it from standard logging. |
| 16 | `severity_confidence` | text | `confirmed` \| `provisional` \| `estimated` | Per addendum Section 1. |
| 17 | `casualties` | integer or blank | | Blank, not zero, if genuinely unknown — zero means confirmed no casualties. |
| 18 | `displaced` | integer or blank | | As above. |
| 19 | `support_required` | text | `local` \| `national` \| `international` \| blank | Highest level of support mentioned in reporting so far. |
| 20 | `recovery_time_estimate` | text | `days` \| `weeks` \| `months` \| `years` \| blank | |
| 21 | `cost_pct_gdp` | number or blank | | Usually blank at first pass — see addendum Section 1. Revisable in later updates. |
| 22 | `severity_rationale` | text (free) | | Which schema rows drove the call, and whether/how `income_group` or `small_state_flag` shifted it — per addendum Section 2. |
| 23 | `description` | text (free) | 2–4 sentences | Brief summary of the impact itself. |
| 24 | `source_1_url` | text (URL) | | Most reputable source. |
| 25 | `source_2_url` | text (URL) | | |
| 26 | `source_3_url` | text (URL) or blank | | Optional third source. |

## Hazard type list

**Weather:**
`Tropical Cyclone` · `Flood` · `Severe Storm/Wind` · `Tornado` · `Wildfire` ·
`Heatwave` · `Cold Wave/Winter Storm` · `Drought`

**Geophysical (non-weather-attributed):**
`Earthquake` · `Volcanic Eruption` · `Tsunami` · `Landslide/Glacier Failure`

A landslide or glacier failure only goes under Geophysical when reporting
doesn't attribute it to recent rainfall/weather (e.g. the August 2026 Nepal
glacier collapse). If a source does attribute a landslide to recent heavy
rain, log it under Weather → `Flood` instead, with the landslide noted in
`description`.

## Why 10 days

The 10-day window is a deliberate compromise between this dataset's two
operational uses: situational awareness of recent weather/geohazard
exposure (where ~14 days back is the more natural window — e.g. does
today's rain worsen a wildfire burn scar or a recent landslide zone?), and
verifying a 7-day forecast product against what actually occurred. 10 days
covers the forecast-verification case with a few days' margin and stays
close enough to the situational-awareness case to remain useful for both,
without the dataset drifting into being a general disaster-recovery feed.

## Notes for the merge/prune/archive script

- Match on `impact_id` for updates (revising an existing row) vs. inserts
  (a genuinely new row).
- Prune on `date_occurred` older than 10 days — not `date_logged`, since a
  slow-to-report event shouldn't be kept alive past its actual impact date,
  and a multi-country event's earlier-hit countries should drop off before
  its later-hit countries do.
- Archive the previous day's full file as `YYYY_MM_DD_impacts.csv` before
  writing the new merged version.
