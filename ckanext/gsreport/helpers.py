#!/usr/bin/env python
# -*- coding: utf-8 -*-

from beaker.cache import CacheManager

from ckan.plugins import toolkit as t
from ckan.lib.i18n import get_lang
from ckanext.gsreport.reports import EMPTY_STRING_PLACEHOLDER

try:
    from ckanext.multilang.model.package_multilang import GroupMultilang, PackageMultilang
except ImportError, err:
    GroupMultilang = PackageMultilang = None

try:
    from ckan.common import config
except ImportError:
    from pylons import config

DEFAULT_LANG = config.get('ckan.locale_default', 'en')

cache = CacheManager(type='memory')


def facets_hide_item(item):
    """
    Return False if facet item should be hidden from rendering in list
    """
    return item['name'] == EMPTY_STRING_PLACEHOLDER


def get_organizations():
    """
    Return list of tuples with (org name, org title) with localized names
    """
    org_list = t.get_action('organization_list')
    ctx = {'for_view': True,
           'user_is_admin': True,
           'metadata_modified': '',
           'with_private': True}

    data_dict = {'all_fields': True,
                 'include_dataset_count': False}

    for org in org_list(ctx, data_dict):
        yield (org['name'], org['title'],)

@cache.cache('localized_org_title', expire=30)
def get_localized_org_title(org_name, lang):
    """
    Returns localized organization title if possible.
    """
    if GroupMultilang is not None:

        g = GroupMultilang.get_for_group_name_and_lang(org_name, lang)
        if not g:
            g = GroupMultilang.get_for_group_name_and_lang(org_name, DEFAULT_LANG)
        for row in g:
            if row.field == 'title':
                return row.text

@cache.cache('localized_pkg_title', expire=30)
def get_localized_pkg_title(pkg_id, lang):
    """
    Returns localized organization title if possible.
    """
    field_type = 'package'
    if PackageMultilang is not None:
        g = PackageMultilang.get(pkg_id, 'title', lang, field_type)
        if not g:
            g = PackageMultilang.get(pkg_id, 'title', DEFAULT_LANG, field_type)
        if g:
            return g.text
