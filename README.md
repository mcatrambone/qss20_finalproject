# Rural Health Access Analysis

This project examines whether spatiotemporal access measures (E2SFCA gravity scores) explain county-level mortality variation beyond what physician density and rurality classification (RUCC codes) alone can capture. The analysis covers all contiguous U.S. counties using AHRF 2025, CDC PLACES, Census ACS 5-year, and OSRM drive-time data.

## Repository Structure

```
data/               
output/
  figures/          Choropleth maps, heatmaps, forest plots
  tables/           Summary statistics, regression results (.csv and .tex)
code/
  utils.py            Shared helper functions (imported by all scripts)
  01_clean.py         Data ingestion, access score construction, analytic dataset
  02_eda.py           Descriptive statistics, missingness tables, choropleths
  03_ols.py           Correlations, WLS regressions, R² tables, forest plots
  04_exploration.py   Subgroup comparisons (Appalachia and Great Plains)
```

---

## Data files 
### 1. [utils.py](code/utils.py)

Shared utility functions imported by all other scripts.

Provides reusable functions for numeric coercion (`to_num`), z-scoring (`zscore`), Spearman correlation with significance stars (`spearman_scalar`, `star`), WLS model fitting and tidying (`fit_wls`, `tidy_model`), partial R² and cross-validated R² (`partial_r2`, `cv_r2`), residualized Spearman correlations (`partial_spearman_resid`), and LaTeX/PNG table export (`df_to_latex`, `save_table_csv_tex`, `df_to_booktabs_png`)

Does not input or output anything. 

---

### 2. [01_clean.py](code/01_clean.py)

Data ingestion and cleaning pipeline. 

* **Inputs:**
  * `data/AHRF2025geo.csv` (AHRF geographic data)
  * `data/AHRF2025hp.csv` (AHRF 2025 health professions data)
  * `data/AHRF2025pop.csv` (AHRF 2025, population module data)
  * Census API key (Further population and SES data)
  * OSRM public API (Live coded drive times)
  * CDC PLACES 2023 API (Behavioral risk variables; no key required)
  * Census TIGER shapefiles (Downloaded automatically from Census GENZ2022 if not cached)

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
  * `data/analytic_dataset.csv` — Main analytic file 
  * `data/osrm_cache.csv` — Cached drive-time matrix
  * `data/tract_pop_2022.csv` — Cached ACS 2022 tract population counts

### 3. [02_eda.py](code/02_eda.py)

Exploratory and descriptive analysis.

* **Inputs:**

  * `data/analytic_dataset.csv`
  * Plotly GeoJSON county boundaries (fetched automatically from GitHub)

* **What it does:**

  * Builds a sample characteristics table
  * Computes overall missingness for each variable and mortality missingness broken down by rural region
  * Generates choropleth maps
  * Computes within-region partial Spearman correlations (residualized on age and state fixed effects) among RUCC code, PCP density percentile, and E2SFCA score percentile

* **Outputs:**

  * `output/tables/tab2_eda_summary_stats.csv` / `.tex` — Table 2
  * `output/tables/tab6_eda_missingness_overall.csv` / `.tex` — Table 6, left panel
  * `output/tables/tab6_eda_mortality_missingness_by_region.csv` / `.tex` — Table 6, right panel
  * `output/tables/tab7_eda_access_rucc_correlation_by_region.csv` / `.tex` — Table 7
  * `output/figures/fig1_choropleth_primary_access.png` — Figure 1 (RUCC code, PCP density, primary care E2SFCA score)
  * `output/figures/fig3_choropleth_specialist_access.png` — Appendix Figure 3 (cardiology and emergency access)
  * `output/figures/fig4_choropleth_behavior_rurality.png` — Appendix Figure 4 (rurality, smoking, obesity)
  * `output/figures/fig5_choropleth_mortality.png` — Appendix Figure 5 (all-cause, IHD, stroke, respiratory mortality)

---

### 4. [03_ols.py](code/03_ols.py)

Correlation analysis and incremental weighted least squares (WLS) regression.

* **Inputs:**

  * `data/analytic_dataset.csv`

* **What it does:**

  * Computes a partial Spearman correlation matrix among all access measures, residualized on age composition and state fixed effects
  * Computes partial Spearman correlations between each access measure and each mortality outcome; visualizes as a heatmap
  * Fits five incremental WLS models per mortality outcome (population-weighted)
  * Generates forest plots showing RUCC code coefficient attenuation from Model 0 through Model 4 for each outcome

* **Outputs:**

  * `output/tables/tab3_access_correlations.csv` / `.tex` — Table 3

  * `output/tables/tab4_r2_table_primary_allcause.csv` / `.tex` — Table 4

  * `output/tables/tab8_r2_table_specialist_outcomes.csv` / `.tex` — Table 8

  * `output/figures/fig2_access_mortality_relevant_correlations.png` — Access–mortality correlation heatmap

  * `output/figures/fig6_forest_mort_allcause.png` — Forest plot, all-cause mortality

  * `output/figures/fig7_forest_mort_heart.png` — Forest plot, IHD mortality

  * `output/figures/fig8_forest_mort_resp.png` — Forest plot, respiratory mortality

  * `output/figures/fig9_forest_mort_stroke.png` — Forest plot, stroke mortality

---

### 5. [04_exploration.py](code/04_exploration.py)

Focused subgroup comparisons for two geographically motivated hypotheses.

* **Takes in:**

  * `data/analytic_dataset.csv` (output of `01_clean.py`)

* **What it does:**

  * Defines two regional subgroups:

    * **H4 — Appalachian coal country** (KY, WV, VA, TN): tests whether E2SFCA access scores discriminate respiratory mortality risk better in this subgroup than nationally, motivated by the near-zero correlation between E2SFCA scores and RUCC in the region (ρ = −0.009)
    * **H6 — Great Plains** (ND, SD, NE, KS, OK): tests whether access measures retain discriminating power for IHD and stroke mortality when RUCC variation is compressed (mean RUCC = 8.54, near-zero SD)
  * Computes partial Spearman correlations (residualized on % under 65 and state fixed effects) for each predictor vs. each outcome in both the full national sample and the subgroup
  * Reports Δρ (subsample rho minus full-sample rho) for each predictor
  * Builds a parsed table retaining only rows where Δρ < −0.05 (access measure meaningfully stronger in subgroup) plus RUCC as reference

* **Outputs:**

  * `output/tables/tab5_subgroup_comparison_parsed.csv` / `.tex` — Table 5: parsed rows where Δρ < −0.05, with RUCC reference

---

## Notes

**RUCC sign convention:** Raw RUCC codes run 1 (most urban) to 9 (most rural). In `03_ols.py` and `04_exploration.py`, codes are reversed (`ruca_less_rural = 10 − RUCC`) so that higher values indicate less rural counties, consistent with the direction of access measures. Choropleths in `02_eda.py` display raw RUCC codes and are labeled accordingly.

**OSRM cache:** The drive-time matrix API query is slow on first run. After `data/osrm_cache.csv` exists, set `FORCE_REBUILD_CACHE = False` in `01_clean.py` (the default) to skip re-querying.

**Excluded geographies:** Alaska (02), Hawaii (15), and all territories (60, 66, 69, 72, 78) are excluded from all analyses.
