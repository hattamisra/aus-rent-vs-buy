#!/usr/bin/env python3
"""Download South Australia private rent report Excel files from the dataset web page."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

DATASET_URL = "https://data.sa.gov.au/data/dataset/private-rent-report"
EXCEL_EXTENSIONS = {".xlsx", ".xls", ".xlsm"}


def _normalise_filename(name: str, fallback_url: str | None = None) -> str:
    """Create a safe filename from a resource title or URL."""
    candidate = name.strip() if name else ""
    if not candidate:
        candidate = Path(urlparse(fallback_url or "").path).name or "download"

    candidate = re.sub(r"[^A-Za-z0-9._-]+", "_", candidate).strip("._")
    if not candidate:
        candidate = "download"

    if Path(candidate).suffix.lower() not in EXCEL_EXTENSIONS:
        candidate = f"{candidate}.xlsx"

    return candidate


def _build_output_path(output_dir: Path, filename: str) -> Path:
    """Return a unique output path, avoiding collisions."""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / filename
    counter = 1
    while path.exists():
        stem = Path(filename).stem
        suffix = Path(filename).suffix
        path = output_dir / f"{stem}_{counter}{suffix}"
        counter += 1
    return path


def get_excel_links(dataset_url: str = DATASET_URL) -> list[str]:
    """Scrape the dataset page and return all Excel resource links."""
    response = requests.get(dataset_url, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    links: list[str] = []
    seen: set[str] = set()

    for anchor in soup.find_all("a", href=True):
        href = anchor.get("href", "")
        if not href or "/resource/" not in href:
            continue

        resource_url = urljoin(dataset_url, href)
        suffix = Path(urlparse(resource_url).path).suffix.lower()
        if suffix in EXCEL_EXTENSIONS:
            if resource_url not in seen:
                seen.add(resource_url)
                links.append(resource_url)

    if links:
        return links

    # Fallback: pick up resource URLs from the HTML text if the anchor parser misses them.
    for match in re.finditer(r"https://data\.sa\.gov\.au/data/dataset/private-rent-report/resource/[^\"'\s]+", response.text):
        resource_url = match.group(0)
        if resource_url not in seen:
            seen.add(resource_url)
            links.append(resource_url)

    return links


def download_excel_resources(output_dir: str | Path | None = None, dataset_url: str = DATASET_URL) -> list[Path]:
    """Download all Excel files referenced by the South Australia private rent report page."""
    repo_root = Path(__file__).resolve().parent.parent
    target_dir = Path(output_dir) if output_dir is not None else repo_root / "rent-and-price-data" / "sa"
    target_dir.mkdir(parents=True, exist_ok=True)

    resource_links = get_excel_links(dataset_url=dataset_url)
    if not resource_links:
        raise RuntimeError("No Excel resource links were found on the dataset page.")

    downloaded_paths: list[Path] = []
    for resource_url in resource_links:
        print(f"Downloading {resource_url}")
        response = requests.get(resource_url, allow_redirects=True, timeout=60)
        response.raise_for_status()

        content_disposition = response.headers.get("Content-Disposition", "")
        filename = ""
        if "filename*=" in content_disposition:
            match = re.search(r"filename\*=UTF-8''([^;]+)", content_disposition)
            if match:
                filename = match.group(1)
        elif "filename=" in content_disposition:
            match = re.search(r"filename=\"?([^;\"]+)\"?", content_disposition)
            if match:
                filename = match.group(1)

        if not filename:
            filename = Path(urlparse(response.url).path).name or Path(urlparse(resource_url).path).name or "download"

        filename = _normalise_filename(filename, response.url)
        destination = _build_output_path(target_dir, filename)

        with destination.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    handle.write(chunk)

        downloaded_paths.append(destination)

    return downloaded_paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Download South Australia private rent report Excel files")
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory where files should be saved (defaults to rent-and-price-data/sa)",
    )
    args = parser.parse_args()

    downloaded_paths = download_excel_resources(output_dir=args.output_dir)
    output_dir = Path(args.output_dir or "rent-and-price-data/sa").resolve()
    print(f"Downloaded {len(downloaded_paths)} files to {output_dir}")


if __name__ == "__main__":
    main()
