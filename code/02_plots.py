"""
Input:
analytic_ahrf.csv (Output of 01_clean.py)

Outputs:
pcp_mortality_ruca.png (Scatter of PCP supply vs. mortality by rurality
mortality_rurality_hpsa.png (Boxplot of mortality by rurality and HPSA status) 
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# Load
df = pd.read_csv("analytic_ahrf.csv", low_memory=False)
print(f"Loaded analytic file: {df.shape}")

# Plot 1: PCP supply vs. mortality, colored by rurality  
fig, ax = plt.subplots(figsize=(9, 6))

colors = {
    "Metro (RUCA 1–3)":       "#2196F3",
    "Small Urban (RUCA 4–6)": "#FF9800",
    "Rural (RUCA 7–9)":       "#E53935",
}

for label, grp in df.groupby("rurality", observed=True):
    ax.scatter(
        grp["pcp_per_100k"],
        grp["mortality_per_1k"],
        c=colors[str(label)],
        alpha=0.45,
        s=18,
        label=str(label),
        edgecolors="none",
    )
    m, b = np.polyfit(grp["pcp_per_100k"], grp["mortality_per_1k"], 1)
    x_line = np.linspace(grp["pcp_per_100k"].min(), grp["pcp_per_100k"].max(), 100)
    ax.plot(x_line, m * x_line + b, color=colors[str(label)], linewidth=1.8, alpha=0.9)

    r = np.corrcoef(grp["pcp_per_100k"], grp["mortality_per_1k"])[0, 1]
    print(f"{label}: n={len(grp)}, r={r:.3f}")

ax.set_xlabel("Primary Care Physicians per 100,000 Population (2023)", fontsize=11)
ax.set_ylabel("Crude Mortality Rate per 1,000 Population (2023)", fontsize=11)
ax.set_title(
    "PCP Supply vs. Mortality by Rural-Urban Category (by County)",
    fontsize=12, fontweight="bold", pad=10,
)
ax.legend(title="Rurality (RUCC)", fontsize=9, title_fontsize=9)

plt.tight_layout()
plt.savefig("output/pcp_mortality_ruca.png", dpi=180, bbox_inches="tight")
plt.close()

# Plot 2: Mortality boxplots by rurality × HPSA designation
fig, ax = plt.subplots(figsize=(10, 6))

rurality_cats = ["Metro (RUCA 1–3)", "Small Urban (RUCA 4–6)", "Rural (RUCA 7–9)"]
hpsa_cats     = ["Not HPSA Designated", "HPSA Designated"]
box_colors    = {"Not HPSA Designated": "#90CAF9", "HPSA Designated": "#E53935"}

width  = 0.3
x_base = np.arange(len(rurality_cats)) * 1.2

positions  = []
box_data   = []
fill_colors = []

for i, rur in enumerate(rurality_cats):
    for j, hpsa in enumerate(hpsa_cats):
        mask = (df["rurality"] == rur) & (df["hpsa_label"] == hpsa)
        data = df.loc[mask, "mortality_per_1k"].dropna().values
        pos  = x_base[i] + j * (width + 0.05)
        positions.append(pos)
        box_data.append(data)
        fill_colors.append(box_colors[hpsa])

bp = ax.boxplot(
    box_data,
    positions=positions,
    widths=width,
    patch_artist=True,
    medianprops=dict(color="black", linewidth=2),
    whiskerprops=dict(linewidth=1.2),
    capprops=dict(linewidth=1.2),
    flierprops=dict(marker="o", markersize=2.5, alpha=0.3, linestyle="none"),
)

for patch, color in zip(bp["boxes"], fill_colors):
    patch.set_facecolor(color)
    patch.set_alpha(0.8)

tick_positions = [x_base[i] + (width + 0.05) / 2 for i in range(len(rurality_cats))]
ax.set_xticks(tick_positions)
ax.set_xticklabels(rurality_cats, fontsize=11)

ax.set_ylabel("Crude Mortality Rate per 1,000 Population", fontsize=11)
ax.set_title(
    "Mortality Rate by Rurality and PCP Shortage Designation (by County)",
    fontsize=12, fontweight="bold", pad=10,
)

patches = [mpatches.Patch(color=c, alpha=0.8, label=l) for l, c in box_colors.items()]
ax.legend(handles=patches, fontsize=9, loc="upper left")

for pos, data in zip(positions, box_data):
    ax.text(
        pos, ax.get_ylim()[0] - 0.3, f"n={len(data)}",
        ha="center", va="top", fontsize=7, color="gray",
    )

plt.tight_layout()
plt.savefig("output/mortality_rurality_hpsa.png", dpi=180, bbox_inches="tight")
plt.close()
