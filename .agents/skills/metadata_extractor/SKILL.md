---
name: metadata_extractor
description: Loads a generated .npy file and prints basic array metadata to the terminal.
---

# Metadata Extraction Protocol

You are the **NumPy Metadata Extraction Expert**. When this skill is active, load the requested generated `.npy` file and print basic metadata directly to the terminal.

## Step 1: Load the Array

- Use `numpy.load()` to load the `.npy` file supplied by the user.
- Confirm that the path exists before loading it.
- If the file is missing, stop and report the missing path.

## Step 2: Print Metadata

Print these fields to the terminal:

- file size
- file path
- shape
- data type
- minimum value
- maximum value

Use a simple readable format, for example:

```text
File: output/example.npy
File size: 28 MB
Shape: (128, 128, 128)
Data type: float32
Min value: 0.0
Max value: 1.0
```

## Technical Constraints

- Do not modify the input `.npy` file.
- Do not save reports, plots, or derived files unless the user explicitly requests them.
- If the array is empty and min/max cannot be computed, print the shape and data type, then report that min/max are unavailable for an empty array.
- If a temporary helper script is created, remove it once processing is finished.
