# ckanext-gsreport

CKAN report infrastructure.

## Purpose

This CKAN extension provides reports about resources properties. Extension uses `ckanext-report` and adds reports to dashboard at `/report`.

## Installation

This extension requires `ckanext-report` and `owslib` to be installed before using `ckanext-gsreport`.

1. Install `ckanext-report` and init db:

> $ git clone https://github.com/datagovuk/ckanext-report.git
 $ cd ckanext-report
 $ pip install -e .
 $ paster --plugin=ckanext-report report initdb --config=path/to/config.ini

2. Clone repository and install package:

> $ git clone https://github.com/geosolutions-it/ckanext-gsreport.git
 $ cd ckanext-gsreport
 $ pip install -e .

3. Add `status_reports` to plugins. **Note** Order of entries matters. This plugin should be placed **before** `report` plugin.

> ckan.plugins = .. status_reports report

4. Run solr data reindexing (license and resource format reports are using special placeholders in solr to access data without value):

> paster --plugin=ckan search-index rebuild_fast -c /path/to/config.ini

5. Run reports generation (see [Report generation] below)

After reports are generated, They can be seen in dashboard in `/report` path, for example http://localhost:5000/report

## Report generation

Report can be generated in two ways:

 * in CLI (this can be used to set up cron job):
  
   * generate all reports:

   > paster --plugin=ckanext-report report generate --config=path/to/config.ini

   * generate one report

   > paster --plugin=ckanext-report report generate $report-name --config=path/to/config.ini

 * in UI, opening `/report` url:
   * when user opens report page for the first time (with no data in report),
   * when user cliks 'refresh' button

**Warning** 
** this can take a while to produce results. Especially `broken-links` report may take significant amount of time, because it will check each resource for availability.**

**Report generation speed depends on network speed, response time from resources and number of resources to check.**

** It is recommended to run reports generation outside web process, for example with cron.** 

Also, see `ckanext-report` documentation: https://github.com/datagovuk/ckanext-report/blob/master/README.md#command-line-interface

Report, once generated, is stored in database. When new report is generated, it will replace existing data after regeneration. If report, for some reason, will fail during generation, report data from previous runs will be still available.

## Available Reports

 * `resources-format` - list of formats used in active resources

 * `licenses` - list of licenses used in active datasets

 * `broken-links` - list of links that do not work correctly (this may consume significant amount of time to generate, because each link is validated with live request).

This extension requires superuser to access reports.
