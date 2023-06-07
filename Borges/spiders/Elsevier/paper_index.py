#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import json
import argparse
import requests

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
import random

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

def parse_doc_search_result(res, journal_doc, source):

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
        if source == 'Scopus':
            paper_sum["Open_Access"] = res['openaccessFlag']
        elif source == 'SciDir':
            paper_sum["Open_Access"] = res['openaccessArticle']
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

    # TODO: can we get ORCID

    paper_sum["Authors"] = []

    try:
        paper_sum["Authors"].extend([f"{ath['$'].split(', ')[1]} {ath['$'].split(', ')[0]}"
                                for ath in res['dc:creator']])
        paper_sum["Authors"].extend([f"{ath['$'].split(', ')[1]} {ath['$'].split(', ')[0]}"
                                for ath in res['authors']['author']])
    except:
        paper_sum["Authors"] = res['authors']

    try:
        paper_sum["Issue"] = int(res[u'prism:issueIdentifier'].encode("utf-8"))
    except:
        paper_sum["Issue"] = None

    return paper_sum

def index_papers_by_journal_year(
        journal_title,
        first_year,
        final_year,
        client,
        api_key,
        source,
        mongo_insert=False,
        mongo_update=False):
    paper_l = []
    missed_paper_l = []

    # Grab MongoDB journal entry
    journal_doc = journal_col.find_one({'Journal_Title': journal_title})
    if not journal_doc:
        return

    years_to_query = [(yyyy, None) for yyyy in range(first_year, final_year)]

    # Update list of years to query (include unqueried and those that gave query errors earlier)
    # years_indexed can be initiated more intelligently
    years_indexed = []
    old_years_indexed = journal_doc['Years_Indexed']
    if old_years_indexed:
        for y in old_years_indexed:
            if not ( # this logic checks if the year exists but we haven't looked through a particular source yet
                (
                    source == 'SciDir' and (
                        'SciDir_Available' not in y.keys() or
                        y['SciDir_Available'] == None
                    )
                ) or
                (
                    source == 'Scopus' and (
                        'Scopus_Available' not in y.keys() or
                        y['Scopus_Aviailabe'] == None
                    )
                )
            ):
                years_to_query.remove(y['Year'])
            else:
                years_to_query[years_to_query.index((y['Year'], None))] = (y['Year'], y)

    # Grab number of indexed and missing docs if previously queried
    if paper_col.find_one({'Journal': journal_title}):
        indexed_docs = [p for p in paper_col.find({'Journal': journal_title})]
    else:
        indexed_docs = []
    if missed_paper_col.find_one({'Journal': journal_title}):
        missed_docs = [p for p in missed_paper_col.find({'Journal': journal_title})]
    else:
        missed_docs = []

    for year, year_meta in years_to_query:

        if not year_meta: # could be a better way of doing this...

            year_indexed_doc_num = 0
            year_missed_doc_num = 0

            current_year = False
            if year == final_year-1:
                current_year = True

        else:
            year_indexed_doc_num = year_meta['Indexed_Doc_Num']
            year_missed_doc_num = year_meta['Missed_Doc_Num']
            current_year = year_meta['Current_Year']

        # Below is a slow step for large queries
        # TODO: add more query endpoints (e.g. keywords)

        search_success = True

        if source == 'Scopus':
             doc_search = ElsSearch('ISSN({}) AND PUBYEAR = {}'.format(journal_doc["Journal_ISSN"], year), 'scopus') # Note this was pretty tricky to figure out... there needs to be spaces between the qualifying and "PUBYEAR"/year... also need to use 'scopus' instead of 'scidir'
             try:
                 doc_search.execute(client, get_all=True)
                 results = doc_search.results
             except:
                 search_success = False

        elif source == 'SciDir':
            results = []

            i = 0
            og_count = 100
            total_entries = 1
            while i < total_entries / og_count:

                if total_entries != 1 and (total_entries / og_count) - i < 1: # first half of this logic might be iffy...
                    count = total_entries % og_count
                else:
                    count = og_count

                res = requests.get(
                    f"https://api.elsevier.com/content/metadata/article?query="
                    f"(issn({journal_doc['Journal_ISSN'].replace('-', '')})+AND+pub-date+is+{year})&view=COMPLETE&count={count}&start={i}&apikey={api_key}"
                )
                i += 1
                try:
                    total_entries = int(json.loads(res.content.decode())['search-results']['opensearch:totalResults'])
                    results.extend(json.loads(res.content.decode())['search-results']['entry'])
                except:
                    search_success = False

        if search_success:

            if not year_meta:
                scopus_available = None
                scidir_available = None
            else:
                scopus_available = year_meta['Scopus_Available']
                if 'SciDir_Available' in year_meta.keys(): # will be able to remove this if logic after subsequent run
                    scidir_available = year_meta['SciDir_Available']
                else:
                    scidir_available = None

            if results == [{'@_fa': 'true', 'error': 'Result set was empty'}]:
                print("Search was successful but result set was empty for {}".format(year))
                if source == 'Scopus':
                    scopus_available = False
                elif source  == 'SciDir':
                    scidir_available = False
                    scopus_available = False # WARNING: should remove this after initial run... better to add an indicator that

            else:
                if source == 'Scopus':
                    scopus_available = True
                elif source == 'SciDir':
                    scidir_available = True

                for res in results:

                    paper_sum = parse_doc_search_result(res, journal_doc, source)

                    if paper_sum['DOI']:
                        indexed_docs.append(paper_sum)
                        paper_l.append(paper_sum)
                        year_indexed_doc_num += 1
                    else:
                        missed_docs.append(paper_sum)
                        missed_paper_l.append(paper_sum)
                        year_missed_doc_num += 1

                print("Search success for {} ({})!\nIndexed {} new papers\nMissed {} new papers ".format(
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
            'SciDir_Available': scidir_available,
            'Indexed_Doc_Num': year_indexed_doc_num,
            'Missed_Doc_Num': year_missed_doc_num,
            'last_updated': datetime.utcnow()
        }

        years_indexed.append(year_meta)

    # TODO: move dumping inside year-by-year loop? (This may actually be worse for restarting / conditioning)
    # TODO: Would be nice to have a way to know for certain that we don't already have the paper, then insert it


    if mongo_insert:
        print(f'Dumping {len(paper_l)} papers from {journal_doc["Journal_Title"]} into ElsevierPapers...\n')
        if paper_l:
            paper_col.insert_many(paper_l)
        if missed_paper_l:
            missed_paper_col.insert_many(missed_paper_l)

    if mongo_update:
        print(f'Updating journal entry for {journal_doc["Journal_Title"]} in ElsevierJournals...\n')
        journal_col.update_one({"_id": journal_doc["_id"]}, {"$set": {
            "Years_Indexed": years_indexed
        }})


    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", type=int, required=False, help="API key number")
    parser.add_argument("-s", "--source", type=str, required=True, help="Source for scraping (Scopus or SciDir)")
    parser.add_argument("-i", "--ignore_indexed", action='store_true', required=False,
                        help="Only index papers from unattempted journals")
    parser.add_argument("-u", "--only_unindexed", action='store_true', required=False,
                        help="Flag to only index papers for previously unindexible journals (issue for Scopus querying)")
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
    else:
        api_key_list = list(api_keys.keys())

    # TODO: add as a command line argument, not hardcoded into script
    first_year = 2000
    final_year = 2024

    if args.ignore_indexed:
        journal_titles = [d['Journal_Title'] for d in journal_col.find({
            'Years_Indexed': {'$not': {'$size': final_year - first_year}}
        })]
    elif args.only_unindexed:
        from Borges.db_scripts.journal_scripts import get_unindexed_journals
        journal_titles = get_unindexed_journals("ElsevierJournals")
    else:
        journal_titles = [d['Journal_Title'] for d in journal_col.find({})]

    for key in api_key_list:
        for journal_title in journal_titles:
            print(f"=====Searching for papers from {journal_title} ({first_year}-{final_year - 1}) (API KEY {key})=====\n")
            client = ElsClient(api_keys[key])
            journal_year_index = index_papers_by_journal_year(
                journal_title,
                first_year,
                final_year,
                client,
                api_keys[key],
                source=args.source,
                mongo_insert=True,
                mongo_update=True
            )
            if not journal_year_index:
                if key != 8:
                    print(f"\n\nSwitching to API KEY {key+1}\n\n")
                    break
                else:
                    print("\n\nHitting quota for all API keys.")
