# Add interpreter location?

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import json
import adal
import requests
from datetime import datetime, timedelta
import pickle
import time
from difflib import SequenceMatcher

from lxml import etree

from pprint import pprint

from DBGater.db_singleton_mongo import SynDevAdmin
from Borges.settings import AIP_BASEURL, AIP_RESOURCE, AIP_AUTHORITY_URL, AIP_CLIENT_ID, AIP_CLIENT_SECRET
from Borges.db_scripts.create_dummy_col import create_dummy_col
from Borges.db_scripts.mongo2pickle import mongo2pickle

__author__ = 'Kevin Cruse',
__maintainer__ = 'Kevin Cruse'
__email__ = 'kevcruse96@gmail.com'

run_date = datetime.today().strftime("%Y%m%d")

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
papers_host = f"{AIP_BASEURL}/api/Search/abstract"

def wait_for_quota_replenish(response):
    # TODO: This chunk is used in a lot of AIP scraping scripts... should generalize and put somewhere for importing
    time_formatted = response['message'].split('replenished in ')[1].replace('.', '')
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
    return

def etree_similarity(etrees, remove_whitespace=False):
    # calculates the similarity between two lxml etree objects
    #
    # Args:
    #    etrees: list of lxml etree elements (not strings)
    #    rules: (optional) rules to replace specific characters if required (like newline tabs)
    assert len(etrees) == 2
    etree.strip_tags(etrees[0], 'named-content')
    etree.strip_tags(etrees[1], 'named-content')
    etree_1 = etree.tostring(etrees[0]).decode()
    etree_2 = etree.tostring(etrees[1]).decode()

    if remove_whitespace:
        etree_1 = " ".join(etree_1.split())
        etree_2 = " ".join(etree_2.split())

    return SequenceMatcher(None, etree_1, etree_2).ratio()

def download_abstract(doi):
    abstract = requests.get(
        papers_host + f"?doi={doi}",
        headers=headers,
    ).json()
    return abstract

def add_abstract_to_fulltext(abstract_response, fulltext_response):
    
    abstract_response_xml = etree.fromstring(abstract_response)
    fulltext_response_xml = etree.fromstring(fulltext_response)

    error = None

    # Get appropriate abstract element trees
    abstract_body = []
    for elem in abstract_response_xml.xpath('.//abstract[not(@abstract-type="key-points")]'):
        # Check for "key-points" id since highlights are sometimes included...
        if elem.findall('p'):
            abstract_body.append(elem)

    # Check for irregularities in downloaded abstract
    if len(abstract_body) == 1:
        # This should generally be true
        abstract_body = abstract_body[0]
    elif not abstract_body:
        # This will happen if there are no <abstract.p> tags
        error = "Non-abstract content (see Abstract_Content)"
    elif len(abstract_body) == 2 and etree_similarity(abstract_body, remove_whitespace=True) >= 0.99:
        # Sometimes the abstract is included twice, occasionally with minor variations like additional newline tabs...
        abstract_body = abstract_body[0]
        error = "Duplicated abstract in response, took first instance"
        # TODO: make a note when this is the case?
    else:
        # Troubleshoot remaining cases
        for a in abstract_body:
            pprint(etree.tostring(a))
        error = "Unspecified error"

    # Generally fewer irregularities in fulltext... mainly checking if fulltext is duplicated
    fulltext = fulltext_response_xml.findall('.//fulltext')
    if len(fulltext) == 1:
        fulltext = fulltext[0]
    elif len(fulltext) == 2 and etree_similarity(fulltext, remove_whitespace=True) >= 0.99:
        fulltext = fulltext[0]
        # TODO: make a note when this is the case?

    # if we extracted an abstract, insert it into the fulltext xml
    if abstract_body is not None and abstract_body != [] :
        fulltext.insert(0, abstract_body)

    return etree.tostring(fulltext).decode(), error

# TODO: combine with download_paper_v2023... basically just add abstract scraping on top of full text
def scrape_abstracts(dois_to_scrape_abstracts, paper_col, headers, mongo_update=False):
    wait_time = 1.25
    total_dois = len(dois_to_scrape_abstracts)
    for i, doc in enumerate(dois_to_scrape_abstracts):

        _id = doc['_id']
        doi = doc['DOI']
        paper_content = doc['Paper_Content']

        combined_paper_content = None
        abstract_response = None
        abstract_crawled = False
        abstract_error = None

        while not abstract_crawled:
            print(
                f"Scraping {doi} ({i + 1}/{total_dois}, {time.ctime(time.time())})...")

            if paper_content:
                abstract_response = download_abstract(doi)
                if abstract_response:
                    combined_paper_content, abstract_error = add_abstract_to_fulltext(
                        abstract_response,
                        paper_content
                    )
                    if type(abstract_response) == dict:
                        if (
                                'message' in abstract_response.keys() and
                                abstract_response['message'].startswith('Out of bandwidth quota.')
                        ):
                            wait_for_quota_replenish(abstract_response)
                    else:
                        abstract_crawled = True
                else:
                    abstract_error = "No abstract"

            if mongo_update:
                paper_col.update_one(
                    {'_id': _id},
                    {
                        '$set': {
                            'Combined_Paper_Content': combined_paper_content,
                            'Abstract_Content': abstract_response,
                            'Abstract_Crawled': abstract_crawled,
                            'Abstract_Error': abstract_error
                        }
                    }
                )

        time.sleep(wait_time)
    return

if __name__ == "__main__":
    db = SynDevAdmin.db_access()
    db.connect()
    paper_col = db.collection("AIPPapers")

    create_dummy_col("AIPPapers_Test", col_to_dupe=paper_col, randomize=False, sample_size=6000)

    test_col = db.collection("AIPPapers_Test")

    mongo2pickle(
        f'{run_date}_dois_no_abstracts.pkl',
        test_col,
        store_keys=['_id', 'DOI', 'Paper_Content'],
        overwrite=True,
        # We are not trying to grab abstracts from papers with "Invalid Response" or "View Subscription..." errors
        criteria={'$and': [
            {'Error': None},
            {'$or': [
                {'Abstract_Crawled': {'$exists': False}},
                {'Abstract_Crawled': False}
            ]}
        ]}
    )

    with open(f'./data/{run_date}_dois_no_abstracts.pkl', 'rb') as fp:
        dois_to_scrape_abstracts = pickle.load(fp)

    scrape_abstracts(dois_to_scrape_abstracts, test_col, headers, mongo_update=True)



