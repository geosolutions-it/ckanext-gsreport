import logging

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit

from ckanext.report.interfaces import IReport
from ckanext.gsreport.reports import all_reports, EMPTY_STRING_PLACEHOLDER

log = logging.getLogger(__name__)



def check_if_super(context, data_dict=None):
    out = {'success': False,
           'msg': ''}
    user = context.get('auth_user_obj')
    if not user:
        out['msg'] = 'User must be logged in'
        return out
    if not (user.state == 'active' and user.sysadmin):
        out['msg'] = 'Only superuser can use reports'
        return out
    out['success'] = True
    return out



class StatusReportPlugin(plugins.SingletonPlugin):
    plugins.implements(IReport)
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IAuthFunctions)
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
        res_format = list(set([r for r in res_formats if r]))
        res_formats = list(set([r or EMPTY_STRING_PLACEHOLDER for r in res_formats]))

        dataset_dict['res_format'] = res_format
        #dataset_dict['res_formats'] = res_format
        dataset_dict['license_id'] = dataset_dict.get('license_id') or EMPTY_STRING_PLACEHOLDER
        return dataset_dict

    # ------------- IAuthFunctions --------------- #
    def get_auth_functions(self):
        out = {}
        for k in ('report_list', 'report_show',
                  'report_data_get', 'report_key_get',
                  'report_refresh',):
            out[k] = check_if_super

        # monkeypatch report plugin to avoid auth functions conflict
        # in authz
        from ckanext.report.plugin import ReportPlugin
        def fake_get_auth_functions(s):
            return {}
        ReportPlugin.get_auth_functions = fake_get_auth_functions
        
        return out
