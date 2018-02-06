import logging

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit

from ckanext.report.interfaces import IReport
from ckanext.gsreport.reports import all_reports

log = logging.getLogger(__name__)




class StatusReportPlugin(plugins.SingletonPlugin):
    plugins.implements(IReport)
    plugins.implements(plugins.IConfigurer)

    # ------------- IConfigurer ---------------#

    def update_config(self, config):
        toolkit.add_template_directory(config, 'templates')
        toolkit.add_public_directory(config, 'public')
        toolkit.add_resource('fanstatic', 'ckanext-gsreport')

    # ------------- IReport ---------------#

    def register_reports(self):
        return all_reports()

