import tifffile
from pathlib import Path
import json

json_path = Path(r"C:\Users\andre\llnl_data_science_challenge_2026\data\missing_struts\registered_jsons\210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.json")

file_path = Path(r"C:\Users\andre\llnl_data_science_challenge_2026\data\9x9x9_octet_lattice\9x9x9_octet_lattice.tif")

print("Exists: ", file_path.exists())
print("Is file", file_path.is_file())

with tifffile.TiffFile(file_path) as tif:
    print("Number of slices: ", len(tif.pages))
    print("Number of series: ", len(tif.series))

    first_series = tif.series[0]

    print(f"Volume shape: {first_series.shape} voxels")
    print("Axes: ", first_series.axes)

with json_path.open("r", encoding="utf-8") as file:
    data = json.load(file)

print("JSON SUMMARY")
print("-" * 50)

print(f"Top-level keys: {list(data.keys())}")

for key, value in data.items():
    if isinstance(value, list):
        print(f"{key}: {len(value):,} records")
    elif isinstance(value, dict):
        print(f"{key}: {len(value):,} fields")
    else:
        print(f"{key}: {value}")

struts = data.get("struts", [])
unit_cells = data.get("unit_cells", [])
junctions = data.get("junctions", [])

print("\nLATTICE COUNTS")
print("-" * 50)
print(f"Junctions: {len(junctions):,}")
print(f"Struts: {len(struts):,}")
print(f"Unit cells: {len(unit_cells):,}")
