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

def index_papers_by_journal_year(journal_title, first_year, final_year, mongo_insert=False, mongo_update=False):
    journal_doc = journal_col.find_one({'Journal_Title': journal_title})
    if not journal_doc:
        return

    # TODO: add a field for partially indexed years, like current year
    # Check to see what the last year indexed was
    years_indexed = journal_doc['Years_Indexed']
    if years_indexed:
        years_sorted = sorted([y['Year'] for y in years_indexed])
        if years_sorted[-1] != final_year - 1:
            first_year_upd = years_sorted[-1] + 1
        else:
            return
    else:
        first_year_upd = first_year

    print(f"========Searching for papers from {journal_doc['Journal_Title']} ({first_year_upd}-{final_year - 1})========\n")

    paper_l = []
    missed_paper_l = []


    if paper_col.find_one({'Journal': journal_title}):
        indexed_docs = [p for p in paper_col.find({'Journal': journal_title})]
    else:
        indexed_docs = []

    if missed_paper_col.find_one({'Journal': journal_title}):
        missed_docs = [p for p in missed_paper_col.find({'Journal': journal_title})]
    else:
        missed_docs = []

    for year in range(first_year_upd, final_year):

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
            if doc_search.results == [{'@_fa': 'true', 'error': 'Result set was empty'}]:
                print("Search was successful but result set was empty for {}".format(year))
                search_success = False
            else:
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

                print("Search success for from {} ({} up thru {})!\nIndexed {} new papers\nMissed {} new papers ".format(
                    journal_doc["Journal_Title"],
                    first_year_upd,
                    year,
                    year_indexed_doc_num,
                    year_missed_doc_num
                ),
                    end='\r'
                )
        else:
            print("Search failure for {} in {}".format(journal_doc['Journal_Title'], year))

        print('\n\n')
        year_meta = {
            'Year': year,
            'Current_Year': current_year,
            'Search_Success': search_success,
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

    return

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", type=int, required=True, help="API key number")
    args = parser.parse_args()

    # TODO: find a way to check rate limits (here's a start: https://dev.elsevier.com/api_key_settings.html)
    api_keys = {
        1: ELSEVIER_API_1,
        2: ELSEVIER_API_2,
        3: ELSEVIER_API_3,
        4: ELSEVIER_API_4,
    }
    client = ElsClient(api_keys[args.n])

    # TODO: add as a command line argument, not hardcoded into script
    first_year = 2000
    final_year = 2024

    # TODO: Make the loop a list of all the journal names
    journal_titles = [d['Journal_Title'] for d in journal_col.find({})]
    for journal_title in journal_titles:
        index_papers_by_journal_year(
            journal_title,
            first_year,
            final_year,
            mongo_insert=True,
            mongo_update=True
        )