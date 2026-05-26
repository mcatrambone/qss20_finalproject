"""
Input:
merged_ahrf.csv  (Output of 00_pullandmerge.py)

Output:
analytic_ahrf.csv (Clean, county-level dataset) 
"""

import pandas as pd

# Column references
RUCC_COL  = "rural_urban_contnm_23"   # Rural-Urban Continuum Code (ERS 2023)
PCP_COL   = "phys_nf_prim_care_pc_exc_rsdt_23"  # Non-federal PCPs
POP_COL   = "popn_est_23"             # Total population estimate
DEATH_COL = "deth_july_1_june_30_23"  # Total deaths 2023
HPSA_COL  = "hpsa_prim_care_25"       # HPSA primary care designation (2025)

# Load
df = pd.read_csv("merged_ahrf.csv", low_memory=False)
print(f"Loaded merged file: {df.shape}")

# Select columns
cols = ["fips_st_cnty", RUCC_COL, PCP_COL, POP_COL, DEATH_COL, HPSA_COL]
df = df[cols].copy()

for c in [RUCC_COL, PCP_COL, POP_COL, DEATH_COL, HPSA_COL]:
    df[c] = pd.to_numeric(df[c], errors="coerce")

df = df.dropna()
print(f"After dropna: {df.shape}")

## Derived variables: 
df["pcp_per_100k"]     = (df[PCP_COL]   / df[POP_COL]) * 100_000
df["mortality_per_1k"] = (df[DEATH_COL] / df[POP_COL]) * 1_000

# Bin RUCC into three readable rurality categories
df["rurality"] = pd.cut(
    df[RUCC_COL],
    bins=[0, 3, 6, 9],
    labels=["Metro (RUCA 1–3)", "Small Urban (RUCA 4–6)", "Rural (RUCA 7–9)"])

# Binary HPSA label
df["hpsa_label"] = df[HPSA_COL].apply(
    lambda x: "HPSA Designated" if x >= 1 else "Not HPSA Designated")

# Filter implausible values 
# Extreme values likely reflect small-population instability
df = df[(df["pcp_per_100k"] < 200) & (df["mortality_per_1k"] < 50)]
df = df.dropna(subset=["rurality"])

print(f"After filtering: {df.shape}")

# Save
df.to_csv("analytic_ahrf.csv", index=False)
print("Saved → analytic_ahrf.csv")
