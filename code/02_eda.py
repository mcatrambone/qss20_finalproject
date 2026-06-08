"""
02_eda.py
---------
Exploratory and descriptive analysis.

Tasks:
  - Summary statistics table (LaTeX + CSV)
  - Overall missingness table for all key variables (LaTeX + CSV)
  - Mortality missingness by rural region (LaTeX + CSV)
  - Choropleths: primary care access, specialist access,
                 rurality + behavioral risk, mortality rates
  - Regional partial Spearman correlations: RUCC vs PCP density
    vs E2SFCA scores, by region (Appendix Table)

Notes on RUCC Code:
  Choropleths show raw RUCC codes 1-9 (1 = most urban, 9 = most rural).
  The sign of RUCC is NOT flipped here. The analytical decision to reverse
  RUCC codes in regression models (so that higher = less rural, consistent
  with the direction of access measures) is described in 03_ols.py.

Inputs:
  data/analytic_dataset.csv

Outputs:
  output/tables/tab2_eda_summary_stats.csv / .tex
  output/tables/tab6_eda_missingness_overall.csv / .tex
  output/tables/tab6_eda_mortality_missingness_by_region.csv / .tex
  output/tables/tab7_eda_access_rucc_correlation_by_region.csv / .tex
  output/figures/fig1_choropleth_primary_access.png
  output/figures/fig3_choropleth_specialist_access.png
  output/figures/fig4_choropleth_behavior_rurality.png
  output/figures/fig5_choropleth_mortality.png
"""

import os
import warnings
import requests
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from scipy import stats
from numpy.linalg import lstsq

from utils import to_num, first_existing, df_to_latex, df_to_booktabs_png

warnings.filterwarnings("ignore")

os.makedirs("output/tables",  exist_ok=True)
os.makedirs("output/figures", exist_ok=True)

try:
    plt.rcParams["font.family"] = "Arial"
except Exception:
    pass

DPI       = 300
EXCL_FIPS = {"02", "15", "60", "66", "69", "72", "78"}
GEO_URL   = ("https://raw.githubusercontent.com/plotly/datasets/"
              "master/geojson-counties-fips.json")

# ---------------------------------------------------------------------------
# 1. Table-building functions
# ---------------------------------------------------------------------------

def summary_table(df, spec):
    """Build descriptive statistics table from a variable spec list."""
    rows = []
    for col, label, units in spec:
        if col not in df.columns:
            continue
        s = pd.to_numeric(df[col], errors="coerce")
        rows.append({
            "Variable":    label,
            "Units":       units,
            "N":           int(s.notna().sum()),
            "Missing (%)": round(s.isna().mean() * 100, 1),
            "Mean":        round(s.mean(), 2),
            "SD":          round(s.std(), 2),
            "Median":      round(s.median(), 2),
            "Min":         round(s.min(), 2),
            "Max":         round(s.max(), 2),
        })
    return pd.DataFrame(rows)


def missingness_overall(df, spec):
    """
    Overall missingness table. Total N in caption, not repeated per row.
    Columns: Variable, N Missing, Missing (%).
    """
    n_total = len(df)
    rows = []
    for col, label, _ in spec:
        miss = int(df[col].isna().sum()) if col in df.columns else n_total
        rows.append({
            "Variable":    label,
            "N Missing":   f"{miss:,}",
            "Missing (%)": round(miss / n_total * 100, 1) if n_total else np.nan,
        })
    return pd.DataFrame(rows)


def mortality_missingness_by_region(df, mort_cols, region_col="rural_region"):
    """
    Missingness in mortality outcomes by rural region (rural counties only).
    Rows = region, columns = outcomes. Cells: 'n missing (pct%)'.
    """
    MORT_LABELS = {
        "mort_allcause": "All-Cause",
        "mort_heart":    "IHD",
        "mort_resp":     "Respiratory",
        "mort_stroke":   "Stroke",
    }
    rural = df[df.get("rurality_tier", pd.Series("Rural", index=df.index)) == "Rural"].copy()
    if region_col not in rural.columns:
        return pd.DataFrame()

    rows = []
    for region in sorted(rural[region_col].dropna().unique()):
        sub = rural[rural[region_col] == region]
        n = len(sub)
        row = {"Region": region, "N": f"{n:,}"}
        for col in mort_cols:
            label = MORT_LABELS.get(col, col)
            if col not in sub.columns or n == 0:
                row[label] = "—"
                continue
            miss = int(sub[col].isna().sum())
            pct = miss / n * 100 if n else np.nan
            row[label] = f"{miss:,} ({pct:.1f}%)"
        rows.append(row)
    return pd.DataFrame(rows)


def add_pctile(df, source_col, pctile_col=None):
    """Add a national percentile rank column (0-100) for source_col."""
    if source_col not in df.columns:
        return None
    pctile_col = pctile_col or f"{source_col}_pctile_map"
    x = pd.to_numeric(df[source_col], errors="coerce")
    df[pctile_col] = x.rank(pct=True, na_option="keep") * 100
    return pctile_col


# ---------------------------------------------------------------------------
# 2. Regional partial Spearman correlation table (Appendix)
#    Tests whether PCP density and E2SFCA track RUCC differently by region,
#    and whether the two access measures are correlated with each other.
# ---------------------------------------------------------------------------

def partial_spearman_pair(x, y, covariates):
    """
    Residualise x and y on covariates via OLS, return Spearman rho and p.
    Used by access_rucc_correlation_by_region.
    """
    mask = (
        np.isfinite(x) & np.isfinite(y) &
        np.all(np.isfinite(covariates), axis=1)
    )
    x, y, cov = x[mask], y[mask], covariates[mask]
    if len(x) < 10:
        return np.nan, np.nan

    def resid(v):
        coef, *_ = lstsq(cov, v, rcond=None)
        return v - cov @ coef

    rho, p = stats.spearmanr(resid(x), resid(y))
    return round(float(rho), 3), round(float(p), 3)


def format_rho(rho, p):
    """Format rho with significance stars."""
    if np.isnan(rho):
        return "—"
    stars = (
        "***" if p < 0.001 else
        "**"  if p < 0.01  else
        "*"   if p < 0.05  else ""
    )
    return f"{rho:.3f}{stars}"


def access_rucc_correlation_by_region(
    df,
    pcp_pct_col="pcp_per_10k_pctile_map",
    access_pct_col="primary_access_score_pctile_map",
    rucc_col="ruca_raw",
    age_col="pct_under65",
    region_col="rural_region",
):
    """
    Within each region, compute three partial Spearman correlations
    residualised on age composition and state fixed effects:
        1. rho(PCP density percentile, RUCC Code)
        2. rho(E2SFCA score percentile, RUCC Code)
        3. rho(PCP density percentile, E2SFCA score percentile)

    Regions where rho(PCP-RUCC) >> rho(E2SFCA-RUCC) indicate settings
    where rurality predicts physician supply but not spatiotemporal
    reachability. Near-zero rho(PCP-E2SFCA) confirms orthogonality.
    """
    state_dummies = pd.get_dummies(
        df["fips_st_cnty"].str[:2], prefix="st", drop_first=True
    ).astype(float)

    age  = pd.to_numeric(df[age_col],       errors="coerce").values
    rucc = pd.to_numeric(df[rucc_col],      errors="coerce").values
    pcp  = pd.to_numeric(df[pcp_pct_col],   errors="coerce").values
    acc  = pd.to_numeric(df[access_pct_col],errors="coerce").values

    X_base = np.column_stack([age, state_dummies.values, np.ones(len(df))])

    def row_for(label, idx):
        idx = np.array(idx)
        r1, p1 = partial_spearman_pair(pcp[idx],  rucc[idx], X_base[idx])
        r2, p2 = partial_spearman_pair(acc[idx],  rucc[idx], X_base[idx])
        r3, p3 = partial_spearman_pair(pcp[idx],  acc[idx],  X_base[idx])
        n = int(np.sum(
            np.isfinite(pcp[idx]) &
            np.isfinite(acc[idx]) &
            np.isfinite(rucc[idx])
        ))
        return {
            "Region":         label,
            "N":              n,
            "ρ PCP–RUCC":    format_rho(r1, p1),
            "ρ E2SFCA–RUCC": format_rho(r2, p2),
            "ρ PCP–E2SFCA":  format_rho(r3, p3),
        }

    rows = [row_for("All counties", np.arange(len(df)))]
    for region, grp in df.groupby(region_col):
        rows.append(row_for(region, grp.index))

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 3. Choropleth drawing functions
# ---------------------------------------------------------------------------

def draw_panel(ax, gdf, col, title, cmap="viridis",
               missing_color="#f0f0f0", is_rucc=False):
    """
    Draw one choropleth panel onto ax.
    - is_rucc=True: discrete RUCC 1-9 scale with labeled colorbar.
    - Otherwise: continuous percentile scale (1st-99th percentile range).
    Missing counties rendered in near-white (#f0f0f0).
    """
    if col not in gdf.columns:
        ax.set_title(title + "\n(data not available)", fontsize=10, fontweight="bold")
        ax.axis("off")
        return

    plot_gdf = gdf.copy()
    plot_gdf[col] = pd.to_numeric(plot_gdf[col], errors="coerce")
    missing_gdf = plot_gdf[plot_gdf[col].isna()]
    good_gdf    = plot_gdf.dropna(subset=[col])

    if not missing_gdf.empty:
        missing_gdf.plot(ax=ax, color=missing_color,
                         linewidth=0.05, edgecolor="white")

    if good_gdf.empty:
        ax.set_title(title + "\n(no data)", fontsize=16, fontweight="bold")
        ax.axis("off")
        return

    if is_rucc:
        from matplotlib.colors import BoundaryNorm
        from matplotlib.cm import ScalarMappable

        bounds  = list(range(1, 11))
        norm    = BoundaryNorm(bounds, ncolors=9)
        palette = plt.get_cmap("RdYlGn_r", 9)

        for val in sorted(good_gdf[col].dropna().unique()):
            good_gdf[good_gdf[col] == val].plot(
                ax=ax, color=palette(norm(val)),
                linewidth=0.05, edgecolor="white",
            )

        sm = ScalarMappable(cmap=palette, norm=norm)
        sm.set_array([])
        cb = plt.colorbar(sm, ax=ax, orientation="horizontal",
                          shrink=0.55, pad=0.01, ticks=list(range(1, 10)))
        cb.ax.set_xticklabels(
            ["1\n(Urban)"] + [str(i) for i in range(2, 9)] + ["9\n(Most Rural)"],
            fontsize=6,
        )
    else:
        vmin = good_gdf[col].quantile(0.01)
        vmax = good_gdf[col].quantile(0.99)
        good_gdf.plot(
            column=col, ax=ax, cmap=cmap,
            vmin=vmin, vmax=vmax,
            linewidth=0.05, edgecolor="white",
            legend=True,
            legend_kwds={"shrink": 0.55, "orientation": "horizontal",
                         "pad": 0.01, "label": "Percentile"},
        )
        if not missing_gdf.empty:
            ax.legend(
                handles=[mpatches.Patch(facecolor=missing_color,
                                        edgecolor="#aaaaaa", label="Missing")],
                fontsize=7, loc="lower left", framealpha=0.85,
            )

    ax.set_title(title, fontsize=18, fontweight="bold", pad=5)
    ax.axis("off")


def make_choropleth(gdf, panels, outfile, title, ncols=3):
    """
    Produce a multi-panel choropleth figure.
    panels: list of (col, panel_title, cmap) or (col, panel_title, cmap, is_rucc).
    """
    n     = len(panels)
    nrows = int(np.ceil(n / ncols))
    fig, axes = plt.subplots(nrows, ncols,
                              figsize=(6.5 * ncols, 5.2 * nrows))
    axes = np.atleast_1d(axes).flatten()

    for ax, panel in zip(axes, panels):
        is_rucc = len(panel) > 3 and panel[3]
        draw_panel(ax, gdf, panel[0], panel[1], cmap=panel[2], is_rucc=is_rucc)

    for ax in axes[len(panels):]:
        ax.axis("off")

    plt.tight_layout()
    fig.savefig(outfile, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {outfile}")


# ---------------------------------------------------------------------------
# 4. Load data
# ---------------------------------------------------------------------------
print("Loading analytic_dataset.csv ...")
df_raw = pd.read_csv("data/analytic_dataset.csv",
                     dtype={"fips_st_cnty": str, "fips_st": str})
df_raw["fips_st_cnty"] = df_raw["fips_st_cnty"].str.zfill(5)
df_raw["fips_st"]      = df_raw["fips_st"].str.zfill(2)

df = df_raw[~df_raw["fips_st"].isin(EXCL_FIPS)].copy().reset_index(drop=True)
print(f"  Contiguous-48: {len(df):,} counties")

if "pct_under65" not in df.columns and "pct_65plus" in df.columns:
    df["pct_under65"] = 100 - to_num(df, "pct_65plus")

cardio_count_col = first_existing(df.columns,
    ["cardio_per_10k", "cardiologist_per_10k", "cardiology_per_10k"])
em_count_col = first_existing(df.columns,
    ["em_per_10k", "emergency_per_10k", "em_phys_per_10k"])

if cardio_count_col is None and {"md_nf_card_dis_23", "popn_est_23"}.issubset(df.columns):
    df["cardio_per_10k"] = to_num(df, "md_nf_card_dis_23") / to_num(df, "popn_est_23") * 10_000
    cardio_count_col = "cardio_per_10k"
if em_count_col is None and {"md_nf_emerg_med_23", "popn_est_23"}.issubset(df.columns):
    df["em_per_10k"] = to_num(df, "md_nf_emerg_med_23") / to_num(df, "popn_est_23") * 10_000
    em_count_col = "em_per_10k"

# Raw RUCC for choropleth (not flipped — flip only happens in 03_ols.py)
df["ruca_raw"] = pd.to_numeric(df["rural_urban_contnm_23"], errors="coerce")

# Percentile columns used in choropleth panels
add_pctile(df, "pcp_per_10k",             "pcp_per_10k_pctile_map")
add_pctile(df, "primary_access_score",    "primary_access_score_pctile_map")
if cardio_count_col:
    add_pctile(df, cardio_count_col,      "cardio_per_10k_pctile_map")
add_pctile(df, "cardiology_access_score", "cardiology_access_score_pctile_map")
if em_count_col:
    add_pctile(df, em_count_col,          "em_per_10k_pctile_map")
add_pctile(df, "emergency_access_score",  "emergency_access_score_pctile_map")
add_pctile(df, "smoking_pct",             "smoking_pct_pctile_map")
add_pctile(df, "obesity_pct",             "obesity_pct_pctile_map")
for col in ["mort_allcause", "mort_heart", "mort_stroke", "mort_resp"]:
    add_pctile(df, col, f"{col}_pctile_map")

# ---------------------------------------------------------------------------
# 5. Summary statistics (Table 3)
# ---------------------------------------------------------------------------
print("\n[1] Summary statistics ...")

SUMMARY_SPEC = [
    ("ruca_raw",               "RUCC Code",                 "1–9"),
    ("pcp_per_10k",            "PCPs per 10,000",           "per 10,000"),
    ("primary_access_score",   "Primary Care E2SFCA Score", "per 10,000"),
    (cardio_count_col or "cardio_per_10k",
                               "Cardiologists per 10,000",  "per 10,000"),
    ("cardiology_access_score","Cardiology E2SFCA Score",   "per 10,000"),
    (em_count_col or "em_per_10k",
                               "EM Physicians per 10,000",  "per 10,000"),
    ("emergency_access_score", "Emergency E2SFCA Score",    "per 10,000"),
    ("pct_65plus",             "Population ≥65 (%)",        "%"),
    ("smoking_pct",            "Current Smoking (%)",       "%"),
    ("obesity_pct",            "Obesity (%)",               "%"),
    ("mort_allcause",          "All-Cause Mortality",       "per 100,000"),
    ("mort_heart",             "IHD Mortality",             "per 100,000"),
    ("mort_stroke",            "Stroke Mortality",          "per 100,000"),
    ("mort_resp",              "Respiratory Mortality",     "per 100,000"),
]

summary_df = summary_table(df, SUMMARY_SPEC)
summary_df.to_csv("output/tables/eda_summary_stats.csv", index=False)
df_to_latex(
    summary_df,
    "output/tables/eda_summary_stats.tex",
    caption="Sample characteristics of U.S.\\ counties ($n = 3{,}072$).",
    label="tab:summary_stats",
    col_format="llrrrrrrr",
)
print("  Saved eda_summary_stats (.csv / .tex)")

# ---------------------------------------------------------------------------
# 6. Missingness tables (Table 2)
# ---------------------------------------------------------------------------
print("\n[2] Missingness tables ...")

miss_df = missingness_overall(df, SUMMARY_SPEC)
miss_df.to_csv("output/tables/eda_missingness_overall.csv", index=False)
df_to_latex(
    miss_df,
    "output/tables/eda_missingness_overall.tex",
    caption=f"Overall missingness for key variables in the analytic sample (N = {len(df):,} counties).",
    label="tab:missingness_overall",
    col_format="lrr",
)
print("  Saved eda_missingness_overall (.csv / .tex)")

MORT_REGION_COLS = ["mort_allcause", "mort_heart", "mort_resp", "mort_stroke"]
mort_miss_region_df = mortality_missingness_by_region(df, mort_cols=MORT_REGION_COLS)
if not mort_miss_region_df.empty:
    mort_miss_region_df.to_csv("output/tables/eda_mortality_missingness_by_region.csv", index=False)
    df_to_latex(
        mort_miss_region_df,
        "output/tables/eda_mortality_missingness_by_region.tex",
        caption=(r"Missingness in mortality outcomes by rural region, "
                 r"rural counties only (RUCC Code 7--9). "
                 r"Cells show number missing (percent missing). "
                 r"Cause-specific mortality is suppressed by NCHS in counties "
                 r"with fewer than ten events in a three-year window."),
        label="tab:mortality_missingness_by_region",
        col_format="llrrrr",
    )
    print("  Saved eda_mortality_missingness_by_region (.csv / .tex)")
else:
    print("  WARNING: rural_region column not found — skipped.")

# ---------------------------------------------------------------------------
# 7. Choropleths
# ---------------------------------------------------------------------------
print("\n[3] Building choropleths ...")

try:
    r = requests.get(GEO_URL, timeout=60)
    r.raise_for_status()
    geo_json = r.json()
    gdf_raw  = gpd.GeoDataFrame.from_features(geo_json["features"])
    gdf_raw["fips_st_cnty"] = (gdf_raw["STATE"].str.zfill(2) +
                                gdf_raw["COUNTY"].str.zfill(3))
    gdf_raw = gdf_raw[~gdf_raw["STATE"].isin(EXCL_FIPS)]
    gdf_raw = gdf_raw.set_crs("EPSG:4326").to_crs("ESRI:102003")

    n_geo = len(gdf_raw)
    gdf   = gdf_raw.merge(df, on="fips_st_cnty", how="left")
    print(f"  GeoJSON: {n_geo:,} polygons -> after merge: {len(gdf):,}")

    # Figure 1: Primary Care Access (main text)
    make_choropleth(
        gdf,
        panels=[
            ("ruca_raw",
             "A. RUCC Code\n(1 = most urban, 9 = most rural)",
             "RdYlGn_r", True),
            ("pcp_per_10k_pctile_map",
             "B. PCPs per 10,000\n(Percentile)",
             "YlGn", False),
            ("primary_access_score_pctile_map",
             "C. Primary Care Access Score\n(Percentile)",
             "Blues", False),
        ],
        outfile="output/figures/choropleth_primary_access.png",
        title="Primary Care Access Measures Across U.S. Counties",
        ncols=3,
    )

    # Appendix Figure 4: Specialist and Emergency Access
    make_choropleth(
        gdf,
        panels=[
            ("cardio_per_10k_pctile_map",
             "A. Cardiologists per 10,000\n(Percentile)",
             "PuBuGn", False),
            ("cardiology_access_score_pctile_map",
             "B. Cardiology Access Score\n(Percentile)",
             "Purples", False),
            ("em_per_10k_pctile_map",
             "C. EM Physicians per 10,000\n(Percentile)",
             "YlOrBr", False),
            ("emergency_access_score_pctile_map",
             "D. Emergency Access Score\n(Percentile)",
             "OrRd", False),
        ],
        outfile="output/figures/choropleth_specialist_access.png",
        title="Specialist and Emergency Access Measures Across U.S. Counties",
        ncols=2,
    )

    # Appendix Figure 5: Rurality and Behavioral Risk
    make_choropleth(
        gdf,
        panels=[
            ("ruca_raw",
             "A. RUCC Code\n(1 = most urban, 9 = most rural)",
             "RdYlGn_r", True),
            ("smoking_pct_pctile_map",
             "B. Current Smoking Rate\n(Percentile)",
             "magma", False),
            ("obesity_pct_pctile_map",
             "C. Obesity Rate\n(Percentile)",
             "plasma", False),
        ],
        outfile="output/figures/choropleth_behavior_rurality.png",
        title="Rurality and Behavioral Risk Factors Across U.S. Counties",
        ncols=3,
    )

    # Appendix Figure 6: Mortality Rates
    make_choropleth(
        gdf,
        panels=[
            ("mort_allcause_pctile_map",
             "A. All-Cause Mortality\n(Percentile)",
             "OrRd", False),
            ("mort_heart_pctile_map",
             "B. IHD Mortality\n(Percentile)",
             "YlOrRd", False),
            ("mort_stroke_pctile_map",
             "C. Stroke Mortality\n(Percentile)",
             "PuBu", False),
            ("mort_resp_pctile_map",
             "D. Respiratory Mortality\n(Percentile)",
             "PuRd", False),
        ],
        outfile="output/figures/choropleth_mortality.png",
        title="Mortality Rates Across U.S. Counties",
        ncols=2,
    )

except Exception as e:
    print(f"  WARNING: Choropleth section failed: {e}")
    import traceback; traceback.print_exc()

# ---------------------------------------------------------------------------
# 8. Regional partial Spearman correlation table (Appendix Table)
#    rho(PCP-RUCC), rho(E2SFCA-RUCC), rho(PCP-E2SFCA) by region,
#    residualised on age composition and state fixed effects.
# ---------------------------------------------------------------------------
print("\n[4] Regional partial Spearman correlations ...")

corr_region_df = access_rucc_correlation_by_region(df)
corr_region_df.to_csv(
    "output/tables/eda_access_rucc_correlation_by_region.csv",
    index=False,
)
df_to_latex(
    corr_region_df,
    "output/tables/eda_access_rucc_correlation_by_region.tex",
    caption=(
        r"Partial Spearman correlations among RUCC Code, physician density "
        r"percentile, and E2SFCA accessibility percentile within each region, "
        r"residualised on age composition and state fixed effects. "
        r"Regions where $\rho$(PCP--RUCC) substantially exceeds "
        r"$\rho$(E2SFCA--RUCC) in magnitude indicate settings where rurality "
        r"predicts physician supply but not spatiotemporal reachability. "
        r"$^{***}p<0.001$, $^{**}p<0.01$, $^{*}p<0.05$."
    ),
    label="tab:access_rucc_correlation_by_region",
    col_format="lrrrr",
)
print("  Saved eda_access_rucc_correlation_by_region (.csv / .tex)")

print("\n02_eda.py complete.")
print("Outputs:")
for f in [
    "output/tables/eda_summary_stats.csv / .tex         — Table 3",
    "output/tables/eda_missingness_overall.csv / .tex   — Table 2 (left)",
    "output/tables/eda_mortality_missingness_by_region.csv / .tex — Table 2 (right)",
    "output/tables/eda_access_rucc_correlation_by_region.csv / .tex — Appendix Table",
    "output/figures/choropleth_primary_access.png       — Figure 1",
    "output/figures/choropleth_specialist_access.png    — Appendix Figure 4",
    "output/figures/choropleth_behavior_rurality.png    — Appendix Figure 5",
    "output/figures/choropleth_mortality.png            — Appendix Figure 6",
]:
    print(f"  {f}")
