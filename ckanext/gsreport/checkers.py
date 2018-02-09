#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from datetime import datetime
import urllib2
from urllib import urlopen, urlencode
from urlparse import urlparse, urlunparse, parse_qs
from functools import partial
import owslib.wms, owslib.wfs, owslib.csw, owslib.wmts
from jinja2.utils import escape
from ckan.lib.base import config
from ckan.plugins import toolkit as t


log = logging.getLogger(__name__)

SITE_URL = config['ckan.site_url']


def headers_to_str(headers):
    """
    Make headers more readable
    """
    return '\n'.join(headers)

def clean_for_markdown(val):
    """
    Escape markdown markers from raw string
    """
    return escape(val).replace('[', '\\[').replace(']', '\\]') #.replace('<', '\\[').replace('>', '\\]')

def check_url(res):
    """
    Performs a check on Resource if url provided is working correctly.

    This will use resource's .format to establish which check to run. Basic check is HTTP-level availability,
    some resource types may use more complex checks, provided in `ckanext.gsreport.checkers.check_handlers`.

    :param res: Resource to check
    :type res: ckan.model.resource.Resource instance

    :rtype:
        None, if check is successful

        dict, if check is unsuccessful (resource url is not working)

    Return dict contains following keys:
        * code - http response code
        * url - used url
        * resource_url - url in resource (may be different from url)
        * resource_name - name of resource
        * resource_format - format of resource (CSV, XML, WMS, WFS..)
        * dataset_title - title of related dataset
        * dataset_id - id of related dataset
        * dataset_url - full url to dataset in local ckan
        * checked_at - timestamp of check
        * headers - string with list of headers 
        * data - response data (first 1024 bytes)
        * msg - error message (may be exception or richer description
        * error - error name
   
    Error names describes type of error:
     * connection-error - client couldn't connect to server (dns/network problem)
     * bad-response-code - server responded with non-200 response
     * response-error - response was not correct (for example no xml when xml was expected)
     * not-valid-ows - OWS response was expected, but that failed
     * not-valid-ows-good-http - OWS response was expected, but that failed, regular http response was correct
    
    """
    log.debug('checking [%s] resource: %s from %s [%s dataset]', res.format, res.url, res.name, res.package.title)
    res_url = res.url

    # not real url, just a file name or path.
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

    # find handler or use default
    try:
        handler = check_handlers[res_format.lower()]
    except KeyError:
        handler = check_http

    resp = handler(res, res_url)
    if resp:
        out.update(resp)
        return out


# to check ows service, we must know the type
# from type, we'll get client class and list of
# defaults to detect if ows supports any known version
ows_clients = {'wms': (owslib.wms.WebMapService, (dict(version='1.1.1'),
                                       dict(version='1.3.0'))),
               'wfs': (owslib.wfs.WebFeatureService, (dict(version='1.0'),
                                                      dict(version='1.1'),
                                                      dict(version='2.0'),)),
               'csw': (owslib.csw.CatalogueServiceWeb, (dict(version=v) for v in ('2.0.0', '2.0.1', '2.0.2',)),)
               }
                            

def check_ows(res, res_url, format):
    """
    Check if resource's url is actual OWS endpoint.

    OWS endpoint will be tested if it's actual spatial service.
    If not, regular http check will be also performed. If OWS fails and HTTP works,
    that may be an indication that url is not OWS.
    """
    out = _check_ows(res, res_url, format)
    if out:
        out_http = check_http(res, res_url, return_headers=True)
        # we have invalid ows and valid http check
        # let's update it with http responses and mark with the message
        if not out_http.get('error'):
            for k in ('headers', 'code', 'data',):
                if k in out_http:
                    out[k] = out_http[k]
            out['msg'] = t._(""" ** Warning:** Resource's URL is """
                          """invalid for OWS service, however it responds """
                          """with correct HTTP response.\n\n**OWS error:** """
                          """ {}\n\n**OWS data:**\n\n {}""").format(out['error'],
                                                                     out['msg'] or '')
            out['error'] = 'not-valid-ows-good-http'
            return out

        return out_http


def _check_ows(res, res_url, format):
    """
    Perform OWS request check on resource.
    """

    out = {'code': None,
           'headers': None,
           'error': None,
           'msg': None,
           'data': None}
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
            out['error'] = 'connection-error'
            out['msg'] = clean_for_markdown(str(err))
            return out
            
        try:
            contents = client.contents
        except ServiceException, err:
            log.debug("OWS service %s is not using %s params", res_url, params)

            out['error'] = 'response-error'
            out['msg'] = clean_for_markdown(str(err))
            return out
        break
    else:
        # we iterated thourgh all defaults, and none worked,
        # endpoint doesn't accept any of them, so maybe it's not
        # an OWS endpoint
        out['error'] = 'not-valid-ows'
        out['msg'] = "Provided url doesn't work as OWS endpoint"
        return out
    return out

def check_http(res, res_url, return_headers=False):
    """
    Perform http check on resource
    """
    out = {'headers': None,
           'code': None}
    try:
        resp = urlopen(res_url)
    except IOError, err:
        log.warning('Cannot connect to %s: %s', res_url, err)
        out['msg'] = clean_for_markdown(str(err))
        out['error'] = 'connection-error'
        return out
    resp_code = resp.getcode()
    info = resp.info()
    data = resp.read(1024)
    out.update({'code': resp_code,
                'headers': headers_to_str(info.headers),
                'data': data})

    if resp_code != 200:
        out['error'] = 'bad-response-code'
        log.warning('bad response from resource: %s: %s', resp_code, data)
        return out
    if return_headers:
        return out



# res.format -> callable(resource, url)
# callable will return error dictionary if check failed
check_handlers = {'wms': partial(check_ows, format='wms'),
                  'wfs': partial(check_ows, format='wfs'),
                  'map_srvc': partial(check_ows, format='wms'),
                  }
