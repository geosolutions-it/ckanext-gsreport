# ckanext-gsreport

CKAN report infrastructure

## Purpose

This CKAN extension provides reports about resources properties. Extension uses `ckanext-report` and adds reports to dashboard at `/report`.

## Installation

This extension requires `ckanext-report` and `owslib` to be installed before using `ckanext-gsreport`.

1. Clone repository and install package:

> $ git clone https://github.com/geosolutions-it/ckanext-gsreport.git
 $ cd ckanext-gsreport
 $ pip install -e .

2. Add `status_reports` to plugins. **Note** Order of entries matters. This plugin should be placed **before** `report` plugin.

> ckan.plugins = .. status_reports report

3. Run reports generation. 

> paster --plugin=ckanext-report report generate --config=<path to config.ini>

**Warning** this can take a while to produce results. Especially `broken-links` report may take significant amount of time, because it will check each resource for availability. It is recommended to run reports generation outside web process, for example with cron.

After reports are generated, They can be seen in dashboard in `/report` path, for example http://localhost:5000/report.
