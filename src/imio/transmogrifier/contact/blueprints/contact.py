# -*- coding: utf-8 -*-

from collective.contact.importexport.blueprints.main import ANNOTATION_KEY
from collective.contact.plonegroup.config import PLONEGROUP_ORG
from collective.transmogrifier.interfaces import ISection
from collective.transmogrifier.interfaces import ISectionBlueprint
from Products.CMFPlone.utils import safe_unicode
from zope.annotation.interfaces import IAnnotations
from zope.interface import classProvides
from zope.interface import implements

import os


class PlonegroupOrganizationPath(object):
    """Searches input item with plonegroup_org_title value and updates existing plonegroup_org_id object
    with corresponding item values.

    Parameters:
        * plonegroup_org_title = M, organization title to search.
        * plonegroup_org_id = O, plonegroup organization id. Default: plonegroup-organization.
    """
    classProvides(ISectionBlueprint)
    implements(ISection)

    def __init__(self, transmogrifier, name, options, previous):
        self.pgo_title = safe_unicode(options.get('plonegroup_org_title', '')).strip()
        self.pgo_id = safe_unicode(options.get('plonegroup_org_id', PLONEGROUP_ORG).strip())
        self.previous = previous
        self.storage = IAnnotations(transmogrifier).get(ANNOTATION_KEY)
        self.directory_path = self.storage['directory_path']
        self.ids = self.storage['ids']

    def __iter__(self):
        for item in self.previous:
            if self.pgo_title and item['_type'] == 'organization' and self.pgo_title == item['title']:
                item['_path'] = os.path.join(self.directory_path, self.pgo_id)
                self.ids['organization'][item['_set']][item['_id']]['path'] = item['_path']
                item['_act'] = 'update'
                item['use_parent_address'] = False
            yield item


class PlonegroupInternalParent(object):
    """Sets _parent key of internal contacts to store items at the right place.

    Parameters:
        * internal_field = O, internal field name. Default: _ic.
        * plonegroup_org_id = O, plonegroup organization id. Default: plonegroup-organization.
        * plonegroup_pers_id = O, plonegroup personnel folder id. Default: personnel-folder.
    """
    classProvides(ISectionBlueprint)
    implements(ISection)

    def __init__(self, transmogrifier, name, options, previous):
        self.internal_fld = safe_unicode(options.get('internal_field', '_ic').strip())
        self.pgo_id = safe_unicode(options.get('plonegroup_org_id', PLONEGROUP_ORG).strip())
        self.pgp_id = safe_unicode(options.get('plonegroup_pers_id', 'personnel-folder').strip())
        self.previous = previous
        self.storage = IAnnotations(transmogrifier).get(ANNOTATION_KEY)
        self.directory_path = self.storage['directory_path']

    def __iter__(self):
        for item in self.previous:
            if item.get(self.internal_fld, False):
                if item['_type'] == 'organization':
                    item['_parent'] = os.path.join(self.directory_path, self.pgo_id)
                elif item['_type'] == 'person':
                    item['_parent'] = os.path.join(self.directory_path, self.pgp_id)
            yield item
