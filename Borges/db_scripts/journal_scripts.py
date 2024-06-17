#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import json
import argparse

from DBGater.db_singleton_mongo import SynDevAdmin
from pprint import pprint

__author__ = 'Kevin Cruse'
__maintainer__ = 'Kevin Cruse'
__email__ = 'kevcruse96@gmail.com'

db = SynDevAdmin.db_access()
db.connect()

def get_unindexed_journals(journal_col):
    total_journals = db.collection(journal_col).count_documents({})

    unindexed_journals = [] # journal is considered unindexed if NO year contains any value >0 in Indexed_Doc_Num
    print("Collecting unindexed journals...")
    for i, j in enumerate(db.collection(journal_col).find({})):
        if j['Years_Indexed']:
            indexed = False
            for y in j['Years_Indexed']:
                if y['Indexed_Doc_Num']:
                    indexed = True
            if not indexed:
                unindexed_journals.append(j['Journal_Title'])
        print(f'{i+1}/{total_journals}', end='\r')

    print(f"\nDone! Collected {len(unindexed_journals)} unindexed journals")
    return unindexed_journals


def update_journal_entry(journal_col, journal_title, year, success):
    journal_doc = journal_col.find_one({'Journal_Title': journal_title})
    years_crawled = journal_doc['Years_Crawled']

    if years_crawled:
        if year in [y['Year'] for y in years_crawled]:
            for y in years_crawled:
                if y['Year'] == year:
                    if success:
                        y['Scraped_Doc_Num'] = y['Scraped_Doc_Num'] + 1
                    else:
                        y['Missed_Doc_Num'] = y['Missed_Doc_Num'] + 1
        else:
            scraped = 0
            missed = 0
            if success:
                scraped = 1
            else:
                missed = 1

            new_y = {
                'Year': year,
                'Scraped_Doc_Num': scraped,
                'Missed_Doc_Num': missed,
                'last_updated': datetime.utcnow()
            }

            years_crawled.append(new_y)

    journal_col.update_one({
        {'Journal_Title': journal_title},
        {'$set': {'Years_Crawled': years_crawled}}
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", type=str, required=True, help="Collection to query")
    parser.add_argument("-o", type=str, required=False, help="File to write unindexed journals into")
    args = parser.parse_args()

    journal_col = db.collection(args.c)

    unindexed_journals = get_unindexed_journals(journal_col)

    if args.o:
        with open(args.o, 'w') as fp:
            json.dump(unindexed_journals, fp)