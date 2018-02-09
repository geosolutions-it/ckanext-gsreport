#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from datetime import datetime
import urllib2
from urllib import urlopen, urlencode
from urlparse import urlparse, urlunparse, parse_qs
from functools import partial
import owslib.wms, owslib.wfs, owslib.csw, owslib.wmts
from ckan.lib.base import config


log = logging.getLogger(__name__)

SITE_URL = config['ckan.site_url']


def check_url(res):
    """
    Performs a check on Resource if url provided is working correctly
    """
    log.debug('checking [%s] resource: %s from %s [%s dataset]', res.format, res.url, res.name, res.package.title)
    res_url = res.url

    if not res_url.startswith(('http://', 'https://')):
        res_url = '{}/{}'.format(SITE_URL, res_url.lstrip('/'))
        log.debug('rewriting url from %s to %s', res.url, res_url)

    res_format = res.format

    out = {'code': None,
           'url': res_url,
           'resource_url': res.url,
           'resource_name': res.name,
           'resource_format': res.format,
           'dataset_title': res.package.title,
           'dataset_id': res.package_id,
           'dataset_url': '{}/dataset/{}'.format(SITE_URL, res.package.name),
           'checked_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
           'headers': {},
           'data': None,
           'msg': None,
           'error': None}

    try:
        handler = check_handlers[res_format.lower()]
    except KeyError:
        handler = check_http

    resp = handler(res, res_url)
    if resp:
        out.update(resp)
        return out


ows_clients = {'wms': (owslib.wms.WebMapService, (dict(version='1.1.1'),
                                       dict(version='1.3.0'))),
               'wfs': (owslib.wfs.WebFeatureService, (dict(version='1.0'),
                                                      dict(version='1.1'),
                                                      dict(version='2.0'),)),
               'csw': (owslib.csw.CatalogueServiceWeb, (dict(version=v) for v in ('2.0.0', '2.0.1', '2.0.2',)),)
               }
                            

def check_ows(res, res_url, format):
    out = _check_ows(res, res_url, format)
    if out:
        out_http = check_http(res, res_url)
        return out_http or out


def _check_ows(res, res_url, format):
    if format in ('map_srvc'):
        format = 'wms'
    client_cls, defaults = ows_clients[format]
    url = urlparse(res_url)
    in_params = parse_qs(url.query)
    normalized = dict((k.lower(), v) for k, v in in_params.items())

    # if we have forced version in params, we'll use it instead of versions from defaults
    if 'version' in normalized:
        defaults = (in_params,)

    for params in defaults:
        # replace query in url
        new_url = urlunparse(url[:4] + (urlencode(params, True),) + url[5:])
        try:
            client = client_cls(new_url)
        # bad version will cause Attr error
        except AttributeError:
            log.debug("OWS service %s is not using %s params", res_url, params)
            continue
        except urllib2.URLError, err:
            return {'code': None,
                    'headers': None,
                    'error': 'connection-error',
                    'msg': str(err),
                    'data': None}
            
        try:
            contents = client.contents
        except ServiceException, err:

            log.debug("OWS service %s is not using %s params", res_url, params)
            return {'code': None,
                    'headers': None,
                    'error': 'response-error',
                    'msg': str(err),
                    'data': None}

def check_http(res, res_url):
    out = {}
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

# res.format -> callable(resource, url)
# callable will return error dictionary if check failed
check_handlers = {'wms': partial(check_ows, format='wms'),
                  'wfs': partial(check_ows, format='wfs'),
                  'map_srvc': partial(check_ows, format='wms'),
                  }
