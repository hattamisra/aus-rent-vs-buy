#!/usr/bin/env python3
"""Combine South Australia rent Excel reports into one tidy pandas DataFrame."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any
from tqdm import tqdm
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_INPUT_DIR = ROOT_DIR / "rent-and-price-data" / "sa"
DEFAULT_OUTPUT_PATH = DEFAULT_INPUT_DIR / "sa-rent-combined.csv"

SHEET_CANDIDATES = ("Final Region", "Region", "Region and State", "Sheet1")


def _slugify(label: str) -> str:
    """Create a stable, lowercase column name from a header label."""
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", str(label or "").strip()).strip("_")
    return cleaned.lower() or "column"


def _clean_text(value: Any) -> str:
    """Normalise a workbook cell to text."""
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
    """Extract year and month from a South Australia report filename."""
    match = re.search(r"(\d{4})[-_.](\d{1,2})", path.name)
    if not match:
        return None, None

    year = int(match.group(1))
    month = int(match.group(2))
    return year, month


def _find_metric_row(frame: pd.DataFrame) -> int:
    """Find the row that contains Count/Median labels."""
    for index, row in frame.iterrows():
        values = [str(value).strip().lower() for value in row.tolist() if value is not None]
        if any(value in {"count", "median"} for value in values):
            return index
    raise ValueError("Could not find a Count/Median header row")


def _build_metric_columns(frame: pd.DataFrame, metric_row: int) -> list[str]:
    """Create metric column names from the labels above the Count/Median row.

    This implements the pairing logic: a `count` column sets the current
    category (slugified) and the following `median` column reuses that
    category name with a `_median` suffix. This covers the pre-2020 layout.
    """
    columns: list[str] = []
    previous_category: str | None = None

    for col_idx in range(1, len(frame.columns)):
        metric_label = _clean_text(frame.iloc[metric_row, col_idx]).lower()

        if metric_label == "count":
            label = ""
            for row_idx in range(metric_row - 1, -1, -1):
                candidate = _clean_text(frame.iloc[row_idx, col_idx])
                if candidate and candidate.lower() not in {"count", "median"}:
                    label = candidate
                    break

            if not label:
                label = f"column_{col_idx}"

            previous_category = _slugify(label)
            columns.append(f"{previous_category}_count")

        elif metric_label == "median":
            if previous_category is None:
                previous_category = f"column_{col_idx}"
            columns.append(f"{previous_category}_median")

        else:
            # fallback for non-standard layouts
            label = _clean_text(frame.iloc[metric_row, col_idx]) or f"column_{col_idx}"
            previous_category = _slugify(label)
            columns.append(previous_category)

    return columns


def _read_report_table(path: Path) -> tuple[pd.DataFrame, list[str]]:
    """Read one workbook and return the extracted region table plus metric column names."""
    suffix = path.suffix.lower()
    engine = "xlrd" if suffix == ".xls" else "openpyxl"

    excel_file = pd.ExcelFile(path, engine=engine)

    sheet_name = next(
        (name for name in SHEET_CANDIDATES if name in excel_file.sheet_names),
        None,
    )
    if sheet_name is None:
        sheet_name = excel_file.sheet_names[0]

    frame = pd.read_excel(path, sheet_name=sheet_name, header=None, engine=engine)

    metric_row = _find_metric_row(frame)
    metric_columns = _build_metric_columns(frame, metric_row)

    # Find the first actual data row beneath the header area
    data_start = metric_row + 1
    while data_start < len(frame):
        first_cell = _clean_text(frame.iloc[data_start, 0]).lower()
        if first_cell and first_cell not in {
            "row labels",
            "row label",
            "state government region",
            "grand total",
            "total",
        }:
            break
        data_start += 1

    if data_start >= len(frame):
        raise ValueError(f"No data rows found in {path.name}")

    rows: list[list[Any]] = []
    for row_idx in range(data_start, len(frame)):
        region = _clean_text(frame.iloc[row_idx, 0])
        if not region:
            continue
        if region.lower() in {"total", "grand total"}:
            continue

        values = []
        for col_idx in range(1, len(frame.columns)):
            values.append(_clean_value(frame.iloc[row_idx, col_idx]))

        if all(pd.isna(value) for value in values):
            continue

        rows.append([region, *values])

    if not rows:
        raise ValueError(f"No data rows found in {path.name}")

    metric_columns = _build_metric_columns(frame, metric_row)
    value_columns = [row[1:] for row in rows]

    valid_indices = [
        idx
        for idx, column in enumerate(zip(*value_columns))
        if any(not pd.isna(value) for value in column)
    ]

    filtered_metric_columns = [metric_columns[idx] for idx in valid_indices]
    filtered_rows = [
        [row[0], *[row[1 + idx] for idx in valid_indices]]
        for row in rows
    ]

    data = pd.DataFrame(
        filtered_rows,
        columns=["region", *filtered_metric_columns],
    )

    return data, filtered_metric_columns

def combine_sa_rent_data(
    input_dir: str | Path | None = None,
    output_path: str | Path | None = None,
) -> tuple[pd.DataFrame, int]:
    """Read all SA rent reports and return one combined DataFrame."""
    input_dir = Path(input_dir or DEFAULT_INPUT_DIR)
    output_path = Path(output_path) if output_path is not None else DEFAULT_OUTPUT_PATH

    excel_files = sorted(list(input_dir.glob("*.xlsx")) + list(input_dir.glob("*.xls")))
    relevant_files = [
        path
        for path in excel_files
        if re.search(r".*(private|quarterly).*rental.*report", path.name, flags=re.IGNORECASE)
        and "lsg_stats" not in path.name.lower()
    ]

    if not relevant_files:
        raise RuntimeError(f"No SA rent Excel files found in {input_dir}")

    records: list[dict[str, Any]] = []
    files_read = 0

    for path in tqdm(relevant_files):
        year, month = _parse_year_month(path)
        if year is None or month is None:
            continue

        try:
            table, metric_columns = _read_report_table(path)
            files_read += 1
        except Exception as exc:
            print(f"Skipping {path.name}: {exc}")
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
            for metric_column in metric_columns:
                record[metric_column] = row[metric_column]
            records.append(record)

    if not records:
        raise RuntimeError("No usable rows were extracted from the SA Excel files")

    combined = pd.DataFrame(records)
    combined = combined.sort_values(
        ["year", "month", "region"],
        kind="mergesort",
    ).reset_index(drop=True)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(output_path, index=False)

    return combined, files_read


def main() -> None:
    parser = argparse.ArgumentParser(description="Combine South Australia private rent report Excel files")
    parser.add_argument("--input-dir", default=str(DEFAULT_INPUT_DIR), help="Directory with the SA Excel files")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH), help="Where the combined CSV should be written")
    args = parser.parse_args()

    combined, files_read = combine_sa_rent_data(input_dir=args.input_dir, output_path=args.output)
    print(f"\nSaved {len(combined)} rows to {args.output}")
    print(f"{files_read} files read")
    print(f"Columns: {list(combined.columns)}")


if __name__ == "__main__":
    main()