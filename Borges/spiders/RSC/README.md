# Steps to scrape RCS websites:

1. Prepare two files manually to generate the issue links for each RSC journals
`start_url_gen_params_format_1.yaml` and `start_url_gen_params_format_2.yaml`. Notice two files
are of different formats to accommodate different journal issue number formats.
2. Run script `python start_url_gen.py` to generate the `start_urls.yaml` file.
3. Run command `scrapy crawl RSC -o RSC.jl` (You will first need to run a splash docker container)
4. Run script `python ../../db_scripts/insert_jl.py -i RSC.jl -c RSCPapers`
5. Run command `scrapy crawl RSC_paper`