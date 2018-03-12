from ckan.lib import helpers
from ckan.lib.base import config
from routes import request_config


ufunc = helpers.url_for

# monkey-patching helpers.url_for
# see https://github.com/geosolutions-it/ckanext-provbz/issues/20#issuecomment-366279774
# see https://github.com/ckan/ckan/issues/3499
# see https://github.com/ckan/ckan/pull/3749
def url_for(*args, **kwargs):

    def _local(_u):
        return '{}/{}'.format(config['ckan.site_url'],
                              _u.lstrip('/'))
    
    if len(args) == 1 and isinstance(args[0], basestring):
        u = args[0]
        if u.startswith('/'):
            return _local(u)
        mapper = request_config().mapper
        if not mapper.routematch(u):
            return _local(u)
    return ufunc(*args, **kwargs)

helpers.url_for = url_for
