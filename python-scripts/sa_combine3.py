# combines the pre and post 2020 SA data into a single file
# %%
import pandas as pd
import os
from pathlib import Path

folderpath = os.path.join(Path(__file__).resolve().parent.parent, 'rent-and-price-data', 'sa')

df_pre = pd.read_csv(os.path.abspath(os.path.join(folderpath, 'sa-rent-combined-pre-2020.csv')))
df_post = pd.read_csv(os.path.abspath(os.path.join(folderpath, 'sa-rent-combined-post-2020.csv')))
df_combined = pd.concat([df_pre, df_post], ignore_index=True)
#%%
# remove duplicate year-month
df_combined = df_combined.drop_duplicates(subset=['region', 'year', 'month'])
# %%
df_combined.to_csv(os.path.abspath(os.path.join(folderpath, 'sa-rent-combined.csv')), index=False)