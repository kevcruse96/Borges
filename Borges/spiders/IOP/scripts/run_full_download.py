import os
from download_via_sftp import IOPDownloader
from upload_to_mongodb import MongoUploader

cwd = os.getcwd()

host     = os.getenv("IOP_host")
username = os.getenv("IOP_username")
password = os.getenv("IOP_password")

downloader = IOPDownloader(host, username, password)

output_dir = f"{os.path.abspath(str(cwd)+'/../data/')}"
mu = MongoUploader(data_path=output_dir)

for batch_no in range(9,12):
    downloader.connect()
    if downloader.connected:
        print(f"\nGetting batch #{batch_no}")
        if batch_no == 1:
            for i, file_no in enumerate(range(1, 121)):
                downloader.connect()
                if downloader.connected:
                    print(f"\nGetting sub-batch #{batch_no} for JPDAP")

                    downloader.run(
                        batch_no,
                        journal=None,
                        n_files=1,
                        file_no=file_no,
                        output_dir=output_dir
                    )

                    proceed = mu.run(
                        extract_to_temp=True,
                        ext_filter=['xml'], # for now, just xml... work on HTML parsing later
                        redownload=True
                    )

                    if proceed == -1:
                        break
            break
        else:
            downloader.run(
                batch_no,
                journal=None,
                n_files=1,
                file_no=None,
                output_dir=output_dir
            )
            proceed = mu.run(
                extract_to_temp=True,
                ext_filter=['xml'], # for now, just xml... work on HTML parsing later
                redownload=True
            )

            if proceed == -1:
                break

else:
    print("Closing. Come back later!")
