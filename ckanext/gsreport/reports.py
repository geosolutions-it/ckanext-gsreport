#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import datetime
from itertools import product
import logging
from sqlalchemy import func, and_, or_
from sqlalchemy.sql.functions import coalesce
from ckan import model
import ckan.plugins.toolkit as t
from ckanext.report import lib
from ckan.common import OrderedDict
from ckan.model.license import LicenseRegister
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
license_reg = LicenseRegister()

DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

def dformat(val):
    """
    Return timestamp as string
    """
    if isinstance(val, datetime):
        return val.strftime(DATE_FORMAT)


def _get_organizations():
    call = t.get_action('organization_list')
    orgs = call(DEFAULT_ORG_CTX, {})
    return orgs + [None]


def get_organizations():
    orgs = _get_organizations()
    return [{'organization': org} for org in orgs]

def get_formats():
    s = model.Session
    R = model.Resource
    P = model.Package
    O = model.Group

    q = s.query(coalesce(R.format, ''))\
         .join(P, P.id == R.package_id)\
         .filter(and_(R.state == 'active',
                      P.state == 'active'))\
         .group_by(coalesce(R.format, ''))
    return [item[0] for item in q] + [None]

def resources_format_options_combinations():
    formats = get_formats()
    organizations = _get_organizations()
    param_names = ('res_format', 'org',)
    
    return [ dict(zip(param_names, prod)) for prod in product(formats, organizations)]

org_options = OrderedDict({'organization': None})
resources_format_options = OrderedDict({'org': None, 'res_format': None})


def report_licenses(organization=None):
    s = model.Session
    P = model.Package
    O = model.Group
    q = s.query(coalesce(P.license_id, ''), func.count(1))\
         .filter(and_(P.state=='active',
                      P.type=='dataset'))\
         .group_by(coalesce(P.license_id, ''))\
         .order_by(desc(func.count(P.license_id)))

    if organization:
        q = q.join(O, O.id == P.owner_org).filter(O.name==organization)
    count = q.count()

    def get_license(lid):
        l = license_reg.get(r[0])
        return l.title if l else lid

    table = [{'title': get_license(r[0]), 'license': r[0], 'count': r[1]} for r in q]
    return {'table': table,
            'number_of_licenses': count}

def report_broken_links(organization=None, dataset=None):
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
    if dataset:
        q = q.filter(or_(D.name == dataset,
                         D.id == dataset,
                         D.title == dataset))

    table = []
    count = q.count()
    log. info("Checking broken links for %s items", count)
    for res in q:
        out = check_url(res)
        if out:
            table.append(out)

    return {'table': table,
            'number_of_resources': count,
            'number_of_errors': len(table)}

def resources_formats(org=None, res_format=None):
    s = model.Session
    R = model.Resource
    P = model.Package
    O = model.Group

    if res_format:

        q = s.query(O.name,
                    P.title,
                    P.id,
                    P.name,
                    P.notes,
                    coalesce(R.format, ''),
                    R.name,
                    R.url,
                    R.id,
                    R.size,
                    R.last_modified,
                    R.description,
                    R.created,
                    R.id,
                    R.state,
                    P.private
                    ,
                    )\
             .select_from(R)\
             .join(P, P.id == R.package_id)\
             .join(O, O.id == P.owner_org)\
             .filter(and_(P.state == 'active',
                          R.format==res_format))\
             .order_by(O.name, P.title, R.name)

        if org:
             q = q.filter(O.name==org)
        q_count = s.query(func.count(R.format))
        count = q.count()
        res_count = q_count.one()[0]

        table = [{'organization': {'name': r[0]},
                  'dataset': {'title': r[1],
                              'id': r[2],
                              'name': r[3],
                               'private': r[15],
                              'notes': r[4]},
                  'resource': {'format': r[5],
                               'name': r[6],
                               'url': r[7],
                               'id': r[8],
                               'size': r[9],
                               'last_modified': dformat(r[10]),
                               'description': r[11],
                               'created': dformat(r[12]),
                               'id': r[13],
                               'state': r[14],
                              }
                    } 
                  for r in q]
        options_hide = False
    else:
        q = s.query(coalesce(R.format, ''), func.count(1))\
             .join(P, P.id == R.package_id)\
             .filter(and_(R.state == 'active',
                          P.state == 'active'))\
             .group_by(coalesce(R.format, ''))\
             .order_by(desc(func.count(R.format)))
        table = [{'format': r[0], 'count': r[1]} for r in q]
        
        q_count = s.query(func.count(R.format))
        count = q.count()
        res_count = q_count.one()[0]
        options_hide = True

    return {'table': table,
            'number_of_resources': res_count,
            'organization': org,
            'options_hide': options_hide,
            'res_format': res_format,
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
        'option_defaults': resources_format_options,
        'generate': resources_formats,
        'option_combinations': resources_format_options_combinations,
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
