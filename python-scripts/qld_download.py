#!/usr/bin/env python3
"""Download Queensland RTA Excel files from archived quarterly subpages.
This script doesn't work properly because it doesn't parse all the files
Still, better than nothing, just do the rest manually"""

import re
from pathlib import Path
from urllib.parse import urljoin, urlparse
from tqdm import tqdm
import time

import requests
from requests.adapters import HTTPAdapter, Retry
from bs4 import BeautifulSoup

urls = ['https://web.archive.org/web/20110902023218/http://www.rta.qld.gov.au/median_weekly_rents.cfm', 'https://web.archive.org/web/20080605022743/http://www.rta.qld.gov.au/median_weekly_rents.cfm']

def extract_excel_links(html: str, base_url: str) -> list[str]:
    """Extract the Excel file we want from archived Queensland rent pages."""
    soup = BeautifulSoup(html, "html.parser")
    links: list[str] = []

    for tag in soup.find_all("a", href=True):
        href = tag["href"]
        if not href:
            continue

        resolved = urljoin(base_url, href)

        parsed = urlparse(resolved)
        if 'houses' not in parsed.path.lower() and 'flats' not in parsed.path.lower() and 'thouses' not in parsed.path.lower():
            if 'sa_' in parsed.path.lower():
                links.append(resolved)
            elif 'selected_' in parsed.path.lower():
                links.append(resolved)

    return links


def build_subpage_url(base_url: str) -> str:
    """Return subpage url"""

    s = requests.Session()
    retries = Retry(total=6, backoff_factor=10, status_forcelist=[403, 500, 502, 503, 504])
    s.mount('https://', HTTPAdapter(max_retries=retries))
    response = s.get(base_url)

    soup = BeautifulSoup(response.text, "html.parser")

    subpage_urls = []

    for tag in soup.find_all("a", href=True):
        href = tag["href"]
        if "_quarter_" in href:
            subpage_urls.append(urljoin(base_url, href))

    return subpage_urls


def download_excel_from_subpage(subpage_url: str, output_dir: Path, pbar) -> list[Path]:
    """Fetch Excel file linked from a quarterly subpage."""
    response = requests.get(subpage_url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()

    excel_links = extract_excel_links(response.text, base_url=subpage_url)
    if not excel_links:
        raise RuntimeError(f"No Excel links found at {subpage_url}")

    output_dir.mkdir(parents=True, exist_ok=True)

    for link in excel_links:
        file_response = requests.get(link, timeout=60, headers={"User-Agent": "Mozilla/5.0"}, stream=True)
        file_response.raise_for_status()

        filename = Path(urlparse(file_response.url).path).name or Path(urlparse(link).path).name or "download"
        filename = re.sub(r"[^A-Za-z0-9._-]+", "_", filename).strip("._") or "download"

        # add quarter and year from link to end of filename
        match = re.search(r"([june|september|december|march]+)_(qtr|quarter)_(\d{2,4})", link, flags=re.IGNORECASE)
        if match:
            # only download if match
            quarter = match.group(1).lower().replace('june', 'q2').replace('september', 'q3').replace('december', 'q4').replace('march', 'q1')
            year = match.group(3)
            filename = f"qld_{filename}_{year}_{quarter}{Path(filename).suffix}"
            pbar.set_description(f"Downloading {filename}")
        else:
            match_year = re.search(r"_+(\d{2,4})", link)
            match_quarter = re.search(r"([june|september|december|march]+)", link, flags=re.IGNORECASE)
            if match_year and match_quarter:
                year = match_year.group(1)
                quarter = match_quarter.group(1).lower().replace('june', 'q2').replace('september', 'q3').replace('december', 'q4').replace('march', 'q1')
                filename = f"qld_{filename}_{year}{Path(filename).suffix}"
                pbar.set_description(f"Downloading {filename}")
            else:
                pbar.set_description(f"Downloading {filename} without renaming (no quarter/year match)")
                continue # skip if no quarter/year match
        destination = output_dir / filename
        counter = 1
        while destination.exists():
            destination = output_dir / f"{Path(filename).stem}_{counter}{Path(filename).suffix}"
            counter += 1

        with destination.open("wb") as handle:
            for chunk in file_response.iter_content(chunk_size=8192):
                if chunk:
                    handle.write(chunk)

def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    output_dir = repo_root / "rent-and-price-data" / "qld"

    subpage_urls = []
    for url in urls:
        subpage_urls += build_subpage_url(url)

    # remove duplicates
    subpage_urls = list(set(subpage_urls))

    print(len(subpage_urls), "subpage URLs found. Starting download...")

    pbar = tqdm(total=len(subpage_urls))

    for subpage_url in tqdm(subpage_urls):
        try:
            download_excel_from_subpage(subpage_url, output_dir, pbar)
            time.sleep(5)
        except Exception as e:
            pbar.set_description(f"Error downloading from {subpage_url}: {e}")
            continue

if __name__ == "__main__":
    main()