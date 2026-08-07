import re
from pathlib import Path

import pandas as pd
from tqdm import tqdm
import traceback

ROOT_DIR = Path(__file__).resolve().parent.parent
INPUT_DIR = ROOT_DIR / "rent-and-price-data" / "qld"
OUTPUT_PATH = ROOT_DIR / "rent-and-price-data" / "qld" /"qld-rent-combined.csv"

SHEET_TARGETS = ["Flats 2", "2 Bed Flats", "2 Bed Flats ", "House 3", "3 Bed Houses"]

def _parse_year_quarter(path):
    """parse year and quarter from QLD workbook filename"""
    match = re.search(r'(\d{4})_q([1-4])', path.name, flags=re.IGNORECASE)
    if not match:
        return None

    year = int(match.group(1))
    quarter = int(match.group(2))
    return year, quarter

def _read_sheet_rows(path, sheet_name, property_type, date_label):
    """Read one sheet starting at row A4 and return cleaned records."""
    suffix = path.suffix.lower()
    engine = "xlrd"

    frame = pd.read_excel(
        path,
        sheet_name=sheet_name,
        header=None,
        skiprows=3,
        usecols=[0, 1, 2],
        engine=engine,
    )

    # drop all rows where column B is blank
    frame = frame.dropna(subset=[1])

    rows = []
    for _, row in frame.iterrows():

        try:
            region = row.iloc[0].replace('*','').replace('^','').replace('~','').strip()
        except Exception:
            continue

        rent_value = row.iloc[1]
        if rent_value is None:
            continue

        rows.append({
            "Region": region,
            "Date": date_label,
            "Type": property_type,
            "Rent ($)": rent_value,
            "Count": row.iloc[2]
        })

    rows = pd.DataFrame(rows)

    return rows

def _read_workbook(path):
    engine = "xlrd"

    excel_file = pd.ExcelFile(path, engine=engine)
    year, quarter = _parse_year_quarter(path)
    if year is None or quarter is None:
        raise ValueError(f"Could not infer year/quarter from {path.name}")

    quarter_month_map = {1: 3, 2: 6, 3: 9, 4: 12}
    date_label = f"{year}-{quarter_month_map[quarter]:02d}-01"
    data = pd.DataFrame()

    for sheet in SHEET_TARGETS:
        if sheet in excel_file.sheet_names:
            if "Flats" in sheet:
                property_type = "Flat 2"
            elif "House" in sheet:
                property_type = "House 3"
            else:
                property_type = "unknown"
            sheet_data = _read_sheet_rows(path, sheet, property_type, date_label)
            data = pd.concat([data, sheet_data], ignore_index=True)

    data = pd.DataFrame(data)

    return data


def combine_qld_rent_data(input_dir):
    excel_files = sorted(list(input_dir.glob("*.xls")))
    if not excel_files:
        raise RuntimeError(f'No Excel files found in {input_dir}')

    records = pd.DataFrame()
    files_read = 0

    for path in tqdm(excel_files):
        try:
            wb_data = _read_workbook(path)
            records = pd.concat([records, wb_data], ignore_index=True)
            files_read += 1
        except Exception:
            print(f"Skipping {path.name}: {traceback.format_exc()}")
            continue

    return records, files_read

if __name__ == "__main__":
    records, files_read = combine_qld_rent_data(INPUT_DIR)
    records.to_csv(OUTPUT_PATH, index=False)