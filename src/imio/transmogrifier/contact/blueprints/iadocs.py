# -*- coding: utf-8 -*-

from collective.contact.importexport.blueprints.main import ANNOTATION_KEY
from collective.contact.importexport.utils import input_error
from collective.transmogrifier.interfaces import ISection
from collective.transmogrifier.interfaces import ISectionBlueprint
from plone import api
from Products.CMFPlone.utils import safe_unicode
from zope.annotation.interfaces import IAnnotations
from zope.interface import classProvides
from zope.interface import implements


class UseridInserter(object):
    """Adds userid key on internal person with internal_number column value."""
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


class CreatingGroupInserter(object):
    """Adds creating_group key following given org title.

    Parameters:
        * creating_group = M, creating group title value set for imported contacts.
    """
    classProvides(ISectionBlueprint)
    implements(ISection)

    def __init__(self, transmogrifier, name, options, previous):
        self.previous = previous
        self.portal = transmogrifier.context
        self.storage = IAnnotations(transmogrifier).get(ANNOTATION_KEY)
        self.ids = self.storage['ids']
        creating_group = safe_unicode(options.get('creating_group', '').strip())
        if not creating_group:
            raise Exception(u'{}: You have to set creating_group value in this section !'.format(name))
        reg = api.portal.get_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig.contact_group_encoder')
        if not reg:
            raise Exception(u'{}: You have to activate the contact creating group option in iadocs config'.format(name))
        # get imio.dms.mail.ActiveCreatingGroupVocabulary
        from imio.dms.mail.vocabularies import ActiveCreatingGroupVocabulary
        voc = ActiveCreatingGroupVocabulary()(self.portal)
        creating_groups = {term.title: term.value for term in voc}
        if creating_group not in creating_groups:
            raise Exception(u"{}: given creating_group '{}' isn't an active creating group organization".format(
                            name, creating_group))
        self.creating_org = creating_groups[creating_group]

    def __iter__(self):
        for item in self.previous:
            item['creating_group'] = self.creating_org
            yield item


class InbwSubtitleUpdater(object):
    """Updates title field with _service field value."""
    classProvides(ISectionBlueprint)
    implements(ISection)

    def __init__(self, transmogrifier, name, options, previous):
        self.previous = previous
        self.portal = transmogrifier.context
        self.storage = IAnnotations(transmogrifier).get(ANNOTATION_KEY)
        self.ids = self.storage['ids']
        self.fieldnames = self.storage['fieldnames']
        if '_service' not in self.fieldnames['organization']:
            raise Exception(u"{}: '_service' field is not defined in fieldnames".format(name))

    def __iter__(self):
        for item in self.previous:
            if item['_type'] == 'organization' and item['_service']:
                if item['_service'].startswith('c/o'):
                    item['title'] += u' {}'.format(item['_service'])
                else:
                    item['title'] += u' ,% {}'.format(item['_service'])
            yield item
