# Rural Health Access Analysis

This project examines whether spatiotemporal access measures (E2SFCA gravity scores) explain county-level mortality variation beyond what physician density and rurality classification (RUCC codes) alone can capture. The analysis covers all contiguous U.S. counties using AHRF 2025, CDC PLACES, Census ACS 5-year, and OSRM drive-time data.

---

## Repository Structure

```
data/               Raw and analytic data files (place inputs here)
output/
  figures/          Choropleth maps, heatmaps, forest plots
  tables/           Summary statistics, regression results (.csv and .tex)
utils.py            Shared helper functions (imported by all scripts)
01_clean.py         Data ingestion, access score construction, analytic dataset
02_eda.py           Descriptive statistics, missingness tables, choropleths
03_ols.py           Correlations, WLS regressions, R² tables, forest plots
04_exploration.py   Subgroup comparisons (Appalachia and Great Plains)
```

---

## Order to Run

### 1. [utils.py](utils.py)

Shared utility functions imported by all other scripts. Do not run directly.

* **Takes in:** Nothing (no I/O of its own)
* **What it does:** Provides reusable functions for numeric coercion (`to_num`), z-scoring (`zscore`), Spearman correlation with significance stars (`spearman_scalar`, `star`), WLS model fitting and tidying (`fit_wls`, `tidy_model`), partial R² and cross-validated R² (`partial_r2`, `cv_r2`), residualized Spearman correlations (`partial_spearman_resid`), and LaTeX/PNG table export (`df_to_latex`, `save_table_csv_tex`, `df_to_booktabs_png`)
* **Outputs:** None

---

### 2. [01_clean.py](01_clean.py)

Data ingestion and cleaning pipeline. **Run this first.** All downstream scripts depend on its output.

* **Takes in:**
  * `data/AHRF2025geo.csv` — Area Health Resources File 2025, geographic module (place manually)
  * `data/AHRF2025hp.csv` — AHRF 2025, health professions module (place manually)
  * `data/AHRF2025pop.csv` — AHRF 2025, population module (place manually)
  * Census API key (hardcoded in script; used to fetch ACS 2022 tract populations and county-level SES variables)
  * OSRM public API (queried live for county-to-county drive times; cached after first run)
  * CDC PLACES 2023 API (queried live for behavioral risk variables; no key required)
  * Census TIGER shapefiles (downloaded automatically from Census GENZ2022 if not cached)

* **What it does:**
  * Merges the three AHRF modules on county FIPS code
  * Downloads Census TIGER county shapefile and builds population-weighted county centroids from ACS 2022 tract data
  * Queries the OSRM routing API to build a county-to-county drive-time matrix (cached in `data/osrm_cache.csv`; set `FORCE_REBUILD_CACHE = False` after the first run)
  * Fetches CDC PLACES 2023 behavioral variables (smoking, obesity) and Census ACS 5-year SES variables (poverty, uninsured rate, median household income, educational attainment)
  * Derives physician density rates (PCPs, cardiologists, EM physicians per 10,000), age composition, mortality rates per 100,000 (all-cause, cancer, stroke, IHD, respiratory, diabetes), and HPSA flags
  * Computes Enhanced 2-Step Floating Catchment Area (E2SFCA) gravity access scores for primary care, cardiology, and emergency medicine
  * Imputes residual missing access scores via spatial neighbor fallback
  * Assigns rurality tiers and rural region labels
  * Filters to contiguous 48 states and counties with population ≥ 500
  * Writes a data dictionary to stdout

* **Outputs:**
  * `data/analytic_dataset.csv` — Main analytic file (~3,072 county rows × ~50 columns); input to all downstream scripts
  * `data/osrm_cache.csv` — Cached drive-time matrix (incremental; preserved across runs)
  * `data/tract_pop_2022.csv` — Cached ACS 2022 tract population counts

---

### 3. [02_eda.py](02_eda.py)

Exploratory and descriptive analysis.

* **Takes in:**
  * `data/analytic_dataset.csv` (output of `01_clean.py`)
  * Plotly GeoJSON county boundaries (fetched automatically from GitHub)

* **What it does:**
  * Builds a sample characteristics table (mean, SD, median, min, max, missingness for all key variables)
  * Computes overall missingness for each variable and mortality missingness broken down by rural region (rural counties only)
  * Generates four multi-panel choropleth maps at 300 DPI
  * Computes within-region partial Spearman correlations (residualized on age and state fixed effects) among RUCC code, PCP density percentile, and E2SFCA score percentile

* **Outputs:**
  * `output/tables/eda_summary_stats.csv` / `.tex` — Table 3 (sample characteristics)
  * `output/tables/eda_missingness_overall.csv` / `.tex` — Table 2, left panel
  * `output/tables/eda_mortality_missingness_by_region.csv` / `.tex` — Table 2, right panel
  * `output/tables/eda_access_rucc_correlation_by_region.csv` / `.tex` — Appendix correlation table
  * `output/figures/choropleth_primary_access.png` — Figure 1 (RUCC code, PCP density, primary care E2SFCA score)
  * `output/figures/choropleth_specialist_access.png` — Appendix Figure 4 (cardiology and emergency access)
  * `output/figures/choropleth_behavior_rurality.png` — Appendix Figure 5 (rurality, smoking, obesity)
  * `output/figures/choropleth_mortality.png` — Appendix Figure 6 (all-cause, IHD, stroke, respiratory mortality)

---

### 4. [03_ols.py](03_ols.py)

Correlation analysis and incremental weighted least squares (WLS) regression.

* **Takes in:**
  * `data/analytic_dataset.csv` (output of `01_clean.py`)

* **What it does:**
  * Computes a partial Spearman correlation matrix among all access measures, residualized on age composition and state fixed effects
  * Computes partial Spearman correlations between each access measure and each mortality outcome; visualizes as a heatmap (negative correlations only)
  * Fits five incremental WLS models per mortality outcome (population-weighted), where RUCC codes are reversed so higher = less rural:
    * **Model 0:** RUCC code only
    * **Model 1:** RUCC code + % under 65 + state fixed effects
    * **Model 2:** Model 1 + outcome-matched physician density
    * **Model 3:** Model 1 + outcome-matched E2SFCA access score
    * **Model 4:** Model 1 + density + access score
  * Computes adjusted R², ΔR² vs. Model 1, partial R² for the access measure, 5-fold cross-validated R², and AIC for each model
  * Generates forest plots showing RUCC code coefficient attenuation from Model 0 through Model 4 for each outcome

* **Outputs:**
  * `output/tables/access_correlations.csv` / `.tex` — Partial Spearman correlation matrix
  * `output/tables/access_mortality_relevant_correlations.csv` — Access–mortality correlations (long form)
  * `output/tables/ols_results_full.csv` — All model coefficients, SEs, CIs, and fit statistics
  * `output/tables/r2_table_primary_allcause.csv` / `.tex` — R² table for primary care / all-cause mortality
  * `output/tables/r2_table_specialist_outcomes.csv` / `.tex` — R² table for cardiology/IHD, emergency/stroke, emergency/respiratory
  * `output/figures/access_spearman_related_only.png` — Access measure correlation heatmap
  * `output/figures/access_mortality_relevant_correlations.png` — Access–mortality heatmap
  * `output/figures/forest_mort_allcause.png` — Forest plot, all-cause mortality
  * `output/figures/forest_mort_heart.png` — Forest plot, IHD mortality
  * `output/figures/forest_mort_stroke.png` — Forest plot, stroke mortality
  * `output/figures/forest_mort_resp.png` — Forest plot, respiratory mortality

---

### 5. [04_exploration.py](04_exploration.py)

Focused subgroup comparisons for two geographically motivated hypotheses.

* **Takes in:**
  * `data/analytic_dataset.csv` (output of `01_clean.py`)

* **What it does:**
  * Defines two regional subgroups:
    * **H4 — Appalachian coal country** (KY, WV, VA, TN): tests whether E2SFCA access scores discriminate respiratory mortality risk better in this subgroup than nationally, motivated by the near-zero correlation between E2SFCA scores and RUCC in the region (ρ = −0.009)
    * **H6 — Great Plains** (ND, SD, NE, KS, OK): tests whether access measures retain discriminating power for IHD and stroke mortality when RUCC variation is compressed (mean RUCC = 8.54, near-zero SD)
  * Computes partial Spearman correlations (residualized on % under 65 and state fixed effects) for each predictor vs. each outcome in both the full national sample and the subgroup
  * Reports Δρ (subsample rho minus full-sample rho) for each predictor
  * Builds a full table (all predictors) and a parsed table retaining only rows where Δρ < −0.05 (access measure meaningfully stronger in subgroup) plus RUCC as reference
  * Saves both tables as CSV and LaTeX

* **Outputs:**
  * `output/tables/subgroup_comparison_combined.csv` / `.tex` — Full subgroup comparison table (all predictors, both regions)
  * `output/tables/subgroup_comparison_parsed.csv` / `.tex` — Table 6 (main text): parsed rows where Δρ < −0.05, with RUCC reference

---

## Notes

**RUCC sign convention:** Raw RUCC codes run 1 (most urban) to 9 (most rural). In `03_ols.py` and `04_exploration.py`, codes are reversed (`ruca_less_rural = 10 − RUCC`) so that higher values indicate less rural counties, consistent with the direction of access measures. Choropleths in `02_eda.py` display raw RUCC codes and are labeled accordingly.

**OSRM cache:** The drive-time matrix API query is slow on first run. After `data/osrm_cache.csv` exists, set `FORCE_REBUILD_CACHE = False` in `01_clean.py` (the default) to skip re-querying.

**Excluded geographies:** Alaska (02), Hawaii (15), and all territories (60, 66, 69, 72, 78) are excluded from all analyses.
