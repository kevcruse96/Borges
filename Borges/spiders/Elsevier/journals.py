#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from bs4 import BeautifulSoup

import scrapy

__author__ = 'Ziqin (Shaun) Rong'
__maintainer__ = 'Ziqin (Shaun) Rong'
__email__ = 'rongzq08@gmail.com'

class ElsevierJournals(scrapy.Spider):
    name = "Elsevier_Journal"
    start_urls = [f"https://www.elsevier.com/search-results?labels=journals&page={page}" for page in range(1, 3)]

    def parse(self, response):
        journal_titles = response.css('.search-result-title a::text').extract()
        # TODO: find a way to extract true/false for "Open Access"
        journal_urls = response.css('.journal-website a::attr(href)').extract()
        journal_issns = response.css('.journal-result-issn *::text').extract() # ISSNs were not extracted in previous version... not sure when they were grabbed before

        for (t, u, i) in zip(journal_titles, journal_urls, journal_issns):
            yield {
                'Journal_Title': t,
                'Open_Access': None,
                'Journal_Main_Page_Link': u,
                'Journal_ISSN': i
            }