# -*- coding: utf-8 -*-

from collective.contact.importexport.blueprints.main import ANNOTATION_KEY
from collective.contact.importexport.utils import input_error
from collective.transmogrifier.interfaces import ISection
from collective.transmogrifier.interfaces import ISectionBlueprint
from imio.transmogrifier.contact.utils import replace_relation
from plone import api
from Products.CMFPlone.utils import safe_unicode
from zc.relation.interfaces import ICatalog
from zope.annotation.interfaces import IAnnotations
from zope.component import queryUtility
from zope.interface import classProvides
from zope.interface import implements
from zope.intid import IIntIds


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


class InbwMerger(object):
    """Replaces a contact with another one. "_merger column" is used to indicate the replacing internal number.

    Parameters:
        * raise = O, raise Exception if a problematic error happens. Default = 1.
    """
    classProvides(ISectionBlueprint)
    implements(ISection)

    def __init__(self, transmogrifier, name, options, previous):
        self.previous = previous
        self.portal = transmogrifier.context
        self.catalog = self.portal.portal_catalog
        self.rel_catalog = queryUtility(ICatalog)
        self.intids = queryUtility(IIntIds)
        self.storage = IAnnotations(transmogrifier).get(ANNOTATION_KEY)
        self.fieldnames = self.storage['fieldnames']
        self.ids = self.storage['ids']
        if '_merger' not in self.fieldnames['organization']:
            raise Exception(u"{}: '_merger' field is not defined in fieldnames".format(name))
        self.must_raise = bool(options.get('raise', '0'))

    def __iter__(self):  # noqa
        for item in self.previous:
            if item['_merger']:
                # checking current contact
                current_obj = self.portal.unrestrictedTraverse(item['_path'], default=None)
                if current_obj is None:
                    input_error(item, "Cannot find main object with path '{}' and act '{}'".format(item['_path'],
                                                                                                   item['_act']))
                current_iid = self.intids.queryId(current_obj)
                if current_iid is None:
                    input_error(item, u"cannot find current object intid: {}".format(current_obj))
                    if self.must_raise:
                        raise Exception("Cannot find current object intid '{}'".format(current_obj))

                # searching replacement object
                brains = self.catalog.unrestrictedSearchResults({'portal_type': item['_type'],
                                                                 'internal_number': item['_merger']})
                if len(brains) > 1:
                    input_error(item, u"the search with 'internal_number'='{}' gets multiple objs: {}".format(
                        item['_merger'], u', '.join([b.getPath() for b in brains])))
                    if self.must_raise:
                        raise Exception("Find multiple objects with internal number '{}'".format(item['_merger']))
                elif not brains:
                    input_error(item, u"the search with 'internal_number'='{}' doesn't "
                                      u"get any result".format(item['_merger']))
                    if self.must_raise:
                        raise Exception("Cannot find object with internal number '{}'".format(item['_merger']))
                repl_obj = brains[0].getObject()
                repl_iid = self.intids.getId(repl_obj)
                if repl_iid is None:
                    input_error(item, u"cannot find replacement object intid: {}".format(repl_obj))
                    if self.must_raise:
                        raise Exception("Cannot find replacement object intid '{}'".format(repl_obj))

                # getting relations pointing to current object
                rels = list(self.rel_catalog.findRelations({'to_id': current_iid}))
                for rel in rels:
                    if rel.from_object.portal_type in ('dmsincomingmail', 'dmsincoming_email') and \
                            rel.from_attribute == 'sender':
                        replace_relation(item, self.portal, self.catalog, rel,
                                         path='from_path', field='sender', repl_iid=repl_iid)
                    elif rel.from_object.portal_type == 'dmsoutgoingmail' and rel.from_attribute == 'recipients':
                        replace_relation(item, self.portal, self.catalog, rel,
                                         path='from_path', field='recipients', repl_iid=repl_iid)
                    elif rel.from_object.portal_type == 'held_position' and rel.from_attribute == 'position':
                        replace_relation(item, self.portal, self.catalog, rel,
                                         path='from_path', field='position', repl_iid=repl_iid)
                    elif rel.from_object.portal_type == 'contact_list' and rel.from_attribute == 'contacts':
                        replace_relation(item, self.portal, self.catalog, rel,
                                         path='from_path', field='contacts', repl_iid=repl_iid)
                    else:
                        input_error(item, u"relation type not handled! pt '{}', field '{}'".format(
                            rel.from_object.portal_type, rel.from_attribute))
                        if self.must_raise:
                            raise Exception("Relation type not handled! pt '{}', field '{}'".format(
                                rel.from_object.portal_type, rel.from_attribute))
                # getting relations pointing to current object
                rels = list(self.rel_catalog.findRelations({'from_id': current_iid}))
                if rels:
                    input_error(item, u"relation from_id not handled! to paths '{}'".format(
                        ', '.join([rel.to_path for rel in rels])))
                    if self.must_raise:
                        raise Exception(u"relation from_id not handled! to paths '{}'".format(
                            ', '.join([rel.to_path for rel in rels])))
                # deleting current obj
                api.content.delete(obj=current_obj)
                item['_act'] = 'delete'
                # cleaning item
                item['_del_path'] = item.pop('_path')  # we remove the path so all others sections are skipped
            yield item
