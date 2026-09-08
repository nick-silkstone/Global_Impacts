# build_country_context.R
#
# Builds/refreshes country_context.csv — the per-country calibration table
# used by the nightly severity-classification step for the Weather Impacts
# Viewer. This is deliberately NOT a hand-typed table: income group and
# population are pulled live from the World Bank API each run, so the
# reference data stays current and auditable rather than going stale.
#
# Output columns:
#   country          - World Bank "name" field (English short name)
#   iso3c            - ISO 3166-1 alpha-3 code
#   income_group     - World Bank FY income classification (Low / Lower middle
#                       income / Upper middle income / High income)
#   population       - most recent available population estimate (SP.POP.TOTL)
#   small_state_flag - TRUE if population <= 1,500,000, matching the World
#                       Bank's own "small states" threshold. This is a stated,
#                       reproducible rule rather than a manually curated list —
#                       it will misclassify a handful of edge cases (e.g. small
#                       *by area* but populous states, or vice versa) which is
#                       why the addendum treats this as one input among several,
#                       not a verdict.
#
# Usage: run standalone, or source() this and call refresh_country_context()
# from the nightly pipeline before the classification step runs.

library(httr)
library(jsonlite)
library(dplyr)

refresh_country_context <- function(out_path = "country_context.csv") {
  
  # --- 1. Income classification ---------------------------------------
  income_url <- "https://api.worldbank.org/v2/country?format=json&per_page=400"
  resp <- GET(income_url)
  stop_for_status(resp)
  income_raw <- fromJSON(content(resp, as = "text", encoding = "UTF-8"))[[2]]
  
  income_df <- income_raw %>%
    as_tibble() %>%
    filter(region$value != "Aggregates") %>%   # drop non-country aggregates
    transmute(
      iso3c        = id,
      country      = name,
      income_group = incomeLevel$value,
      region       = region$value
    )
  
  # --- 2. Population (most recent non-NA year) -------------------------
  pop_url <- "https://api.worldbank.org/v2/country/all/indicator/SP.POP.TOTL?format=json&per_page=20000&mrnev=1"
  resp2 <- GET(pop_url)
  stop_for_status(resp2)
  pop_raw <- fromJSON(content(resp2, as = "text", encoding = "UTF-8"))[[2]]
  
  pop_df <- pop_raw %>%
    as_tibble() %>%
    transmute(
      iso3c      = countryiso3code,
      population = as.numeric(value)
    ) %>%
    filter(iso3c != "")
  
  # --- 3. Join + flag ----------------------------------------------------
  country_context <- income_df %>%
    left_join(pop_df, by = "iso3c") %>%
    mutate(small_state_flag = population <= 1500000) %>%
    filter(income_group != "Aggregates", income_group != "") %>%
    arrange(country)
  
  write.csv(country_context, out_path, row.names = FALSE)
  message(sprintf("Wrote %d countries to %s", nrow(country_context), out_path))
  invisible(country_context)
}

if (sys.nframe() == 0) {
  refresh_country_context()
}