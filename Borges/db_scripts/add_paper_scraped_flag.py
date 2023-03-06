#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import argparse

from DBGater.db_singleton_mongo import SynDevAdmin

__author__ = 'Ziqin (Shaun) Rong'
__maintainer__ = 'Ziqin (Shaun) Rong'
__email__ = 'rongzq08@gmail.com'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", type=str, help="collection name where the flag is added")
    args = parser.parse_args()

    db = SynDevAdmin.db_access()
    db.connect()
    col = db.collection(args.c)

    for doc in col.find():
        if 'HTML_Crawled' not in doc.keys() or doc['HTML_Crawled']:
            col.update_one({'_id': doc['_id']}, {'$set': {'HTML_Crawled': False}})
        elif 'Crawled' in doc.keys():
            col.update_one({'_id': doc['_id']}, {'$rename': {'Crawled': 'HTML_Crawled'}})
