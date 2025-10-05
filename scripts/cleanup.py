# Automated cleaning script for bank statements.
# This script reads the messy CSV, standardizes dates to YYYY-MM-DD,
# trims extra spaces and fixes typos in descriptions,
# ensures amounts are floats (fills missing with 0),
# standardizes categories to title case (fills missing with 'Uncategorized'),
# and outputs a cleaned CSV.

import os
import re
import logging
from datetime import datetime
from dateutil.parser import parse
import pandas as pd
import numpy as np

"""
Personal Finance Tracker - automated cleaning script
- Normalizes dates to YYYY-MM-DD
- Cleans descriptions (reverses common obfuscation, trims)
- Cleans amounts (removes currency chars, preserves NaNs, interpolates)
- Standardizes categories using synonyms + fuzzy matching
- Computes running balance and monthly summaries
- Flags anomalous transactions
- Outputs cleaned CSV and monthly summary CSV into ../data/cleaned/
"""

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

BASE_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
RAW_PATH = os.path.join(BASE_DIR, 'data', 'raw', 'messy_bank_statements.csv')
CLEAN_DIR = os.path.join(BASE_DIR, 'data', 'cleaned')
os.makedirs(CLEAN_DIR, exist_ok=True)
CLEANED_CSV = os.path.join(CLEAN_DIR, 'cleaned_bank_statements.csv')
MONTHLY_SUMMARY_CSV = os.path.join(CLEAN_DIR, 'monthly_summary.csv')

# Valid categories + synonyms
VALID_CATEGORIES = ['Groceries', 'Utilities', 'Entertainment', 'Salary', 'Rent', 'Transportation', 'Dining Out', 'Miscellaneous', 'Unspecified']
SYNONYM_MAP = {
    'Groceries': ['food', 'grocery', 'grocer', 'supermarket', 'groc3ry', 'groc3ry shopping'],
    'Utilities': ['utility', 'utilities', 'electric', 'el3ctric', 'water', 'gas bill'],
    'Entertainment': ['movie', 'movietickets', 'movieticket', 'movi3', 'concert', 'streaming', 'dining out'],
    'Salary': ['salary', 'salaray', 's@l@ry', 'payroll', 'paycheck', 'deposit'],
    'Rent': ['rent', 'r3nt', 'landlord', 'lease'],
    'Transportation': ['gas', 'g@s', 'gas station', 'transportation'],
    'Dining Out': ['dinner', 'restaurant', 'dinn3r'],
    'Miscellaneous': ['misc', 'miscellaneous', 'unspecified']
}
# reverse sync
SYN_TO_CAT = {syn.lower(): cat for cat, lst in SYNONYM_MAP.items() for syn in lst}

# fuzzy matching fallback (use python's built-in difflib to avoid extra dependencies)
from difflib import get_close_matches

def standardize_date(s):
    if pd.isna(s):
        return pd.NaT
    try:
        # strip and try to parse
        return parse(str(s).strip(), dayfirst=False, yearfirst=False).date()
    except Exception:
        # try common alternative formats
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%Y/%m/%d", "%d-%b-%Y", "%d-%B-%Y"):
            try:
                return datetime.strptime(str(s).strip(), fmt).date()
            except Exception:
                continue
    return pd.NaT

def clean_description(s):
    if pd.isna(s):
        return "Unspecified"
    s = str(s).strip()
    # reverse common obfuscation
    s = s.replace('@', 'a').replace('3', 'e').replace('0', 'o').replace('$', 's').replace('5', 's')
    # remove repeated non-alphanumeric (except spaces and punctuation)
    s = re.sub(r'[^A-Za-z0-9\-\.,& ]+', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def clean_amount(a):
    if pd.isna(a) or str(a).strip() == '':
        return np.nan
    s = str(a)
    # remove currency symbols and thousands separators
    s = re.sub(r'[^\d\.\-]', '', s)
    # collapse multiple dots
    s = re.sub(r'\.{2,}', '.', s)
    # ensure single leading negative if present
    if s.count('-') > 1:
        s = '-' + s.replace('-', '')
    try:
        return round(float(s), 2)
    except Exception:
        return np.nan

def clean_category(cat):
    if pd.isna(cat) or str(cat).strip() == '':
        return 'Unspecified'
    c = str(cat).strip().lower()
    # direct synonym match
    if c in SYN_TO_CAT:
        return SYN_TO_CAT[c]
    # close match among synonyms
    match = get_close_matches(c, list(SYN_TO_CAT.keys()), n=1, cutoff=0.8)
    if match:
        return SYN_TO_CAT[match[0]]
    # close match among valid categories
    match2 = get_close_matches(c.title(), VALID_CATEGORIES, n=1, cutoff=0.8)
    if match2:
        return match2[0]
    return 'Unspecified'

def load_and_clean(path):
    logging.info(f"Loading raw data from: {path}")
    df = pd.read_csv(path, dtype=str, keep_default_na=False, na_values=['', 'None', 'nan', 'NaN'])
    # normalize column names
    df.columns = [c.strip().title() for c in df.columns]
    # ensure required columns exist
    for col in ['Date', 'Description', 'Amount', 'Category']:
        if col not in df.columns:
            df[col] = np.nan

    # Clean columns
    df['Date'] = df['Date'].apply(lambda x: standardize_date(x))
    df['Description'] = df['Description'].apply(clean_description)
    df['Amount'] = df['Amount'].apply(clean_amount)
    df['Category'] = df['Category'].apply(clean_category)

    # convert date to datetime and sort
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values(by='Date').reset_index(drop=True)

    # Interpolate missing amounts linearly if there are numeric neighbors, otherwise leave NaN
    if df['Amount'].notna().sum() >= 2:
        df['Amount'] = df['Amount'].astype(float)
        df['Amount'] = df['Amount'].interpolate(method='linear').round(2)

    # Compute running balance
    df['Balance'] = df['Amount'].fillna(0).cumsum().round(2)

    # Flag anomalies: transactions with absolute value > mean_abs + 3*std_abs
    abs_stats = df['Amount'].abs().dropna()
    if not abs_stats.empty:
        mean_abs = abs_stats.mean()
        std_abs = abs_stats.std(ddof=0)
        threshold = mean_abs + 3 * (std_abs if not np.isnan(std_abs) else 0)
        df['Anomaly'] = df['Amount'].abs().apply(lambda x: bool(x > threshold) if not pd.isna(x) else False)
    else:
        df['Anomaly'] = False

    return df

def monthly_summary(df):
    df2 = df.copy()
    df2 = df2[df2['Date'].notna()]
    df2['Month'] = df2['Date'].dt.to_period('M').astype(str)
    summary = df2.groupby('Month').agg(
        transactions=('Amount', 'count'),
        total_income=('Amount', lambda x: x[x>0].sum()),
        total_expense=('Amount', lambda x: x[x<0].sum()),
        net=('Amount', 'sum')
    ).reset_index()
    # category breakdown per month (top categories)
    cat_breakdown = df2.groupby(['Month', 'Category'])['Amount'].sum().reset_index()
    return summary, cat_breakdown

def save_outputs(df, summary, cat_breakdown):
    logging.info(f"Saving cleaned data to: {CLEANED_CSV}")
    df.to_csv(CLEANED_CSV, index=False, date_format='%Y-%m-%d')
    logging.info(f"Saving monthly summary to: {MONTHLY_SUMMARY_CSV}")
    # combine summary and top categories per month for a compact CSV
    # we'll save summary and a separate category breakdown
    summary.to_csv(MONTHLY_SUMMARY_CSV, index=False)
    cat_breakdown.to_csv(os.path.join(CLEAN_DIR, 'category_breakdown_by_month.csv'), index=False)

def main():
    df = load_and_clean(RAW_PATH)
    summary, cat_breakdown = monthly_summary(df)
    save_outputs(df, summary, cat_breakdown)
    logging.info("Cleaning complete.")
    # brief stdout summary
    print("Sample cleaned rows:")
    print(df.head().to_string(index=False))
    print("\nMonthly summary:")
    print(summary.head().to_string(index=False))
    total_income = df[df['Amount'] > 0]['Amount'].sum()
    total_expense = df[df['Amount'] < 0]['Amount'].sum()
    final_balance = df['Balance'].iloc[-1] if not df.empty else 0
    print(f"\nTotal Income: {total_income:.2f}")
    print(f"Total Expenses: {total_expense:.2f}")
    print(f"Final Balance: {final_balance:.2f}")

if __name__ == '__main__':
    main()