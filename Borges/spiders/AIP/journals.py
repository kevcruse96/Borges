from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import json
import adal
import requests
from datetime import datetime
import time

from DBGater.db_singleton_mongo import SynDevAdmin, SynProAdmin

from Borges.settings import AIP_BASEURL, AIP_RESOURCE, AIP_AUTHORITY_URL, AIP_CLIENT_ID, AIP_CLIENT_SECRET

# connect to appropriate database
db = SynProAdmin.db_access()
db.connect() # It seems that this method uses the .authenticate() method, which was eliminated after
             # pymongo v3.4 (probably)... might be worthwhile to update DBGater accordingly, but for now
             # pymongo==3.4 locally to run this

# establish AIP access token, header authentication, and appropriate target URL
context = adal.AuthenticationContext(AIP_AUTHORITY_URL)
access_token = context.acquire_token_with_client_credentials(
    AIP_RESOURCE,
    AIP_CLIENT_ID,
    AIP_CLIENT_SECRET
)
headers = {
    'Authorization': f"Bearer {access_token['accessToken']}",
    'Content-Type': "application/json"
}
journals_host = f"{AIP_BASEURL}/api/list/journals"

# Loop through the pages of journal titles and collect them into journals_list
journals_list = []
result_count = 1
page = 1
while len(journals_list) < result_count:
    page_journals = json.loads(requests.get(journals_host+f"?page={page}", headers=headers).json())
    result_count = page_journals['listResult']['resultMetadata']['resultCount']
    #TODO: clean up the formatting of the names (lots of \n characters and tabs... seems to work for now, though)
    journals_list.extend(page_journals['listResult']['result'])
    page+=1
    time.sleep(2)
    print(f"Collected {len(journals_list)}/{result_count} AIP Journal Titles", end='\r')

# Save journals list to new line-delimited JSON file
with open(f"./{datetime.today().strftime('%Y%m%d')}_journal.jl", 'w') as fp:
    for j in journals_list:
        if j['JournalTitle']: # TODO: there is a "null" journal title... see if this is legit for some articles
            json.dump({'Journal_Title': j['JournalTitle']}, fp)
            fp.write('\n')