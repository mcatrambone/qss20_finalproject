"""
utils.py
--------
Shared functions for my QSS20 final project
Will be used in 01_clean.py, 02_eda.py, 03_ols.py, and 04_exploration.py.
"""

import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import statsmodels.formula.api as smf
from scipy import stats


# ---------------------------------------------------------------------------
# General data helpers
# ---------------------------------------------------------------------------

def to_num(df, col):
    """Coerce a column to numeric; return NaN series if column absent."""
    if col in df.columns:
        return pd.to_numeric(df[col], errors="coerce")
    return pd.Series(np.nan, index=df.index)


def zscore(series):
    """Standardize a series (subtract mean, divide by SD). Returns NaN series if SD=0."""
    s = pd.to_numeric(series, errors="coerce")
    sd = s.std()
    if pd.isna(sd) or sd == 0:
        return s * np.nan
    return (s - s.mean()) / sd


def first_existing(columns, candidates):
    """Return the first candidate column name that exists in `columns`."""
    for c in candidates:
        if c in columns:
            return c
    return None


def log_merge(left, right, on, how="left", label=""):
    """
    Merge two data frames and print row counts before and after.
    """
    n_before = len(left)
    result   = left.merge(right, on=on, how=how)
    n_after  = len(result)
    tag      = f" [{label}]" if label else ""
    print(f"  Merge{tag}: {n_before:,} rows → {n_after:,} rows "
          f"({'no change' if n_before == n_after else f'Δ {n_after - n_before:+,}'})")
    return result


def format_n(n):
    """Format an integer with comma separator."""
    return f"{int(n):,}"


# ---------------------------------------------------------------------------
# Statistical helpers
# ---------------------------------------------------------------------------

def spearman_scalar(x, y):
    """
    Compute Spearman rho between two series, dropping NaNs.
    Returns (rho, p, n). Returns (nan, nan, n) if insufficient data.
    """
    sub = pd.DataFrame({"x": x, "y": y}).dropna()
    n   = len(sub)
    if n < 10 or sub["x"].nunique() < 2 or sub["y"].nunique() < 2:
        return np.nan, np.nan, n
    rho, p = stats.spearmanr(sub["x"], sub["y"])
    return float(rho), float(p), n


def star(p):
    """Return significance stars for a p-value."""
    if pd.isna(p):  return ""
    if p < 0.001:   return "***"
    if p < 0.01:    return "**"
    if p < 0.05:    return "*"
    return ""


def fit_wls(formula, data, needed_cols, weight_col="popn_est_23"):
    """
    Fit a WLS model. Returns (fitted_model, subset_df).
    Returns (None, subset_df) if n < 30 or model fails.
    """
    needed = list(dict.fromkeys(needed_cols + [weight_col]))
    sub    = data[[c for c in needed if c in data.columns]].copy().dropna()
    if len(sub) < 30:
        print(f"  WARNING: n={len(sub):,} < 30 after listwise deletion — skipping: {formula[:80]}")
        return None, sub
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model = smf.wls(formula=formula, data=sub, weights=sub[weight_col]).fit()
        return model, sub
    except Exception as e:
        print(f"  WARNING: WLS failed — {e}")
        return None, sub


def tidy_model(model, outcome, outcome_label, model_label, model_family, focal_vars):
    """
    Convert a fitted statsmodels result to a list of coefficient dicts.
    Each dict has: model_family, outcome, outcome_label, model, variable,
    coef, se, t, p, ci_lower, ci_upper, r2, adj_r2, aic, bic, n, focal.
    """
    ci   = model.conf_int()
    rows = []
    for var in model.params.index:
        rows.append({
            "model_family":  model_family,
            "outcome":       outcome,
            "outcome_label": outcome_label,
            "model":         model_label,
            "variable":      var,
            "coef":          model.params[var],
            "se":            model.bse[var],
            "t":             model.tvalues[var],
            "p":             model.pvalues[var],
            "ci_lower":      ci.loc[var, 0],
            "ci_upper":      ci.loc[var, 1],
            "r2":            model.rsquared,
            "adj_r2":        model.rsquared_adj,
            "aic":           model.aic,
            "bic":           model.bic,
            "n":             int(model.nobs),
            "focal":         var in focal_vars,
        })
    return rows


def partial_r2(model, focal_var):
    """
    Partial R² for focal_var: fraction of residual variance from the
    reduced model explained by adding focal_var.
    """
    try:
        formula_reduced = model.model.formula
        terms           = [t.strip() for t in formula_reduced.split("~")[1].split("+")]
        terms_reduced   = [t for t in terms if focal_var not in t]
        if not terms_reduced:
            return np.nan
        outcome   = formula_reduced.split("~")[0].strip()
        formula_r = f"{outcome} ~ " + " + ".join(terms_reduced)
        data      = model.model.data.frame
        w         = model.model.weights
        m_red     = smf.wls(formula=formula_r, data=data, weights=w).fit()
        ssr_full    = model.ssr
        ssr_reduced = m_red.ssr
        if ssr_reduced == 0:
            return np.nan
        return float((ssr_reduced - ssr_full) / ssr_reduced)
    except Exception:
        return np.nan


def cv_r2(formula, data, needed_cols, weight_col="popn_est_23", k=5, seed=42):
    """
    K-fold cross-validated weighted R².
    Safer version: only compares y_true and y_pred on rows where prediction succeeds.
    """
    needed = list(dict.fromkeys(needed_cols + [weight_col]))
    sub = data[[c for c in needed if c in data.columns]].dropna().reset_index(drop=True)

    if len(sub) < k * 10:
        return np.nan

    outcome = formula.split("~")[0].strip()
    n = len(sub)
    fold_size = n // k
    indices = np.random.RandomState(seed).permutation(n)

    y_true_all, y_pred_all, w_all = [], [], []

    for fold in range(k):
        start = fold * fold_size
        end = (fold + 1) * fold_size if fold < k - 1 else n

        val_idx = indices[start:end]
        train_idx = np.setdiff1d(indices, val_idx)

        train = sub.iloc[train_idx].copy()
        val = sub.iloc[val_idx].copy()

        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                m = smf.wls(
                    formula=formula,
                    data=train,
                    weights=train[weight_col]
                ).fit()

            pred = m.predict(val)

            tmp = val[[outcome, weight_col]].copy()
            tmp["pred"] = np.asarray(pred)

            tmp = tmp.replace([np.inf, -np.inf], np.nan).dropna(
                subset=[outcome, weight_col, "pred"]
            )

            y_true_all.extend(tmp[outcome].to_numpy())
            y_pred_all.extend(tmp["pred"].to_numpy())
            w_all.extend(tmp[weight_col].to_numpy())

        except Exception:
            continue

    if len(y_true_all) == 0:
        return np.nan

    y_true = np.asarray(y_true_all, dtype=float)
    y_pred = np.asarray(y_pred_all, dtype=float)
    w = np.asarray(w_all, dtype=float)

    valid = np.isfinite(y_true) & np.isfinite(y_pred) & np.isfinite(w) & (w > 0)

    y_true = y_true[valid]
    y_pred = y_pred[valid]
    w = w[valid]

    if len(y_true) == 0 or w.sum() <= 0:
        return np.nan

    w = w / w.sum()

    ss_res = np.sum(w * (y_true - y_pred) ** 2)
    ss_tot = np.sum(w * (y_true - np.average(y_true, weights=w)) ** 2)

    return float(1 - ss_res / ss_tot) if ss_tot > 0 else np.nan

def partial_spearman_resid(df, col, control_formula_rhs="pct_under65_z + C(fips_st)"):
    """
    Residualise `col` on `control_formula_rhs` via OLS.
    Returns residuals re-indexed to df.index; NaN series on failure.
    """
    needed = [col, "pct_under65_z", "fips_st"]
    sub    = df[[c for c in needed if c in df.columns]].dropna()
    if len(sub) < 50 or sub[col].nunique() < 3:
        return pd.Series(np.nan, index=df.index)
    try:
        resid = smf.ols(f"{col} ~ {control_formula_rhs}", data=sub).fit().resid
        return resid.reindex(df.index)
    except Exception as e:
        print(f"  WARNING: residualisation failed for {col}: {e}")
        return pd.Series(np.nan, index=df.index)


# ---------------------------------------------------------------------------
# LaTeX / table export
# ---------------------------------------------------------------------------

def df_to_latex(df, outpath, caption="", label="", col_format=None):
    """Write a clean LaTeX booktabs table to `outpath`."""
    n_cols     = len(df.columns)
    col_format = col_format or ("l" + "r" * (n_cols - 1))

    def _escape(s):
        return str(s).replace("%", r"\%").replace("_", r"\_").replace("&", r"\&")

    lines = [r"\begin{table}[ht]", r"\centering", r"\small"]
    if caption:
        lines.append(f"\\caption{{{_escape(caption)}}}")
    if label:
        lines.append(f"\\label{{{label}}}")
    lines += [
        f"\\begin{{tabular}}{{{col_format}}}",
        r"\toprule",
        " & ".join(_escape(c) for c in df.columns) + r" \\",
        r"\midrule",
    ]
    for _, row in df.iterrows():
        cells = [_escape(v) if not pd.isna(v) else "---" for v in row]
        lines.append(" & ".join(cells) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    with open(outpath, "w") as f:
        f.write("\n".join(lines) + "\n")



def save_table_csv_tex(df_table, base_path, caption="", label="", col_format=None, drop_internal=True):
    """
    Save a table as CSV + LaTeX only.

    Parameters
    ----------
    df_table : pandas.DataFrame
        Table to save.
    base_path : str
        Output path without extension, e.g. "output/tables/my_table".
    caption : str
        LaTeX table caption.
    label : str
        LaTeX table label.
    col_format : str, optional
        LaTeX tabular column format. If None, df_to_latex chooses a default.
    drop_internal : bool
        If True, drop columns whose names start with "_" before saving.

    Outputs
    -------
    <base_path>.csv
    <base_path>.tex
    """
    out = df_table.copy()
    if drop_internal:
        out = out[[c for c in out.columns if not str(c).startswith("_")]].copy()

    csv_path = base_path + ".csv"
    tex_path = base_path + ".tex"

    out.to_csv(csv_path, index=False)
    df_to_latex(out, tex_path, caption=caption, label=label, col_format=col_format)

    print(f"  Saved {csv_path}")
    print(f"  Saved {tex_path}")
    return out

def df_to_booktabs_png(df, outpath, title=""):
    """
    Render a DataFrame as a publication-style booktabs PNG.
    Horizontal rules only, serif font, white background.
    No cell shading. Left-aligned first column, right-aligned others.
    """
    n_rows, n_cols = df.shape
    fig_h = max(1.8, n_rows * 0.32 + 0.45 + 0.6)
    fig_w = max(6,   n_cols * 1.8)

    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    fig.patch.set_facecolor("white")

    col_positions = np.linspace(0.02, 0.98, n_cols + 1)
    row_height    = 0.85 / (n_rows + 1)
    y_header      = 0.92
    y_positions   = [y_header - (i + 1) * row_height for i in range(n_rows)]

    # Rules
    ax.axhline(y_header + row_height * 0.6,
               xmin=0.01, xmax=0.99, color="black", linewidth=1.2)
    ax.axhline(y_header - row_height * 0.55,
               xmin=0.01, xmax=0.99, color="black", linewidth=0.8)
    ax.axhline(y_positions[-1] - row_height * 0.55,
               xmin=0.01, xmax=0.99, color="black", linewidth=1.2)

    # Header
    for j, col_name in enumerate(df.columns):
        ha = "left" if j == 0 else "right"
        x  = col_positions[j] + 0.005 if j == 0 else col_positions[j + 1] - 0.005
        ax.text(x, y_header, str(col_name),
                ha=ha, va="center", fontsize=9,
                fontweight="bold", fontfamily="serif",
                transform=ax.transAxes)

    # Data rows
    for i, (_, row) in enumerate(df.iterrows()):
        y = y_positions[i]
        for j, val in enumerate(row):
            ha  = "left" if j == 0 else "right"
            x   = col_positions[j] + 0.005 if j == 0 else col_positions[j + 1] - 0.005
            txt = str(val) if not pd.isna(val) else "---"
            ax.text(x, y, txt,
                    ha=ha, va="center", fontsize=8.5,
                    fontfamily="serif", transform=ax.transAxes)

    if title:
        fig.text(0.5, 0.98, title, ha="center", va="top",
                 fontsize=10, fontweight="bold", fontfamily="serif")

    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    fig.savefig(outpath, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
