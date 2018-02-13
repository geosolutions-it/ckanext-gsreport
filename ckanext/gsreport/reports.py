#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from sqlalchemy import func, and_, or_
from sqlalchemy.sql.functions import coalesce
from ckan import model
import ckan.plugins.toolkit as t
from ckanext.report import lib
from ckan.common import OrderedDict
from sqlalchemy import desc

from ckanext.gsreport.checkers import check_url
log = logging.getLogger(__name__)




DEFAULT_CTX = {'ignore_auth': True}
DEFAULT_ORG_CTX = DEFAULT_CTX.copy()
DEFAULT_ORG_CTX.update(dict((k, False) for k in ('include_tags',
                                                 'include_users',
                                                 'include_groups',
                                                 'include_extras',
                                                 'include_followers',)))


def get_organizations():
    call = t.get_action('organization_list')
    orgs = call(DEFAULT_ORG_CTX, {})
    return [{'organization': org} for org in orgs]
    
org_options = OrderedDict({'organization': None})

def report_licenses(organization=None):
    s = model.Session
    P = model.Package
    O = model.Group
    q = s.query(coalesce(P.license_id, ''), func.count(P.license_id))\
         .filter(and_(P.state=='active',
                      P.type=='dataset'))\
         .group_by(coalesce(P.license_id, ''))\
         .order_by(desc(func.count(P.license_id)))

    if organization:
        q = q.join(O, O.id == P.owner_org).filter(O.name==organization)
    count = q.count()
    table = [{'license': r[0], 'count': r[1]} for r in q]
    return {'table': table,
            'number_of_licenses': count}

def report_broken_links(organization=None):
    s = model.Session
    R = model.Resource
    D = model.Package
    O = model.Group

    q = s.query(R)\
         .join(D, D.id == R.package_id)\
         .filter(and_(R.state == 'active',
                      D.state == 'active'))\
         .order_by(R.url)

    if organization:
        q = q.join(O, O.id == D.owner_org).filter(O.name==organization)

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

def resources_formats(organization=None):
    s = model.Session
    R = model.Resource
    P = model.Package
    O = model.Group

    q = s.query(coalesce(R.format, ''), func.count(R.format))\
         .join(P, P.id == R.package_id)\
         .filter(and_(R.state == 'active',
                      P.state == 'active'))\
         .group_by(coalesce(R.format, ''))\
         .order_by(desc(func.count(R.format)))

    if organization:
        if organization:
            q = q.join(O, O.id == P.owner_org).filter(O.name==organization)

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
        'option_defaults': org_options.copy(),
        'generate': report_broken_links,
        'option_combinations': get_organizations,
        'template': 'report/broken_links_report.html',
    }

    resources_format_info = {
        'name': 'resources-format',
        'description': t._("List formats used in resources"),
        'option_defaults': org_options.copy(),
        'generate': resources_formats,
        'option_combinations': get_organizations,
        'template': 'report/resources_format_report.html',
    }

    licenses_info = {
        'name': 'licenses',
        'description': t._("List of licenses used"),
        'option_defaults': org_options.copy(),
        'generate': report_licenses,
        'option_combinations': get_organizations,
        'template': 'report/licenses_report.html',
    }

    return [
        resources_format_info,
        broken_link_info,
        licenses_info,
        ]
