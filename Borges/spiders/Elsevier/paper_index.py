#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import argparse

from DBGater.db_singleton_mongo import SynDevAdmin
from elsapy.elsclient import ElsClient
from elsapy.elssearch import ElsSearch

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

from datetime import datetime

from pprint import pprint

__author__ = 'Ziqin (Shaun) Rong'
__maintainer__ = 'Kevin Cruse'
__email__ = 'kevcruse96@gmail.com'

db = SynDevAdmin.db_access()  # 2023-02-22: KJC changed the local environmental variables to go to the SynPro DB
db.connect()
# Below collections are from matgen MongoDB... not sure if able to access...
# pointing these to new collections in SynPro for testing.
journal_col = db.collection("ElsevierJournals")
paper_col = db.collection("ElsevierPapers")
missed_paper_col = db.collection("ElsevierPapers_missed")

def parse_doc_search_result(res, journal_doc):

    paper_sum = dict()

    # Note that after python 3, all strings are unicode so the 'u' prefix is not necessary

    paper_sum['Crawled'] = False
    paper_sum["Publisher"] = "Elsevier"  # this was under the subsequent "except" level... not sure why
    paper_sum["Journal"] = journal_doc["Journal_Title"]

    # TODO: grab the year as a timestamp rather than just the published year (good to have more info)

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
    # TODO: can we get ORCID
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

    return paper_sum

def index_papers_by_journal_year(journal_title, first_year, final_year, client, mongo_insert=False, mongo_update=False):
    paper_l = []
    missed_paper_l = []

    # Grab MongoDB journal entry
    journal_doc = journal_col.find_one({'Journal_Title': journal_title})
    if not journal_doc:
        return

    # Update list of years to query (include unqueried and those that gave query errors earlier)
    years_to_query = [y for y in range(first_year, final_year)]
    years_indexed = journal_doc['Years_Indexed']
    if years_indexed:
        for y in years_indexed:
            years_to_query.remove(y['Year'])

    # Grab number of indexed and missing docs if previously queried
    if paper_col.find_one({'Journal': journal_title}):
        indexed_docs = [p for p in paper_col.find({'Journal': journal_title})]
    else:
        indexed_docs = []
    if missed_paper_col.find_one({'Journal': journal_title}):
        missed_docs = [p for p in missed_paper_col.find({'Journal': journal_title})]
    else:
        missed_docs = []

    for year in years_to_query:

        year_indexed_doc_num = 0
        year_missed_doc_num = 0

        current_year = False
        if year == final_year-1:
            current_year = True

        # Below is a slow step for large queries
        # TODO: add more query endpoints (e.g. keywords)
        # TODO: some journals (e.g. Focus on Powder Coatings) are not accessible by Scopus, but are by ScienceDirect... so we do need scidir
        doc_search = ElsSearch('ISSN({}) AND PUBYEAR = {}'.format(journal_doc["Journal_ISSN"], year), 'scopus') # Note this was pretty tricky to figure out... there needs to be spaces between the qualifying and "PUBYEAR"/year... also need to use 'scopus' instead of 'scidir'

        # Check if credentials are good
        search_success = True
        try:
            doc_search.execute(client, get_all=True)
        except:
            search_success = False

        if search_success:
            scopus_available = None
            if doc_search.results == [{'@_fa': 'true', 'error': 'Result set was empty'}]:
                print("Search was successful but result set was empty for {}".format(year))
                scopus_available = False

            else:
                scopus_available = True
                for res in doc_search.results:

                    paper_sum = parse_doc_search_result(res, journal_doc)

                    if paper_sum['DOI']:
                        indexed_docs.append(paper_sum)
                        paper_l.append(paper_sum)
                        year_indexed_doc_num += 1
                    else:
                        missed_docs.append(paper_sum)
                        missed_paper_l.append(paper_sum)
                        year_missed_doc_num += 1

                print("Search success for from {} ({})!\nIndexed {} new papers\nMissed {} new papers ".format(
                    journal_doc["Journal_Title"],
                    year,
                    year_indexed_doc_num,
                    year_missed_doc_num
                ),
                    end='\r'
                )
        else:
            print("Search failure for {} in {}".format(journal_doc['Journal_Title'], year))
            return False


        print('\n\n')
        year_meta = {
            'Year': year,
            'Current_Year': current_year,
            'Scopus_Available': scopus_available,
            'Indexed_Doc_Num': year_indexed_doc_num,
            'Missed_Doc_Num': year_missed_doc_num,
            'last_updated': datetime.utcnow()
        }

        years_indexed.append(year_meta)

    # TODO: move dumping inside year-by-year loop?

    print(f'Dumping {len(paper_l)} papers from {journal_doc["Journal_Title"]} into ElsevierPapers...\n')

    # TODO: Would be nice to have a way to know for certain that we don't already have the paper, then insert it

    if mongo_insert:
        if paper_l:
            paper_col.insert_many(paper_l)
        if missed_paper_l:
            missed_paper_col.insert_many(missed_paper_l)

    if mongo_update:
        journal_col.update_one({"_id": journal_doc["_id"]}, {"$set": {
            "Years_Indexed": years_indexed
        }})


    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", type=int, required=False, help="API key number")
    args = parser.parse_args()

    # TODO: find a way to check rate limits (here's a start: https://dev.elsevier.com/api_key_settings.html)
    api_keys = {
        1: ELSEVIER_API_1,
        2: ELSEVIER_API_2,
        3: ELSEVIER_API_3,
        4: ELSEVIER_API_4,
        5: ELSEVIER_API_5,
        6: ELSEVIER_API_6,
        7: ELSEVIER_API_7,
        8: ELSEVIER_API_8,
    }

    if args.n:
        api_key_list = args.n

    # TODO: add as a command line argument, not hardcoded into script
    first_year = 2000
    final_year = 2024

    journal_titles = [d['Journal_Title'] for d in journal_col.find({})]

    for key in api_keys:
        for journal_title in journal_titles:
            print(f"=====Searching for papers from {journal_title} ({first_year}-{final_year - 1}) (API KEY {key})=====\n")
            client = ElsClient(api_keys[key])
            journal_year_index = index_papers_by_journal_year(
                journal_title,
                first_year,
                final_year,
                client,
                mongo_insert=True,
                mongo_update=True
            )
            if not journal_year_index:
                if key != 8:
                    print(f"\n\nSwitching to API KEY {key+1}\n\n")
                    break
                else:
                    print("\n\nHitting quota for all API keys.")
