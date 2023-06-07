#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import os
import sys
import requests
from DBGater.db_singleton_mongo import SynDevAdmin, FullTextAdmin
import time
import pickle
from pymongo.errors import DocumentTooLarge
from Borges.db_scripts.journal_scripts import update_journal_entry
from Borges.db_scripts.create_dummy_col import create_dummy_col

from Borges.settings import (
    ELSEVIER_API_1,
    ELSEVIER_API_2,
    ELSEVIER_API_3,
    ELSEVIER_API_4,
    ELSEVIER_API_5,
    ELSEVIER_API_6,
    ELSEVIER_API_7,
    ELSEVIER_API_8
)

from tqdm import tqdm
from datetime import datetime
from pprint import pprint

__author__ = 'Ziqin (Shaun) Rong'
__maintainer__ = 'Kevin Cruse'
__email__ = 'kevcruse96@gmail.com'

current_year = 2023

def scrape_paper(wait_time, paper_col, journal_col, api_key, run_date, old_paper_col=None):
    time.sleep(wait_time)

    # TODO: Collect all of these first rather than querying for every call (use a dictionary with doi as key, 0/1 as Crawled)... then pickle it
    doc = paper_col.find_one({"Crawled": False})
    # doc = [p for p in paper_col.aggregate([{'$sample': {'size': 1}}])][0]

    if not doc:
        return 1

    # check if paper has already been crawled in FullText.Paper_Raw_HTML
    # TODO: this takes a lot of time... do the same thing here, collect all of these first instead of querying
    if old_paper_col is not None and  old_paper_col.find_one({'DOI': doc['DOI']}):
        paper_col.update_one(
            {'_id': doc["_id"]},
            {
                "$set": {
                    "Crawled": True,
                    "Notes": "Crawled in previous download",
                    "Error": None
                }
            }
        )
        return

    # Scrape HTML and update paper_col entry
    print(f'Start Scraping for Paper {format(doc["DOI"])} (using {api_key}')

    res = requests.get("https://api.elsevier.com/content/article/doi/{}?apikey={}&view=FULL".format(
        doc['DOI'],
        api_key)
    )

    if res.status_code == 200:
        try:
            paper_col.update_one(
                {'_id': doc["_id"]},
                {
                    "$set": {
                        "Paper_Content": res.content,
                        "Crawled": True,
                        "Error": None
                    }
                }
            )
            print("Successfully Downloaded Paper {}.".format(doc["DOI"]))

            # Update relevant journal_col entry
            # update_journal_entry(journal_col, doc['Journal'], doc['Published_Year'], )
            # TODO: Fix journal entry updating

        except DocumentTooLarge:
            print("Document Too Large Error for Paper {}".format(doc['DOI']))

            paper_col.update_one(
                {'_id': doc['_id']},
                {
                    "$set": {
                        "Error": "pymongo.errors.DocumentTooLarge",
                        "Crawled": True
                    }
                }
            )

    elif res.status_code == 400:
        print("Bad request URL for Paper {}".format(doc['DOI']))

        paper_col.update_one(
            {'_id': doc['_id']},
            {
                "$set": {
                    "Error": "Bad Request Code",
                    "Crawled": True
                }
            }
        )

    elif res.status_code == 404:
        print(f"The resource specified cannot be found for {doc['DOI']}")

        paper_col.update_one(
            {'_id': doc['_id']},
            {
                "$set": {
                    "Error": "Resource Not Found",
                    "Crawled": True
                }
            }
        )

    else:
        print(f"Response Code: {res.status_code}\n{res.content}\nExiting...")
        return 1

    return 0


if __name__ == '__main__':

    run_date = datetime.today().strftime("%Y%m%d")

    db = SynDevAdmin.db_access()
    fulltext_db = FullTextAdmin.db_access() # connecting to old database to make sure we don't download twice
    # TODO: above, add a field that shows when single paper was downloaded

    db.connect()
    fulltext_db.connect()

    old_paper_col = fulltext_db.collection("Paper_Raw_HTML")
    paper_col = db.collection("ElsevierPapers")
    journal_col = db.collection("ElsevierJournals")

    pprint(old_paper_col.find_one({}))
    stop

    create_dummy_col("ElsevierPapers_Test", col_to_dupe=paper_col, randomize=True, sample_size=400000)

    test_col = db.collection("ElsevierPapers_Test")

    # Collect and store all un-crawled DOIs
    if not os.path.isfile(f'./data/{run_date}_dois_crawled.pkl'):
        dois_crawled = []
        total_docs = test_col.count_documents({})
        for doc in tqdm(test_col.find({}), total=total_docs):
            dois_crawled.append({doc['DOI']: doc['Crawled']})

        print(len(dois_crawled))
        pickle.dump(dois_crawled, f'./data/{run_date}_dois_crawled.pkl')

    # TODO: wait about a minute after every 100 or so requests
    while True:
        continue_l = []
        for api in [
            ELSEVIER_API_1,
            ELSEVIER_API_2,
            ELSEVIER_API_3,
            ELSEVIER_API_4,
            ELSEVIER_API_5,
            ELSEVIER_API_6,
            ELSEVIER_API_7,
            ELSEVIER_API_8,
        ]:
            for i in range(3):
                continue_l.append(scrape_paper(
                    0.1,
                    test_col,
                    journal_col,
                    api,
                    run_date,
                    old_paper_col=old_paper_col
                ))
        if sum(continue_l) > 0:
            break
