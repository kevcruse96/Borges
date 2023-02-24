#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
import argparse
import json_lines
from DBGater.db_singleton_mongo import SynDevAdmin

__author__ = 'Ziqin (Shaun) Rong'
__maintainer__ = 'Ziqin (Shaun) Rong'
__email__ = 'rongzq08@gmail.com'


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
            if not col.find_one({'Journal_ISSN' : item['Journal_ISSN']}):
                col.insert_one(item)
                unique_j_num += 1
                print(f'Inserted {unique_j_num} journals to {args.c}...', end='\r')

    print(f'\n Inserted total of {i} journals to {args.c}')
