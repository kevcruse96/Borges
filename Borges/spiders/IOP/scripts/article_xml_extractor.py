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
iop_paper_col = db.collection("IOPPapers") # TODO make this more general
ecs_paper_col = db.collection("ECSPapers")

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

class ArticleXMLDataExtractor:

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

        doi_s = self.article_meta_tree.xpath(
            ".//article-id[@pub-id-type='doi']/text()"
        )
        assert len(doi_s) == 1, print(doi_s)
        self.doi = doi_s[0]


    def _get_journal_title(self):
        ## journal title
        journal_s = self.journal_meta_tree.xpath(".//journal-title/text()")

        if len(journal_s) == 0:
            journal_id_s = self.journal_meta_tree.xpath(
                ".//journal-id[@journal-id-type='publisher-id']/text()"
            )
            assert len(journal_id_s) == 1, print(doi,
                etree.tostring(self.article_tree, pretty_print=True)
            )
            self.journal_title = journal_id_s[0]
            self.notes.append(
                "Journal is [@journal-id-type='publisher-id']"

            )

        else:
            assert len(journal_s) == 1, print(doi, journal_s)
            self.journal_title = journal_s[0]

    def _get_issn(self):
        ## ISSN
        journal_issn_s = self.journal_meta_tree.xpath(
            './/issn[@pub-type="ppub"]/text()'
        )
        if not journal_issn_s:
            self.journal_issn = None
        else:
            assert len(journal_issn_s) == 1, print(doi, journal_issn_s)
            self.journal_issn = journal_issn_s[0]

        ## eISSN
        journal_eissn_s = self.journal_meta_tree.xpath(
            './/issn[@pub-type="epub"]/text()'
        )
        if not journal_eissn_s:
            self.journal_eissn = None
        else:
            assert len(journal_eissn_s) == 1, print(doi, journal_eissn_s)
            self.journal_eissn = journal_eissn_s[0]

    def _get_issue(self):
        ## Issue
        issue_s = self.article_meta_tree.xpath(
            './/issue/text()'
        )
        assert len(issue_s) == 1, print(issue_s)
        self.issue = issue_s[0]

    def _get_published_year(self):
        ## Publication year
        published_year_s = self.article_meta_tree.xpath(
            './/pub-date[@pub-type="ppub"]/year/text()'
        )

        if len(published_year_s) == 0:
            published_year_s = self.article_meta_tree.xpath(
                './/pub-date[@pub-type="epub"]/year/text()'
            )
        assert len(published_year_s) == 1, print(
            doi,
            published_year_s,
            etree.tostring(self.article_tree, pretty_print=True)
            )
        self.published_year = published_year_s[0]

    def _get_title(self):
        ## Title
        # Below is more specific, used for JPDAP, maybe general is okay?
        # title_tree_s = article_meta_tree.xpath(
        #     './/article-title[@xml:lang="en"]',
        #     namespaces={"xml": "http://www.w3.org/XML/1998/namespace"}
        # )
        title_tree_s = self.article_meta_tree.xpath(
            './/article-title'
        )
        assert len(title_tree_s) == 1, print(
            doi, [''.join(t.itertext()) for t in title_tree_s]
            )
        title_tree = etree.fromstring(etree.tostring(title_tree_s[0]))

        if title_tree.find(".//tex-math") is not None:
            etree.strip_elements(
                title_tree,
                "tex-math",
                with_tail=False
            )

        # Sometimes acknowledgements are included
        if title_tree.xpath(".//xref") is not None:
            etree.strip_elements(
                title_tree,
                "xref",
                with_tail=False
            )

        # Followup section after footnote asterisk
        if title_tree.xpath(".//fn") is not None:
            etree.strip_elements(
                title_tree,
                "fn",
                with_tail=False
            )

        self.title = ''.join(title_tree.itertext()).replace('\n','')

    def _get_authors(self):
        ## Authors
        # TODO: remove repition (can make author parsing function)
        authors_tree_s = self.article_meta_tree.xpath(
            './/contrib[@contrib-type="author"]'
        )
        self.authors = []

        for auth_tree in authors_tree_s:

            # Append cjk characters if they exist
            cjk_to_append = []

            surname_s = auth_tree.xpath(".//surname/text()")

            if not surname_s:
                continue
            else:
                for n in surname_s:
                    for c in n:
                        if self._is_cjk(c):
                            cjk_to_append.append(n)

                surname_s = [
                    s for s in surname_s if
                    s not in cjk_to_append and
                    # only include strings with letters
                    s.replace(' ', '').isalpha()
                ]
                if surname_s:
                    assert len(surname_s) == 1, print(doi, surname_s)
                    surname = surname_s[0]
                else:
                    surname = None

            given_names_s = auth_tree.xpath(".//given-names/text()")

            if given_names_s:
                for n in given_names_s:
                    for c in n:
                        if self._is_cjk(c):
                            cjk_to_append.append(n)
                            break
                given_names_s = [
                    g for g in given_names_s if
                    g not in cjk_to_append and
                    # only include strings with letters
                    g.replace(' ', '').replace('-','').isalpha()
                ]
                if given_names_s:
                    assert len(given_names_s) == 1, print(given_names_s)
                    given_names = given_names_s[0]

                else:
                    given_names = None

                if given_names and surname and not cjk_to_append:
                    self.authors.append(given_names + ' ' + surname)
                elif given_names and surname and cjk_to_append is not None:
                    self.authors.append(
                        given_names + ' ' + surname + ' ' +
                        '(' + ''.join(cjk_to_append) + ')'
                    )
                elif (
                    not given_names and
                    not surname and
                    len(cjk_to_append) != 0
                ):
                    self.authors.append(''.join(cjk_to_append))

            elif not given_names_s and surname:
                self.authors.append(surname)

            elif not given_names_s and not surname and len(cjk_to_append) != 0:
                self.authors.append(''.join(cjk_to_append))

    def _get_abstract(self):
        ## Abstract
        # Below is more specific, used for JPDAP, maybe general is okay?
        # abstract_s = article_meta_tree.xpath(
        #     './/abstract[@xml:lang="en"]',
        #     namespaces={"xml": "http://www.w3.org/XML/1998/namespace"}
        # )
        abstract_s = self.article_meta_tree.xpath(
            './/abstract'
        )

        if abstract_s:

            abstract_s_list = [
                ''.join(a.itertext()).strip() for a in abstract_s
            ]
            idxs_to_keep = []
            for idx, a in enumerate(abstract_s_list):
                if (
                    not any(t in a for t in [
                        "GENERAL SCIENTIFIC SUMMARY",
                        "General Scientific Summary",
                        "General scientific summary",
                        "General Summary",
                        "General summary",
                        "Scientific Summary",
                        "Scientific summary",
                        "Video Abstract",
                        "Video abstract",
                        "Graphical Abstract",
                        "Graphical abstract",
                        "Plain Language Summary",
                        "Plain language summary",
                        "PLAIN LANGUAGE SUMMARY"
                    ]) and
                    (
                        "Highlight" not in a or
                        "Highlight" in a and "Abstract" in a
                    ) and
                    (
                        "Figure" not in a or
                        "Figure" in a and "Abstract" in a
                    )
                ):
                    idxs_to_keep.append(idx)

            if len(idxs_to_keep) == 0:
                self.abstract = None

            else:

                assert len(idxs_to_keep) == 1, print(
                    self.doi,
                    len(abstract_s),
                    abstract_s_list
                )

                abstract_tree = abstract_s[idxs_to_keep[0]]

                if abstract_tree.find('.//title') is not None:

                    etree.strip_elements(
                        abstract_tree,
                        "title",
                        with_tail=False
                    ) # just do lxml.html.etree.strip_element for html?

                if abstract_tree.find('.//inline-formula') is not None:

                    etree.strip_elements(
                        abstract_tree,
                        "inline-formula",
                        with_tail=False
                    ) # just do lxml.html.etree.strip_element for html?

                if self.journal_title == 'Journal of The Electrochemical Society':
                    abstract_tmp = (
                        ''.join(abstract_tree.itertext()).replace('\n', '')
                    )
                    self.abstract = abstract_tmp.replace(
                        " © 2000 The Electrochemical Society. "
                        "All rights reserved.",
                        ''
                    )
                else:
                    self.abstract = ''.join(abstract_tree.itertext()).replace('\n', '')

        else:
            self.abstract = None


    def _check_for_article_body(self):
        #### Article body ######################################################

        ## Grab full html if body exists
        if self.article_tree.find(".//body") is not None:
            self.contains_body = True

            # note you are grabbing the whole html tree, not just the body
            # self.paper_content = etree.tostring(
            #     self.article_tree,
            #     encoding='UTF-8',
            #     pretty_print=True
            # ).decode()
            pass
        else:
            # self.paper_content = None
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

    def extract_article_data(self):

        self.notes = []

        ## Article metadata tree
        article_meta_tree_s = self.article_tree.xpath(".//article-meta")
        assert len(article_meta_tree_s) == 1, print(
            etree.tostring(self.article_tree, pretty_print=True)
        )
        self.article_meta_tree = article_meta_tree_s[0]

        ## Journal metadata tree
        journal_meta_tree_s = self.article_tree.xpath(".//journal-meta")
        assert len(journal_meta_tree_s) == 1, print(journal_meta_tree_s)
        self.journal_meta_tree = journal_meta_tree_s[0]

        self._get_doi()
        self._get_journal_title()
        self._get_issn()
        self._get_published_year()
        self._get_title()
        self._get_authors()
        self._get_issue()
        self._get_abstract()
        self._check_for_article_body()

        self.article_data = {
            'DOI': self.doi,
            'Publisher': "Institute of Physics",
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
