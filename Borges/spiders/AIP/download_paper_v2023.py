from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import json
import adal
import requests
from datetime import datetime, timedelta
import time
import pickle
import xml.etree.ElementTree as ET

from DBGater.db_singleton_mongo import SynDevAdmin, SynProAdmin, FullTextAdmin
from Borges.settings import AIP_BASEURL, AIP_RESOURCE, AIP_AUTHORITY_URL, AIP_CLIENT_ID, AIP_CLIENT_SECRET
from Borges.db_scripts.create_dummy_col import create_dummy_col
from Borges.db_scripts.mongo2pickle import mongo2pickle

from pprint import pprint

__author__ = 'Kevin Cruse'
__maintainer__ = 'Kevin Cruse'
__email__ = 'kevcruse96@gmail.com'

# Establish persistent variables
run_date = datetime.today().strftime("%Y%m%d")

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
metadata_host = f"{AIP_BASEURL}/api/Search/metadata"
fulltext_host = f"{AIP_BASEURL}/api/Search/fulltext"


def scrape_paper(doi, _id, wait_time, paper_col, journal_col, headers, mongo_update=False, old_paper_col=None):
    time.sleep(wait_time)

    error = None

    metadata_res = requests.get(
        f"{metadata_host}?doi={doi}",
        headers=headers
    ).json()

    fulltext_res = requests.get(
        f"{fulltext_host}?doi={doi}",
        headers=headers
    ).json()

    if type(fulltext_res) == dict:
        if 'message' in fulltext_res.keys() and fulltext_res['message'].startswith('Out of bandwidth quota.'):
            error = 'Out of bandwidth quota.'
            return error

        elif 'message' not in fulltext_res.keys():
            error = fulltext_res
            return error

    elif fulltext_res == 'Invalid Response!':
        error = f"Invalid response for Paper {doi}"
        if mongo_update:
            paper_col.update_one(
                {'_id': _id},
                {
                    "$set": {
                        "Error": error,
                        "Crawled": True
                    }
                }
            )
        return error

    else:
        try:
            xml_parse = ET.fromstring(fulltext_res)
            view_subscription = xml_parse.find('.//fulltext').text
            if (
                view_subscription and
                view_subscription.startswith("View requires subsription: ") # [sic]
            ):
                error = view_subscription

            if mongo_update:
                paper_col.update_one(
                    {'_id': _id},
                    {
                        "$set": {
                            "Paper_Content": fulltext_res,
                            "Crawled": True,
                            "Error": error
                        }
                    }
                )


        except Exception as e:
            pprint(fulltext_res)
            print(e)

    return error

def scrape_papers(doc, paper_col, journal_col, headers, old_paper_col=None):
    # TODO: Most of the code below is an exact copy of Elsevier.paper_xml.py ... should turn this into a skeleton script
    wait_time = 1.25
    total_dois = len(dois_to_scrape)
    for i, doc in enumerate(dois_to_scrape):
        _id = doc['_id']
        doi = doc['DOI']
        crawled = False
        while not crawled:
            print(
                f"Scraping {doi} ({i + 1}/{total_dois}, {time.ctime(time.time())})...")

            error = scrape_paper(
                doi,
                _id,
                wait_time,
                paper_col,
                journal_col,
                headers,
                mongo_update=True
            )

            if error == 'Out of bandwidth quota.':
                print("Out of bandwidth quota")
                # TODO: This chunk is used in a lot of AIP scraping scripts... should generalize and put somewhere for importing
                time_formatted = fulltext_res['message'].split('replenished in ')[1].replace('.', '')
                time_object = time.strptime(time_formatted, '%H:%M:%S')
                tick = int(timedelta(
                    hours=time_object.tm_hour,
                    minutes=time_object.tm_min,
                    seconds=time_object.tm_sec
                ).total_seconds()) + 30  # add 30 seconds on for good measure
                while tick > 0:
                    min, sec = divmod(tick, 60)
                    print("Time remaining: {:02d}:{:02d}".format(min, sec), end='\r')
                    time.sleep(1)
                    tick -= 1

            elif error:
                crawled = True
                print(f"...{error}")
                print()

            else:
                crawled = True
                print(f"...Success for {doi}!")
                print()


    return

if __name__ == "__main__":
    db = SynDevAdmin.db_access()
    # fulltext_db = FullTextAdmin.db_access()  # connecting to old database to make sure we don't download twice
    # TODO: above, add a field that shows when single paper was downloaded

    db.connect()
    # fulltext_db.connect()

    # old_paper_col = fulltext_db.collection("Paper_Raw_HTML")
    paper_col = db.collection("AIPPapers")
    journal_col = db.collection("AIPJournals")

    # create_dummy_col("AIPPapers_Test", col_to_dupe=paper_col, randomize=True, sample_size=60000)

    # test_col = db.collection("AIPPapers_Test")

    mongo2pickle(f'{run_date}_dois_crawled.pkl', paper_col, store_keys=['_id', 'DOI'], overwrite=True, criteria={'Crawled': False})

    with open(f'./data/{run_date}_dois_crawled.pkl', 'rb') as fp:
        dois_to_scrape = pickle.load(fp)

    scrape_papers(dois_to_scrape, paper_col, journal_col, headers)
