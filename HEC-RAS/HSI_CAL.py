# -*- coding: utf-8 -*-
"""
Created on Mon Mar  9 18:08:33 2026

@author: acer
"""

import pandas as pd
from scipy.interpolate import interp1d

# -----------------------------
# Read HEC-RAS output
# -----------------------------
hec_file = r"I:/My Drive/Personal Webpage/Github/SWAT_RELATED/HEC-RAS/HEC_RAS_OUTPUT.xlsx"
df = pd.read_excel(hec_file)

print("HEC-RAS columns:")
print(df.columns.tolist())
print(df.head())

# -----------------------------
# Read Fish 1 suitability curves
# -----------------------------
fish_file = r"I:/My Drive/Personal Webpage/Github/SWAT_RELATED/HEC-RAS/Fish1.xlsx"

velocity_si = pd.read_excel(fish_file, sheet_name="Velocity")
depth_si = pd.read_excel(fish_file, sheet_name="Depth")

print("\nVelocity Suitability:")
print(velocity_si)

print("\nDepth Suitability:")
print(depth_si)

# -----------------------------
# Build interpolation functions
# -----------------------------
vel_func = interp1d(
    velocity_si.iloc[:, 0],
    velocity_si.iloc[:, 1],
    bounds_error=False,
    fill_value=(0, 0)
)

depth_func = interp1d(
    depth_si.iloc[:, 0],
    depth_si.iloc[:, 1],
    bounds_error=False,
    fill_value=(0, 0)
)

# -----------------------------
# Compute suitability indices
# -----------------------------
df["Velocity_SI"] = vel_func(df["Vel Total"])
df["Depth_SI"] = depth_func(df["Max Chl Dpth"])

df["Velocity_SI_Area"] = df["Velocity_SI"] * df["Flow Area"]
df["Depth_SI_Area"] = df["Depth_SI"] * df["Flow Area"]

# Combined habitat suitability
df["HSI"] = df["Velocity_SI"] * df["Depth_SI"]
df["WUA_Area"] = df["HSI"] * df["Flow Area"]

# -----------------------------
# Aggregate by Profile
# -----------------------------
wua_table = df.groupby("Profile", as_index=False).agg(
    Total_Flow_Area=("Flow Area", "sum"),
    Velocity_WUA=("Velocity_SI_Area", "sum"),
    Depth_WUA=("Depth_SI_Area", "sum"),
    Combined_WUA=("WUA_Area", "sum")
)

wua_table["Velocity_Weighted_Avg_SI"] = (
    wua_table["Velocity_WUA"] / wua_table["Total_Flow_Area"]
)
wua_table["Depth_Weighted_Avg_SI"] = (
    wua_table["Depth_WUA"] / wua_table["Total_Flow_Area"]
)
wua_table["Combined_Weighted_Avg_HSI"] = (
    wua_table["Combined_WUA"] / wua_table["Total_Flow_Area"]
)

print("\nWUA Summary:")
print(wua_table)

# -----------------------------
# Save outputs
# -----------------------------
df.to_csv("HECRAS_with_SI_WUA.csv", index=False)
wua_table.to_csv("WUA_Profile_Summary.csv", index=False)