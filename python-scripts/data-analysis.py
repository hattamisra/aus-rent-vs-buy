# %%
import urllib.request
import pandas as pd
url = 'https://discover.data.vic.gov.au/api/3/action/datastore_search?resource_id=19ace27e-97b5-418f-b331-891c57d87fbc&limit=5&q=title:melbourne'  
fileobj = urllib.request.urlopen(url)
fileobjread = fileobj.read()
# %%
# get fileobjread in json format
import json
data = json.loads(fileobjread)
# decompose the result row of data into a list of dictionaries
data['result']
# %%
# convert dictionary into a pandas dataframe 
# where key is col name and value is the value of the column
df = pd.DataFrame(data['result']['fields'])
# display the dataframe
# %%
print("Run complete")