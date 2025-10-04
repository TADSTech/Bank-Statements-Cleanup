import pandas as pd
import numpy as np
import re
from dateutil import parser as dtpr
from fuzzywuzzy import fuzz, process
import charset_normalizer
import os

def check_file_encoding(file_path):
    """Check the encoding of the input file."""
    try:
        with open(file_path, 'rb') as rawdata:
            result = charset_normalizer.detect(rawdata.read(15000))
        print(f"File encoding: {result}")
        return result
    except FileNotFoundError:
        raise FileNotFoundError(f"Input file {file_path} not found.")

def standardize_date(date_str):
    """
    Standardize date strings to 'DD/MM/YY' format.
    Args:
        date_str: Input date string.
    Returns:
        Formatted date string or NaN if invalid.
    """
    if pd.isna(date_str) or not isinstance(date_str, str) or date_str.strip() == '':
        return np.nan
    try:
        parsed_date = dtpr.parse(date_str)
        return parsed_date.strftime('%d/%m/%y')
    except (ValueError, TypeError):
        return np.nan

def clean_amount(amount):
    """
    Clean amount by removing non-numeric characters and rounding to 2 decimals.
    Args:
        amount: Input value.
    Returns:
        Float rounded to 2 decimals or NaN if invalid.
    """
    if pd.isna(amount) or amount == '':
        return np.nan
    amount_str = str(amount)
    cleaned = re.sub(r'[^\\d.-]', '', amount_str)
    cleaned = re.sub(r'\\.+', '.', cleaned)
    if cleaned.count('-') > 1:
        cleaned = '-' + cleaned.replace('-', '')
    try:
        return round(float(cleaned), 2)
    except ValueError:
        return np.nan

def clean_category(category, valid_categories, synonym_to_category, threshold=80):
    """
    Standardize category using fuzzy matching and synonyms.
    Args:
        category: Input category string.
        valid_categories: List of valid category names.
        synonym_to_category: Dictionary mapping synonyms to valid categories.
        threshold: Fuzzy matching score threshold.
    Returns:
        Standardized category or 'Unspecified' if no match.
    """
    if pd.isna(category) or not isinstance(category, str) or category.strip() == '':
        return 'Unspecified'
    category_lower = category.lower().strip()
    if category_lower in synonym_to_category:
        return synonym_to_category[category_lower]
    match = process.extractOne(category_lower, valid_categories, scorer=fuzz.ratio)
    return match[0] if match and match[1] >= threshold else 'Unspecified'

def perfect_cleanup(df):
    """
    Create a strict version of the dataset by dropping rows with any NaNs,
    except for Amount, which is interpolated.
    Args:
        df: Input DataFrame.
    Returns:
        Cleaned DataFrame with no missing values.
    """
    df_clean = df.copy()
    df_clean['Amount'] = df_clean['Amount'].interpolate(method='linear').round(2)
    df_clean = df_clean.dropna()
    return df_clean

def clean_bank_data(input_path, output_dir):
    """
    Main function to clean bank statements dataset and export results.
    Args:
        input_path: Path to the raw CSV file.
        output_dir: Directory to save cleaned CSV files.
    """
    # Set seed for reproducibility
    np.random.seed(42)

    # Check file encoding
    check_file_encoding(input_path)

    # Load data
    try:
        bank_data = pd.read_csv(input_path)
    except Exception as e:
        raise Exception(f"Failed to load data: {e}")

    # Log initial missing data
    missing_data_count = bank_data.isnull().sum()
    total_cells = np.prod(bank_data.shape)
    total_missing = missing_data_count.sum()
    percent_missing = round((total_missing / total_cells) * 100, 2)
    print(f"Initial missing data: {percent_missing}%")
    print("Missing values per column:")
    print(missing_data_count)

    # Clean Date column
    bank_data['Date'] = bank_data['Date'].apply(standardize_date)
    bank_data['Date'] = pd.to_datetime(bank_data['Date'], format='%d/%m/%y', errors='coerce')
    bank_data['Date'] = bank_data['Date'].ffill()

    # Clean Description column
    bank_data['Description'] = bank_data['Description'].fillna('Unspecified').astype('string')
    bank_data['Description'] = bank_data['Description'].replace('nan', 'Unspecified').str.strip()

    # Clean Amount column
    bank_data['Amount'] = bank_data['Amount'].apply(clean_amount)
    bank_data['Amount'] = bank_data['Amount'].interpolate(method='linear').round(2)

    # Clean Category column
    valid_categories = ['Groceries', 'Utilities', 'Entertainment', 'Salary', 'Rent', 'Unspecified']
    synonym_map = {
        'Groceries': ['food', 'grocery', 'grocreies', 'supermarket', 'market'],
        'Utilities': ['bills', 'uti', 'utility', 'gas', 'electricity', 'water', 'phone', 'internet'],
        'Entertainment': ['fun', 'entervtainment', 'dining', 'movie', 'concert', 'streaming'],
        'Salary': ['income', 'salaray', 'wages', 'payroll', 'paycheck', 'freelance'],
        'Rent': ['housing', 'landlord', 'lease', 'rent']
    }
    synonym_to_category = {syn.lower(): cat for cat, syn_list in synonym_map.items() for syn in syn_list}
    bank_data['Category'] = bank_data['Category'].fillna('Unspecified').apply(
        lambda x: clean_category(x, valid_categories, synonym_to_category)
    )

    # Clean Account column
    bank_data['Account'] = bank_data['Account'].fillna('Unspecified').astype(str)
    bank_data['Account'] = bank_data['Account'].replace('nan', 'Unspecified').str.strip()

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Export cleaned datasets
    bank_data.to_csv(os.path.join(output_dir, 'bank_data_with_leeway.csv'), index=False)
    bank_data_improved = perfect_cleanup(bank_data)
    bank_data_improved.to_csv(os.path.join(output_dir, 'bank_data_no_leeway.csv'), index=False)
    sorted_bank_data = bank_data_improved.sort_values(by='Date').reset_index(drop=True)
    sorted_bank_data.to_csv(os.path.join(output_dir, 'bank_data_sorted_nl.csv'), index=False)

    print("Cleaned datasets exported successfully to", output_dir)

if __name__ == "__main__":
    input_file = '../data/raw/bank_statements_2025.csv'
    output_directory = '../data/cleaned'
    clean_bank_data(input_file, output_directory)