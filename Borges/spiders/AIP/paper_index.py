# Add interpreter location?

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import argparse

from DBGater.db_singleton_mongo import SynDevAdmin, SynProAdmin
import adal
import requests

from Borges.settings import AIP_BASEURL, AIP_RESOURCE, AIP_AUTHORITY_URL, AIP_CLIENT_ID, AIP_CLIENT_SECRET

__author__ = 'Kevin Cruse',
__maintainer__ = 'Kevin Cruse'
__email__ = 'kevcruse96@gmail.com'

if __name__ == "__main__":
    db = SynProAdmin.db_access()
    db.connect() # It seems that this method uses the .authenticate() method, which was eliminated after
                 # pymongo v3.4 (probably)... might be worthwhile to update DBGater accordingly, but for now
                 # pymongo==3.4 locally to run this



