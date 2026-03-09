# -*- coding: utf-8 -*-
"""
Created on Mon Mar  9 18:25:24 2026

@author: acer
"""

# -*- coding: utf-8 -*-
"""
Compute SI / HSI / WUA for multiple fish species
"""

import pandas as pd
import numpy as np
from scipy.interpolate import interp1d
from pathlib import Path

# --------------------------------------------------
# INPUT FILES
# --------------------------------------------------
hec_file = Path(r"I:\My Drive\Personal Webpage\Github\SWAT_RELATED\HEC-RAS\HEC_RAS_OUTPUT.xlsx")
fish_folder = Path(r"I:\My Drive\Personal Webpage\Github\SWAT_RELATED\HEC-RAS\fish")
out_folder = Path(r"I:\My Drive\Personal Webpage\Github\SWAT_RELATED\HEC-RAS\output_multi_fish")
out_folder.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------
# READ HEC-RAS DATA
# --------------------------------------------------
df = pd.read_excel(hec_file).copy()

required_cols = ["Profile", "Flow Area", "Vel Total", "Max Chl Dpth"]
missing = [c for c in required_cols if c not in df.columns]
if missing:
    raise ValueError(f"Missing required columns in HEC-RAS file: {missing}")

# --------------------------------------------------
# DEFINE FISH WEIGHTS HERE
# Keys should match fish file stem names
# Example file Fish1.xlsx -> key "Fish1"
# --------------------------------------------------
fish_weights = {
    "Fish1": 0.5,
    "Fish2": 0.3,
    "Fish3": 0.2,
    # add more here
}

# If some fish are not listed above, they will get equal remaining/default handling later
default_weight = None   # set to a number like 1.0 if you want same default before normalization

# --------------------------------------------------
# HELPER FUNCTION
# --------------------------------------------------
def make_interp(curve_df):
    x = pd.to_numeric(curve_df.iloc[:, 0], errors="coerce").values
    y = pd.to_numeric(curve_df.iloc[:, 1], errors="coerce").values

    mask = (~np.isnan(x)) & (~np.isnan(y))
    x = x[mask]
    y = y[mask]

    # sort in case file is unordered
    order = np.argsort(x)
    x = x[order]
    y = y[order]

    return interp1d(
        x, y,
        bounds_error=False,
        fill_value=(0, 0)   # outside suitability range = 0
    )

# --------------------------------------------------
# FIND ALL FISH FILES
# --------------------------------------------------
fish_files = sorted(fish_folder.glob("*.xlsx"))

if not fish_files:
    raise FileNotFoundError(f"No fish Excel files found in: {fish_folder}")

fish_names = [f.stem for f in fish_files]

# --------------------------------------------------
# PREPARE WEIGHTS
# --------------------------------------------------
weights = {}
for name in fish_names:
    if name in fish_weights:
        weights[name] = fish_weights[name]
    elif default_weight is not None:
        weights[name] = default_weight
    else:
        weights[name] = 1.0

# normalize weights
weight_sum = sum(weights.values())
if weight_sum == 0:
    raise ValueError("Sum of fish weights is zero. Please check fish_weights.")

weights = {k: v / weight_sum for k, v in weights.items()}

print("Normalized fish weights:")
for k, v in weights.items():
    print(f"{k}: {v:.4f}")

# --------------------------------------------------
# STORE RESULTS
# --------------------------------------------------
profile_summary_list = []
fish_detail_tables = {}

# Make a working copy for all-fish outputs
df_all = df.copy()

# --------------------------------------------------
# LOOP THROUGH EACH FISH
# --------------------------------------------------
for fish_file in fish_files:
    fish_name = fish_file.stem
    print(f"\nProcessing {fish_name} ...")

    velocity_si = pd.read_excel(fish_file, sheet_name="Velocity")
    depth_si = pd.read_excel(fish_file, sheet_name="Depth")

    vel_func = make_interp(velocity_si)
    depth_func = make_interp(depth_si)

    # fish-specific calculations
    vel_col = f"{fish_name}_Velocity_SI"
    dep_col = f"{fish_name}_Depth_SI"
    hsi_col = f"{fish_name}_HSI"
    vel_area_col = f"{fish_name}_Velocity_SI_Area"
    dep_area_col = f"{fish_name}_Depth_SI_Area"
    wua_col = f"{fish_name}_WUA_Area"

    df_all[vel_col] = vel_func(df_all["Vel Total"])
    df_all[dep_col] = depth_func(df_all["Max Chl Dpth"])

    df_all[vel_area_col] = df_all[vel_col] * df_all["Flow Area"]
    df_all[dep_area_col] = df_all[dep_col] * df_all["Flow Area"]

    df_all[hsi_col] = df_all[vel_col] * df_all[dep_col]
    df_all[wua_col] = df_all[hsi_col] * df_all["Flow Area"]

    # profile-wise summary for this fish
    fish_summary = df_all.groupby("Profile", as_index=False).agg(
        Total_Flow_Area=("Flow Area", "sum"),
        Velocity_WUA=(vel_area_col, "sum"),
        Depth_WUA=(dep_area_col, "sum"),
        Combined_WUA=(wua_col, "sum")
    )

    fish_summary["Velocity_Weighted_Avg_SI"] = fish_summary["Velocity_WUA"] / fish_summary["Total_Flow_Area"]
    fish_summary["Depth_Weighted_Avg_SI"] = fish_summary["Depth_WUA"] / fish_summary["Total_Flow_Area"]
    fish_summary["Combined_Weighted_Avg_HSI"] = fish_summary["Combined_WUA"] / fish_summary["Total_Flow_Area"]
    fish_summary["Fish"] = fish_name
    fish_summary["Weight"] = weights[fish_name]

    profile_summary_list.append(fish_summary)
    fish_detail_tables[fish_name] = fish_summary

    # save fish-wise detailed dataframe if desired
    fish_cols = ["Profile", "Flow Area", "Vel Total", "Max Chl Dpth",
                 vel_col, dep_col, hsi_col, vel_area_col, dep_area_col, wua_col]
    df_all[fish_cols].to_csv(out_folder / f"{fish_name}_detailed_results.csv", index=False)
    fish_summary.to_csv(out_folder / f"{fish_name}_profile_summary.csv", index=False)

# --------------------------------------------------
# COMBINE ALL FISH SUMMARIES
# --------------------------------------------------
all_fish_summary = pd.concat(profile_summary_list, ignore_index=True)
all_fish_summary.to_csv(out_folder / "All_Fish_Profile_Summaries.csv", index=False)

# --------------------------------------------------
# COMPUTE WEIGHTED MULTI-FISH INDEX PROFILE-WISE
# --------------------------------------------------
weighted_rows = []

for profile, grp in all_fish_summary.groupby("Profile"):
    total_flow_area = grp["Total_Flow_Area"].iloc[0]

    weighted_velocity_avg_si = np.sum(grp["Velocity_Weighted_Avg_SI"] * grp["Weight"])
    weighted_depth_avg_si = np.sum(grp["Depth_Weighted_Avg_SI"] * grp["Weight"])
    weighted_combined_hsi = np.sum(grp["Combined_Weighted_Avg_HSI"] * grp["Weight"])

    weighted_velocity_wua = np.sum(grp["Velocity_WUA"] * grp["Weight"])
    weighted_depth_wua = np.sum(grp["Depth_WUA"] * grp["Weight"])
    weighted_combined_wua = np.sum(grp["Combined_WUA"] * grp["Weight"])

    weighted_rows.append({
        "Profile": profile,
        "Total_Flow_Area": total_flow_area,
        "Weighted_Velocity_WUA": weighted_velocity_wua,
        "Weighted_Depth_WUA": weighted_depth_wua,
        "Weighted_Combined_WUA": weighted_combined_wua,
        "Weighted_Velocity_Avg_SI": weighted_velocity_avg_si,
        "Weighted_Depth_Avg_SI": weighted_depth_avg_si,
        "Weighted_Combined_Avg_HSI": weighted_combined_hsi
    })

weighted_summary = pd.DataFrame(weighted_rows).sort_values("Profile")
weighted_summary.to_csv(out_folder / "Weighted_MultiFish_WUA_Summary.csv", index=False)

print("\nWeighted summary:")
print(weighted_summary)

# --------------------------------------------------
# OPTIONAL: SAVE FULL MASTER DATAFRAME
# --------------------------------------------------
df_all.to_csv(out_folder / "HECRAS_AllFish_Detailed.csv", index=False)

print(f"\nDone. Outputs saved in:\n{out_folder}")