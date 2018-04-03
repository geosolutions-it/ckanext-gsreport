#!/usr/bin/env python
# -*- coding: utf-8 -*-


from ckanext.gsreport.reports import EMPTY_STRING_PLACEHOLDER

def gsreport_facets_hide_item(item):
    """
    Return False if facet item should be hidden from rendering in list
    """
    return item['name'] == EMPTY_STRING_PLACEHOLDER
