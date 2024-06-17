import os

from download_via_sftp import IOPDownloader
from upload_to_mongodb import MongoUploader

cwd = os.getcwd()

host     = os.getenv("IOP_host")
username = os.getenv("IOP_username")
password = os.getenv("IOP_password")

downloader = IOPDownloader(host, username, password)
downloader.connect()

output_dir = f"{os.path.abspath(str(cwd)+'/../data/for_counting/')}"
mu = MongoUploader(data_path=output_dir)

abstract_ct = 0
fulltext_ct = 0

if downloader.connected:
    for batch_no in range(1,12):
        print(f"\nChecking fulltext from Batch {batch_no}")
        print(f"Currently {fulltext_ct} fulltext and {abstract_ct} only abstract \n\n")
        if batch_no == 1:
            for file_no in range(3, 121):
                print(f"\nChecking fulltext from Batch {batch_no}")
                print(f"Currently {fulltext_ct} fulltext and {abstract_ct} only abstract \n\n")
                downloader.run(
                    batch_no,
                    journal=None,
                    n_files=1,
                    file_no=file_no,
                    output_dir=output_dir
                )
                a_ct, f_ct = mu.count_fulltext(
                    "body",
                    ext_filter=['xml', 'html']
                )

                abstract_ct += a_ct
                fulltext_ct += f_ct
        else:
            a_ct, f_ct = mu.count_fulltext(
                "body",
                ext_filter=['xml', 'html']
            )

            abstract_ct += a_ct
            fulltext_ct += f_ct
