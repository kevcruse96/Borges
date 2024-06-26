## Scraping Elsevier Papers

1. Run `scrapy crawl Elsevier_Journal -o journals.jl` to record all relevant journals
2. Run `python ../../db_scripts/insert_jl.py -i journals.jl -c ElsevierJournals` to insert all journal records into database
3. Register 4 API keys at [https://dev.elsevier.com/](https://dev.elsevier.com/), add add them to settings `ELSEVIER_API_1` to `ELSEVIER_API_4` variables
4. Run `python paper_index.py -n <N>` to index all Elsevier relevant papers in the database, where `<N>` is the API (1-4).
5. (No longer necessary, scraping flag set in paper_index.py) Run `python ../db_scripts/add_paper_scraped_flag.py -c ElsevierPapers` to add scraping flag to all papers.
6. Run `python paper_xml.py` to scrape all paper xmls in the database.