from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

from DBGater.db_singleton_mongo import SynDevAdmin

__author__ = 'Kevin Cruse'
__maintainer__ = 'Kevin Cruse'
__email__ = 'kevcruse96@gmail.com'

def create_dummy_col(name, col_to_dupe=None, randomize=False, sample_size = 10, data=None):
    db = SynDevAdmin.db_access()
    db.connect()

    if name in db._connected_db.list_collection_names():
        print(f"{name} already exists!")
        return

    dummy_col = db.collection(name)

    if col_to_dupe is not None:
        if randomize:
            dummy_col.insert_many([p for p in col_to_dupe.aggregate([{'$sample': {'size': sample_size}}])])

    else:
        print("Please provide a dataset or a collection to duplicate a sample from ")

if __name__ == "__main__":
    pass