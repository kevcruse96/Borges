# Add interpreter location?

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import json
import adal
import requests
from pprint import pprint

from DBGater.db_singleton_mongo import SynDevAdmin, SynProAdmin

from Borges.settings import AIP_BASEURL, AIP_RESOURCE, AIP_AUTHORITY_URL, AIP_CLIENT_ID, AIP_CLIENT_SECRET

__author__ = 'Kevin Cruse',
__maintainer__ = 'Kevin Cruse'
__email__ = 'kevcruse96@gmail.com'

if __name__ == "__main__":
    db = SynProAdmin.db_access()
    db.connect() # It seems that this method uses the .authenticate() method, which was eliminated after
                 # pymongo v3.4 (probably)... might be worthwhile to update DBGater accordingly, but for now
                 # pymongo==3.4 locally to run this

    # journal_col = db.collection("AIPJournals")
    # paper_col = db.collection("AIPPapers_Update")

    # Get journal titles from file for now, save to MongoDB later
    with open('./20230126_journal.jl', 'r') as fp:
        journals_list = []
        for l in fp:
            journals_list.append(json.loads(l))

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
    papers_host = f"{AIP_BASEURL}/api/Search/searcharticles"

    # TODO: there doesn't appear to be any articles in ArticlesQuery with associated Publisheddate fields?
    for journal in journals_list:
        for year in range(2018, 2023):
            articles_query = requests.get(
                papers_host+f"?searchvalue=synthesis&page=2406",
                headers=headers
            ).json()
            pprint(articles_query)
            stop

