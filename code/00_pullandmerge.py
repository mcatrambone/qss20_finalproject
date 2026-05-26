"""
00_pullandmerge.py
------------------
Load the three AHRF 2024-2025 sub-files and merge them into a single
flat county-level dataframe keyed on fips_st_cnty.

Inputs:
    data/AHRF2025geo.csv   -- geographic / classification variables
    data/AHRF2025hp.csv    -- health professions variables
    data/AHRF2025pop.csv   -- population, mortality, and SES variables

Output:
    merged_ahrf.csv        -- all three files joined on fips_st_cnty
"""

import pandas as pd

PATH = "/Users/mattcatrambone/Desktop/qss20_proj/data_2024_2025"

# ── Load ──────────────────────────────────────────────────────────────────────
geo = pd.read_csv(f"{PATH}/AHRF2025geo.csv", sep=",", encoding="latin1", low_memory=False)
hp  = pd.read_csv(f"{PATH}/AHRF2025hp.csv",  sep=",", encoding="latin1", low_memory=False)
pop = pd.read_csv(f"{PATH}/AHRF2025pop.csv",  sep=",", encoding="latin1", low_memory=False)

print(f"geo shape:  {geo.shape}")
print(f"hp shape:   {hp.shape}")
print(f"pop shape:  {pop.shape}")

# ── Merge ─────────────────────────────────────────────────────────────────────
df = (
    geo
    .merge(hp,  on="fips_st_cnty", suffixes=("", "_hp"))
    .merge(pop, on="fips_st_cnty", suffixes=("", "_pop"))
)

print(f"\nMerged shape: {df.shape}")

# ── Save ──────────────────────────────────────────────────────────────────────
df.to_csv("merged_ahrf.csv", index=False)
print("Saved → merged_ahrf.csv")
