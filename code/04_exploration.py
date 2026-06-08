"""
04_exploration.py
-----------------
Focused subgroup comparisons for the rural health access analysis.

Subgroups:
  H4: Appalachian coal country (KY/WV/VA/TN) — Respiratory mortality
  H6: Great Plains (ND/SD/NE/KS/OK) — IHD and Stroke mortality

These subgroups were motivated by two descriptive patterns:
  - In Appalachia, E2SFCA scores decouple from RUCC entirely
    (rho(E2SFCA-RUCC) = -0.009) while behavioral risk is elevated
    regardless of rurality level, raising the possibility that
    spatiotemporal access discriminates respiratory mortality risk
    in ways RUCC cannot.
  - In the Great Plains, nearly all counties share the same RUCC
    classification (mean = 8.54), compressing rurality variation
    to near-zero and potentially leaving RUCC saturated as a
    predictor. Access measures that vary more continuously within
    the region may retain discriminating power.

Both subgroups are tested against the full national sample using
partial Spearman correlations residualised on age and state FE.

Outputs two tables (full and parsed):
  Full:   all rows for both subgroups
  Parsed: only rows where Delta-rho < -0.05 (access measure
          meaningfully stronger in subsample than nationally);
          RUCC Code always included as reference

Inputs:
  data/analytic_dataset.csv

Outputs:
  output/tables/subgroup_comparison_combined.csv / .tex  — full table
  output/tables/subgroup_comparison_parsed.csv / .tex    — Table 6 (main text)
"""

import os
import warnings
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

from utils import to_num, zscore, spearman_scalar, star

warnings.filterwarnings("ignore")
os.makedirs("output/tables", exist_ok=True)

EXCL_FIPS = {"02", "15", "60", "66", "69", "72", "78"}

DISPLAY_COLS = [
    "Predictor",
    "rho (Full sample)",
    "rho (Subsample)",
    "Delta rho",
    "n (Full)",
    "n (Sub)",
]

HEADER_DISPLAY = [
    "Predictor",
    r"$\rho$ (Full sample)",
    r"$\rho$ (Subsample)",
    r"$\Delta\rho$",
    "$n$ (Full)",
    "$n$ (Sub)",
]


# ---------------------------------------------------------------------------
# 1. Helper functions
# ---------------------------------------------------------------------------

def residualise(df_sub, col):
    """
    Residualise col on % under 65 + state fixed effects via OLS.
    Falls back to age-only if only one state is present.
    Returns residuals aligned to df_sub.index.
    """
    needed    = [col, "pct_under65_z", "fips_st"]
    available = [c for c in needed if c in df_sub.columns]
    sub       = df_sub[available].dropna()

    if len(sub) < 30:
        return df_sub[col].copy()

    n_states = sub["fips_st"].nunique() if "fips_st" in sub.columns else 0
    ctrl     = "pct_under65_z + C(fips_st)" if n_states > 1 else "pct_under65_z"

    try:
        resid = smf.ols(f"{col} ~ {ctrl}", data=sub).fit().resid
        return resid.reindex(df_sub.index)
    except Exception:
        return df_sub[col].copy()


def partial_spearman(df_sub, x_col, y_col):
    """Partial Spearman rho after residualising both variables on age + state FE."""
    return spearman_scalar(residualise(df_sub, x_col),
                           residualise(df_sub, y_col))


def build_comparison_table(predictors, outcome, full_df, sub_df):
    """
    Compute partial Spearman rho in the full sample and subsample for each
    predictor vs the outcome. Returns a DataFrame with display columns and
    internal raw columns (prefixed _) used for filtering.
    """
    rows = []
    for z_col, label in predictors:
        rho_full, p_full, n_full = partial_spearman(full_df, z_col, outcome)
        rho_sub,  p_sub,  n_sub  = partial_spearman(sub_df,  z_col, outcome)
        delta = ((rho_sub - rho_full)
                 if pd.notna(rho_sub) and pd.notna(rho_full) else np.nan)
        rows.append({
            "Predictor":         label,
            "rho (Full sample)": f"{rho_full:.2f}{star(p_full)}" if pd.notna(rho_full) else "—",
            "rho (Subsample)":   f"{rho_sub:.2f}{star(p_sub)}"   if pd.notna(rho_sub)  else "—",
            "Delta rho":         f"{delta:+.2f}"                  if pd.notna(delta)    else "—",
            "n (Full)":          f"{n_full:,}",
            "n (Sub)":           f"{n_sub:,}",
            "_rho_full":         rho_full,
            "_rho_sub":          rho_sub,
            "_delta":            delta,
            "_p_sub":            p_sub,
        })
    return pd.DataFrame(rows)


def filter_section(tbl):
    """
    Retain a row if:
      - Predictor contains 'RUCC' (always shown as reference), OR
      - Delta-rho < -0.05 (access measure substantially stronger in subsample)
    """
    mask = (
        tbl["Predictor"].str.contains("RUCC", case=False, na=False) |
        ((tbl["_delta"] < -0.05) & tbl["_delta"].notna())
    )
    return tbl[mask].copy()


def _esc(s):
    """Escape special LaTeX characters."""
    return str(s).replace("%", r"\%").replace("_", r"\_").replace("&", r"\&")


def build_latex_table(section_groups, n_cols, col_format, header_display, footnote):
    """
    Build a LaTeX booktabs table with hierarchical section headers.
    section_groups: list of dicts with keys geo_label and subsections
                    (list of (outcome_label, DataFrame) tuples).
    """
    lines = [
        r"\begin{table}[ht]",
        r"\centering",
        r"\small",
        r"\setlength{\tabcolsep}{6pt}",
        f"\\begin{{tabular}}{{{col_format}}}",
        r"\toprule",
        " & ".join(header_display) + r" \\",
        r"\midrule",
    ]

    n_non_empty_groups = sum(
        1 for g in section_groups
        if any(not t.empty for _, t in g["subsections"])
    )
    groups_written = 0

    for group in section_groups:
        non_empty = [(ol, t) for ol, t in group["subsections"] if not t.empty]
        if not non_empty:
            continue

        lines.append(
            f"\\multicolumn{{{n_cols}}}{{l}}"
            f"{{\\textbf{{{_esc(group['geo_label'])}}}}} \\\\"
        )

        for sub_i, (outcome_label, tbl) in enumerate(non_empty):
            lines.append(
                f"\\multicolumn{{{n_cols}}}{{l}}"
                f"{{\\quad\\textit{{Outcome: {_esc(outcome_label)}}}}} \\\\"
            )
            lines.append(r"\midrule")

            out = tbl[[c for c in DISPLAY_COLS if c in tbl.columns]].copy()
            for _, row in out.iterrows():
                cells    = [_esc(v) if not pd.isna(v) else "---" for v in row]
                cells[0] = r"\quad " + cells[0]
                lines.append(" & ".join(cells) + r" \\")

            if sub_i < len(non_empty) - 1:
                lines.append(r"\addlinespace[3pt]")
                lines.append(r"\midrule")
                lines.append(r"\addlinespace[3pt]")

        groups_written += 1
        if groups_written < n_non_empty_groups:
            lines.append(r"\midrule")
            lines.append(r"\addlinespace[4pt]")

    lines += [
        r"\bottomrule",
        r"\addlinespace[4pt]",
        f"\\multicolumn{{{n_cols}}}{{p{{14cm}}}}{{\\footnotesize \\textit{{{_esc(footnote)}}}}} \\\\",
        r"\end{tabular}",
        r"\end{table}",
    ]
    return lines


# ---------------------------------------------------------------------------
# 2. Load and prepare data
# ---------------------------------------------------------------------------
print("Loading analytic_dataset.csv ...")
df_raw = pd.read_csv(
    "data/analytic_dataset.csv",
    dtype={"fips_st_cnty": str, "fips_st": str},
)
df_raw["fips_st_cnty"] = df_raw["fips_st_cnty"].str.zfill(5)
df_raw["fips_st"]      = df_raw["fips_st"].str.zfill(2)

df = df_raw[~df_raw["fips_st"].isin(EXCL_FIPS)].copy().reset_index(drop=True)
print(f"  Full sample: {len(df):,} counties")

if "pct_under65" not in df.columns and "pct_65plus" in df.columns:
    df["pct_under65"] = 100 - to_num(df, "pct_65plus")

if "cardio_per_10k" not in df.columns and {"md_nf_card_dis_23", "popn_est_23"}.issubset(df.columns):
    df["cardio_per_10k"] = to_num(df, "md_nf_card_dis_23") / to_num(df, "popn_est_23") * 10_000
if "em_per_10k" not in df.columns and {"md_nf_emerg_med_23", "popn_est_23"}.issubset(df.columns):
    df["em_per_10k"] = to_num(df, "md_nf_emerg_med_23") / to_num(df, "popn_est_23") * 10_000

# RUCC Code reversed: higher = less rural (consistent with 03_ols.py)
df["ruca_raw"]        = to_num(df, "rural_urban_contnm_23")
df["ruca_less_rural"] = 10 - df["ruca_raw"]

PRED_MAP = {
    "ruca_z":              "ruca_less_rural",
    "pcp_z":               "pcp_per_10k",
    "primary_access_z":    "primary_access_score",
    "em_count_z":          "em_per_10k",
    "emergency_access_z":  "emergency_access_score",
    "cardio_count_z":      "cardio_per_10k",
    "cardiology_access_z": "cardiology_access_score",
    "pct_under65_z":       "pct_under65",
}
for z_col, raw_col in PRED_MAP.items():
    df[z_col] = zscore(df[raw_col]) if raw_col in df.columns else np.nan

# ---------------------------------------------------------------------------
# 3. Define subgroups
#    H4: Appalachian coal country — KY, WV, VA, TN
#    H6: Great Plains — ND, SD, NE, KS, OK
# ---------------------------------------------------------------------------
df_h4 = df[df["fips_st"].isin({"21", "54", "51", "47"})].copy()
df_h6 = df[df["fips_st"].isin({"38", "46", "31", "20", "40"})].copy()

print(f"  H4 Appalachia (KY/WV/VA/TN):    {len(df_h4):,} counties")
print(f"  H6 Great Plains (ND/SD/NE/KS/OK): {len(df_h6):,} counties")
print(f"  RUCC SD — Great Plains: {df_h6['ruca_raw'].std():.3f} "
      f"vs full sample: {df['ruca_raw'].std():.3f}")

# ---------------------------------------------------------------------------
# 4. Build comparison tables
#    H4: primary + emergency access vs respiratory mortality
#    H6: cardiology access vs IHD; emergency access vs stroke
# ---------------------------------------------------------------------------
print("\n[H4] Appalachia (KY/WV/VA/TN) — respiratory mortality ...")
h4_table = build_comparison_table(
    [("ruca_z",             "RUCC Code"),
     ("pcp_z",              "PCPs per 10,000"),
     ("primary_access_z",   "Primary Access Score"),
     ("em_count_z",         "EM Physicians per 10,000"),
     ("emergency_access_z", "Emergency Access Score")],
    "mort_resp", df, df_h4,
)

print("\n[H6] Great Plains (ND/SD/NE/KS/OK) — IHD and stroke mortality ...")
h6_heart = build_comparison_table(
    [("ruca_z",              "RUCC Code"),
     ("cardio_count_z",      "Cardiologists per 10,000"),
     ("cardiology_access_z", "Cardiology Access Score")],
    "mort_heart", df, df_h6,
)
h6_stroke = build_comparison_table(
    [("ruca_z",             "RUCC Code"),
     ("em_count_z",         "EM Physicians per 10,000"),
     ("emergency_access_z", "Emergency Access Score")],
    "mort_stroke", df, df_h6,
)

# ---------------------------------------------------------------------------
# 5. Define table structure
# ---------------------------------------------------------------------------
SECTION_GROUPS = [
    {
        "geo_label":   "Appalachia",
        "subsections": [("Respiratory mortality", h4_table)],
    },
    {
        "geo_label":   "Great Plains",
        "subsections": [
            ("IHD mortality",    h6_heart),
            ("Stroke mortality", h6_stroke),
        ],
    },
]

SECTION_GROUPS_PARSED = [
    {
        "geo_label":   "Appalachia",
        "subsections": [("Respiratory mortality", filter_section(h4_table))],
    },
    {
        "geo_label":   "Great Plains",
        "subsections": [
            ("IHD mortality",    filter_section(h6_heart)),
            ("Stroke mortality", filter_section(h6_stroke)),
        ],
    },
]

n_cols     = len(DISPLAY_COLS)
col_format = "l" + "r" * (n_cols - 1)

FOOTNOTE_FULL = (
    "Partial Spearman rho, residualised on percentage of population under age 65 "
    "and state fixed effects. "
    "Delta rho = subsample rho minus full-sample rho. "
    "*** p<0.001, ** p<0.01, * p<0.05."
)
FOOTNOTE_PARSED = (
    "Partial Spearman rho, residualised on percentage of population under age 65 "
    "and state fixed effects. "
    "Delta rho = subsample rho minus full-sample rho. "
    "Rows retained where Delta rho < -0.05; "
    "RUCC Code always included as reference. "
    "Great Plains stroke subsample (n = 99) should be interpreted with caution. "
    "*** p<0.001, ** p<0.01, * p<0.05."
)

# ---------------------------------------------------------------------------
# 6. Save full table
# ---------------------------------------------------------------------------
full_lines = build_latex_table(
    SECTION_GROUPS, n_cols, col_format, HEADER_DISPLAY, FOOTNOTE_FULL
)
with open("output/tables/subgroup_comparison_combined.tex", "w") as f:
    f.write("\n".join(full_lines) + "\n")

csv_rows = []
for group in SECTION_GROUPS:
    for outcome_label, tbl in group["subsections"]:
        for _, row in tbl[[c for c in DISPLAY_COLS if c in tbl.columns]].iterrows():
            csv_rows.append({
                "Subsample": group["geo_label"],
                "Outcome":   outcome_label,
                **{c: row[c] for c in DISPLAY_COLS if c in row.index},
            })
pd.DataFrame(csv_rows).to_csv(
    "output/tables/subgroup_comparison_combined.csv", index=False
)
print("  Saved subgroup_comparison_combined (.csv / .tex)")

# ---------------------------------------------------------------------------
# 7. Save parsed table (Table 6 in main text)
# ---------------------------------------------------------------------------
parsed_lines = build_latex_table(
    SECTION_GROUPS_PARSED, n_cols, col_format, HEADER_DISPLAY, FOOTNOTE_PARSED
)
with open("output/tables/subgroup_comparison_parsed.tex", "w") as f:
    f.write("\n".join(parsed_lines) + "\n")

parsed_csv_rows = []
for group in SECTION_GROUPS_PARSED:
    for outcome_label, tbl in group["subsections"]:
        if tbl.empty:
            continue
        for _, row in tbl[[c for c in DISPLAY_COLS if c in tbl.columns]].iterrows():
            parsed_csv_rows.append({
                "Subsample": group["geo_label"],
                "Outcome":   outcome_label,
                **{c: row[c] for c in DISPLAY_COLS if c in row.index},
            })
pd.DataFrame(parsed_csv_rows).to_csv(
    "output/tables/subgroup_comparison_parsed.csv", index=False
)
print("  Saved subgroup_comparison_parsed (.csv / .tex)")

print("\n04_exploration.py complete.")
print("Outputs:")
for f in [
    "output/tables/subgroup_comparison_combined.csv / .tex  — full subgroup table",
    "output/tables/subgroup_comparison_parsed.csv / .tex    — Table 6 (main text)",
]:
    print(f"  {f}")
