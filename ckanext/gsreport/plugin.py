import logging

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit

from ckanext.report.interfaces import IReport
from ckanext.gsreport.reports import all_reports

log = logging.getLogger(__name__)


EMPTY_STRING_PLACEHOLDER='not-specified'

class StatusReportPlugin(plugins.SingletonPlugin):
    plugins.implements(IReport)
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IPackageController, inherit=True)

    # ------------- IConfigurer ---------------#

    def update_config(self, config):
        toolkit.add_template_directory(config, 'templates')
        toolkit.add_public_directory(config, 'public')
        toolkit.add_resource('fanstatic', 'ckanext-gsreport')

    # ------------- IReport ---------------#

    def register_reports(self):
        return all_reports()

    def before_index(self, dataset_dict):
        # replace empty strings in res_format and license_id to EMPTY_STRING_PLACEHOLDER
        res_formats = dataset_dict.get('res_format') or []
        res_formats = list(set([r or EMPTY_STRING_PLACEHOLDER for r in res_formats]))
        dataset_dict['res_format'] = res_formats
        dataset_dict['license_id'] = dataset_dict['license_id'] or EMPTY_STRING_PLACEHOLDER
        return dataset_dict
