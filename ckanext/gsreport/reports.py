#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from datetime import datetime
from sqlalchemy import func, and_, or_
from ckan.lib.base import config
from ckan import model
import ckan.plugins.toolkit as t
from ckanext.report import lib
from ckan.common import OrderedDict
from sqlalchemy import desc
from urllib import urlopen


log = logging.getLogger(__name__)

SITE_BASE = config['ckan.site_url']

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


def check_item(res):
    """
    Performs a check on Resource if url provided is working correctly
    """
    log.debug('checking [%s] resource: %s from %s [%s dataset]', res.format, res.url, res.name, res.package.title)
    res_url = res.url

    if not res_url.startswith(('http://', 'https://')):
        res_url = '{}/{}'.format(SITE_URL, res_url.lstrip('/'))
        log.debug('rewriting url from %s to %s', res.url, res_url)

    out = {'code': None,
           'url': res_url,
           'resource_url': res.url,
           'resource_name': res.name,
           'resource_format': res.format,
           'dataset_title': res.package.title,
           'dataset_id': res.package_id,
           'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
           'headers': {},
           'data': None,
           'msg': None,
           'error': None}

    try:
        resp = urlopen(res_url)
    except IOError, err:
        log.warning('Cannot connect to %s: %s', res_url, err)
        out['msg'] = str(err)
        out['error'] = 'connection-error'
        return out
    resp_code = resp.getcode()
    info = resp.info()
    data = resp.read(1024)
    out.update({'code': resp_code,
                'headers': info.headers,
                'data': data})
    if resp_code != 200:
        out['error'] = 'bad-response-code'
        log.warning('bad response from resource: %s: %s', resp_code, data)
        return out
    if res.format.lower() in ('wms', 'wfs', 'map_srvc'):
        if '<serviceexception' in data.lower():
            out['error'] = 'bad-response-data'
            log.warning('bad response from spatial resource: %s: %s', resp_code, data)
            return out

def report_broken_links():
    s = model.Session
    R = model.Resource
    D = model.Package

    q = s.query(R, D)\
         .join(D, D.id == R.package_id)\
         .filter(and_(R.state == 'active',
                      D.state == 'active'))\
         .order_by(D.title, R.name)

    table = []
    log.info("Checking broken links for %s items", q.count())
    for item in q:
        res, dataset = item
        out = check_item(res)
        if out:
            table.append(out)

    return {'table': table,
            'number_of_formats': count}

def resources_formats():
    s = model.Session
    R = model.Resource
    q = s.query(R.format, func.count(R.format))\
         .group_by(R.format)\
         .order_by(desc(func.count(R.format)))

    count = q.count()
    table = [{'format': r[0], 'count': r[1]} for r in q]

    return {'table': table,
            'number_of_formats': count}

def all_reports():
    broken_link_info = {
        'name': 'broken-links',
        'description': t._("List datasets with resources that are non-existent or return error response"),
        'option_defaults': {},
        'generate': report_broken_links,
        'option_combinations': None,
        'template': None,
    }

    resources_format_info = {
        'name': 'resources-format',
        'description': t._("List formats used in resources"),
        'option_defaults': {},
        'generate': resources_formats,
        'option_combinations': None,
        'template': 'reports/resources_format_report.html',
    }

    licenses_info = {
        'name': 'licenses',
        'description': t._("List of licenses used"),
        'option_defaults': {},
        'generate': report_licenses,
        'option_combinations': None,
        'template': 'reports/licenses_report.html',
    }

    return [
        resources_format_info,
        broken_link_info,
        licenses_info,
        ]
