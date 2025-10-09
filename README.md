# Personal Finance Tracker — Bank Statements Cleanup

This repository provides an automated cleaning pipeline for messy bank statement exports (2025). The goal is to convert inconsistent raw CSV exports into a reliable, analysis-ready dataset to simplify monthly budgeting.

## Key features
- Robust date parsing and normalization (YYYY-MM-DD)
- Description cleanup (reverse obfuscation, trim)
- Amount normalization (remove non-numeric chars, interpolate missing values)
- Category standardization via synonyms and fuzzy/close matching
- Running balance calculation and anomaly flagging
- Monthly summary and category breakdown exports

## Inputs
- `data/raw/messy_bank_statements.csv` — raw export with columns such as Date, Description, Amount, Category (case/typo variations expected).

## Outputs (written to `data/cleaned/`)
- `cleaned_bank_statements.csv` — cleaned transactions with Date, Description, Amount, Category, Balance, Anomaly
- `monthly_summary.csv` — per-month transaction counts, total income, total expenses, net
- `category_breakdown_by_month.csv` — category totals per month

## Quick start
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the cleaning script from the project root:
   ```bash
   python scripts/cleanup.py
   ```

3. Open the notebook to run and inspect results:
   `notebooks/cleanup.ipynb`

## Notes
- The script is conservative with missing amounts: it preserves NaNs and interpolates when possible.
- Category mapping uses a synonym list and difflib-based matching to avoid extra dependencies.
- Customize `SYNONYM_MAP` and `VALID_CATEGORIES` inside `scripts/cleanup.py` to fit your merchant/category mappings.