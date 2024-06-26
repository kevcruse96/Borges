#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
import argparse
import json_lines
from DBGater.db_singleton_mongo import SynDevAdmin

__author__ = 'Ziqin (Shaun) Rong'
__maintainer__ = 'Kevin Cruse'
__email__ = 'kevcruse96@gmail.com'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", type=str, help='input file path')
    parser.add_argument("-c", type=str, help="collection name where the json line file is inserted")
    args = parser.parse_args()

    db = SynDevAdmin.db_access()
    db.connect()
    col = db.collection(args.c)

    with open(args.i, 'r') as jlf:
        unique_j_num = 0
        for i, item in enumerate(json_lines.reader(jlf)):
            if 'DOI' in item.keys(): # for RSC
                dup_key = 'DOI'
            elif 'Journal_ISSN' in item.keys(): # for Elsevier
                dup_key = 'Journal_ISSN'
            elif 'Journal_Title' in item.keys(): # for AIP
                dup_key = 'Journal_Title'
            else:
                print("Please add appropriate key to check for duplicates")
                continue
            if not col.find_one({dup_key : item[dup_key]}):
                col.insert_one(item)
                unique_j_num += 1
                print(f'Inserted {unique_j_num} items to {args.c}...', end='\r')

    print(f'\n Inserted total of {unique_j_num} items to {args.c}')
