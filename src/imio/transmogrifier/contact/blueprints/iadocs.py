# -*- coding: utf-8 -*-

from collective.contact.importexport.blueprints.main import ANNOTATION_KEY
from collective.contact.importexport.utils import input_error
from collective.transmogrifier.interfaces import ISection
from collective.transmogrifier.interfaces import ISectionBlueprint
from plone import api
from zope.annotation.interfaces import IAnnotations
from zope.interface import classProvides
from zope.interface import implements


class UseridUpdater(object):
    classProvides(ISectionBlueprint)
    implements(ISection)

    def __init__(self, transmogrifier, name, options, previous):
        self.previous = previous
        self.portal = transmogrifier.context
        self.storage = IAnnotations(transmogrifier).get(ANNOTATION_KEY)
        self.ids = self.storage['ids']

    def __iter__(self):
        for item in self.previous:
            if item['_type'] == 'person' and item['_ic'] and item['internal_number']:
                # for internal person, internal_number contains plone username
                if not api.user.get(username=item['internal_number']):
                    input_error(item, "username '{}' not found".format(item['internal_number']))
                else:
                    # we define the specific field
                    item['userid'] = item['internal_number']
                item['internal_number'] = None

            yield item
