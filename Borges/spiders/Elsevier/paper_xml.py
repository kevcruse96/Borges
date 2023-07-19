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
import threading
import time
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
    ELSEVIER_API_8,
    ELSEVIER_API_9,
    ELSEVIER_API_10
)

from tqdm import tqdm
from datetime import datetime
from pprint import pprint

__author__ = 'Ziqin (Shaun) Rong'
__maintainer__ = 'Kevin Cruse'
__email__ = 'kevcruse96@gmail.com'

# Initialize constants
run_date = datetime.today().strftime("%Y%m%d")
current_year = 2023

def scrape_paper(
    doi,
    _id,
    wait_time,
    paper_col,
    journal_col,
    api_key,
    mongo_update=False,
    old_paper_col=None
):
    time.sleep(wait_time)

    error = None

    # check if paper has already been crawled in FullText.Paper_Raw_HTML (not currently doing this)
    if old_paper_col is not None and old_paper_col.find_one({'DOI': doi}):
        paper_col.update_one(
            {'DOI': doi},
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
    res = requests.get("https://api.elsevier.com/content/article/doi/{}?apikey={}&view=FULL".format(
        doi,
        api_key)
        )

    # Assign errors if they exist
    if res.status_code == 400:
        error = f"400: Bad request URL"

    elif res.status_code == 401:
        error = f"401: Invalid API key"

    elif res.status_code == 404:
        error = f"404: The resource specified cannot be found"

    elif res.status_code != 200:
        error = f"Response Code: {res.status_code}\n{res.content}"
        return error # returns for a retry if it doesn't work the first time

    if mongo_update:
        if not error:
            Paper_Content = res.content
        else:
            Paper_Content = None

        try:
            paper_col.update_one(
                {'_id': _id},
                {
                    "$set": {
                        "Paper_Content": Paper_Content,
                        "Error": error,
                        "Crawled": True
                    }
                }
            )
        except DocumentTooLarge:
            error = "Document too large"
            paper_col.update_one(
                {'_id': _id},
                {
                    "$set": {
                        "Paper_Content": None,
                        "Error": error,
                        "Crawled": True
                    }
                }
            )


    return error

def scrape_papers(
    dois_to_scrape,
    api_key,
    thread_num,
    paper_col,
    journal_col,
):

    print(f"Starting Thread {thread_num}")

    # Loop through each _id, paper pair and scrape individually
    waittime = 0.1
    total_dois = len(dois_to_scrape)
    for i, doc in enumerate(dois_to_scrape):
        _id = doc['_id']
        doi = doc['DOI']
        for j in range(3):
            error = scrape_paper(
                doi,
                _id,
                waittime,
                paper_col,
                journal_col,
                api_key,
                mongo_update=True
            )
            print(f"Scraping {doi}, attempt {j+1} (Thread {thread_num}: {i+1}/{total_dois}, {time.ctime(time.time())})...")
            # Retry if scrape comes back with an error
            if error:
                print(error)
                print()
                waittime = 5
                if j == 2:
                    if any([error.startswith(e) for e in ['Document', '400', '401', '404']]):
                        print(f"Exceeded attempts for {doi} on Thread {thread_num}")
                        waittime = 0.1
                        if not os.path.isfile(f'./logs/xml_scrape/{run_date}_{thread_num}.log'):
                            with open(f'./logs/xml_scrape/{run_date}_{thread_num}.log', 'w') as fp:
                                fp.write(f'{error}')
                        else:
                            with open(f'./logs/xml_scrape/{run_date}_{thread_num}.log', 'a') as fp:
                                fp.write(f'\n{error}')
                    else:
                        print(f"Thread {thread_num} exiting... Address error above before running again")
                        return
            else:
                print(f"...Success for {doi}!")
                print()
                break

    print(f"Completed Scrape for Thread {thread_num}!")
    return

def mongo2pickle(savefile, col, savetype, store_keys=[], overwrite=False, criteria={}, batches=None):

    # Note that this function only takes one key (optional) and one value (required)

    if overwrite or not os.path.isfile(f'./data/{savefile}'):
        print(f'Collecting and storing entries to {savefile}...')

        #if savetype == dict:
        #    dump_obj = {}
        #elif savetype == list:
        #    dump_obj = []

        dump_obj = []

        total_docs = col.count_documents(criteria)
        for doc in tqdm(col.find(criteria), total=total_docs):
            if savetype == 'dicts':
                doc_to_save = {}
                for k in store_keys:
                    doc_to_save[k] = doc[k]
                dump_obj.append(doc_to_save)
            elif savetype == 'lst':
                dump_obj.append(doc[store_val])

        #dump_obj = list(set(dump_obj))

        if batches:
            batch_size = int(len(dump_obj) / batches)
            leftover = len(dump_obj) % batches
            for i in range(batches):
                if i == batches - 1:
                    end = batch_size + leftover
                else:
                    end = batch_size
                with open(f'./data/{i}_{savefile}', 'wb') as fp:
                    pickle.dump(dump_obj[i*batch_size:i*batch_size+end], fp)

        with open(f'./data/{savefile}', 'wb') as fp:
            pickle.dump(dump_obj, fp)

    else:
        print(f'{savefile} already exists.')

def db_connect():
    fulltext_db = FullTextAdmin.db_access()
    # connecting to old database in case yo want to make sure we don't download twice... not doing this currently

    db.connect()
    fulltext_db.connect()

    old_paper_col = fulltext_db.collection("Paper_Raw_HTML")
    paper_col = db.collection("ElsevierPapers")
    journal_col = db.collection("ElsevierJournals")
    return old_paper_col, paper_col, journal_col

if __name__ == '__main__':

    # Connect to DBs and collections
    db = SynDevAdmin.db_access()
    old_paper_col, paper_col, journal_col = db_connect()

    # Initialize dummy collection if testing
    #create_dummy_col("ElsevierPapers_Test", col_to_dupe=paper_col, randomize=True, sample_size=400000)
    #test_col = db.collection("ElsevierPapers_Test")

    # TODO: Make splitting optional
    # Initialize pickle data files
    mongo2pickle('previously_scraped_dois.pkl', old_paper_col, list, 'DOI', criteria={'Publisher': 'Elsevier'})
    mongo2pickle(f'{run_date}_dois_crawled.pkl', paper_col, 'dicts', store_keys=['_id', 'DOI'], overwrite=True, criteria={'Crawled': False}, batches=8)

    with open('./data/previously_scraped_dois.pkl', 'rb') as fp:
        old_paper_dois = pickle.load(fp)

    #with open(f'./data/{run_date}_dois_crawled.pkl', 'rb') as fp:
    #    dois_to_scrape = pickle.load(fp)

    with open(f'./data/0_{run_date}_dois_crawled.pkl', 'rb') as fp:
        dois_to_scrape_0 = pickle.load(fp)

    with open(f'./data/1_{run_date}_dois_crawled.pkl', 'rb') as fp:
        dois_to_scrape_1 = pickle.load(fp)

    with open(f'./data/2_{run_date}_dois_crawled.pkl', 'rb') as fp:
        dois_to_scrape_2 = pickle.load(fp)

    with open(f'./data/3_{run_date}_dois_crawled.pkl', 'rb') as fp:
        dois_to_scrape_3 = pickle.load(fp)

    with open(f'./data/4_{run_date}_dois_crawled.pkl', 'rb') as fp:
        dois_to_scrape_4 = pickle.load(fp)

    with open(f'./data/5_{run_date}_dois_crawled.pkl', 'rb') as fp:
        dois_to_scrape_5 = pickle.load(fp)

    with open(f'./data/6_{run_date}_dois_crawled.pkl', 'rb') as fp:
        dois_to_scrape_6 = pickle.load(fp)

    with open(f'./data/7_{run_date}_dois_crawled.pkl', 'rb') as fp:
        dois_to_scrape_7 = pickle.load(fp)

    #with open(f'./data/8_{run_date}_dois_crawled.pkl', 'rb') as fp:
    #    dois_to_scrape_8 = pickle.load(fp)

    #with open(f'./data/9_{run_date}_dois_crawled.pkl', 'rb') as fp:
    #    dois_to_scrape_9 = pickle.load(fp)

    # scrape_papers(dois_to_scrape, ELSEVIER_API_1, 1, paper_col, journal_col)

    # TODO: make a threading object using threading module?
    s1 = threading.Thread(target=scrape_papers, args=(dois_to_scrape_0, ELSEVIER_API_1, 1, paper_col, journal_col))
    s2 = threading.Thread(target=scrape_papers, args=(dois_to_scrape_1, ELSEVIER_API_2, 2, paper_col, journal_col))
    s3 = threading.Thread(target=scrape_papers, args=(dois_to_scrape_2, ELSEVIER_API_3, 3, paper_col, journal_col))
    s4 = threading.Thread(target=scrape_papers, args=(dois_to_scrape_3, ELSEVIER_API_4, 4, paper_col, journal_col))
    s5 = threading.Thread(target=scrape_papers, args=(dois_to_scrape_4, ELSEVIER_API_5, 5, paper_col, journal_col))
    s6 = threading.Thread(target=scrape_papers, args=(dois_to_scrape_5, ELSEVIER_API_6, 6, paper_col, journal_col))
    s7 = threading.Thread(target=scrape_papers, args=(dois_to_scrape_6, ELSEVIER_API_7, 7, paper_col, journal_col))
    s8 = threading.Thread(target=scrape_papers, args=(dois_to_scrape_7, ELSEVIER_API_8, 8, paper_col, journal_col))
    #s9 = threading.Thread(target=scrape_papers, args=(dois_to_scrape_8, ELSEVIER_API_9, 9, test_col, journal_col))
    #s10 = threading.Thread(target=scrape_papers, args=(dois_to_scrape_9, ELSEVIER_API_10, 10, test_col, journal_col))

    s1.start()
    s2.start()
    s3.start()
    s4.start()
    s5.start()
    s6.start()
    s7.start()
    s8.start()
    #s9.start()
    #s10.start()

    s1.join()
    s2.join()
    s3.join()
    s4.join()
    s5.join()
    s6.join()
    s7.join()
    s8.join()
    #s9.join()
    #s10.join()
