# -*- coding: utf-8 -*-
from collective.contact.importexport import e_logger
from imio.transmogrifier.contact.testing import BaseTestCase
from imio.transmogrifier.contact.utils import replace_relation
from logging.handlers import BufferingHandler
from plone import api
from z3c.relationfield import RelationValue
from zc.relation.interfaces import ICatalog
from zope.component import getUtility
from zope.intid.interfaces import IIntIds
from zope.lifecycleevent import modified


class TestUtils(BaseTestCase):

    def test_replace_relation(self):
        intids = getUtility(IIntIds)
        catalog = getUtility(ICatalog)
        directory = self.portal['mydirectory']
        degaulle, pepper, corpsb = directory['degaulle'], directory['pepper'], directory['armeedeterre']['corpsb']
        item = self.item('organization')
        # single relation (held position position)
        hp = directory['draper']['divisionbeta']
        [rel] = catalog.findRelations({'from_id': intids.getId(hp)})
        replace_relation(item, self.portal, catalog, rel, field='position', repl_iid=intids.getId(corpsb))
        self.assertEqual(hp.position.to_object, corpsb)
        self.assertEqual([value.from_object for value in catalog.findRelations({'to_id': intids.getId(corpsb)})], [hp])
        # list of relations: the replaced one is removed, the new one appended
        om = api.content.create(container=self.portal, type='dmsoutgoingmail', id='om',
                                recipients=[RelationValue(intids.getId(degaulle)), RelationValue(intids.getId(pepper))])
        [rel] = catalog.findRelations({'to_id': intids.getId(degaulle)})
        replace_relation(item, self.portal, catalog, rel, field='recipients', repl_iid=intids.getId(corpsb))
        self.assertEqual([value.to_object for value in om.recipients], [pepper, corpsb])
        # tuple of relations: becomes a list
        om.recipients = (RelationValue(intids.getId(degaulle)), )
        modified(om)
        [rel] = catalog.findRelations({'to_id': intids.getId(degaulle)})
        replace_relation(item, self.portal, catalog, rel, field='recipients', repl_iid=intids.getId(pepper))
        self.assertEqual([value.to_object for value in om.recipients], [pepper])
        self.assertNotIn('_error', item)
        # linked object not found (relation to a deleted contact): logged and relation unindexed
        api.content.delete(obj=pepper, check_linkintegrity=False)
        [rel] = catalog.findRelations({'from_id': intids.getId(om)})
        self.assertIsNone(rel.to_object)
        rel.broken('/plone/mydirectory/pepper')  # path lost by z3c.relationfield breakRelations on Plone 4.3
        handler = BufferingHandler(10)
        e_logger.addHandler(handler)
        self.addCleanup(e_logger.removeHandler, handler)
        # Plone 4 bug: AttributeError with the portal_catalog given by InbwMerger
        self.assertRaises(AttributeError, replace_relation, item, self.portal, self.portal.portal_catalog, rel,
                          path='to_path', field='recipients', repl_iid=intids.getId(corpsb))
        replace_relation(item, self.portal, catalog, rel, path='to_path', field='recipients',
                         repl_iid=intids.getId(corpsb))
        self.assertEqual(list(catalog.findRelations({'from_id': intids.getId(om)})), [])
        self.assertTrue(item['_error'])
        # Plone 4 bug: the logged path is always from_path
        self.assertEqual([record.getMessage() for record in handler.buffer],
                         [u'set1: O, ln 2, cannot find linked object: /plone/om'] * 2)
