"""
03_ols.py
---------
Correlation analysis and incremental WLS regression models.

Tasks:
  - Partial Spearman correlation matrix among access measures
    (controlling for age composition and state fixed effects)
  - Partial Spearman correlations: access measures vs mortality outcomes
    (negative correlations only shown in heatmap)
  - Incremental WLS model series for each outcome:
      Model 0: RUCC Code only
      Model 1: RUCC Code + % under 65 + State Fixed Effects
      Model 2: Model 1 + physician density (outcome-matched specialist)
      Model 3: Model 1 + gravity access score (outcome-matched)
      Model 4: Model 1 + density + access score
  - R² tables (Adj. R², ΔR², Partial R², CV R², AIC) saved as LaTeX + CSV
  - Forest plots: RUCC Code coefficient attenuation across Model 0–4

Note on RUCC Code sign convention:
  RUCC codes are reversed before analysis (ruca_less_rural = 10 – RUCC)
  so that higher values indicate less rural counties, consistent with
  the direction of access measures (higher = better access).
  A footnote is added to each forest plot to make this explicit.

Inputs:
  data/analytic_dataset.csv

Outputs:
  output/tables/access_correlations.csv / .tex
  output/tables/access_mortality_relevant_correlations.csv
  output/tables/ols_results_full.csv
  output/tables/r2_table_primary_allcause.csv / .tex
  output/tables/r2_table_specialist_outcomes.csv / .tex
  output/figures/access_spearman_related_only.png
  output/figures/access_mortality_relevant_correlations.png
  output/figures/forest_{outcome}.png  (four plots)
"""

import os
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

from utils import (
    to_num, first_existing, zscore,
    spearman_scalar, star, fit_wls, tidy_model,
    partial_r2, cv_r2, partial_spearman_resid,
    df_to_latex, df_to_booktabs_png,
)

warnings.filterwarnings("ignore")

os.makedirs("output/tables",  exist_ok=True)
os.makedirs("output/figures", exist_ok=True)

try:
    plt.rcParams["font.family"] = "Arial"
except Exception:
    pass

PALETTE   = sns.color_palette("colorblind")
DPI       = 300
EXCL_FIPS = {"02", "15", "60", "66", "69", "72", "78"}

# ---------------------------------------------------------------------------
# 1. Model specification constants
# ---------------------------------------------------------------------------

MODEL_SHORT_NAMES = {
    "M0": "Model 0", "M1": "Model 1", "M2": "Model 2",
    "M3": "Model 3", "M4": "Model 4",
}

PREDICTOR_DESCRIPTIONS = {
    "M0": "RUCC Code",
    "M1": "RUCC Code + Age (% under 65) + State FE",
    "M2: M1 + PCPs per 10k":              "RUCC Code + Age + State FE + PCP Density",
    "M2: M1 + Cardiologists per 10k":     "RUCC Code + Age + State FE + Cardiologist Density",
    "M2: M1 + EM physicians per 10k":     "RUCC Code + Age + State FE + EM Physician Density",
    "M3: M1 + Primary access score":      "RUCC Code + Age + State FE + Primary Access Score",
    "M3: M1 + Cardiology access score":   "RUCC Code + Age + State FE + Cardiology Access Score",
    "M3: M1 + Emergency access score":    "RUCC Code + Age + State FE + Emergency Access Score",
    "M4: M1 + both access measures":      "RUCC Code + Age + State FE + Density + Access Score",
}

MODEL_SPECS = [
    {
        "family":       "Primary care / all-cause",
        "outcome":      "mort_allcause",
        "outcome_label":"All-cause mortality",
        "count_var":    "pcp_z",
        "count_label":  "PCPs per 10k",
        "access_var":   "primary_access_z",
        "access_label": "Primary access score",
    },
    {
        "family":       "Cardiology / heart",
        "outcome":      "mort_heart",
        "outcome_label":"IHD mortality",
        "count_var":    "cardio_count_z",
        "count_label":  "Cardiologists per 10k",
        "access_var":   "cardiology_access_z",
        "access_label": "Cardiology access score",
    },
    {
        "family":       "Emergency medicine / stroke",
        "outcome":      "mort_stroke",
        "outcome_label":"Stroke mortality",
        "count_var":    "em_count_z",
        "count_label":  "EM physicians per 10k",
        "access_var":   "emergency_access_z",
        "access_label": "Emergency access score",
    },
    {
        "family":       "Emergency medicine / respiratory",
        "outcome":      "mort_resp",
        "outcome_label":"Respiratory mortality",
        "count_var":    "em_count_z",
        "count_label":  "EM physicians per 10k",
        "access_var":   "emergency_access_z",
        "access_label": "Emergency access score",
    },
]

# ---------------------------------------------------------------------------
# 2. R² table function
# ---------------------------------------------------------------------------

def make_r2_table(r2_df, families, outfile_stem):
    """
    Build and save an R² summary table (LaTeX + CSV) for a set of model families.
    Columns: Model, Outcome, Predictors, Adj. R², ΔR² vs Model 1,
             Partial R² (Access), CV R², AIC.
    """
    sub = r2_df[r2_df["model_family"].isin(families)].copy()
    if sub.empty:
        print(f"  WARNING: no data for {outfile_stem}")
        return

    rows = []
    for _, row in sub.iterrows():
        code      = row.get("model_code", row["model"].split(":")[0].strip())
        short     = MODEL_SHORT_NAMES.get(code, code)
        pred_desc = PREDICTOR_DESCRIPTIONS.get(row["model"]) or \
                    PREDICTOR_DESCRIPTIONS.get(code, row["model"])

        delta = row["delta_r2_vs_covariate_model"]
        part  = row.get("partial_r2_access", np.nan)
        cv    = row.get("cv_r2", np.nan)

        rows.append({
            "Model":               short,
            "Outcome":             row["outcome_label"],
            "Predictors":          pred_desc,
            "Adj. R²":             f"{row['adj_r2']:.3f}" if pd.notna(row["adj_r2"]) else "—",
            "ΔR² vs Model 1":      ("—" if pd.isna(delta) or code in ("M0", "M1")
                                     else f"{delta:+.3f}"),
            "Partial R² (Access)": ("—" if pd.isna(part) or code in ("M0", "M1", "M2")
                                     else f"{part:.3f}"),
            "CV R²":               f"{cv:.3f}" if pd.notna(cv) else "—",
            "AIC":                 f"{row['aic']:,.0f}" if pd.notna(row["aic"]) else "—",
        })

    tbl = pd.DataFrame(rows)
    tbl.to_csv(f"output/tables/{outfile_stem}.csv", index=False)
    df_to_latex(
        tbl,
        f"output/tables/{outfile_stem}.tex",
        caption="",
        label="",
        col_format="llp{5cm}rrrrl",
    )
    print(f"  Saved {outfile_stem} (.csv / .tex)")


# ---------------------------------------------------------------------------
# 3. Load data
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
    ["cardio_per_10k", "cardiologist_per_10k"])
em_count_col = first_existing(df.columns,
    ["em_per_10k", "emergency_per_10k"])

if cardio_count_col is None and {"md_nf_card_dis_23", "popn_est_23"}.issubset(df.columns):
    df["cardio_per_10k"] = to_num(df, "md_nf_card_dis_23") / to_num(df, "popn_est_23") * 10_000
    cardio_count_col = "cardio_per_10k"
if em_count_col is None and {"md_nf_emerg_med_23", "popn_est_23"}.issubset(df.columns):
    df["em_per_10k"] = to_num(df, "md_nf_emerg_med_23") / to_num(df, "popn_est_23") * 10_000
    em_count_col = "em_per_10k"

# ---------------------------------------------------------------------------
# 4. Standardize predictors
#    RUCC Code is reversed (10 – RUCC) so higher = less rural,
#    consistent with the direction of access measures.
# ---------------------------------------------------------------------------
df["ruca_raw"]        = to_num(df, "rural_urban_contnm_23")
df["ruca_less_rural"] = 10 - df["ruca_raw"]

PREDICTOR_MAP = {
    "ruca_z":              ("ruca_less_rural",         "RUCC Code"),
    "pcp_z":               ("pcp_per_10k",             "PCPs per 10k"),
    "primary_access_z":    ("primary_access_score",    "Primary access score"),
    "cardio_count_z":      (cardio_count_col,          "Cardiologists per 10k"),
    "cardiology_access_z": ("cardiology_access_score", "Cardiology access score"),
    "em_count_z":          (em_count_col,              "EM physicians per 10k"),
    "emergency_access_z":  ("emergency_access_score",  "Emergency access score"),
    "pct_under65_z":       ("pct_under65",             "% under age 65"),
}

for new_col, (raw_col, _) in PREDICTOR_MAP.items():
    if raw_col is not None and raw_col in df.columns:
        df[new_col] = zscore(df[raw_col])
    else:
        df[new_col] = np.nan
        print(f"  WARNING: source column not found for {new_col}: {raw_col}")

# ---------------------------------------------------------------------------
# 5. Partial Spearman: access measure correlation matrix
# ---------------------------------------------------------------------------
print("\n[0] Partial Spearman: access measure correlation matrix ...")

ACCESS_VARS = [
    ("ruca_z",             "RUCC Code"),
    ("pcp_z",              "PCPs\nper 10k"),
    ("primary_access_z",   "Primary\naccess"),
    ("cardio_count_z",     "Cardiologists\nper 10k"),
    ("cardiology_access_z","Cardiology\naccess"),
    ("em_count_z",         "EM physicians\nper 10k"),
    ("emergency_access_z", "Emergency\naccess"),
]

resid_cache = {}
for col, _ in ACCESS_VARS:
    resid_cache[col] = (partial_spearman_resid(df, col)
                        if col in df.columns and df[col].notna().sum() > 50
                        else pd.Series(np.nan, index=df.index))

RELATED_PAIRS = set()
for c, _ in ACCESS_VARS:
    RELATED_PAIRS.update({("ruca_z", c), (c, "ruca_z"), (c, c)})
for a, b in [("pcp_z", "primary_access_z"),
             ("cardio_count_z", "cardiology_access_z"),
             ("em_count_z", "emergency_access_z")]:
    RELATED_PAIRS.update({(a, b), (b, a)})

labels    = [l for _, l in ACCESS_VARS]
mat       = pd.DataFrame(np.nan, index=labels, columns=labels)
corr_rows = []

for c1, l1 in ACCESS_VARS:
    for c2, l2 in ACCESS_VARS:
        if (c1, c2) not in RELATED_PAIRS:
            continue
        if c1 == c2:
            rho, p, n = 1.0, 0.0, int(df[c1].notna().sum())
        else:
            rho, p, n = spearman_scalar(resid_cache[c1], resid_cache[c2])
        mat.loc[l1, l2] = rho
        if c1 != c2 and ACCESS_VARS.index((c1, l1)) < ACCESS_VARS.index((c2, l2)):
            corr_rows.append({
                "Measure 1":          l1.replace("\n", " "),
                "Measure 2":          l2.replace("\n", " "),
                "Partial Spearman ρ": round(rho, 3) if pd.notna(rho) else np.nan,
                "p-value":            f"{p:.3f}" if pd.notna(p) else "—",
                "N":                  f"{n:,}",
                "":                   star(p),
            })

access_corr_df = pd.DataFrame(corr_rows)
access_corr_df.to_csv("output/tables/access_correlations.csv", index=False)
df_to_latex(
    access_corr_df,
    "output/tables/access_correlations.tex",
    caption="",
    label="",
    col_format="llrrrr",
)
print("  Saved access_correlations (.csv / .tex)")

# Heatmap
fig, ax = plt.subplots(figsize=(9, 7))
sns.heatmap(
    mat.astype(float),
    annot=True, fmt=".2f",
    cmap="RdBu_r", center=0, vmin=-1, vmax=1,
    linewidths=0.5, linecolor="white",
    mask=mat.isna(),
    cbar_kws={"label": "Partial Spearman ρ"},
    ax=ax,
)
ax.tick_params(axis="x", rotation=35, labelsize=9)
ax.tick_params(axis="y", rotation=0,  labelsize=9)
plt.tight_layout()
fig.savefig("output/figures/access_spearman_related_only.png", dpi=DPI, bbox_inches="tight")
plt.close(fig)
print("  Saved output/figures/access_spearman_related_only.png")

# ---------------------------------------------------------------------------
# 6. Partial Spearman: access measures vs mortality outcomes
#    Heatmap shows negative correlations only (more access → lower mortality)
# ---------------------------------------------------------------------------
print("\n[1] Partial Spearman: access vs mortality ...")

MORT_VARS = ["mort_allcause", "mort_heart", "mort_stroke", "mort_resp"]

for mv in MORT_VARS:
    resid_cache[mv] = (partial_spearman_resid(df, mv)
                       if mv in df.columns and df[mv].notna().sum() > 50
                       else pd.Series(np.nan, index=df.index))

RELEVANT_PAIRS = [
    ("mort_allcause", "All-cause mortality",   "ruca_z",             "RUCC Code"),
    ("mort_allcause", "All-cause mortality",   "pcp_z",              "PCPs per 10k"),
    ("mort_allcause", "All-cause mortality",   "primary_access_z",   "Primary access score"),
    ("mort_heart",    "IHD mortality",         "ruca_z",             "RUCC Code"),
    ("mort_heart",    "IHD mortality",         "cardio_count_z",     "Cardiologists per 10k"),
    ("mort_heart",    "IHD mortality",         "cardiology_access_z","Cardiology access score"),
    ("mort_stroke",   "Stroke mortality",      "ruca_z",             "RUCC Code"),
    ("mort_stroke",   "Stroke mortality",      "em_count_z",         "EM physicians per 10k"),
    ("mort_stroke",   "Stroke mortality",      "emergency_access_z", "Emergency access score"),
    ("mort_resp",     "Respiratory mortality", "ruca_z",             "RUCC Code"),
    ("mort_resp",     "Respiratory mortality", "em_count_z",         "EM physicians per 10k"),
    ("mort_resp",     "Respiratory mortality", "emergency_access_z", "Emergency access score"),
]

mort_corr_rows = []
for outcome, out_label, pred, pred_label in RELEVANT_PAIRS:
    if outcome not in df.columns or pred not in df.columns:
        continue
    rho, p, n = spearman_scalar(resid_cache.get(pred, df[pred]),
                                resid_cache.get(outcome, df[outcome]))
    mort_corr_rows.append({
        "outcome":              out_label,
        "predictor":            pred_label,
        "partial_spearman_rho": round(rho, 3) if pd.notna(rho) else np.nan,
        "spearman_p":           p,
        "n":                    n,
        "sig":                  star(p),
    })

mort_corr_df = pd.DataFrame(mort_corr_rows)
mort_corr_df.to_csv("output/tables/access_mortality_relevant_correlations.csv", index=False)
print("  Saved access_mortality_relevant_correlations.csv")

if not mort_corr_df.empty:
    heat = mort_corr_df.pivot(index="predictor", columns="outcome",
                              values="partial_spearman_rho")
    mask_positive = heat.fillna(0) >= 0

    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    sns.heatmap(
        heat.astype(float),
        annot=True, fmt=".2f",
        cmap="Blues_r",
        vmin=-1, vmax=0,
        linewidths=0.5, linecolor="white",
        mask=heat.isna() | mask_positive,
        cbar_kws={"label": "Partial Spearman ρ", "shrink": 0.75},
        ax=ax, annot_kws={"size": 10},
    )
    sns.heatmap(
        heat.astype(float),
        annot=True, fmt=".2f",
        cmap=sns.light_palette("#cccccc", as_cmap=True),
        vmin=0, vmax=1,
        linewidths=0.5, linecolor="white",
        mask=heat.isna() | ~mask_positive,
        cbar=False, ax=ax, annot_kws={"size": 9, "color": "#aaaaaa"},
    )
    ax.set_xlabel("Mortality Outcome", fontsize=10, labelpad=8)
    ax.set_ylabel("Access Measure",   fontsize=10, labelpad=8)
    ax.tick_params(axis="x", rotation=25, labelsize=9)
    ax.tick_params(axis="y", rotation=0,  labelsize=9)

    for i, pred in enumerate(heat.index):
        for j, out in enumerate(heat.columns):
            row = mort_corr_df[(mort_corr_df["predictor"] == pred) &
                               (mort_corr_df["outcome"]   == out)]
            if not row.empty:
                s = star(row["spearman_p"].values[0])
                if s:
                    ax.text(j + 0.75, i + 0.25, s, ha="center",
                            va="center", fontsize=9, color="black")

    plt.tight_layout()
    fig.savefig("output/figures/access_mortality_relevant_correlations.png",
                dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print("  Saved output/figures/access_mortality_relevant_correlations.png")

# ---------------------------------------------------------------------------
# 7. Incremental WLS model series
# ---------------------------------------------------------------------------
print("\n[2] Running WLS model series ...")

all_rows, r2_rows = [], []

for spec in MODEL_SPECS:
    outcome    = spec["outcome"]
    out_label  = spec["outcome_label"]
    family     = spec["family"]
    count_var  = spec["count_var"]
    access_var = spec["access_var"]

    if outcome not in df.columns:
        print(f"  WARNING: {outcome} not found — skipping {family}")
        continue

    models = [
        ("M0: RUCA only",
         f"{outcome} ~ ruca_z",
         [outcome, "ruca_z"], ["ruca_z"], "M0"),
        ("M1: RUCA + age<65 + state FE",
         f"{outcome} ~ ruca_z + pct_under65_z + C(fips_st)",
         [outcome, "ruca_z", "pct_under65_z", "fips_st"], ["ruca_z"], "M1"),
        (f"M2: M1 + {spec['count_label']}",
         f"{outcome} ~ ruca_z + pct_under65_z + C(fips_st) + {count_var}",
         [outcome, "ruca_z", "pct_under65_z", "fips_st", count_var],
         [count_var], "M2"),
        (f"M3: M1 + {spec['access_label']}",
         f"{outcome} ~ ruca_z + pct_under65_z + C(fips_st) + {access_var}",
         [outcome, "ruca_z", "pct_under65_z", "fips_st", access_var],
         [access_var], "M3"),
        ("M4: M1 + both access measures",
         f"{outcome} ~ ruca_z + pct_under65_z + C(fips_st) + {count_var} + {access_var}",
         [outcome, "ruca_z", "pct_under65_z", "fips_st", count_var, access_var],
         [count_var, access_var], "M4"),
    ]

    baseline_r2  = None
    covariate_r2 = None
    print(f"\n  --- {family}: {out_label} ---")

    for model_label, formula, needed_cols, focal_vars, model_code in models:
        model, _ = fit_wls(formula, df, needed_cols)
        if model is None:
            continue

        if model_code == "M0": baseline_r2  = model.rsquared
        if model_code == "M1": covariate_r2 = model.rsquared

        delta_vs_ruca = (model.rsquared - baseline_r2
                         if baseline_r2 is not None else np.nan)
        delta_vs_m1   = (model.rsquared - covariate_r2
                         if covariate_r2 is not None else np.nan)

        access_partial = (partial_r2(model, access_var)
                          if access_var in focal_vars else np.nan)
        cv     = cv_r2(formula, df, needed_cols)
        cv_str = f"{cv:.4f}" if pd.notna(cv) else "—"

        print(f"    {model_label:<42}  n={int(model.nobs):,}  "
              f"R²={model.rsquared:.4f}  ΔR²={delta_vs_m1:+.4f}  "
              f"CV-R²={cv_str}  AIC={model.aic:,.0f}")

        all_rows.extend(tidy_model(model, outcome, out_label,
                                   model_label, family, focal_vars))
        r2_rows.append({
            "model_family":              family,
            "outcome":                   outcome,
            "outcome_label":             out_label,
            "model":                     model_label,
            "model_code":                model_code,
            "n":                         int(model.nobs),
            "r2":                        model.rsquared,
            "adj_r2":                    model.rsquared_adj,
            "delta_r2_vs_ruca_only":     delta_vs_ruca,
            "delta_r2_vs_covariate_model": delta_vs_m1,
            "partial_r2_access":         access_partial,
            "cv_r2":                     cv,
            "aic":                       model.aic,
            "bic":                       model.bic,
        })

results_df = pd.DataFrame(all_rows)
r2_df      = pd.DataFrame(r2_rows)

results_df.to_csv("output/tables/ols_results_full.csv", index=False)
print(f"\n  Saved ols_results_full.csv ({len(results_df):,} rows)")

# ---------------------------------------------------------------------------
# 8. R² tables
# ---------------------------------------------------------------------------
if not r2_df.empty:
    make_r2_table(
        r2_df,
        families=["Primary care / all-cause"],
        outfile_stem="r2_table_primary_allcause",
    )
    make_r2_table(
        r2_df,
        families=["Cardiology / heart",
                  "Emergency medicine / stroke",
                  "Emergency medicine / respiratory"],
        outfile_stem="r2_table_specialist_outcomes",
    )

# ---------------------------------------------------------------------------
# 9. Forest plots — RUCC Code coefficient attenuation across Model 0–4
# ---------------------------------------------------------------------------
print("\nGenerating RUCC Code attenuation forest plots ...")

for spec in MODEL_SPECS:
    family    = spec["family"]
    outcome   = spec["outcome"]
    out_label = spec["outcome_label"]

    sub = results_df[
        (results_df["model_family"] == family) &
        (results_df["outcome"]      == outcome) &
        (results_df["variable"]     == "ruca_z")
    ].copy()
    if sub.empty:
        continue

    sub["model_code"] = sub["model"].str.split(":").str[0].str.strip()
    sub = (sub.set_index("model_code")
              .reindex(["M0", "M1", "M2", "M3", "M4"])
              .reset_index()
              .dropna(subset=["coef"]))
    if sub.empty:
        continue

    y_labels = [MODEL_SHORT_NAMES.get(c, c) for c in sub["model_code"]]
    y_pos    = np.arange(len(sub))

    fig, ax = plt.subplots(figsize=(9, max(4, 0.9 * len(sub))))

    for i, (_, row) in enumerate(sub.iterrows()):
        ax.errorbar(
            x=row["coef"], y=i,
            xerr=[[row["coef"] - row["ci_lower"]], [row["ci_upper"] - row["coef"]]],
            fmt="o", color=PALETTE[0], capsize=5, linewidth=1.5, markersize=7,
        )

    ax.axvline(0, color="gray", linestyle="--", linewidth=0.9, zorder=0)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(y_labels, fontsize=10)
    ax.set_xlabel("RUCC Code Coefficient per 1-SD (95% CI)", fontsize=10)
    ax.invert_yaxis()

    plt.tight_layout()
    outfile = f"output/figures/forest_{outcome}.png"
    fig.savefig(outfile, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {outfile}")

print("\n03_ols.py complete.")
print("Outputs:")
for f in [
    "output/tables/access_correlations.csv / .tex",
    "output/tables/access_mortality_relevant_correlations.csv",
    "output/tables/ols_results_full.csv",
    "output/tables/r2_table_primary_allcause.csv / .tex",
    "output/tables/r2_table_specialist_outcomes.csv / .tex",
    "output/figures/access_spearman_related_only.png",
    "output/figures/access_mortality_relevant_correlations.png",
    "output/figures/forest_mort_allcause.png",
    "output/figures/forest_mort_heart.png",
    "output/figures/forest_mort_stroke.png",
    "output/figures/forest_mort_resp.png",
]:
    print(f"  {f}")
