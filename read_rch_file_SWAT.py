# -*- coding: utf-8 -*-
"""
Created on Mon Mar  9 17:20:56 2026

@author: acer
"""

# -*- coding: utf-8 -*-
"""
Created on Thu May 29 15:48:00 2025

@author: acer
"""

#%% Read and save output.rch file as df


import pandas as pd
from pathlib import Path

target_folder = Path(r"E:\Tripti\monthly")
file_path = target_folder / "output.rch"

column_names = [
    "NAME", "RCH", "GIS", "MON", "AREAkm2", "FLOW_INcms", "FLOW_OUTcms", "EVAPcms",
    "TLOSScms", "SEDINtons", "SEDOUTtons", "SEDCONCmg/L", "ORGNINkg", "ORGNOUTkg",
    "ORGPINkg", "ORGP_OUTkg", "NO3_INkg", "NO3_OUTkg", "NH4_INkg", "NH4_OUTkg",
    "NO2_INkg", "NO2_OUTkg", "MINP_INkg", "MINP_OUTkg", "CHLA_INkg", "CHLA_OUTkg",
    "CBOD_INkg", "CBOD_OUTkg", "DISOX_INkg", "DISOX_OUTkg", "SOLPST_INmg", "SOLPST_OUTmg",
    "SORPST_INmg", "SORPST_OUTmg", "REACTPSTmg", "VOLPSTmg", "SETTLPSTmg",
    "RESUSP_PSTmg", "DIFFUSEPSTmg", "REACBEDPSTmg", "BURYPSTmg", "BED_PSTmg",
    "BACTP_OUTct", "BACTLP_OUTct", "CMETAL#1kg", "CMETAL#2kg", "CMETAL#3kg",
    "TOT_Nkg", "TOT_Pkg", "NO3ConcMg/l", "WTMPdegc"
]

rows = []
bad_rows = []

with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
    for line_no, line in enumerate(f, start=1):
        parts = line.split()

        # keep only real data rows
        if not parts or parts[0] != "REACH":
            continue

        if len(parts) == len(column_names):
            rows.append(parts)
        else:
            bad_rows.append((line_no, len(parts), line.strip()))

output_rch = pd.DataFrame(rows, columns=column_names)

# numeric conversion for all except NAME
for col in output_rch.columns[1:]:
    output_rch[col] = pd.to_numeric(output_rch[col], errors="coerce")

output_rch.to_csv(target_folder / "output_rch.csv", index=False)

print("Parsed shape:", output_rch.shape)
print("Bad rows:", len(bad_rows))
print("First few bad rows:", bad_rows[:5])
#%%
reaches = [38, 15, 39, 33, 43, 28, 11, 2, 8]

selected_reaches = output_rch[output_rch["RCH"].isin(reaches)]

selected_reaches.to_csv("selected_reaches.csv", index=False)

print(selected_reaches.head())


#%%
import matplotlib.pyplot as plt

reaches = [38, 15, 39, 33, 43, 28, 11, 2, 8]

selected_reaches = output_rch[output_rch["RCH"].isin(reaches)].copy()

# keep monthly records only, if needed
selected_reaches = selected_reaches[selected_reaches["MON"] > 0]

# make sure sorted properly
selected_reaches = selected_reaches.sort_values(["RCH", "MON"])

plt.figure(figsize=(10, 6))

for rch in reaches:
    df_rch = selected_reaches[selected_reaches["RCH"] == rch]
    plt.plot(df_rch["MON"], df_rch["FLOW_OUTcms"], marker='o', label=f"Reach {rch}")

plt.xlabel("Month")
plt.ylabel("Discharge (FLOW_OUTcms)")
plt.title("Discharge of Selected Reaches")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()

#%%

import pandas as pd

reaches = [38, 15, 39, 33, 43, 28, 11, 2, 8]

selected = output_rch[
    (output_rch["RCH"].isin(reaches)) &
    (output_rch["MON"] > 0)     # keep monthly records
]

# exceedance levels you want
exceed_levels = [2,5,10,20,30,40,50,60,70,80,90,95,98]

flow_table = pd.DataFrame()

for p in exceed_levels:
    flow_table[f"Q{p}"] = (
        selected.groupby("RCH")["FLOW_OUTcms"]
        .quantile(1 - p/100)
    )

print(flow_table)

flow_table.to_csv("reach_flow_percentiles.csv")


#%%


pivot_q = selected.pivot_table(
    index=selected.index,
    columns="RCH",
    values="FLOW_OUTcms"
)


from sklearn.linear_model import LinearRegression
import numpy as np
import pandas as pd

base_reach = 38
q_base = np.arange(0, 101, 5)

extrapolated_reg = pd.DataFrame(index=q_base)
extrapolated_reg.index.name = f"BaseQ_Reach_{base_reach}"

for rch in reaches:
    if rch == base_reach:
        extrapolated_reg[f"Reach_{rch}"] = q_base
        continue

    df_pair = selected[selected["RCH"].isin([base_reach, rch])].copy()

    # if monthly rows are aligned by sequence
    q_base_series = selected[selected["RCH"] == base_reach]["FLOW_OUTcms"].reset_index(drop=True)
    q_rch_series  = selected[selected["RCH"] == rch]["FLOW_OUTcms"].reset_index(drop=True)

    n = min(len(q_base_series), len(q_rch_series))
    X = q_base_series.iloc[:n].values.reshape(-1, 1)
    y = q_rch_series.iloc[:n].values

    model = LinearRegression()
    model.fit(X, y)

    extrapolated_reg[f"Reach_{rch}"] = model.predict(q_base.reshape(-1, 1))
extrapolated_reg = extrapolated_reg.T
print(extrapolated_reg)
extrapolated_reg.to_csv("extrapolated_reach_flows_regression.csv")

