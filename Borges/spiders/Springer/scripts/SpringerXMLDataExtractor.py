import os
import re
import regex
import traceback
import argparse
from lxml import etree

from DBGater.db_singleton_mongo import SynDevAdmin

from pprint import pprint

# Only uncomment below if you want to interact with MongoDB
db = SynDevAdmin.db_access()
db.connect()
springer_paper_col = db.collection("SpringerPapers")

parser = argparse.ArgumentParser(description="Specify download requirements")

parser.add_argument(
    "--filename",
    metavar="-fn",
    type=str,
    default=None,
    help="filename of specific .xml to parse (for troubleshooting)"
)

args = parser.parse_args()


# TODO: HTML has a different format!!!

# Check out this site if you need to add any https://jrgraphix.net/r/Unicode/
cjk_characters = [
  {"from": ord(u"\u3300"), "to": ord(u"\u33ff")},         # compatibility ideographs
  {"from": ord(u"\ufe30"), "to": ord(u"\ufe4f")},         # compatibility ideographs
  {"from": ord(u"\uf900"), "to": ord(u"\ufaff")},         # compatibility ideographs
  {"from": ord(u"\U0002F800"), "to": ord(u"\U0002fa1f")}, # compatibility ideographs
  {'from': ord(u'\u3040'), 'to': ord(u'\u309f')},         # Japanese Hiragana
  {"from": ord(u"\u30a0"), "to": ord(u"\u30ff")},         # Japanese Katakana
  {"from": ord(u"\u2e80"), "to": ord(u"\u2eff")},         # cjk radicals supplement
  {"from": ord(u"\u4e00"), "to": ord(u"\u9fff")},
  {"from": ord(u"\u3400"), "to": ord(u"\u4dbf")},
  {"from": ord(u"\uac00"), "to": ord(u"\ud7af")},
  {"from": ord(u"\U00020000"), "to": ord(u"\U0002a6df")},
  {"from": ord(u"\U0002a700"), "to": ord(u"\U0002b73f")},
  {"from": ord(u"\U0002b740"), "to": ord(u"\U0002b81f")},
  {"from": ord(u"\U0002b820"), "to": ord(u"\U0002ceaf")}  # included as of Unicode 8.0
]

class SpringerXMLDataExtractor:

    def __init__(self, article_tree):
        self.article_tree = article_tree

    # This should probably be part of a different module?
    def get_existing_record(self):

        if (
            self.journal_title ==
            'Journal of The Electrochemical Society'
        ):
            paper_col = ecs_paper_col
        else:
            paper_col = iop_paper_col
        doi_regx = re.compile(self.doi, re.IGNORECASE)

        # First, see if a record exists from WoS query
        self.existing_record = paper_col.find_one(
            {'doi': doi_regx}
        )

        # If it doesn't, then see if it's already downloaded
        if self.existing_record is None:
            self.existing_record = paper_col.find_one(
                {'DOI': doi_regx}
            )
        return

    def _is_cjk(self, char):
        return any([
            range["from"] <= ord(char) <= range["to"] for
            range in cjk_characters
        ])

    def _get_doi(self):
        #### DOI ##############################################################

        doi_s = self.article_tree.xpath(
            ".//meta[@name='DOI']/@content"
        )
        if len(doi_s) == 0:
            doi_s = self.article_tree.xpath(
                ".//meta[@name='prism.doi']/@content"
            )

            # if there is still no DOI, abort
            # TODO: need to make this more elegant
            if len(doi_s) == 0:
                self.notes.append("No DOI! Aborting...")
                self.doi = None
                return

            assert len(doi_s) == 1, print(doi_s)
            self.doi = doi_s[0].split('doi:')[1]
        else:
            assert len(doi_s) == 1, print(doi_s)
            self.doi = doi_s[0]

    def _get_publisher(self):
        publisher_s = self.article_tree.xpath(
            ".//meta[@name='dc.publisher']/@content"
        )
        if len(publisher_s) == 1:
            self.publisher = publisher_s[0]
            if self.publisher != 'Springer':
                self.notes.append("Publisher not Springer")
        else:
            self.publisher = 'Springer'
            self.notes.append("Publisher inferred (from 2024 Springer upload)")


    def _get_journal_title(self):
        ## journal title
        journal_s = self.article_tree.xpath(
            ".//meta[@name='prism.publicationName']/@content"
        )
        if len(journal_s) == 1:
            self.journal_title = journal_s[0]
        else:
            self.journal_title = None


    def _get_issn(self):
        ## ISSN
        journal_issn_s = self.article_tree.xpath(
            './/meta[@name="prism.issn"]/@content'
        )
        if not journal_issn_s:
            self.journal_issn = None
        else:
            assert len(journal_issn_s) == 1, print(doi, journal_issn_s)
            self.journal_issn = journal_issn_s[0]

        self.journal_eissn = None

    def _get_issue(self):
        ## Issue
        issue_s = self.article_tree.xpath(
            ".//meta[@name='prism.number']/@content"
        )
        if len(issue_s) == 1:
            self.issue = issue_s[0]
        else:
            self.issue = None

    def _get_published_year(self):
        ## Publication year
        published_year_s = self.article_tree.xpath(
            './/meta[@name="dc.date"]/@content'
        )

        if len(published_year_s) == 1:
            self.published_year = published_year_s[0].split('-')[0]
            assert len(self.published_year) == 4 and self.published_year.isnumeric()

        # TODO: this tag exists sometimes but can't find using xpath()

        # elif len(self.article_tree.xpath(
        #     './/span[@data-test="article-publication-year"]/@content'
        # )) == 1:
        #     published_year_s = self.article_tree.xpath(
        #         './/span[@data-test="article-publication-year"]/@content'
        #     )
        #     self.published_year = published_year_s[0]
        #     assert len(self.published_year) == 4 and self.published_year.isnumeric()

        else:
            self.published_year = None


    def _get_title(self):
        ## Title
        title_s = self.article_tree.xpath(
            './/meta[@name="dc.title"]/@content'
        )

        if len(title_s) == 1:
            self.title = title_s[0]
        else:
            self.title = None

    def _get_authors(self):
        ## Authors

        authors_s = self.article_tree.xpath(
            ".//meta[@name='dc.creator']/@content"
        )

        # TODO: check if the given name / surname ordering is in-line with other publishers
        self.authors = []

        try:
            for a in authors_s:
                self.authors.append(f"{a.split(', ')[1]} {a.split(', ')[0]}")
        except Exception as e:
            self.authors = None
            self.notes.append(f"Error getting authors: {str(e)}")

    def _get_abstract(self):
        ## Abstract

        abstract_s = self.article_tree.xpath(
            './/meta[@name="dc.description"]/@content'
        )

        assert len(abstract_s) == 1, print(self.doi)

        self.abstract = str(abstract_s[0])



    def _check_for_article_body(self):
        #### Article body ######################################################

        ## Grab full html if body exists
        if self.article_tree.find(".//div[@class='main-content']") is not None:
            self.contains_body = True if len(
                self.article_tree.find(".//div[@class='main-content']")
            ) else False
            pass
        else:
            self.contains_body = False

    def _cleanup_fields(self):

        fields_to_unset = [
            "doi",
            "journal",
            "publisher",
            "published_year"
        ]
        self.article_data['_id'] = self.existing_record['_id']

        self.article_data['journal_wos'] = self.existing_record['journal']

        journal_issn_wos = self.existing_record['journal_issn']
        journal_eissn_wos = self.existing_record['journal_eissn']
        if (
            journal_issn_wos and
            self.article_data['Journal_ISSN'] != journal_issn_wos
        ):
            self.notes.append("WoS/IOP ISSN mismatch")
            self.article_data['journal_issn_wos'] = journal_issn_wos
        else:
            fields_to_unset.append('journal_issn')

        if (
            journal_eissn_wos and
            self.article_data['Journal_eISSN'] != journal_eissn_wos
        ):
            self.notes.append("WoS/IOP eISSN mismatch")
            self.article_data['journal_eissn_wos'] = journal_eissn_wos
        else:
            fields_to_unset.append('journal_eissn')

        self.article_data['Notes'] = self.notes

        return fields_to_unset

    def extract_article_data(self, check_for_existing_record=False):

        self.notes = []

        self._get_doi()

        if self.doi == None:
            return False, None

        self._get_publisher()
        self._get_journal_title()
        self._get_issn()
        self._get_issue()
        self._get_published_year()
        self._get_title()
        self._get_authors()
        self._get_abstract()
        self._check_for_article_body()

        self.article_data = {
            'DOI': self.doi,
            'Publisher': self.publisher,
            'Journal': self.journal_title,
            'Journal_ISSN': self.journal_issn,
            'Journal_eISSN': self.journal_eissn,
            'Published_Year': self.published_year,
            'Title': self.title,
            'Authors': self.authors,
            'Issue': self.issue,
            'Abstract': self.abstract,
            'Paper_Content': etree.tostring(
                self.article_tree,
                encoding='UTF-8',
                pretty_print=True
            ).decode(),
            'Contains_Body': self.contains_body,
            'Notes': self.notes
        }

        if check_for_existing_record is True:

            #### Check for existing record ########################################
            self.get_existing_record()

            if not self.existing_record:
                print("\nNo existing record in database to compare for",
                 f"{self.doi}...Creating new record")
                self.article_data['Notes'] = self.notes
                already_downloaded = False
                fields_to_unset = None

            elif 'Paper_Content' in self.existing_record.keys():
                print(f"\nAlready downloaded {self.doi}, checking for updates")
                already_downloaded = True
                fields_to_unset = None

                # Fix error fields here (should make more flexible)

                self.article_data['_id'] = self.existing_record['_id']
                self.article_data['Notes'] = self.existing_record['Notes'] + self.notes
                if 'journal_wos' in self.existing_record.keys():
                    self.article_data['journal_wos'] = self.existing_record['journal_wos']
                if 'journal_issn_wos' in self.existing_record.keys():
                    self.article_data['journal_issn_wos'] = self.existing_record['journal_issn_wos']
                if 'journal_eissn_wos' in self.existing_record.keys():
                    self.article_data['journal_eissn_wos'] = self.existing_record['journal_eissn_wos']

            else:
                print("\nExisting record found in database to compare for",
                 f"{self.doi}... Updating existing record")
                already_downloaded = False
                fields_to_unset = [
                    "doi",
                    "journal",
                    "publisher",
                    "published_year"
                ]
                self._cleanup_fields()

        else:
            already_downloaded = False
            fields_to_unset = None

        return already_downloaded, fields_to_unset


if __name__ == "__main__":
    filename = args.filename

    article_tree = etree.parse(filename)

    axde = ArticleXMLDataExtractor(article_tree)

    axde.extract_article_data()
    # already_downloaded, fields_to_unset = axde._cleanup_fields()

    axde.article_data['Paper_Content'] = axde.article_data['Paper_Content'][:5000]

    pprint(axde.article_data)
    pprint(already_downloaded)
    pprint(fields_to_unset)
