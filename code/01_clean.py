"""
01_clean.py
-----------
Data ingestion and cleaning pipeline.

Tasks:
  - Load and merge AHRF 2025 files (geo, hp, pop)
  - Download Census TIGER county shapefile
  - Build population-weighted county centroids from ACS tract data
  - Query OSRM drive-time matrix (cached after first run)
  - Fetch CDC PLACES behavioral variables
  - Fetch Census ACS 5-year SES variables
  - Compute derived variables (mortality rates, physician density, rurality tiers)
  - Compute E2SFCA gravity access scores
  - Impute residual NaN access scores via spatial neighbor fallback
  - Write analytic_dataset.csv and print data dictionary

Inputs (placed manually):
  data/AHRF2025geo.csv
  data/AHRF2025hp.csv
  data/AHRF2025pop.csv

Outputs:
  data/analytic_dataset.csv
  data/osrm_cache.csv         (incremental; set FORCE_REBUILD_CACHE=False after first run)
  data/tract_pop_2022.csv     (cached after first run)
"""

# ---------------------------------------------------------------------------
# 0. Package installation
# ---------------------------------------------------------------------------
import subprocess, sys

def _ensure(pkg, import_name=None):
    try:
        __import__(import_name or pkg)
    except ImportError:
        print(f"Installing {pkg} ...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q"])

_ensure("geopandas")
_ensure("pyogrio")
_ensure("shapely")

# ---------------------------------------------------------------------------
# 1. Imports
# ---------------------------------------------------------------------------
import os, time
from collections import defaultdict
import numpy as np
import pandas as pd
import requests
import geopandas as gpd
from shapely.ops import unary_union

# Locate project root
BASE_DIR = os.path.abspath(os.getcwd())
while not os.path.exists(os.path.join(BASE_DIR, "data", "AHRF2025geo.csv")):
    BASE_DIR = os.path.dirname(BASE_DIR)

os.makedirs(os.path.join(BASE_DIR, "data"),   exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "output"), exist_ok=True)

CENSUS_KEY         = "9165119ff8f68083cb5bb9f2a2c43ff111706fd8"
CONTIGUOUS_EXCLUDE = {"02", "15", "60", "66", "69", "72", "78"}
BATCH_SIZE         = 50
FORCE_REBUILD_CACHE = False   # Set True to re-query OSRM after centroid changes

CONTIGUOUS_STATES = [
    "01","04","05","06","08","09","10","11","12","13",
    "16","17","18","19","20","21","22","23","24","25",
    "26","27","28","29","30","31","32","33","34","35",
    "36","37","38","39","40","41","42","44","45","46",
    "47","48","49","50","51","53","54","55","56",
]

# ---------------------------------------------------------------------------
# 2. Functions
# ---------------------------------------------------------------------------

def load_ahrf(path):
    """Load an AHRF CSV, print shape, return DataFrame."""
    df = pd.read_csv(path, low_memory=False)
    print(f"  Loaded {os.path.basename(path)}: {df.shape[0]:,} rows × {df.shape[1]:,} cols")
    return df


def pad_fips(df, col, width=5):
    """Zero-pad a FIPS column to `width` digits."""
    df[col] = df[col].astype(str).str.zfill(width)
    return df


def download_if_missing(url, dest):
    """Download a file from `url` to `dest` only if not already present."""
    if not os.path.exists(dest):
        print(f"  Downloading {os.path.basename(dest)} ...")
        r = requests.get(url, timeout=300)
        r.raise_for_status()
        with open(dest, "wb") as f:
            f.write(r.content)
        print(f"  Saved {dest}")
    else:
        print(f"  Already cached: {os.path.basename(dest)}")


def haversine_km(lat1, lon1, lat2, lon2):
    """Vectorized Haversine distance in kilometres."""
    R = 6371.0
    lat1, lon1, lat2, lon2 = (np.radians(np.asarray(x, dtype=float))
                               for x in (lat1, lon1, lat2, lon2))
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2)**2
    return R * 2 * np.arcsin(np.sqrt(a))


def pop_weighted_centroid(grp):
    """
    Compute population-weighted lat/lon centroid for a group of tracts.
    Falls back to unweighted mean if all populations are zero.
    """
    total = grp["tract_pop"].sum()
    if total <= 0:
        return pd.Series({"lat": grp["tract_lat"].mean(),
                          "lon": grp["tract_lon"].mean()})
    return pd.Series({
        "lat": (grp["tract_lat"] * grp["tract_pop"]).sum() / total,
        "lon": (grp["tract_lon"] * grp["tract_pop"]).sum() / total,
    })


def build_county_origins(tract_zip, tract_pop_csv, counties_gdf):
    """
    Build population-weighted county centroids from ACS tract data.
    Falls back to geographic centroid for counties with no tract coverage.
    Returns a DataFrame with columns: fips_st_cnty, lat, lon.
    """
    print("  Reading tract shapefile ...")
    tracts_gdf = gpd.read_file(f"zip://{tract_zip}")
    print(f"    Tract shapefile: {tracts_gdf.shape[0]:,} tracts")

    tracts_gdf["tract_geoid"]  = (tracts_gdf["STATEFP"].str.zfill(2) +
                                   tracts_gdf["COUNTYFP"].str.zfill(3) +
                                   tracts_gdf["TRACTCE"].str.zfill(6))
    tracts_gdf["fips_st_cnty"] = (tracts_gdf["STATEFP"].str.zfill(2) +
                                   tracts_gdf["COUNTYFP"].str.zfill(3))

    tracts_wgs = tracts_gdf.to_crs("EPSG:4326").copy()
    tracts_wgs["tract_lat"] = tracts_wgs.geometry.centroid.y
    tracts_wgs["tract_lon"] = tracts_wgs.geometry.centroid.x

    # ACS tract population
    if not os.path.exists(tract_pop_csv):
        print("  Downloading ACS 2022 tract populations ...")
        chunks = []
        for st in CONTIGUOUS_STATES:
            try:
                resp = requests.get("https://api.census.gov/data/2022/acs/acs5",
                                    params={"get": "B01003_001E", "for": "tract:*",
                                            "in": f"state:{st}", "key": CENSUS_KEY},
                                    timeout=60)
                resp.raise_for_status()
                data = resp.json()
                chunks.append(pd.DataFrame(data[1:], columns=data[0]))
                time.sleep(0.1)
            except Exception as e:
                print(f"    WARNING: state {st} failed: {e}")
        if chunks:
            tract_pop = pd.concat(chunks, ignore_index=True)
            tract_pop["tract_geoid"] = (tract_pop["state"].str.zfill(2) +
                                        tract_pop["county"].str.zfill(3) +
                                        tract_pop["tract"].str.zfill(6))
            tract_pop["tract_pop"] = pd.to_numeric(
                tract_pop["B01003_001E"], errors="coerce").fillna(0).clip(lower=0)
            tract_pop[["tract_geoid", "tract_pop"]].to_csv(tract_pop_csv, index=False)
            print(f"  Saved {tract_pop_csv} ({len(tract_pop):,} tracts)")
        else:
            tract_pop = pd.DataFrame(columns=["tract_geoid", "tract_pop"])
    else:
        print(f"  Loading cached tract populations ...")
        tract_pop = pd.read_csv(tract_pop_csv, dtype={"tract_geoid": str})
        tract_pop["tract_geoid"] = tract_pop["tract_geoid"].str.zfill(11)
        print(f"    Loaded {len(tract_pop):,} tract rows")

    tracts_merged = tracts_wgs[["tract_geoid", "fips_st_cnty",
                                  "tract_lat", "tract_lon"]].merge(
        tract_pop, on="tract_geoid", how="left"
    )
    tracts_merged["tract_pop"] = tracts_merged["tract_pop"].fillna(0).clip(lower=0)

    print(f"  Computing population-weighted centroids ...")
    county_origins = (tracts_merged.groupby("fips_st_cnty")
                                   .apply(pop_weighted_centroid)
                                   .reset_index())
    print(f"    Centroids computed for {len(county_origins):,} counties")

    # Geographic centroid fallback
    geo_centroids = counties_gdf[["fips_st_cnty", "geometry"]].copy().to_crs("EPSG:4326")
    geo_centroids["centroid_lat"] = geo_centroids.geometry.centroid.y
    geo_centroids["centroid_lon"] = geo_centroids.geometry.centroid.x

    result = geo_centroids[["fips_st_cnty", "centroid_lat", "centroid_lon"]].merge(
        county_origins, on="fips_st_cnty", how="left"
    )
    result["lat"] = result["lat"].fillna(result["centroid_lat"])
    result["lon"] = result["lon"].fillna(result["centroid_lon"])
    result = result[["fips_st_cnty", "lat", "lon"]]
    print(f"    Final county origins (with geo fallback): {len(result):,}")
    return result


def build_osrm_cache(origins_48, cache_path):
    """
    Query OSRM for all county-pair drive times within 180km (Haversine).
    Results saved incrementally to `cache_path`.
    Returns the complete cache DataFrame.
    """
    lats     = origins_48["lat"].values
    lons     = origins_48["lon"].values
    fips_arr = origins_48["fips_st_cnty"].values
    n        = len(fips_arr)

    fips_to_coord = {fips_arr[i]: (lats[i], lons[i]) for i in range(n)}

    print(f"  Pre-filtering pairs by 180 km Haversine distance ...")
    pairs_to_query = [
        (fips_arr[i], lats[i], lons[i], fips_arr[j], lats[j], lons[j])
        for i in range(n)
        for j in np.where((haversine_km(lats[i], lons[i], lats, lons) <= 180.0) &
                          (np.arange(n) != i))[0]
    ]
    print(f"  Pairs within 180 km: {len(pairs_to_query):,}")

    origin_to_dests = defaultdict(list)
    for ofips, olat, olon, dfips, dlat, dlon in pairs_to_query:
        origin_to_dests[ofips].append((dfips, dlat, dlon))

    session       = requests.Session()
    new_rows      = []
    batch_count   = 0
    total_origins = len(origin_to_dests)
    cache_df      = pd.DataFrame(columns=["origin_fips", "dest_fips",
                                           "drive_min", "osrm_failed"])
    osrm_table    = "http://router.project-osrm.org/table/v1/driving"

    for origin_idx, (ofips, dest_list) in enumerate(origin_to_dests.items()):
        olat, olon = fips_to_coord[ofips]

        for batch_start in range(0, len(dest_list), BATCH_SIZE):
            batch           = dest_list[batch_start: batch_start + BATCH_SIZE]
            dest_fips_batch = [d[0] for d in batch]
            coords          = f"{olon},{olat}" + "".join(f";{d[2]},{d[1]}" for d in batch)
            dest_indices    = ";".join(str(i + 1) for i in range(len(batch)))
            url             = (f"{osrm_table}/{coords}"
                               f"?sources=0&destinations={dest_indices}&annotations=duration")
            try:
                resp = session.get(url, timeout=30)
                resp.raise_for_status()
                durations = resp.json()["durations"][0]
                for k, dfips in enumerate(dest_fips_batch):
                    dur = durations[k]
                    new_rows.append({
                        "origin_fips": ofips, "dest_fips": dfips,
                        "drive_min":   float("nan") if dur is None else dur / 60.0,
                        "osrm_failed": dur is None,
                    })
            except Exception:
                for dfips in dest_fips_batch:
                    new_rows.append({"origin_fips": ofips, "dest_fips": dfips,
                                     "drive_min": float("nan"), "osrm_failed": True})

            batch_count += 1
            if batch_count % 50 == 0:
                cache_df = pd.concat([cache_df, pd.DataFrame(new_rows)], ignore_index=True)
                cache_df.to_csv(cache_path, index=False)
                new_rows = []
                pct = (origin_idx + 1) / total_origins * 100
                print(f"  Progress: {origin_idx + 1:,}/{total_origins:,} origins ({pct:.1f}%)")

            time.sleep(0.5)

    if new_rows:
        cache_df = pd.concat([cache_df, pd.DataFrame(new_rows)], ignore_index=True)
        cache_df.to_csv(cache_path, index=False)

    print(f"  OSRM matrix complete: {len(cache_df):,} rows cached")
    return cache_df


def compute_e2sfca(county_df, phy_col, pop_col, drive_df):
    """
    Enhanced Two-Step Floating Catchment Area (Luo & Qi 2009).
    Travel-time zones and weights:
      Zone 1:  0–30 min  → weight 1.00
      Zone 2: 30–45 min  → weight 0.68
      Zone 3: 45–60 min  → weight 0.22
    Hard catchment: 60 min. Returns access scores indexed by county FIPS.
    """
    ZONE_WEIGHTS = [(30, 1.00), (45, 0.68), (60, 0.22)]

    valid = drive_df[(drive_df["osrm_failed"] == False) &
                     (drive_df["drive_min"] <= 60)].copy()

    def zone_weight(t):
        for threshold, w in ZONE_WEIGHTS:
            if t <= threshold:
                return w
        return 0.0

    valid["weight"]       = valid["drive_min"].apply(zone_weight)
    valid["pop_i"]        = valid["origin_fips"].map(county_df[pop_col])
    valid["pop_weighted"] = valid["pop_i"] * valid["weight"]

    pop_within_j = valid.groupby("dest_fips")["pop_weighted"].sum()
    R_j = pd.DataFrame({"physicians":   county_df[phy_col],
                         "pop_catchment": pop_within_j})
    R_j["R"] = R_j["physicians"] / R_j["pop_catchment"].replace(0, np.nan)

    valid["R"]          = valid["dest_fips"].map(R_j["R"])
    valid["weighted_R"] = valid["R"] * valid["weight"]

    return (valid.groupby("origin_fips")["weighted_R"]
                 .sum()
                 .rename("access_score")
                 .reindex(county_df.index))


def fill_nan_access_scores(df_clean, score_cols, counties_adj):
    """
    Impute residual NaN access scores using population-weighted mean of
    contiguous neighbors. Falls back to rurality-tier mean if no neighbors
    have valid scores. Adds binary imputation flag columns.
    """
    adj_index = counties_adj.set_index("fips_st_cnty")
    pop_map   = df_clean.set_index("fips_st_cnty")["popn_est_23"]
    tier_map  = df_clean.set_index("fips_st_cnty")["rurality_tier"]

    def get_neighbors(fips):
        if fips not in adj_index.index:
            return []
        geom = adj_index.loc[fips, "geometry"]
        return counties_adj[counties_adj.geometry.touches(geom)]["fips_st_cnty"].tolist()

    for score_col in score_cols:
        n_missing = df_clean[score_col].isna().sum()
        if n_missing == 0:
            print(f"  {score_col}: no missing values.")
            df_clean[score_col.replace("_score", "_imputed")] = 0
            continue

        score_map = df_clean.set_index("fips_st_cnty")[score_col].copy()

        def _fill(row):
            if pd.notna(row[score_col]):
                return row[score_col]
            neighbors = get_neighbors(row["fips_st_cnty"])
            valid_n   = [(n, score_map.get(n), pop_map.get(n, 1))
                         for n in neighbors if pd.notna(score_map.get(n))]
            if valid_n:
                total_pop = sum(p for _, _, p in valid_n)
                if total_pop > 0:
                    return sum(s * p for _, s, p in valid_n) / total_pop
            tier = tier_map.get(row["fips_st_cnty"])
            return df_clean.loc[df_clean["rurality_tier"] == tier, score_col].mean()

        df_clean[score_col] = df_clean.apply(_fill, axis=1)

        flag_col = score_col.replace("_score", "_imputed")
        df_clean[flag_col] = (
            df_clean[score_col].notna() &
            df_clean["fips_st_cnty"].map(lambda f: pd.isna(score_map.get(f)))
        ).astype(int)

        n_filled = df_clean[flag_col].sum()
        print(f"  {score_col}: filled {n_filled:,} of {n_missing:,} "
              f"({n_filled / n_missing * 100:.1f}%)")

    return df_clean


def assign_rurality(code):
    """Map RUCC code (1–9) to Urban / Suburban / Rural tier."""
    try:
        c = int(code)
    except (ValueError, TypeError):
        return np.nan
    if 1 <= c <= 3:   return "Urban"
    elif 4 <= c <= 6: return "Suburban"
    elif 7 <= c <= 9: return "Rural"
    return np.nan


def assign_rural_region(row, rural_regions):
    """Map a rural county to its named region or 'Other Rural'."""
    if row["rurality_tier"] != "Rural":
        return "Non-rural"
    fips2 = str(row["fips_st"]).zfill(2)
    for region, states in rural_regions.items():
        if fips2 in states:
            return region
    return "Other Rural"


def fetch_cdc_places():
    """
    Fetch CDC PLACES 2023 county-level smoking and obesity prevalence.
    Returns wide DataFrame: fips_st_cnty, smoking_pct, obesity_pct.
    """
    CDC_URL = "https://chronicdata.cdc.gov/resource/swc5-untb.json"
    try:
        resp = requests.get(CDC_URL, params={
            "$where": "measureid in ('CSMOKING', 'OBESITY')",
            "$limit": "50000",
            "$select": "locationid,measureid,data_value",
        }, timeout=60)
        resp.raise_for_status()
        raw = pd.DataFrame(resp.json())
        raw["data_value"] = pd.to_numeric(raw["data_value"], errors="coerce")
        raw["locationid"] = raw["locationid"].astype(str).str.zfill(5)
        wide = (raw.pivot_table(index="locationid", columns="measureid",
                                values="data_value", aggfunc="first")
                   .reset_index()
                   .rename(columns={"locationid": "fips_st_cnty",
                                    "CSMOKING": "smoking_pct",
                                    "OBESITY":  "obesity_pct"}))
        print(f"  CDC PLACES: {len(wide):,} counties, columns {list(wide.columns)}")
        return wide
    except Exception as e:
        print(f"  WARNING: CDC PLACES fetch failed ({e}) — smoking/obesity will be NaN.")
        return pd.DataFrame(columns=["fips_st_cnty", "smoking_pct", "obesity_pct"])


def fetch_acs_ses():
    """
    Fetch Census ACS 5-year 2022 county-level SES variables.
    Returns DataFrame: fips_st_cnty, pct_poverty, pct_uninsured,
                       median_hh_income, pct_bachelor.
    """
    ACS_VARS = ("B17001_002E,B17001_001E,"
                "B27010_017E,B27010_033E,B27010_050E,B27010_066E,"
                "B19013_001E,B15003_022E,B15003_001E,B01003_001E")
    try:
        resp = requests.get("https://api.census.gov/data/2022/acs/acs5",
                            params={"get": ACS_VARS, "for": "county:*",
                                    "in": "state:*", "key": CENSUS_KEY},
                            timeout=120)
        resp.raise_for_status()
        data = resp.json()
        acs  = pd.DataFrame(data[1:], columns=data[0])
        print(f"  ACS: {len(acs):,} county rows")
        acs["fips_st_cnty"] = acs["state"].str.zfill(2) + acs["county"].str.zfill(3)
        for col in ACS_VARS.split(","):
            acs[col] = pd.to_numeric(acs[col], errors="coerce")
        acs["pct_poverty"]      = acs["B17001_002E"] / acs["B17001_001E"] * 100
        acs["pct_uninsured"]    = ((acs["B27010_017E"] + acs["B27010_033E"] +
                                    acs["B27010_050E"] + acs["B27010_066E"])
                                   / acs["B01003_001E"] * 100)
        acs["median_hh_income"] = acs["B19013_001E"]
        acs["pct_bachelor"]     = acs["B15003_022E"] / acs["B15003_001E"] * 100
        return acs[["fips_st_cnty", "pct_poverty", "pct_uninsured",
                    "median_hh_income", "pct_bachelor"]]
    except Exception as e:
        print(f"  WARNING: ACS fetch failed ({e}) — SES variables will be NaN.")
        return pd.DataFrame(columns=["fips_st_cnty", "pct_poverty", "pct_uninsured",
                                      "median_hh_income", "pct_bachelor"])


def print_data_dictionary(df):
    """Print a formatted data dictionary to stdout."""
    header = f"{'Variable':<50} {'Type':<12} {'NonNull':>8} {'Mean':>12} {'SD':>12}"
    print(header)
    print("-" * len(header))
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    for col in df.columns:
        dtype   = str(df[col].dtype)
        nonnull = df[col].notna().sum()
        if col in numeric_cols:
            print(f"{col:<50} {dtype:<12} {nonnull:>8,} "
                  f"{df[col].mean():>12.3f} {df[col].std():>12.3f}")
        else:
            print(f"{col:<50} {dtype:<12} {nonnull:>8,} {'—':>12} {'—':>12}")


# ---------------------------------------------------------------------------
# 3. Pipeline
# ---------------------------------------------------------------------------

print("\n=== 3A. Loading and merging AHRF files ===")
geo = load_ahrf(os.path.join(BASE_DIR, "data", "AHRF2025geo.csv"))
hp  = load_ahrf(os.path.join(BASE_DIR, "data", "AHRF2025hp.csv"))
pop = load_ahrf(os.path.join(BASE_DIR, "data", "AHRF2025pop.csv"))

for _df in (geo, hp, pop):
    pad_fips(_df, "fips_st_cnty")

print(f"\n  geo: {len(geo):,} rows, hp: {len(hp):,} rows, pop: {len(pop):,} rows")
df = geo.merge(hp,  on="fips_st_cnty", how="outer", suffixes=("", "_hp"))
print(f"  After geo ✕ hp merge: {len(df):,} rows")
df = df.merge(pop, on="fips_st_cnty", how="outer", suffixes=("", "_pop"))
print(f"  After merge with pop: {len(df):,} rows × {df.shape[1]:,} cols")

# Drop duplicate suffix columns
dup_cols = [c for c in df.columns if c.endswith("_hp") or c.endswith("_pop")]
df.drop(columns=dup_cols, inplace=True, errors="ignore")
df["fips_st"] = df["fips_st"].astype(str).str.zfill(2)

print("\n=== 3B. Downloading Census TIGER county shapefile ===")
COUNTY_ZIP = os.path.join(BASE_DIR, "data", "cb_2022_us_county_500k.zip")
download_if_missing(
    "https://www2.census.gov/geo/tiger/GENZ2022/shp/cb_2022_us_county_500k.zip",
    COUNTY_ZIP,
)
counties_gdf = gpd.read_file(f"zip://{COUNTY_ZIP}")
counties_gdf["fips_st_cnty"] = (counties_gdf["STATEFP"].str.zfill(2) +
                                  counties_gdf["COUNTYFP"].str.zfill(3))
print(f"  County shapefile: {len(counties_gdf):,} counties")

print("\n=== 3C. Building population-weighted county centroids ===")
TRACT_ZIP     = os.path.join(BASE_DIR, "data", "cb_2022_us_tract_500k.zip")
TRACT_POP_CSV = os.path.join(BASE_DIR, "data", "tract_pop_2022.csv")
download_if_missing(
    "https://www2.census.gov/geo/tiger/GENZ2022/shp/cb_2022_us_tract_500k.zip",
    TRACT_ZIP,
)
county_origins = build_county_origins(TRACT_ZIP, TRACT_POP_CSV, counties_gdf)

print("\n=== 3D. OSRM drive-time matrix ===")
CACHE_PATH = os.path.join(BASE_DIR, "data", "osrm_cache.csv")

origins_48 = county_origins[
    ~county_origins["fips_st_cnty"].str[:2].isin(CONTIGUOUS_EXCLUDE)
].dropna(subset=["lat", "lon"]).copy()
print(f"  Contiguous-48 county origins: {len(origins_48):,}")

if FORCE_REBUILD_CACHE and os.path.exists(CACHE_PATH):
    print("  Removing existing cache (FORCE_REBUILD_CACHE=True) ...")
    os.remove(CACHE_PATH)

if os.path.exists(CACHE_PATH) and os.path.getsize(CACHE_PATH) > 0:
    cache_df = pd.read_csv(CACHE_PATH, dtype={"origin_fips": str, "dest_fips": str})
    cache_df["origin_fips"] = cache_df["origin_fips"].str.zfill(5)
    cache_df["dest_fips"]   = cache_df["dest_fips"].str.zfill(5)
    cache_df["osrm_failed"] = cache_df["osrm_failed"].fillna(False).astype(bool)
    print(f"  Loaded cached OSRM matrix: {len(cache_df):,} rows")
else:
    cache_df = build_osrm_cache(origins_48, CACHE_PATH)
    cache_df["origin_fips"] = cache_df["origin_fips"].astype(str).str.zfill(5)
    cache_df["dest_fips"]   = cache_df["dest_fips"].astype(str).str.zfill(5)
    cache_df["osrm_failed"] = cache_df["osrm_failed"].fillna(False).astype(bool)

print("\n=== 3E. Fetching CDC PLACES 2023 ===")
cdc_wide = fetch_cdc_places()

print("\n=== 3F. Fetching Census ACS 5-year 2022 ===")
acs_out = fetch_acs_ses()

print("\n=== 3G. Computing derived variables ===")
NUMERIC_COLS = [
    "phys_nf_prim_care_pc_exc_rsdt_23", "md_nf_card_dis_23",
    "md_nf_emerg_med_23", "md_nf_pulm_dis_23",
    "popn_est_23", "popn_est_ge65_23",
    "deth_3yr_avg_23", "malgnnt_neplsm_deth_3yr_23",
    "cerbrvsc_dis_deth_3yr_23", "ischemc_heart_dis_deth_3yr_23",
    "clrd_deth_3yr_avg_23", "diabetes_deth_3yr_23",
]
for col in NUMERIC_COLS:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    else:
        print(f"  WARNING: {col} not found in AHRF data.")
        df[col] = np.nan

# Physician density
df["pcp_per_10k"]    = df["phys_nf_prim_care_pc_exc_rsdt_23"] / df["popn_est_23"] * 10_000
df["cardio_per_10k"] = df["md_nf_card_dis_23"]                / df["popn_est_23"] * 10_000
df["em_per_10k"]     = df["md_nf_emerg_med_23"]               / df["popn_est_23"] * 10_000

# Age
df["pct_65plus"]  = df["popn_est_ge65_23"] / df["popn_est_23"] * 100
df["pct_under65"] = 100 - df["pct_65plus"]

# Mortality rates (deaths per 100,000)
df["mort_allcause"] = df["deth_3yr_avg_23"]                / df["popn_est_23"] * 100_000
df["mort_cancer"]   = df["malgnnt_neplsm_deth_3yr_23"]    / df["popn_est_23"] * 100_000
df["mort_stroke"]   = df["cerbrvsc_dis_deth_3yr_23"]      / df["popn_est_23"] * 100_000
df["mort_heart"]    = df["ischemc_heart_dis_deth_3yr_23"] / df["popn_est_23"] * 100_000
df["mort_resp"]     = df["clrd_deth_3yr_avg_23"]           / df["popn_est_23"] * 100_000
df["mort_diabetes"] = df["diabetes_deth_3yr_23"]           / df["popn_est_23"] * 100_000

# HPSA flag
df["hpsa_binary"] = df["hpsa_prim_care_25"].apply(
    lambda x: 1 if x in (1, 2, "1", "2") else 0
)

# Rurality tiers and regions
df["rurality_tier"] = df["rural_urban_contnm_23"].apply(assign_rurality)

RURAL_REGIONS = {
    "Appalachia":    {"21", "54", "51", "47", "42"},
    "South":         {"28", "01", "05", "22"},
    "Great Plains":  {"38", "46", "31", "20", "40"},
    "West":          {"30", "16", "56", "08", "04", "49", "32"},
    "Texas":         {"48", "35"},
    "Rural Midwest": {"19", "17", "18", "27", "29", "55", "26"},
    "South Atlantic":{"37", "45", "13", "12"},
}
df["rural_region"] = df.apply(assign_rural_region, axis=1,
                               rural_regions=RURAL_REGIONS)

print("\n=== 3H. Filtering to contiguous 48 states + population ≥ 500 ===")
df["fips_st"] = df["fips_st"].astype(str).str.zfill(2)
n_before = len(df)
df_clean = df[~df["fips_st"].isin(CONTIGUOUS_EXCLUDE)].copy()
df_clean["popn_est_23"] = pd.to_numeric(df_clean["popn_est_23"], errors="coerce")
df_clean = df_clean[df_clean["popn_est_23"] >= 500].copy().reset_index(drop=True)
print(f"  {n_before:,} rows → {len(df_clean):,} counties after filter")

print("\n=== 3I. Merging external data ===")
n_before = len(df_clean)
df_clean = df_clean.merge(cdc_wide, on="fips_st_cnty", how="left")
print(f"  After CDC PLACES merge: {n_before:,} → {len(df_clean):,} rows")

n_before = len(df_clean)
df_clean = df_clean.merge(acs_out, on="fips_st_cnty", how="left")
print(f"  After ACS merge: {n_before:,} → {len(df_clean):,} rows")

print("\n=== 3J. Computing E2SFCA gravity access scores ===")
county_df_idx = df_clean.set_index("fips_st_cnty")[
    ["phys_nf_prim_care_pc_exc_rsdt_23", "md_nf_card_dis_23",
     "md_nf_emerg_med_23", "popn_est_23"]
].copy()

if len(cache_df) > 0:
    for score_col, phy_col in [
        ("primary_access_score",    "phys_nf_prim_care_pc_exc_rsdt_23"),
        ("cardiology_access_score", "md_nf_card_dis_23"),
        ("emergency_access_score",  "md_nf_emerg_med_23"),
    ]:
        scores = compute_e2sfca(county_df_idx, phy_col, "popn_est_23", cache_df)
        df_clean[score_col] = df_clean["fips_st_cnty"].map(scores) * 10_000
        print(f"  {score_col}: {df_clean[score_col].notna().sum():,} non-null, "
              f"mean = {df_clean[score_col].mean():.4f}")
else:
    print("  WARNING: OSRM cache empty — access scores set to NaN.")
    for col in ["primary_access_score", "cardiology_access_score", "emergency_access_score"]:
        df_clean[col] = np.nan

print("\n=== 3K. Spatial neighbor fallback for NaN access scores ===")
counties_adj = counties_gdf[
    counties_gdf["fips_st_cnty"].isin(df_clean["fips_st_cnty"])
].copy().to_crs("ESRI:102003")

df_clean = fill_nan_access_scores(
    df_clean,
    score_cols=["primary_access_score", "cardiology_access_score", "emergency_access_score"],
    counties_adj=counties_adj,
)

print("\n=== 3L. Computing percentile ranks ===")
PCTILE_VARS = ["pcp_per_10k", "cardio_per_10k", "em_per_10k",
               "primary_access_score", "cardiology_access_score", "emergency_access_score"]
for col in PCTILE_VARS:
    if col in df_clean.columns:
        df_clean[f"{col}_pctile"] = df_clean[col].rank(pct=True) * 100
    else:
        print(f"  WARNING: {col} not found — percentile skipped.")

# Legacy aliases
df_clean["primary_access_pctile"]    = df_clean.get("primary_access_score_pctile")
df_clean["cardiology_access_pctile"] = df_clean.get("cardiology_access_score_pctile")
df_clean["emergency_access_pctile"]  = df_clean.get("emergency_access_score_pctile")

print("\n=== 3M. Writing analytic_dataset.csv ===")
ANALYTIC_COLS = [
    # Identifiers
    "fips_st_cnty", "fips_st", "cnty_name", "st_name",
    # Rurality
    "rurality_tier", "rural_region", "rural_urban_contnm_23", "hpsa_binary",
    # Physician counts
    "phys_nf_prim_care_pc_exc_rsdt_23", "md_nf_card_dis_23",
    "md_nf_emerg_med_23", "md_nf_pulm_dis_23",
    "pcp_per_10k", "cardio_per_10k", "em_per_10k",
    "pcp_per_10k_pctile", "cardio_per_10k_pctile", "em_per_10k_pctile",
    # Access scores
    "primary_access_score", "cardiology_access_score", "emergency_access_score",
    "primary_access_score_pctile", "cardiology_access_score_pctile",
    "emergency_access_score_pctile",
    "primary_access_pctile", "cardiology_access_pctile", "emergency_access_pctile",
    "primary_access_imputed", "cardiology_access_imputed", "emergency_access_imputed",
    # Demographics
    "pct_65plus", "pct_under65",
    # Mortality
    "mort_allcause", "mort_cancer", "mort_stroke",
    "mort_heart", "mort_resp", "mort_diabetes",
    # SES
    "pct_poverty", "pct_uninsured", "median_hh_income", "pct_bachelor",
    # Behavioral
    "smoking_pct", "obesity_pct",
    # Population
    "popn_est_23",
]

out_cols = [c for c in ANALYTIC_COLS if c in df_clean.columns]
analytic = df_clean[out_cols].copy()

out_csv = os.path.join(BASE_DIR, "data", "analytic_dataset.csv")
analytic.to_csv(out_csv, index=False)
print(f"  Saved: {out_csv}  ({len(analytic):,} rows × {len(analytic.columns):,} cols)")

print("\n=== DATA DICTIONARY ===")
print_data_dictionary(analytic)
print("\nDone. analytic_dataset.csv is ready for downstream scripts.")
