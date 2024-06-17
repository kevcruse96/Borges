import os
import sys
import json
import math
import argparse
import pysftp
import zipfile

from pprint import pprint

cwd = os.getcwd()

parser = argparse.ArgumentParser(description="Specify download requirements")

parser.add_argument(
    "--batch_number",
    metavar="-b",
    type=int,
    default=None,
    help="number of journal batch (1-11) that you want to download"
)

parser.add_argument(
    "--journal",
    metavar="-j",
    type=str,
    default=None,
    help="journal that you want to download"
)

parser.add_argument(
    "--n_files",
    metavar="-nf",
    type=int,
    default=1,
    help="number of articles to download"
)

parser.add_argument(
    "--file_no",
    metavar="-fn",
    type=int,
    default=None,
    help="file number for JPDAP"
)

parser.add_argument(
    "--output_dir",
    metavar="-od",
    type=str,
    default=f"{os.path.abspath(str(cwd)+'/../data/')}",
    help="output directory for downloaded data"
)

args = parser.parse_args()

def convert_size(size_bytes):
   if size_bytes == 0:
       return "0B"
   size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
   i = int(math.floor(math.log(size_bytes, 1024)))
   p = math.pow(1024, i)
   s = round(size_bytes / p, 2)
   return "%s %s" % (s, size_name[i])

class IOPDownloader:

    def __init__(
        self,
        host,
        username,
        password,
        port=22,
    ):
        """
        Downloader class for secure file transfer; will connect and download
        a single article if run without arguments
        <host>: host url
        <username>: username
        <password>: password
        <port>: port for sftp connection, 22 by default for ssh
        """
        self.host = host
        self.username = username
        self.password = password
        self.port = port

    def connect(self):
        """

        """
        print("Connecting...")
        try:
            self.sftp = pysftp.Connection(
                host     = self.host,
                port     = self.port,
                username = self.username,
                password = self.password
            )
            self.connected = True
            print("...Successfully connected to secure file transfer host!\n")
        except Exception as e:
            self.connected = False
            print("...Failed to establish connection, see error:\n")
            print(e)
        return

    def __get_relevant_zipfiles(
        self,
        batch_no,
        journal,
        n_files,
        file_no,
        output_dir
        ):

        with open('../rsc/zipname2journal.json', 'r') as fp:
            zipname2journal = json.load(fp)

        journal2zipname = {
            vsub:k for k, v in zipname2journal.items() for vsub in v
        }

        if batch_no:
            print(f"Downloading file(s) from batch #{batch_no}, "
            f"transferring from {self.username}@{self.host} to {output_dir}...")
            if batch_no == 1:
                general_filename = list(zipname2journal.keys())[batch_no-1]
                if file_no:
                    self.files = [general_filename.replace("X", str(file_no))]
                else:
                    self.files = [
                        general_filename.replace("X", str(i+1)) for
                        i in range(n_files)
                    ]

            else:
                self.files = [list(zipname2journal.keys())[batch_no-1]]

        elif journal:
            print(f"Downloading file(s) from {journal}, "
            f"transferring from {self.username}@{self.host} to {output_dir}...")
            if journal == "Journal of Physics D: Applied Physics":
                general_filename = journal2zipname[journal]
                self.files = [
                        general_filename.replace("X", i+1) for
                        i in range(n_files)
                    ]
            else:
                self.files = journal2zipname[journal]

        return

    def __order_filenames_jpdap(self):
        self.files.sort(key=lambda x:int(x.split("_")[4]))

    def __print_progress(self, transferred, toBeTransferred):
        print(f"Downloaded {convert_size(transferred)} Out of"
         f"{convert_size(toBeTransferred)}", end='\r')

    def run(self, batch_no, journal, n_files, file_no, output_dir):

        self.__get_relevant_zipfiles(
            batch_no,
            journal,
            n_files,
            file_no,
            output_dir
        )

        for file in self.files[:n_files]:
            print(f"Downloading {file}...\n")
            self.sftp.get(
                file,
                output_dir+"/"+file,
                callback=self.__print_progress
            )

        print("\nFinished!")


if __name__ == "__main__":
    host     = os.getenv("IOP_host")
    username = os.getenv("IOP_username")
    password = os.getenv("IOP_password")

    batch_no   = args.batch_number
    journal    = args.journal
    n_files    = args.n_files

    file_no    = args.file_no

    if batch_no and journal:
        sys.exit(
        "Please select only a batch number or a journal, not both\n...Exiting"
        )

    output_dir = args.output_dir

    downloader = IOPDownloader(host, username, password)
    downloader.connect()

    if downloader.connected:
        downloader.run(batch_no, journal, n_files, file_no, output_dir)
    else:
        print("Closing. Come back later!")
