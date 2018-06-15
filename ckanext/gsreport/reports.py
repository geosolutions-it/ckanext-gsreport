#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import datetime
from itertools import product
import logging
from sqlalchemy import func, and_, or_
from sqlalchemy.sql.functions import coalesce
from ckan import model
import ckan.plugins.toolkit as t
from ckan.common import OrderedDict
from ckan.lib.base import config
from ckan.model.license import LicenseRegister
from sqlalchemy import desc

# # for future ckan versions
# # flask-babel version used is requiring babel.support.NullTranslation (from 1.0 up)
# # which is not present in version in requirements (0.9.6)
try:
    from babel.support import NullTranslation
    from flask.ext.babel import lazy_gettext as _
except ImportError:
    from pylons.i18n import lazy_ugettext as _


from ckanext.gsreport.checkers import check_url
log = logging.getLogger(__name__)


EMPTY_STRING_PLACEHOLDER='not-specified'
DEFAULT_CTX = {'ignore_auth': True}
DEFAULT_ORG_CTX = DEFAULT_CTX.copy()
DEFAULT_ORG_CTX.update(dict((k, False) for k in ('include_tags',
                                                 'include_users',
                                                 'include_groups',
                                                 'include_extras',
                                                 'include_followers',)))
license_reg = LicenseRegister()

DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
DEFAULT_FORMAT_LIST_LIMIT = 100
FORMAT_LIST_CONFIG = "ckanext.gsreport.resource_format.format_limit"
FORMAT_LIST_LIMIT = t.asint(config.get(FORMAT_LIST_CONFIG, 
                                       DEFAULT_FORMAT_LIST_LIMIT))

def dformat(val):
    """
    Return timestamp as string
    """
    if isinstance(val, datetime):
        return val.strftime(DATE_FORMAT)


def _dict_to_row(val_in):
    """
    Translates nested dictionaries into 
      key1.subkey2, value

      list
    """
    out = []

    # keep order
    keys = sorted(val_in.keys())
    for k in keys:
        v = val_in[k]
        if not isinstance(v, dict):
            out.append((k, v,))
        else:
            sub_out = _dict_to_row(v)
            for item in sub_out:
                out.append(('{}.{}'.format(k, item[0]),
                            item[1],))
    return out


def row_dict_norm(val_in):
    return dict(_dict_to_row(val_in))

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
    return [item[0] for item in q] + [None, EMPTY_STRING_PLACEHOLDER]

def resources_format_options_combinations():
    formats = get_formats()
    organizations = _get_organizations()
    param_names = ('res_format', 'org',)
    
    return [ dict(zip(param_names, prod)) for prod in product(formats, organizations)]

def broken_links_options_combinations():
    organizations = _get_organizations()
    return [{'org': org} for org in organizations]

org_options = OrderedDict({'organization': None})
resources_format_options = OrderedDict({'org': None, 'res_format': None})
broken_links_options = OrderedDict({'org': None})


def report_licenses(organization=None):
    s = model.Session
    P = model.Package
    O = model.Group
    q = s.query(coalesce(P.license_id, ''), func.count(1))\
         .filter(and_(P.state=='active',
                      P.private == False,
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

BROKEN_LINKS_MARKER = None

def report_broken_links(org=None, dataset=None):
    """
    """
    # used in get_report_data to detect if report was
    # created within the same session
    global BROKEN_LINKS_MARKER
    if BROKEN_LINKS_MARKER is None:
        BROKEN_LINKS_MARKER = dformat(datetime.now())

    from ckanext.report.report_registry import ReportRegistry, extract_entity_name
    from ckanext.report.model import DataCache

    def get_report_data(options_dict):
        reg = ReportRegistry.instance()
        rep = reg.get_report('broken-links')

        entity_name = extract_entity_name(options_dict)
        key = rep.generate_key(options_dict)
        data, date = DataCache.get(entity_name, key, convert_json=True)
        if data['marker'] == BROKEN_LINKS_MARKER if data else False:
            return data

    def get_report_summary(data):

        out = {'total.resources': 0,
               'total.datasets': 0,
               'errors.resources': 0,
               'errors.datasets': 0,
               'errors.resources_pct': 0,
               'errors.datasets_pct': 0
               }

        for row in data:
            out['total.resources'] += row['total.resources']
            out['total.datasets'] += row['total.datasets']
            out['errors.resources'] += row['errors.resources']
            out['errors.datasets'] += row['errors.datasets']

        if out['total.resources'] > 0:
            out['errors.resources_pct'] = out['errors.resources'] * 100.0/out['total.resources']
        else:
            out['errors.resources_pct'] = 0.0
        if out['total.datasets'] > 0:
            out['errors.datasets_pct'] = out['errors.datasets'] * 100.0/out['total.datasets']
        else:
            out['errors.datasets_pct'] = 0.0
        return out

    def get_report_stats(data, org_name):
        out = {'organization': org_name}
        out.update(dict(((k,v,) for k,v in data.items() if k.startswith('total.'))))
        out.update(dict(((k,v,) for k,v in data.items() if k.startswith('errors.'))))

        if data['total.resources'] > 0:
            out['errors.resources_pct'] = data['errors.resources'] * 100.0/data['total.resources']
        else:
            out['errors.resources_pct'] = 0.0
        if data['total.datasets'] > 0:
            out['errors.datasets_pct'] = data['errors.datasets'] * 100.0/data['total.datasets']
        else:
            out['errors.datasets_pct'] = 0.0
        return out

    s = model.Session
    R = model.Resource
    D = model.Package
    O = model.Group

    if org or dataset:
        q = s.query(R)\
             .join(D, D.id == R.package_id)\
             .filter(and_(R.state == 'active',
                          D.state == 'active'))\
             .order_by(R.url)
        if org:
            q = q.join(O, O.id == D.owner_org).filter(O.name==org)
        if dataset:
            q = q.filter(or_(D.name == dataset,
                             D.id == dataset,
                             D.title == dataset))
        table = []
        count = q.count()
        log. info("Checking broken links for %s items", count)

        # we need dataset count later, in summary report
        dcount_q = s.query(D)\
                    .filter(D.state == 'active')
        if org:
            dcount_q = dcount_q.join(O, O.id == D.owner_org).filter(O.name==org)
        if dataset:
            dcount_q = dcount_q.filter(or_(D.name == dataset,
                                           D.id == dataset,
                                           D.title == dataset))
        dcount = dcount_q.count()

        # datasets with errors
        derr = set()
        for res in q:
            out = check_url(res)
            if out:
                table.append(row_dict_norm(out))
                derr.add(out['dataset_id'])

        return {'table': table,
                'organization': org,
                'dataset': dataset,
                'marker': BROKEN_LINKS_MARKER,
                'total.datasets': dcount,
                'total.resources': count,
                'errors.datasets': len(derr),
                'errors.resources': len(table),
                }
    else:
        table = []

        for org_name in _get_organizations():
            if not org_name:
                continue
            report_args = {'org': org_name, 'dataset': None}
            data = get_report_data(report_args)
            if not data:
                raise ValueError("No report previously "
                                 "cached for {}"
                                 .format(BROKEN_LINKS_MARKER))
            
            row_stats = get_report_stats(data, org_name)
            table.append(row_dict_norm(row_stats))
        out = {'table': table,
                'organization': None,
                'marker': BROKEN_LINKS_MARKER,
                }
        out.update(get_report_summary(table))
        return out

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
             .order_by(O.name, P.title, R.name)
        
        format_q = s.query(coalesce(R.format, ''))\
                    .select_from(R)\
                    .join(P, P.id == R.package_id)\
                    .join(O, O.id == P.owner_org)

        if res_format != EMPTY_STRING_PLACEHOLDER:
            q = q.filter(and_(P.state == 'active',
                              R.format==res_format))

            format_q = format_q.filter(and_(P.state == 'active',
                                            R.format==res_format))

        else:
            q = q.filter(and_(P.state == 'active',
                              R.format.in_(['', None,])))

            format_q = format_q.filter(and_(P.state == 'active',
                                            R.format.in_(['', None,])))

        if org:
             q = q.filter(O.name==org)
             format_q = format_q.filter(O.name == org)

        res_count = q.count()
        format_count = format_q.count()
        if not org:
            q = q.limit(FORMAT_LIST_LIMIT)
        table = [row_dict_norm(
                 {'organization': {'name': r[0]},
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
                    })
                  for r in q]
        options_hide = False
    else:
        q = s.query(coalesce(R.format, EMPTY_STRING_PLACEHOLDER), func.count(1))\
             .join(P, P.id == R.package_id)\
             .filter(and_(R.state == 'active',
                          P.state == 'active'))\
             .group_by(coalesce(R.format, EMPTY_STRING_PLACEHOLDER))\
             .order_by(desc(func.count(R.format)))
        table = [{'format': r[0], 'count': r[1]} for r in q]
        
        format_count = q.count()
        res_count = sum([t['count'] for t in table])
        options_hide = True

    return {'table': table,
            'organization': org,
            'options_hide': options_hide,
            'res_format': res_format,
            'number_of_resources': res_count,
            'number_of_formats': format_count}


def all_reports():
    broken_link_info = {
        'name': 'broken-links',
        'description': _(u"List datasets with resources that are non-existent or return error response"),
        'option_defaults': broken_links_options,
        'generate': report_broken_links,
        'option_combinations': broken_links_options_combinations,
        'template': 'report/broken_links_report.html',
    }

    resources_format_info = {
        'name': 'resources-format',
        'description': _(u"List formats used in resources"),
        'option_defaults': resources_format_options,
        'generate': resources_formats,
        'option_combinations': resources_format_options_combinations,
        'template': 'report/resources_format_report.html',
    }

    licenses_info = {
        'name': 'licenses',
        'description': _(u"List of licenses used"),
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
