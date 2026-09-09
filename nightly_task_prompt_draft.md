# Nightly Weather & Geophysical Impacts Trawl — Task Prompt (DRAFT)

Scheduled to run once daily, 02:00–03:00 UK time.

## Objective

Search reputable media and monitoring sources for severe weather impacts
(and select non-weather geophysical hazards) from the **past 10 days**.
Extract, geolocate, classify, and log each one as a row in a candidate CSV
for merging into the live dataset.

## Reference material (read these first, every run)

- Severity criteria: https://raw.githubusercontent.com/nick-silkstone/Global_Impacts/refs/heads/main/severity_impact_level_schema.md
- Classification addendum (incomplete data, country calibration, multi-country events): https://raw.githubusercontent.com/nick-silkstone/Global_Impacts/refs/heads/main/severity_classification_addendum.md
- Row schema: https://raw.githubusercontent.com/nick-silkstone/Global_Impacts/refs/heads/main/latest_impacts_schema.md
- Country calibration data: https://raw.githubusercontent.com/nick-silkstone/Global_Impacts/refs/heads/main/country_context.csv
- Current live dataset (to avoid re-logging existing events — check `event_id`/`parent_event_name` before assigning a new one): https://raw.githubusercontent.com/nick-silkstone/Global_Impacts/refs/heads/main/latest_impacts.csv

## Scope

**Weather hazards:** Tropical Cyclone, Flood, Severe Storm/Wind, Tornado,
Wildfire, Heatwave, Cold Wave/Winter Storm, Drought.

**Geophysical hazards (log only these, not weather-caused ones):**
Earthquake, Volcanic Eruption, Tsunami, Landslide/Glacier Failure — only
when NOT attributed by sources to recent rainfall/weather (a landslide
attributed to recent heavy rain goes under Flood instead, per the schema
doc).

**Severity floor:** log Low, Medium, and High impact events only. Very Low
impacts are out of scope by design — do not log them even if found.

## Sources

- Wire services: Reuters, Associated Press, AFP
- Major outlets: BBC, The Guardian, Al Jazeera
- Specialist natural hazards news websites: https://watchers.news/  and https://www.accuweather.com/en/weather-news 
- Geophysical monitoring: USGS (earthquakes), Smithsonian Global Volcanism
  Program (eruptions), GDACS, https://mapping.emergency.copernicus.eu/ 
- Humanitarian/impact tracking: ReliefWeb, national disaster management
  agency releases where available


Prefer sources that appear in 2 of these categories for the same event
where possible. Do not use unverified social media, blogs, or single-source
tabloid reporting as a primary source — cross-reference against at least
one wire service or monitoring body before logging.

## Process, per event found

1. Identify the event and check `latest_impacts.csv` for an existing
   `event_id`/`parent_event_name` match — reuse it if found, don't create
   a duplicate thread.
2. If the event affects multiple countries, create one row per country
   per the addendum's multi-country guidance — do not merge them into one
   row or one severity level.
3. Geolocate as precisely as the reporting allows; set
   `geolocation_confidence` honestly rather than guessing a precise point.
4. Classify severity using the Impact Level schema, the addendum's
   incomplete-data handling, and `country_context.csv` for calibration.
   Fill `severity_rationale` explaining the call.
5. Write description (2–4 sentences) and 2–3 source URLs, most reputable
   first.
6. If this is a revision of an existing logged event (firmer numbers,
   updated severity), update that row's fields and `date_last_updated`
   rather than creating a new row — keep the same `impact_id`.

## Output

Write all new and updated rows to `candidate_impacts.csv` in the repo root
(overwrite each run — this file represents only this run's findings, not
a running total). Match the exact column order and types in
`latest_impacts_schema.md`. Commit and push to the repo with a commit
message noting the date and rough count of new/updated rows found.

Do NOT modify `latest_impacts.csv` directly — the merge, prune (10-day
window on `date_occurred`), and archive step is handled separately by a
scheduled script.

## If nothing found

Still commit an empty `candidate_impacts.csv` (header row only) so the
downstream Action has a consistent file to check, and note "no new
impacts found" in the commit message.
