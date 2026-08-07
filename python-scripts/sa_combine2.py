#!/usr/bin/env python3
"""Process post-2020-12 South Australia rent Excel reports into a combined CSV."""

import argparse
import re
from pathlib import Path
from typing import Any
import pandas as pd
import traceback
from tqdm import tqdm

ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_INPUT_DIR = ROOT_DIR / "rent-and-price-data" / "sa"
DEFAULT_OUTPUT_PATH = DEFAULT_INPUT_DIR / "sa-rent-combined-post-2020.csv"
SHEET_CANDIDATES = ["Region"]


def _slugify(label: str) -> str:
    """Create a stable, lowercase column name from a header label."""
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", str(label or "").strip()).strip("_")
    return cleaned.lower() or "column"


def _clean_text(value: Any) -> str:
    """Normalise a workbook cell into a string."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value).strip()


def _clean_value(value: Any) -> float | str:
    """Convert numeric-looking values to floats, otherwise return the original text."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return float("nan")

    text = str(value).strip()
    if not text:
        return float("nan")
    if text.lower() in {"n.a.", "na", "n/a", "-", "*", "x"}:
        return float("nan")

    text = text.replace("$", "").replace(",", "").replace(" ", "")
    try:
        return float(text)
    except ValueError:
        return text


def _parse_year_month(path: Path) -> tuple[int | None, int | None]:
    """Extract the year and month from a South Australia report filename."""
    match = re.search(r"(\d{4})[-_.](\d{1,2})", path.name)
    if not match:
        return None, None

    year = int(match.group(1))
    month = int(match.group(2))
    return year, month


def _read_post_2020_region_sheet(path: Path) -> pd.DataFrame:
    '''Reads post-2020 SA Region sheet and returns a cleaned DataFrame.'''

    ''' The code block below works as a basis for processing the post-2020-12 SA data
    import pandas as pd
    df = pd.read_csv(r'[filepath]/sa-2020-12-format.csv', header = None)

    # Drop specified rows from df
    df = df[~df[0].isin(['Metro', 'Rest of State'])]

    df = df.ffill(axis=1)

    # Drop columns
    df = df.drop(columns=[9, 10, 19, 20, 23, 24, 25, 26])

    df.columns = df.iloc[1] + ' ' + df.iloc[0] + ' ' + df.iloc[2]

    df = df.iloc[3:]
    '''
    suffix = path.suffix.lower()
    engine = "xlrd" if suffix == ".xls" else "openpyxl"

    excel_file = pd.ExcelFile(path, engine=engine)
    sheet_name = next((name for name in SHEET_CANDIDATES if name in excel_file.sheet_names), None)
    if sheet_name is None:
        sheet_name = excel_file.sheet_names[0]

    # start reading from cell A13
    frame = pd.read_excel(path, sheet_name=sheet_name, header=None, skiprows=12, engine=engine)

    # if any of the cells in the first row have value "Column Labels", then drop the first row
    if frame.iloc[0].str.contains("Column Labels", case=False, na=False).any():
        frame = frame.iloc[1:]

    # Remove Metro / Rest of State rows and forward-fill across the wide header layout.
    frame = frame[~frame.iloc[:, 0].isin(['Metro', 'Rest of State'])]
    frame = frame.ffill(axis=1)

    # Drop columns that are not needed for the final combined structure.
    # drop columns where 'Count' or 'Median' is in the first row
    drop_columns = [col for col in range(len(frame.columns)) if any(str(frame.iloc[0, col]).strip().lower() in {"count", "median"} for col in range(len(frame.columns)))]
    col_to_drop = [col for col in drop_columns if col < len(frame.columns)]
    frame = frame.drop(columns=col_to_drop)

    # Build a combined header from the three header rows, matching the example logic.
    if len(frame) < 3:
        raise ValueError(f"Not enough rows to build headers for {path.name}")

    header_parts = []
    for col_idx in range(len(frame.columns)):
        parts = [
            _clean_text(frame.iloc[1, col_idx]),
            _clean_text(frame.iloc[0, col_idx]),
            _clean_text(frame.iloc[2, col_idx]),
        ]
        header_parts.append(" ".join(part for part in parts if part))

    frame.columns = header_parts
    frame = frame.iloc[3:].reset_index(drop=True)

    # Rename the first column to the standard region column.
    frame.rename(columns={frame.columns[0]: "region"}, inplace=True)

    # Build a consistent set of metric column names.
    metric_columns = [_slugify(column) for column in frame.columns[1:]]
    frame.columns = ["region", *metric_columns]

    # Keep only data rows that contain a region.
    frame = frame.dropna(subset=["region"], how="all")

    # rename columns so that all columns with 'bedrooms_flats_units' in the name is replaced with 'br_flats' and 'bedrooms_houses' change to 'br_houses'
    frame = frame.rename(columns=lambda x: re.sub(r"bedrooms?_flats_units", "br_flats", x, flags=re.IGNORECASE))
    frame = frame.rename(columns=lambda x: re.sub(r"bedrooms?_houses", "br_houses", x, flags=re.IGNORECASE))

    return frame


def combine_post_2020_sa_data(input_dir: str | Path | None = None, output_path: str | Path | None = None) -> tuple[pd.DataFrame, int]:
    """Combine post-2020-12 SA rent data into a single CSV."""
    input_dir = Path(input_dir or DEFAULT_INPUT_DIR)
    output_path = Path(output_path) if output_path is not None else DEFAULT_OUTPUT_PATH

    excel_files = sorted(list(input_dir.glob("*.xlsx")) + list(input_dir.glob("*.xls")))
    relevant_files = [
        path
        for path in excel_files
        if re.search(r"2020-12|202[1-9]-[0-9]{2}", path.name)
        and re.search(r"(private|quarterly).*rental.*report", path.name, flags=re.IGNORECASE)
        and "lsg_stats" not in path.name.lower()
    ]

    if not relevant_files:
        raise RuntimeError(f"No post-2020-12 SA rent Excel files found in {input_dir}")

    records: list[dict[str, Any]] = []
    files_read = 0

    for path in tqdm(relevant_files):
        year, month = _parse_year_month(path)
        if year is None or month is None:
            continue

        try:
            table = _read_post_2020_region_sheet(path)
            files_read += 1
        except Exception as exc:
            print(f"Skipping {path.name}: {exc}")
            print(traceback.format_exc())
            continue

        for _, row in table.iterrows():
            region = _clean_text(row["region"])
            if not region:
                continue
            if region.lower() in {"total", "grand total"}:
                continue

            record: dict[str, Any] = {
                "region": region,
                "year": year,
                "month": month,
            }
            for column in table.columns[1:]:
                record[column] = _clean_value(row[column])
            records.append(record)

    if not records:
        raise RuntimeError("No usable rows were extracted from the post-2020-12 SA Excel files")

    combined = pd.DataFrame(records)
    combined = combined.sort_values(["year", "month", "region"], kind="mergesort").reset_index(drop=True)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(output_path, index=False)

    return combined, files_read


def main() -> None:
    parser = argparse.ArgumentParser(description="Combine post-2020-12 South Australia private rent report Excel files")
    parser.add_argument("--input-dir", default=str(DEFAULT_INPUT_DIR), help="Directory with the SA Excel files")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH), help="Where the combined CSV should be written")
    args = parser.parse_args()

    combined, files_read = combine_post_2020_sa_data(input_dir=args.input_dir, output_path=args.output)
    print(f"\nSaved {len(combined)} rows to {args.output}")
    print(f"{files_read} files read")
    print(f"Columns: {list(combined.columns)}")


if __name__ == "__main__":
    main()
