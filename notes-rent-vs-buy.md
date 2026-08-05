<!--Converted to Markdown using https://word2md.com/-->

Rent vs Buy in Australia, 2006-2025

The Australian version of PWL Capital's [Renting vs Owning a Home in Canada 2005-2024](https://pwlcapital.com/wp-content/uploads/2025/08/PWL-Capital-Renting-vs.-Owning-a-Home-in-Canada-2005-2024.pdf) (Felix & Bin Arif 2025) ([YouTube video](https://www.youtube.com/watch?v=aU7v87EhDBI))

# Data

## Rents

Felix & Bin Arif use a weighted average of apartment rents - single family (detached) home rental data is sparse in Canada so they only look at apartments.

- Median rents from ABS ([link](https://www.abs.gov.au/articles/latest-insights-rental-market))
  - Not clear where the data is from and it only goes back to 2018 anyway. By state, not GCCSA. And again, hedonic adjustments
- Domain/Cotality indices
  - Gotta pay
- CPI Table 18 has Aus housing and rent components from Sep 1972 but it's not disaggregated by capital city
- State bonds data ([NSW](https://dcj.nsw.gov.au/about-us/families-and-communities-statistics/housing-rent-and-sales/rent-and-sales-report.html), [QLD](https://www.rta.qld.gov.au/forms-resources/rta-quarterly-data/median-rents-quarterly-data), [SA](https://data.sa.gov.au/data/dataset/private-rent-report), VIC [rent index](https://discover.data.vic.gov.au/dataset/rental-report-quarterly-data-tables)/[median rents](https://discover.data.vic.gov.au/dataset/rental-report-quarterly-moving-annual-rents-by-suburb))
  - ugh gotta go through the data every quarter smh AND IT'S BY LGA
    - (but eh a bit of Python can deal with that, no worries)
  - NSW rent data is quartiles by dwelling type and postcode, LGA, and wider aggregations including GCCSA (as well as inner/outer ring LGAs, etc) so this is a really friendly dataset for us. Sadly it's a separate file for each quarter :( but at least there's time series data for metro LGAs 1990-2017.
  - QLD rent data is median by dwelling type and postcode, suburb, and LGA. No GCCSA but thankfully Brisbane LGAs are big so there's only five fully in the GCCSA and three partially.
    - 2006-13 data is also given in the pdf reports by the QLD RTA.
    - We can get the median Brisbane metro rents by taking the weighted average of the metro LGA's medians for the dwelling type.
  - [SA rent data](https://data.sa.gov.au/data/dataset/private-rent-report) is median by dwelling type and postcode, suburb, and LGA (called [SLA](https://www.abs.gov.au/AUSSTATS/abs@.nsf/Latestproducts/DEDA554E1B6BB78BCA25791F000EEA26) in the dataset). Sadly it's (again) a separate file for each quarter :(
    - Update: Get over it Hatta at least you have a dataset. A bit of python does the mind good.
  - VIC has [quarterly median rents](https://discover.data.vic.gov.au/dataset/rental-report-quarterly-quarterly-median-rents-by-lga) by dwelling type and LGA (including metro aggregation) from Mar 2000 as well as a Metropolitan Rent Index.
  - [TAS rent data](https://data.gov.au/data/organization/department-of-justice-tasmania?q=rental+bond+and+rental+data&sort=metadata_modified+desc&page=1) is raw monthly (1300+ data points per month!) but has all the info we need: weekly rent, number of bedrooms, dwelling type. Get python and pandas and we're cooking.
  - Sadly we don't have any data for WA - the closest we have is bond lodgement data that gives the suburb and weekly rent… but not type of dwelling!
    - Can get median for all dwellings from [Rental Affordability Index](https://sgsep.com.au/projects/rental-affordability-index) - can then cross-check with Census data (ABS TableBuilder?) to estimate median rents for 2-bed flats and 3-bed houses as a % of the median for all dwellings
- [Cox & Followill 2018](https://www.financialplanningassociation.org/article/journal/MAY18-rent-or-buy-30-year-perspective) find that owned homes in the US tend to be larger (in floor area) than rented homes, so we ought to be careful and make sure our rent vs house price comparisons are accurate

## Other renter costs - Tenant insurance and moving

- CPI Table 18 has insurance CPI from Sep 1989
- Assuming moving every two years at \$1200 gets around \$600/year in moving costs in modern money. Adding renter's insurance gets to about \$800/year, then deflate this per CPI.

## Investments

- Aus & international indices net of dividends ([MSCI provides index data](https://www.msci.com/indexes?index-category=market-cap&index-market-cap=standard&index-region=global))
  - S&P/ASX 200 or [MSCI Australia IMI](https://www.msci.com/indexes/index/664147), and [MSCI World IMI](https://www.msci.com/indexes/index/664185)
    - IMI includes mid and small cap
  - Use gross total return index for Aus because that shows tax advantage, net total return for world because there's no tax advantage
  - [ASX 200 ETF](https://www.ssga.com/au/en_gb/intermediary/etfs/state-street-spdr-spasx-200-etf-stw) existed since 2001 so the Aus allocation is fine (ok maybe not if we use MSCI but WHATEVER), but we might not be able to assume people can easily invest in international shares over the earlier part of the horizon. iShares listed international ETFs in Oct/Nov 2007 ([link](https://web.archive.org/web/20160520020246/http:/www.asx.com.au/products/etf/managed-funds-etp-product-list.htm)) so that has developed (US+EAFE) and emerging markets covered. Aus outperformed World in 2007-2015 anyway so assuming the investor didn't invest in international until iShares listed would have made investing (& renting) look better.

## Home prices

Felix & Bin Arif use the MLS Home Price Indexes Apartment Benchmark. It is a hybrid model that merges repeat-sales and hedonic pricing. Repeat sales pricing tracks price changes to properties sold multiple times. Hedonic pricing measures the attributes of the homes. Combining these methods controls for differences in property characteristics.

- Total Value of Dwellings from ABS
  - Median Price of Established House/Attached Dwelling Transfers (by GCCSA)
  - Limitations: no hedonic adjustments (home prices increased partly because they got bigger and better)
- State data ([NSW](https://dcj.nsw.gov.au/about-us/families-and-communities-statistics/housing-rent-and-sales/rent-and-sales-report.html), [SA](https://data.sa.gov.au/data/dataset/metro-median-house-sales))
  - NSW has sales data by LGA and wider aggregations (incl GCCSA) but only divided by strata/non-strata. Sadly it's a separate file for each quarter :( but at least there's time series data for metro LGAs 1991-2017.
  - SA is only median for houses by suburb and it's ALSO a separate file for each quarter. Although [someone else](https://mappage.net.au/?a=st_hous_ad) has done the legwork in extracting the data so that's nice.
- First-quartile and median house and unit prices in certain LGAs and GCCSAs from 2017/18 ([housing.id.com.au](https://housing.id.com.au/))
- There's data for 3b houses and 2b units up to SA4 ([openstats.com.au](https://openstats.com.au/dashboards/property-prices/sa4/sydney-city-and-inner-south/)) but no way to download?? Also unclear where the data comes from.
- Census data indicates that the median house is 3b and the median unit is 2b (see [Data Explorer](https://dataexplorer.abs.gov.au/) - Census data timeseries - Dwellings by number of bedrooms) which could be useful for us.
  - NSW and SA (along with other states) give us median house/unit prices so we can compare the ABS Median Price of Dwelling Transfers to 3b house and 2b unit rents! Maybe this is also the logic that Openstats uses to give 3b house/2b unit prices - they're just using the median.

## Transaction costs

- Transfer duty (stamp duty)
- [REA commissions](https://www.realestate.com.au/advice/real-estate-agent-commissions/) (1.5-2.5%)

## Depreciation, maintenance, and renovation costs

Felix & Bin Arif use 1% of home prices for depreciation and 1/3 of gross rents for maintenance, with the simple average for both in their sample of Canadian cities being 2.66% of home prices.

Fox and Tulip 2014 (Tables 1, A2) look at ATO 2010-11 tax statistics and calculate home ownership running costs (e.g. council rates, maintenance and plant depreciation[<sup>\[1\]](#footnote-1)</sup>) of 35.8% of rental income or 1.5% of property value. Using the same method with 2022-23 data gets between 29.3% in WA and 40.6% in QLD with a simple average of 33.2% so the analysis still holds up.

_Ibid._:

Stapledon \[2007, 2012\] estimates that over most of this period (1960-2005), expenditure on alterations and additions contributed 1.15 percentage points a year to average house values, the higher quality and size of new houses contributed 0.87 percentage points, and depreciation detracted 1.06 percentage points.

1\. Depreciation of assets that aren't part of the rental property structure, such as furniture. [↑](#footnote-ref-1)

## Mortgage rates

- RBA indicator lending rates has monthly original rates since 1959 and discounted rates since 2004
  - We can use original or discounted rates
- The low-downpayment sensitivity would include lenders mortgage insurance
  - Not including LMI would be ahistorical but it might be interesting to see what would happen if Howard had introduced the First Home Guarantee

## Home insurance

- CPI Table 18 has insurance CPI from Sep 1989

## Council rates

- [Ratescope.com.au](https://ratescope.com.au/) has current median rates and some historical rates.
- [IPART NSW](https://www.ipart.nsw.gov.au/Home/Industries/Local-Government/For-Ratepayers/The-rate-peg) and [ESC VIC](https://www.esc.vic.gov.au/local-government/annual-council-rate-caps) rate caps may be useful in extending the time series back.

## Taxes - renter's superannuation

Australia's superannuation system is generally a "TTE" retirement savings scheme, i.e. contributions are taxed (the first T), and so are earnings (the second T), but at the end withdrawals during pension phase are exempt (E). But an individual investor can have a very low or even zero effective tax rate on super investment earnings, avoiding the second T, through direct investment options or SMSFs. See the page on [Passive Investing Australia](https://passiveinvestingaustralia.com/the-problem-with-pooled-funds/) for more details. This is why we don't consider tax of investment earnings within super.

This is convenient for us since considering how investment earnings would be taxed in super would be tough (especially since the tax treatment of capital gains and dividends are different, and let's not even talk about franking credits). I suppose we can pull net investment return data from superannuation funds (or other data like [after tax performance of Vanguard ETFs](https://www.vanguard.com.au/adviser/invest/etf?portId=8205&tab=performance)), which is after those earnings taxes, but that's difficult. Anyway they don't have quarterly data like MSCI do.

## Taxes - stamp duty (transfer duty)

We're assuming stamp duty (transfer duty) on buying the house based on Jan 2006 (~3‑3.5%) calcs just to keep things simple for now. Extension: Calculate stamp duty for multiple starting years in our model. Note: no need to calculate stamp duty when selling. As the buyer pays stamp duty, it is already priced in the home sale price.

# Plan

It would be interesting to do rent-vs-buy for both houses and units, but that's quite a bit of work. I think doing the analysis for houses would be more interesting because of the "Australian dream" focus of having a detached house with a yard and a Hills Hoist etc., and the popular conception of houses being a better investment than apartments because they go up quicker in value.

# Superannuation

Prior to May 2006, there were [no caps on superannuation contributions](https://www.cpaaustralia.com.au/about-cpa-australia/media/in-the-news/are-caps-on-superannuation-redundant) and there were "[reasonable benefit limits](https://www.ato.gov.au/tax-rates-and-codes/key-superannuation-rates-and-thresholds/other-super-rates-and-thresholds#ato-Reasonablebenefitlimits)" that limited tax concessions for high lump-sum/pension withdrawals from super.