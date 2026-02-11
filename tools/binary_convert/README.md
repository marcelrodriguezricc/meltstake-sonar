# Imagenex Model 881A Dat to CSV Converter (binary_convert) - by Louis Ross

Converts sonar scan .dat files to a single RunData.csv file.


## Requirements

A directory which contains:
- `RunIndex.csv` - an indexed list of time, type, and name of all sonarScanX.dat files,
- One or many `sonarScanX.dat` files - contains raw sonar data

## Usage

From repository root run:

```bash
python -m tools.binary_convert.main /path/to/sonar/data
```