import pandas as pd

file_path = r"pcp1.pcp"
output_file_path = r"pcp2.pcp"

data = []
header_lines = []

# Read file
with open(file_path, 'r') as file:
    
    # Read header (3 lines for SWAT)
    for i in range(4):
        header_lines.append(next(file))
    
    # Read data
    for line in file:
        line = line.strip()
        
        year = line[:4]
        day = line[4:7]
        
        values = [line[i:i+5] for i in range(7, len(line), 5)]
        
        data.append([year, day] + values)

# Create DataFrame
df = pd.DataFrame(data)

# Convert rainfall columns to float and multiply
for col in df.columns[2:]:
    df[col] = df[col].astype(float) * 1.2
    df.loc[df[col] < 0, col] = -99
# Write back to SWAT format
with open(output_file_path, 'w') as f:
    
    # write header
    for line in header_lines:
        f.write(line)
    
    # write data
    for _, row in df.iterrows():
        
        year = f"{int(row[0]):04d}"
        day  = f"{int(row[1]):03d}"
        
        values = ''.join([f"{float(v):5.1f}" for v in row[2:]])
        
        f.write(year + day + values + "\n")

print("PCP file successfully modified.")
