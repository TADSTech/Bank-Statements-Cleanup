# Bank Statements Data Cleaning

## Overview

This project provides a Python script (`cleanup.py`) to clean a bank statements dataset from 2025. The script standardizes data formats, handles missing values, corrects inconsistencies, and exports three versions of the cleaned data:
- `bank_data_with_leeway.csv`: Preserves all data with missing values filled.
- `bank_data_no_leeway.csv`: Drops rows with any remaining missing values (except for interpolated amounts).
- `bank_data_sorted_nl.csv`: Same as no-leeway but sorted by date.

The dataset is expected to have columns: `Date`, `Description`, `Amount`, `Category`, and `Account`.

## Prerequisites

- Python 3.8+
- Required libraries:
  ```bash
  pip install pandas numpy charset-normalizer python-dateutil fuzzywuzzy
  ```

## Usage

1. **Prepare the Input Data**:
   - Place the raw dataset (`bank_statements_2025.csv`) in the `data/raw/` directory.
   - Ensure the CSV file has the expected columns: `Date`, `Description`, `Amount`, `Category`, `Account`.

2. **Run the Script**:
   ```bash
   python cleanup.py
   ```

3. **Output**:
   - Cleaned datasets are saved in the `data/cleaned/` directory.
   - The script prints:
     - File encoding details.
     - Initial missing data statistics.
     - Confirmation of successful export.

## Cleaning Process

1. **File Encoding Check**: Verifies the input CSV's encoding using `charset_normalizer`.
2. **Date Standardization**: Converts dates to `DD/MM/YY` format and fills missing dates with forward-fill.
3. **Description Cleaning**: Fills missing values with 'Unspecified', converts to string, and trims whitespace.
4. **Amount Cleaning**: Removes non-numeric characters, rounds to 2 decimals, and interpolates missing values.
5. **Category Standardization**: Uses fuzzy matching with an expanded synonym map to correct typos and inconsistencies.
6. **Account Cleaning**: Fills missing values with 'Unspecified' and standardizes to string format.
7. **Export**: Saves three versions of the cleaned data as described above.

## Notes

- The script assumes the input file is in `../data/raw/bank_statements_2025.csv`. Modify the `input_file` path in the script if needed.
- Output files are saved to `../data/cleaned/`. The directory is created if it doesn't exist.
- The script uses `fuzzywuzzy` for category standardization, which may require additional computational resources for large datasets.