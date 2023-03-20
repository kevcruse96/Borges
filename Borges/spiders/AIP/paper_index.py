# Add interpreter location?

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import json
import adal
import requests
import time
from pprint import pprint
from datetime import datetime, timedelta

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

    journal_col = db.collection("AIPJournals")
    paper_col = db.collection("AIPPapers")

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
    papers_host = f"{AIP_BASEURL}/api/Query/ArticlesQuery"

    # TODO: Contact AIP about missing "Associated_Journal" fields (not a big deal for us, but might be for them)

    journal_list = [j['Journal_Title'] for j in journal_col.find({})]

    for journal_title in journal_list:

        paper_l = []

        for year in range(2000, 2024):

            journal = journal_col.find_one({'Journal_Title': journal_title})

            if 'Years_Indexed' in journal.keys():
                if year in [y['Year'] for y in journal['Years_Indexed']]:
                    continue
            else:
                journal_col.update_one({"_id": journal["_id"]}, {"$set": {
                    "Years_Indexed": []
                }})

            year_papers = []
            page = 1
            num_results = 20 # currently the length of results returned on single page
            year_indexed_doc_num = 0

            current_year = year == 2023

            while 0 < num_results <= 20:

                articles_query = requests.get(
                    papers_host+f"?journaltitle={journal_title}&Publisheddate={year}&page={page}",
                    headers=headers,
                ).json()
                time.sleep(3) # wait at least 3 seconds before next query

                # Wait 15 minutes if we get an "Out of bandwidth message"
                # While you wait, focus on your breathing... what do you smell? What are you thankful for today?
                if type(articles_query) != list:
                    if articles_query['message'].startswith('Out of bandwidth quota.'):
                        print(articles_query['message'])
                        time_formatted = articles_query['message'].split('replenished in ')[1].replace('.', '')
                        time_object = time.strptime(time_formatted, '%H:%M:%S')
                        tick = int(timedelta(
                            hours=time_object.tm_hour,
                            minutes=time_object.tm_min,
                            seconds=time_object.tm_sec
                        ).total_seconds()) + 30 # add 30 seconds on for good measure
                        while tick > 0:
                            min, sec = divmod(tick, 60)
                            print("Time remaining: {:02d}:{:02d}".format(min, sec), end='\r')
                            time.sleep(1)
                            tick -= 1
                        continue
                    else:
                        print(articles_query)
                        stop

                articles = [
                    {
                        'Crawled': False,
                        'Publisher': 'American Institute of Physics',
                        'Journal': journal_title,
                        'Published_Year': int(p['PublishedDate'].split('-')[0]),
                        'Open_Access': None,
                        'DOI': p['DOI'],
                        'Title': p['Title'],
                        'Authors': None,
                        'Issue': None
                    } for
                    p in articles_query if p
                ]

                num_results = len(articles)

                year_papers.extend(articles)
                paper_l.extend(articles)

                year_indexed_doc_num += num_results
                page += 1

                print(
                    f'Indexed {year_indexed_doc_num} papers from {journal_title} for {year} ({len(paper_l)} total)',
                    end='\r'
                )

            print()

            if year_papers:
                for i, paper in enumerate(year_papers): # There should be a more efficient way to do this block
                    if not paper_col.find_one({'DOI': paper['DOI']}):
                        paper_col.insert_one(paper)
                    print(f"Inserted (or discarded) {i} out of {len(year_papers)}", end='\r')
            print()

            year_meta = {
                'Year': year,
                'Current_Year': current_year,
                'Indexed_Doc_Num': year_indexed_doc_num,
                'last_updated': datetime.utcnow()
            }

            journal_col.update_one(
                {"_id": journal["_id"]},
                {"$push": {"Years_Indexed": year_meta}}
            )

        print()