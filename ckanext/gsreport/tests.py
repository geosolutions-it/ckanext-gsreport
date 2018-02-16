#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
from ckan import model
from ckan.lib.base import config
from ckan.model.meta import Session as session
from ckan.tests.helpers import call_action, reset_db
from ckanext.report import model as report_model
from ckanext.report.report_registry import ReportRegistry


def make_pkg(idx, org, license_id, formats):
    return {'title': 'pkg {}'.format(idx),
            'name': 'pkg-{}'.format(idx),
            'license_id': license_id,
            'owner_org': org,
            'resources': [{'name': 'res {}'.format(ridx),
                           'url': 'res/{}'.format(ridx),
                           'format': f} for ridx, f in enumerate(formats)]}


class ReporTestCase(unittest.TestCase):

    def setUp(self):
        report_model.init_tables()

        self.orgs = [{'name': 'org1',
                     'licenses': ['cc-by', 'cc-by', 'cc-nd', 'other'],
                     'formats': ['pdf', 'pdf', 'doc']},
                     {'name': 'org2',
                     'licenses': ['cc-by', 'cc-nd', 'cc-nd', 'other'],
                     'formats': ['pdf', 'doc', 'doc']},
                    ]

        self.ctx = {'ignore_auth': True,
                    'model': model,
                    'session': session,
                    'user': 'user'}
        
        self.data = data = []

        user = {'name': 'user',
                'email': 'invalid@test.com',
                'password': 'pass'}
        call_action('user_create', context=self.ctx, **user)

        for org_dict in self.orgs:
            licenses = org_dict.pop('licenses')
            formats = org_dict.pop('formats')
            org = call_action('organization_create', context=self.ctx, **org_dict)
            org_id = org['id']
            org['packages'] = []
            data.append(org)
            for idx, license in enumerate(licenses):
                pkg = make_pkg(idx, org_id, license, formats)
                pkg_dict = call_action('package_create', context=self.ctx, **pkg)
                org['packages'].append(pkg_dict)
       
    def tearDown(self):
        reset_db()

    def testReports(self):
        timings = {}
        registry = ReportRegistry.instance()
        registry.refresh_cache_for_all_reports()
