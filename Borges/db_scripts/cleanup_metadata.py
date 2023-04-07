#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import argparse
import requests
from DBGater.db_singleton_mongo import SynDevAdmin
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

__author__ = 'Kevin Cruse'
__maintainer__ = 'Kevin Cruse'
__email__ = 'kevcruse96@gmail.com'

db = SynDevAdmin.db_access()
db.connect()

# Elsevier Collections
els_journal_col = db.collection("ElsevierJournals")
els_paper_col = db.collection("ElsevierPapers")
els_missed_paper_col = db.collection("ElsevierPapers_missed")

def elsevier_cleanup():

    return

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--publisher", action='store_true', required=False,
                        help="Target publisher for metadata cleaning")
    parser.add_argument("-s", "--cleanup-source", type=str, required=False,
                        help='Source where metadata is retrieved from ("scidir", "crossref", etc.)')
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

