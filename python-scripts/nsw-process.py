import os
import time
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re

# Target web page URL
BASE_URL = 'https://dcj.nsw.gov.au/about-us/families-and-communities-statistics/housing-rent-and-sales/previous-rent-and-sales-reports.html'

def get_download_links(rent_sales):
    """Retrieve links to CSV/XLS/XLSX files from the page"""
    response = requests.get(BASE_URL)
    if response.status_code != 200:
        print("Failed to retrieve the page")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    links = []

    for tag in soup.find_all("a", href=True):
        href = tag["href"]
        if href.endswith((".csv", ".xlsx", ".xls")):
            full_url = 'https://dcj.nsw.gov.au' + href
            links.append(full_url)

    # only files with "rent" in the name 
    if rent_sales == "rent":
        links = [link for link in links if "rent-tables" in link.lower()]
    elif rent_sales == "sales":
        links = [link for link in links if "sales-tables" in link.lower()]
    else:
        print("Invalid option for rent_sales. Use 'rent' or 'sales'.")
        return []

    return links

def download_file(url, download_dir):
    """Save the file from the link (append a number if the filename already exists)"""
    base_filename = url.split("/")[-1]
    name, ext = os.path.splitext(base_filename)
    filepath = os.path.join(download_dir, base_filename)
    counter = 1

    while os.path.exists(filepath):
        filepath = os.path.join(download_dir, f"{name}_{counter}{ext}")
        counter += 1

    print(f"Downloading: {url}")
    try:
        response = requests.get(url, stream=True, timeout=10)
        with open(filepath, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"Saved: {filepath}")
    except requests.RequestException as e:
        print(f"Error downloading {url}: {e}")

    time.sleep(1)  # Wait a bit to avoid sending too many requests in a short time

def process_nsw_file(filepath):
    """Placeholder for processing the downloaded file (e.g., read and clean data)"""
    # filepath = "nsw-rent/issue-121-rent-tables-september-2017.xlsx"
    print(f"Processing file: {filepath}")
    nsw = pd.read_excel(filepath, sheet_name='LGA') 

    # find the first row with either "GMR (Greater Metropolitan Region)" 
    # or "Greater Metropolitan Region (GMR)" in the first column
    header_row_index = nsw[nsw.iloc[:, 0].str.contains(
        "GMR \(Greater Metropolitan Region\)|Greater Metropolitan Region \(GMR\)", na=False
        )].index[0]
        
    # drop rows above the header row and reset the index and headers
    nsw = nsw.iloc[header_row_index:].reset_index(drop=True)
    nsw.columns = nsw.iloc[0]  # set the first row as the header
    nsw = nsw.drop(0).reset_index(drop=True)  # drop the header row from the data

    # renaming columns of old files to that in newest files for consistency
    rename_mapping = {
        "GMR (Greater Metropolitan Region)": "Greater Metropolitan Region (GMR)",
        "LGA (Local Government Areas)": "Local Government Area (LGA)",
        "Local Government Areas (LGAs)": "Local Government Area (LGA)",
        "Qtly change in New Bonds Lodged": "Quarterly change in New Bonds Lodged",
        "Bedroom Numbers": "Number of Bedrooms",
        "DwellingType": "Dwelling Type",
        "Qtly change in Median": "Quarterly change in Median",
        "Qtly change in Count": "Quarterly change in Count",
    }

    for key in rename_mapping:
        if key in nsw.columns:
            nsw = nsw.rename(columns={key: rename_mapping[key]})

    # parse filepath for the year and quarter
    filename = os.path.basename(filepath)
    # use regex to find the year in the filename (4 digits)
    year_match = re.search(r'(\d{4})', filename)
    year = pd.to_numeric(year_match.group(1), errors='coerce') if year_match else None
    # for quarter, use month in filename to determine the quarter (e.g., "september" is Q3)
    month_match = re.search(r'(march|june|september|december|mar|jun|sep|dec)', filename, flags=re.IGNORECASE)
    month = month_match.group(1).lower() if month_match else None
    quarter = {
        'march': 1, 'mar': 1,
        'june': 2, 'jun': 2,
        'september': 3, 'sep': 3,
        'december': 4, 'dec': 4
    }.get(month)

    # create 'year' and 'quarter' columns in the dataframe
    nsw['Year'] = year
    nsw['Quarter'] = quarter

    # removing (most but not all) redundant rows 
    # drop all columns where all of the below are true:
    # LGA is NOT 'Total'
    # One or more of 'Greater Metropolitan Region (GMR)', 'Greater Sydney', or 'Rings' IS 'Total'
    nsw = nsw[~((nsw['Local Government Area (LGA)'] != 'Total') & 
                            ((nsw['Greater Metropolitan Region (GMR)'] == 'Total') | 
                             (nsw['Greater Sydney'] == 'Total') | 
                             (nsw['Rings'] == 'Total')))]

    return nsw

if __name__ == "__main__":

    """     
    rent_sales = "rent"  # or "sales" if you want to download sales reports
    rent_links = get_download_links(rent_sales)
    print(rent_links)
    for link in rent_links:
        download_file(link, "nsw-" + rent_sales) 
    """

    nsw_data = pd.DataFrame()

    # extract data from excel files in folder
    folder_path = "nsw-rent"
    for filename in os.listdir(folder_path):
        if filename.endswith(".xlsx") or filename.endswith(".xls"):
            file_path = os.path.join(folder_path, filename)
            nsw_qtr_data = process_nsw_file(file_path)

            # concat nsw qtr to nsw
            nsw_data = pd.concat([nsw_data, nsw_qtr_data])

    print(nsw_data.describe(include='all'))
    
    # write to csv with timestamped filename
    date_now = time.strftime("%Y%m%d")
    time_now = time.strftime("%H%M%S")
    nsw_data.to_csv(f"{folder_path}_processed_{date_now}T{time_now}.csv", index=False)
