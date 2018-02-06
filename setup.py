from setuptools import setup, find_packages
import sys, os

version = '0.1'

setup(
    name='ckanext-gsreport',
    version=version,
    description="Extension provides useful status reports",
    long_description='''
    ''',
    classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    keywords='',
    author='Cezary Statkiewicz',
    author_email='cezary.statkiewicz@geo-solutions.it',
    url='http://www.geo-solutions.it/',
    license='',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    namespace_packages=['ckanext', 'ckanext.gsreport'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        # -*- Extra requirements: -*-
    ],
    entry_points='''
        [ckan.plugins]
        status_reports=ckanext.gsreport.plugin:StatusReportPlugin

        [babel.extractors]
        ckan = ckan.lib.extract:extract_ckan

        [nose.plugins]
        main = ckan.ckan_nose_plugin:CkanNose
    ''',

    # Translations
    message_extractors={
        'ckanext': [
            ('**.py', 'python', None),
            ('**.js', 'javascript', None),
            ('**/templates/**.html', 'ckan', None),
        ],
    }
)
