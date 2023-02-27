#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import os
import yaml
from datetime import datetime

__author__ = 'Ziqin (Shaun) Rong'
__maintainer__ = 'Kevin Cruse'
__email__ = 'kevcruse96@gmail.com'

current_date = datetime.today().strftime('%Y%m%d')

if __name__ == '__main__':
    # TODO: get rid of YAML warning
    with open(os.path.join(os.path.dirname(__file__), '.', 'start_url_gen_params_format_1_20230224.yml'), 'r') as yf1:
        params_1 = yaml.load(yf1)
    with open(os.path.join(os.path.dirname(__file__), '.', 'start_url_gen_params_format_2_20230224.yml'), 'r') as yf2:
        params_2 = yaml.load(yf2)
    start_url = {"RSC": []}
    for k, v in params_1['RSC'].items():
        for vol in range(v['start_vol'], v['end_vol'] + 1):
            # TODO: add flexibility with incomplete volumes (e.g. the current one)... might be fine as is, will just have some links in .yaml that won't work
            # TODO: add switch to only grab new issues if journal is already in database (i.e. after 2017)
            for iss in range(1, v['issue_per_year'] + 1):
                vol_issue_str = str(vol).zfill(3) + str(iss).zfill(3)
                start_url['RSC'].append(v['format'].format(vol_issue_str))
    for k, v in params_2['RSC'].items():
        for vol in range(v['start_vol'], v['end_vol'] + 1):
            for iss in range(v['start_issue'], v['end_issue'] + 1):
                vol_issue_str = str(vol).zfill(3) + str(iss).zfill(3)
                start_url['RSC'].append(v['format'].format(vol_issue_str))
    with open(os.path.join(os.path.dirname(__file__), '.', f'start_urls_{current_date}.yaml'), 'w') as yf:
        yaml.dump(start_url, yf, default_flow_style=False)
