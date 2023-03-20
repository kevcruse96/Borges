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

from pprint import pprint

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

def clean_journal_title(journal_title):
    acronym_bank = ['AIP', 'APL', 'AVS', 'JASA']
    lower_bank = ['of', 'in', 'and', 'the', 'on']

    tmp = journal_title.replace('\n', ' ')
    tmp = tmp.replace(' '*10, '')
    tmp = tmp.replace(' '*21, ' ')

    cleaned_journal_title = ''
    for i, t in enumerate(tmp.split(' ')):
        if i == 0:
            spacer = ''
        else:
            spacer = ' '
        if t in acronym_bank or t in lower_bank:
            cleaned_journal_title += spacer + t
        else:
            cleaned_journal_title += spacer + t.capitalize()

    return cleaned_journal_title

def collect_journals(savefile=False):
    # Loop through the pages of journal titles and collect them into journals_list
    journals_list = []
    result_count = 1
    page = 1
    while len(journals_list) < result_count:
        page_journals = json.loads(requests.get(journals_host + f"?page={page}", headers=headers).json())
        result_count = page_journals['listResult']['resultMetadata']['resultCount']
        # TODO: clean up the formatting of the names (lots of \n characters and tabs... seems to work for now, though)
        journals_list.extend(page_journals['listResult']['result'])
        page += 1
        time.sleep(2)
        print(f"Collected {len(journals_list)}/{result_count} AIP Journal Titles", end='\r')
    print()

    if savefile:
        # Save journals list to new line-delimited JSON file
        # TODO: There are repeat journal names... should code in a way to remove those duplicates
        journal_insert_list = []
        with open(f"./{datetime.today().strftime('%Y%m%d')}_aip_journals.jl", 'w') as fp:
            for j in journals_list:
                # TODO: there is a "null" journal title... see if this is legit for some articles
                if j['JournalTitle'] and clean_journal_title(j['JournalTitle']) not in journal_insert_list:
                    cleaned_journal_title = clean_journal_title(j['JournalTitle'])
                    journal_insert_list.append(cleaned_journal_title)
                    json.dump({'Journal_Title': cleaned_journal_title}, fp)
                    fp.write('\n')

        print(f"Collected total of {len(journal_insert_list)} unique AIP journal titles.")


    return

if __name__ == "__main__":
    collect_journals(savefile=True)

