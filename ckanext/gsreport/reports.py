#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from sqlalchemy import func, and_, or_
from ckan import model
import ckan.plugins.toolkit as t
from ckanext.report import lib
from ckan.common import OrderedDict
from sqlalchemy import desc

from ckanext.gsreport.checkers import check_url
log = logging.getLogger(__name__)

def report_licenses():
    s = model.Session
    P = model.Package
    q = s.query(P.license_id, func.count(P.license_id))\
         .group_by(P.license_id)\
         .order_by(desc(func.count(P.license_id)))

    count = q.count()
    table = [{'license': r[0], 'count': r[1]} for r in q]

    return {'table': table,
            'number_of_licenses': count}

def report_broken_links():
    s = model.Session
    R = model.Resource
    D = model.Package

    q = s.query(R)\
         .join(D, D.id == R.package_id)\
         .filter(and_(R.state == 'active',
                      D.state == 'active'))\
         .order_by(R.url)

    table = []
    count = q.count()
    log.info("Checking broken links for %s items", count)
    for res in q:
        out = check_url(res)
        if out:
            table.append(out)

    return {'table': table,
            'number_of_resources': count,
            'number_of_errors': len(table)}

def resources_formats():
    s = model.Session
    R = model.Resource
    q = s.query(R.format, func.count(R.format))\
         .group_by(R.format)\
         .order_by(desc(func.count(R.format)))

    q_count = s.query(func.count(R.format))

    count = q.count()
    res_count = q_count.one()[0]
    table = [{'format': r[0], 'count': r[1]} for r in q]

    return {'table': table,
            'number_of_resources': res_count,
            'number_of_formats': count}

def all_reports():
    broken_link_info = {
        'name': 'broken-links',
        'description': t._("List datasets with resources that are non-existent or return error response"),
        'option_defaults': {},
        'generate': report_broken_links,
        'option_combinations': None,
        'template': 'report/broken_links_report.html',
    }

    resources_format_info = {
        'name': 'resources-format',
        'description': t._("List formats used in resources"),
        'option_defaults': {},
        'generate': resources_formats,
        'option_combinations': None,
        'template': 'report/resources_format_report.html',
    }

    licenses_info = {
        'name': 'licenses',
        'description': t._("List of licenses used"),
        'option_defaults': {},
        'generate': report_licenses,
        'option_combinations': None,
        'template': 'report/licenses_report.html',
    }

    return [
        resources_format_info,
        broken_link_info,
        licenses_info,
        ]
