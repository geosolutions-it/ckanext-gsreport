#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ckan.plugins import toolkit as t
from ckanext.gsreport.reports import EMPTY_STRING_PLACEHOLDER

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
