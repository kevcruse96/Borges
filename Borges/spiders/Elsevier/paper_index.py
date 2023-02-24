#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import argparse

from DBGater.db_singleton_mongo import SynDevAdmin
from elsapy.elsclient import ElsClient
from elsapy.elssearch import ElsSearch

from Borges.settings import ELSEVIER_API_1, ELSEVIER_API_2, ELSEVIER_API_3, ELSEVIER_API_4

from pprint import pprint

__author__ = 'Ziqin (Shaun) Rong'
__maintainer__ = 'Ziqin (Shaun) Rong'
__email__ = 'rongzq08@gmail.com'


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", type=int, required=True, help="API key number")
    args = parser.parse_args()

    db = SynDevAdmin.db_access() # 2022-02-22: KJC changed the local environmental variables to go to the SynPro DB
    db.connect()
    # Below collections are from matgen MongoDB... not sure if able to access...
    # pointing these to new collections in SynPro for testing.
    journal_col = db.collection("ElsevierJournals")
    paper_col = db.collection("ElsevierPapers_Meta")

    api_keys = {
        1: ELSEVIER_API_1,
        2: ELSEVIER_API_2,
        3: ELSEVIER_API_3,
        4: ELSEVIER_API_4,
    }
    client = ElsClient(api_keys[args.n])

    # complete = True
    # TODO: Get a way to flag if it was crawled (probably start from beginning and flag everything as 'Crawled': False
    # TODO: Issue with Focus on Powder Coatings
    for doc in journal_col.find({'Crawled' : False}):
        # doc = journal_col.find_one({"Journal_Title": "Journal of Controlled Release"})
        # if not doc:
        #     break
        print("Searching for papers from {}".format(doc["Journal_Title"]))

        paper_l = []
        scraped_doc_num = 0
        missed_doc_num = 0

        for year in range(2018, 2023):
            print()
            doc_search = ElsSearch('ISSN({}) AND PUBYEAR = {}'.format(doc["Journal_ISSN"], year), 'scopus') # Note this was really tricky to find... there needs to be spaces between the qualifying and "PUBYEAR"/year... also need to use 'scopus' instead of 'scidir'
            search_success = True
            try:
                doc_search.execute(client, get_all=True)
            except:
                search_success = False

            if search_success:
                for res in doc_search.results:

                    try:
                        if res['prism:doi']:
                            scraped_doc_num += 1
                        else:
                            missed_doc_num += 1
                    except:
                        pprint(res)
                        stop
                        print(f"Error querying {doc['Journal_Title']} for {year}")
                        journal_col.update_one({"_id": doc["_id"]}, {"$set": {"Crawled": False,
                                                                              f"Missed_{year}": True
                                                                              }})
                        break


                    print("Scraped {} papers, missed {} papers from {} (2018 up to {}).".format(
                        scraped_doc_num,
                        missed_doc_num,
                        doc["Journal_Title"],
                        year
                    ),
                        end='\r'
                    )

                    # If this DOI already exists in paper metadata collection, do not insert
                    if paper_col.find_one({'DOI' : res['prism:doi']}):
                        continue

                    paper_sum = dict()

                    # Note that after python 3, all strings are unicode so the 'u' prefix is not necessary

                    paper_sum["Publisher"] = "Elsevier" # this was under the subsequent "except" level... not sure why
                    paper_sum["Journal"] = doc["Journal_Title"]

                    try:
                        paper_sum['Published_Year'] = int(res['prism:coverDate'].split('-')[0])
                    except:
                        paper_sum["Published_Year"] = None

                    try:
                        paper_sum["Open_Access"] = res['openaccessFlag']
                    except:
                        paper_sum["Open_Access"] = False

                    try:
                        paper_sum["DOI"] = res['prism:doi']
                    except:
                        paper_sum["DOI"] = None

                    try:
                        paper_sum["Title"] = res['dc:title']
                    except:
                        paper_sum["Title"] = None

                    # TODO: will need to find another way to get author and issue if using Scopus
                    try:
                        paper_sum["Authors"] = ["{} {}".format(ath[u'given-name'].encode("utf-8"),
                                                               ath[u'surname'].encode("utf-8"))
                                                for ath in res[u'authors'][u'author']]
                    except:
                        paper_sum["Authors"] = None
                    try:
                        paper_sum["Issue"] = int(res[u'prism:issueIdentifier'].encode("utf-8"))
                    except:
                        paper_sum["Issue"] = None

                    if paper_sum['DOI']:
                        paper_l.append(paper_sum)

        print('\n')

        print(f'Dumping {len(paper_l)} papers from {doc["Journal_Title"]} into ElsevierPapers_Meta...')

        if paper_l:
            paper_col.insert_many(paper_l)

            journal_col.update_one({"_id": doc["_id"]}, {"$set": {"Crawled": True,
                                                          "Scraped_Doc": scraped_doc_num,
                                                          "Missed_Doc": missed_doc_num
                                                          }})
        # complete = False
