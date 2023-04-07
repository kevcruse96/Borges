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