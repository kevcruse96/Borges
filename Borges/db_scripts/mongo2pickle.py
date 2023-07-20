import os
import pickle
from tqdm import tqdm

def mongo2pickle(savefile, col, store_keys=[], overwrite=False, criteria={}, batches=None):

    if overwrite or not os.path.isfile(f'./data/{savefile}'):
        print(f'Collecting and storing entries to {savefile}...')

        dump_obj = []

        total_docs = col.count_documents(criteria)
        for doc in tqdm(col.find(criteria), total=total_docs):
            doc_to_save = {}
            for k in store_keys:
                doc_to_save[k] = doc[k]
            dump_obj.append(doc_to_save)

        if batches:
            batch_size = int(len(dump_obj) / batches)
            leftover = len(dump_obj) % batches
            for i in range(batches):
                if i == batches - 1:
                    end = batch_size + leftover
                else:
                    end = batch_size
                with open(f'./data/{i}_{savefile}', 'wb') as fp:
                    pickle.dump(dump_obj[i*batch_size:i*batch_size+end], fp)

        with open(f'./data/{savefile}', 'wb') as fp:
            pickle.dump(dump_obj, fp)

    else:
        print(f'{savefile} already exists.')