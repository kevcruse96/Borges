import os
from glob import glob
import subprocess
import traceback
from lxml import etree
from zipfile import ZipFile
from zipfile_fasttargeting import ZipFile as ZipFileFast
from tqdm import tqdm
import collections

import random
from pprint import pprint

from DBGater.db_singleton_mongo import SynDevAdmin

from article_xml_extractor import ArticleXMLDataExtractor

# TODO: make separate class for ZipUnloader

# Only uncomment below if you want to interact with MongoDB
db = SynDevAdmin.db_access()
db.connect()
iop_paper_col = db.collection("IOPPapers") # TODO make this more general
ecs_paper_col = db.collection("ECSPapers")


class MongoUploader: # Change this name... it handles more than this


    def __init__(self, data_path=None, article_filepaths=None):
        self.data_path = data_path
        self.article_filepaths = article_filepaths


    def _get_zipfile_names(self):
        self.zipfile_names = [
            fn for fn in os.listdir(self.data_path) if
            "." in fn and
            fn.split(".")[1] == "zip"
        ]


    def _get_zipfile_content_namelist(self, zf):
        with ZipFile(f"{self.data_path}/{zf}", 'r') as zp:
            self.zipfile_content_namelist = zp.namelist()


    def _get_article_filepaths(self, ext_filter=None):

        if type(ext_filter) != list:
            ext_filter = [ext_filter]

        print("Collecting existing zip files...")
        zfs = self._get_zipfile_names()
        print(f"There are {len(self.zipfile_names)} zip files\n")


        # TODO: make filename extraction a separate function?
        print("Extracting contents of zip files")
        if ext_filter:
            print(
                f"(Only considering {', '.join([f for f in ext_filter])} files)"
            )
        for zf in self.zipfile_names:
            print(f"Finding filenames from {zf}...")
            self._get_zipfile_content_namelist(zf)
            self.article_filepaths = [
                fp for fp in self.zipfile_content_namelist if
                fp.split(".")[1] in ext_filter
            ]
            print(f"...There are {len(self.article_filepaths)} articles in ",
                f"{zf} to extract to temporary folder"
            )


    def _check_single_file_for_tag(self, zipper, tag, zf, filepath):
        contains_fulltext = False

        with zipper as zp:
            with zp.open(filepath) as zfo:
                if filepath.endswith('xml'):
                    parser = etree.XMLParser()
                    article_string = zfo.read().decode()
                elif filepath.endswith('html'):
                    parser = etree.HTMLParser()
                    article_string = zfo.read().decode(encoding='windows-1252')

                if etree.fromstring(
                    article_string.encode(),
                    parser
                ).find(tag) is not None:
                    contains_fulltext = True

        return contains_fulltext


    def _extract_single_file_from_zip(
        self,
        zipper,
        zf,
        filepath,
        extract_to_temp
    ):
        if not os.path.isdir(f"{self.data_path}/temp"):
            os.mkdir(f"{self.data_path}/temp")

        with zipper as zp:
            with zp.open(filepath) as zfo:

                if filepath.endswith('xml'):
                    parser = etree.XMLParser()
                    article_string = zfo.read().decode()
                elif filepath.endswith('html'):
                    parser = etree.HTMLParser()
                    article_string = zfo.read().decode(encoding='windows-1252')

                if extract_to_temp:
                    with open(
                        f"{self.data_path}/temp/{filepath.split('/')[-1]}",
                        'w'
                    ) as fp:
                        fp.write(article_string)

        return etree.fromstring(
            article_string.encode(),
            parser
        )


    def _extract_zip_files_to_temp(self, ext_filter=None):
        """
        Extracts contents of zip file to temporary folder, optionally based
        on a given filter for filename features

        ext_filter: list or str -- filter for specific extensions
        """

        self._get_article_filepaths(ext_filter=ext_filter)

        for zf in self.zipfile_names:

            print(f"Extracting files from {zf}...")
            for afp in tqdm(
               self.article_filepaths,
               total=len(self.article_filepaths)
            ):
                try: # try fast Zip extraction first
                    zipper = ZipFileFast(
                        f"{self.data_path}/{zf}",
                        to_extract=[afp],
                        mode='r'
                    )
                    self._extract_single_file_from_zip(
                        zipper,
                        zf,
                        afp,
                        extract_to_temp=True
                        )
                except: # if fast extraction doesn't work just use regular
                    zipper = ZipFile(
                        f"{self.data_path}/{zf}",
                        mode='r'
                    )
                    self._extract_single_file_from_zip(
                        zipper,
                        zf,
                        afp,
                        extract_to_temp=True
                        )
            print()


    def __delete_zipfile(self, zf):
        os.remove(zf)


    def __delete_tempfiles(self):
        for f in glob(f"{self.data_path}/temp/*.xml"):
            os.remove(f)
        for f in glob(f"{self.data_path}/temp/*.html"):
            os.remove(f)


    def _update_existing_article(self, article_data, fields_to_unset):
        if article_data['Journal'] == 'Journal of The Electrochemical Society':
            col = ecs_paper_col
        else:
            col = iop_paper_col

        if fields_to_unset:
            col.update_one(
                {'_id': article_data.pop('_id')},
                [
                    {'$set': article_data},
                    {'$unset': fields_to_unset},
                ]
            )
        else:
            col.update_one(
                {'_id': article_data.pop('_id')},
                [
                    {'$set': article_data},
                ]
            )
        return


    def _insert_new_article(self, article_data):
        if article_data['Journal'] == 'Journal of The Electrochemical Society':
            col = ecs_paper_col
        else:
            col = iop_paper_col

        col.insert_one(article_data)
        return


    def _upload_file_to_mongodb(self, article_tree, temp_afp, redownload=False):

        proceed = True

        try:
            axde = ArticleXMLDataExtractor(article_tree)
            already_downloaded, fields_to_unset = axde.extract_article_data()

            # TODO: could actually just make this one call to
            # _update_existing_article() and use upsert to create a new document
            # if an existing one does not exist

            if not already_downloaded:
                if fields_to_unset is not None:
                    self._update_existing_article(
                        axde.article_data,
                        fields_to_unset
                    )
                else:
                    self._insert_new_article(axde.article_data)
            else:
                if redownload:
                    print(f"\nRedownloading {axde.article_data['DOI']}")
                    self._update_existing_article(
                        axde.article_data,
                        fields_to_unset
                    )
                else:
                    print(f"\nAlready downloaded {axde.article_data['DOI']}...",
                     " Moving on")



        except Exception as e:
            print(e)
            print(temp_afp)
            pprint(axde.article_data.keys())
            traceback.print_exc()
            proceed = False

        return proceed


    def run(self, extract_to_temp=False, ext_filter=None, redownload=False):

        if extract_to_temp:
            self._extract_zip_files_to_temp(ext_filter=ext_filter)
            print(
                f"Beginning upload process for articles in"
                f"{self.data_path}/temp/"
            )

            articles_to_update = []
            articles_to_insert = []

            if not self.article_filepaths:
                self.article_filepaths = os.listdir(f"{self.data_path}/temp/")

            total = len(self.article_filepaths)
            for i, zafp in enumerate(self.article_filepaths):
                temp_afp = f"{self.data_path}/temp/{zafp.split('/')[-1]}"

                if temp_afp.endswith('xml'):
                    parser = etree.XMLParser()
                elif temp_afp.endswith('html'):
                    # parser = etree.HTMLParser()
                    continue # skip html for now... work on parsing later

                article_tree = etree.parse(temp_afp, parser=parser)

                proceed = self._upload_file_to_mongodb(
                    article_tree,
                    temp_afp,
                    redownload=redownload
                )

                if not proceed:
                    return -1

                print(f"Downloaded {i}/{total}")

            print("\n Done!")

            for zf in self.zipfile_names:
                self.__delete_zipfile(
                    os.path.abspath(str(os.getcwd())+'/../data/'+zf)
                )
            self.__delete_tempfiles()

        else:
            self._get_article_filepaths(ext_filter=ext_filter)

            for zf in self.zipfile_names:
                print(f"Uploading articles for {zf}...")
                total = len(self.article_filepaths)
                for i, afp in enumerate(self.article_filepaths):

                    try: # try fast Zip extraction first
                        zipper = ZipFileFast(
                            f"{self.data_path}/{zf}",
                            to_extract=[filepath],
                            mode='r'
                        )
                        article_tree = self._extract_single_file_from_zip(
                            zipper,
                            zf,
                            afp,
                            extract_to_temp
                        )
                    except: # if fast extraction doesn't work just use regular
                        zipper = ZipFile(
                            f"{self.data_path}/{zf}",
                            mode='r'
                        )
                        article_tree = self._extract_single_file_from_zip(
                            zipper,
                            zf,
                            afp,
                            extract_to_temp
                        )

                    self._upload_file_to_mongodb(article_tree)

                self.__delete_zipfile(
                    os.path.abspath(str(os.getcwd())+'/../data/'+zf)
                )

        return proceed

    def count_fulltext(self, tag, ext_filter=None):
        abstract_ct = 0
        fulltext_ct = 0

        self._get_article_filepaths(ext_filter=ext_filter)

        for zf in self.zipfile_names:
            print(f"Checking fulltext for {zf}...")
            total = len(self.article_filepaths)
            for i, afp in enumerate(self.article_filepaths):
                try: # attempt fast Zip extraction first
                    zipper = ZipFileFast(
                        f"{self.data_path}/{zf}",
                        to_extract=[afp],
                        mode='r'
                    )
                    contains_fulltext = self._check_single_file_for_tag(
                        zipper,
                        tag,
                        zf,
                        afp
                    )
                except: # if it fails, just use regular Zip extraction
                    zipper = ZipFile(
                        f"{self.data_path}/{zf}",
                        mode='r'
                    )
                    contains_fulltext = self._check_single_file_for_tag(
                        zipper,
                        tag,
                        zf,
                        afp
                    )

                if not contains_fulltext:
                    abstract_ct += 1
                else:
                    fulltext_ct += 1

                print(
                    f"Checked {i}/{total} ({abstract_ct} only abstract,"
                    f"{fulltext_ct} fulltext)",
                    end='\r'
                )

            self.__delete_zipfile(
                os.path.abspath(str(os.getcwd())+'/../data/for_counting/'+zf)
            )

        return abstract_ct, fulltext_ct

if __name__ == "__main__":
    cwd = os.getcwd()
    data_path = os.path.abspath(str(cwd)+'/../data/')
    mu = MongoUploader(data_path=data_path)
    mu.run()
