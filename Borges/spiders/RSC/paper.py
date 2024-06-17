#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import scrapy
from scrapy_splash import SplashRequest

from pprint import pprint

from DBGater.db_singleton_mongo import SynDevAdmin

__author__ = 'Ziqin (Shaun) Rong'
__maintainer__ = 'Kevin Cruse'
__email__ = 'kevcruse96@gmail.com'

class RSCPaperSpider(scrapy.Spider):
    name = "RSC_Paper"

    # http_user = 'user'
    # http_pass = 'userpass'
    user_agent = "CederGroup@berkeley-TDMCrawler"

    # db = SynDevAdmin.db_access()
    # db.connect()
    # col = db.collection('RSCPapers')

    def start_requests(self):
        for doc in range(2): #self.col.find({'HTML_Crawled': False}):
            url = 'http://pubs.rsc.org/en/content/articlehtml/2018/an/c7an01683b'
            # url = doc['Article_HTML_Link']
            request = SplashRequest(url, self.parse, args={'wait': 5})
            #request.meta['DOI'] = doc['DOI']
            yield request

    def parse(self, response):
        print(response.headers)
        pprint(response.css('div#maincontent').extract_first())
        stop
        try:
            html = response.css('div#wrapper').extract_first()
            # if html:
            #     self.col.update_one({"DOI": response.meta['DOI']}, {'$set': {'HTML_Crawled': True,
            #                                                              "Paper_Content_HTML": html}})
            # else:
            #     self.col.update_one({"DOI": response.meta['DOI']}, {'$set': {'HTML_Crawled': False,
            #                                                              'Error_Msg': "HTML string is None"}})
        except Exception as e:
            stop
            pass
            # self.col.update_one({"DOI": response.meta['DOI']}, {'$set': {'HTML_Crawled': False,
            #                                                          'Error_Msg': str(e)}})
