#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
import os
import json_lines
from bs4 import BeautifulSoup

import scrapy

__author__ = 'Ziqin (Shaun) Rong'
__maintainer__ = 'Kevin Cruse'
__email__ = 'kevcruse96@gmail.com'

if os.path.isfile('./journals.jl'):
    journal_meta_list = [item for item in json_lines.reader(open('./journals.jl'), 'r')]
else:
    journal_meta_list = []

class ElsevierJournals(scrapy.Spider):
    name = "Elsevier_Journal"
    # Add functionality for either automatic checking of page range OR just cycle until an error below

    start_urls = [f"https://www.elsevier.com/search-results?labels=journals&subject-0=27360&page={page}" for
                  page in range(1, 17)
                  ] + \
                 [f"https://www.elsevier.com/search-results?labels=journals&subject-0=27362&page={page}" for
                  page in range(1, 20)
                  ] + \
                 [f"https://www.elsevier.com/search-results?labels=journals&subject-0=27364&page={page}" for
                  page in range(1, 16)
                  ] + \
                 [f"https://www.elsevier.com/search-results?labels=journals&subject-0=27366&page={page}" for
                  page in range(1, 15)
                  ] + \
                 [f"https://www.elsevier.com/search-results?labels=journals&subject-0=27368&page={page}" for
                  page in range(1, 11)
                  ] + \
                 [f"https://www.elsevier.com/search-results?labels=journals&subject-0=27370&page={page}" for
                  page in range(1, 25)
                  ] + \
                 [f"https://www.elsevier.com/search-results?labels=journals&subject-0=27372&page={page}" for
                  page in range(1, 14)
                  ] + \
                 [f"https://www.elsevier.com/search-results?labels=journals&subject-0=27374&page={page}" for
                  page in range(1, 21)
                  ] + \
                 [f"https://www.elsevier.com/search-results?labels=journals&subject-0=27376&page={page}" for
                  page in range(1, 15)
                  ] + \
                 [f"https://www.elsevier.com/search-results?labels=journals&subject-0=27378&page={page}" for
                  page in range(1, 18)
                  ]

    def parse(self, response):
        journal_titles = response.css('.search-result-title a::text').extract()
        # TODO: find a way to extract true/false for "Open Access"
        journal_urls = response.css('.journal-website a::attr(href)').extract()
        journal_issns = response.css('.journal-result-issn *::text').extract() # ISSNs were not extracted in previous version... not sure when they were grabbed before

        for (t, u, i) in zip(journal_titles, journal_urls, journal_issns):
            journal_meta = {
                'Journal_Title': t,
                'Open_Access': None,
                'Journal_Main_Page_Link': u,
                'Journal_ISSN': i,
                'Years_Indexed': [],
                'Years_Crawled': []
            }
            if journal_meta not in journal_meta_list:
                journal_meta_list.append(journal_meta)
                yield journal_meta