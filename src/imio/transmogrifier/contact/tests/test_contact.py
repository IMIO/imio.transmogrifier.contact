# -*- coding: utf-8 -*-
from collective.contact.plonegroup.config import PLONEGROUP_ORG
from collective.transmogrifier.interfaces import ISectionBlueprint
from imio.transmogrifier.contact.blueprints.contact import PlonegroupInternalParent
from imio.transmogrifier.contact.blueprints.contact import PlonegroupOrganizationPath
from imio.transmogrifier.contact.testing import BaseTestCase
from zope.component import getUtility


class TestPlonegroupOrganizationPath(BaseTestCase):

    def test___init__(self):
        self.assertIs(getUtility(ISectionBlueprint, 'imio.transmogrifier.contact.plonegrouporganizationpath'),
                      PlonegroupOrganizationPath)
        section = self.section(PlonegroupOrganizationPath)
        self.assertEqual((section.pgo_title, section.pgo_id), (u'', PLONEGROUP_ORG))
        self.assertEqual(section.directory_path, 'mydirectory')
        self.assertIs(section.ids, self.storage['ids'])
        section = self.section(PlonegroupOrganizationPath, plonegroup_org_title=' Mon CPAS ',
                               plonegroup_org_id=' cpas ')
        self.assertEqual((section.pgo_title, section.pgo_id), (u'Mon CPAS', u'cpas'))

    def test___iter__(self):
        self.storage['ids']['organization']['set1']['1'] = {'path': 'mydirectory/1'}
        items = [self.item('organization', title=u'Mon CPAS'),
                 self.item('organization', _id='2', title=u'Autre'),
                 self.item('person', lastname=u'Mon CPAS')]
        items = list(self.section(PlonegroupOrganizationPath, items, plonegroup_org_title='Mon CPAS'))
        self.assertEqual(items[0], self.item('organization', title=u'Mon CPAS', _act='update', use_parent_address=False,
                                             _path='mydirectory/plonegroup-organization'))
        self.assertEqual(self.storage['ids']['organization']['set1']['1'],
                         {'path': 'mydirectory/plonegroup-organization'})
        self.assertEqual(items[1:], [self.item('organization', _id='2', title=u'Autre'),
                                     self.item('person', lastname=u'Mon CPAS')])
        # no title option: nothing changed
        items = list(self.section(PlonegroupOrganizationPath, [self.item('organization', title=u'')]))
        self.assertEqual(items, [self.item('organization', title=u'')])


class TestPlonegroupInternalParent(BaseTestCase):

    def test___init__(self):
        self.assertIs(getUtility(ISectionBlueprint, 'imio.transmogrifier.contact.plonegroupinternalparent'),
                      PlonegroupInternalParent)
        section = self.section(PlonegroupInternalParent)
        self.assertEqual((section.internal_fld, section.pgo_id, section.pgp_id),
                         (u'_ic', PLONEGROUP_ORG, u'personnel-folder'))
        self.assertEqual(section.directory_path, 'mydirectory')
        section = self.section(PlonegroupInternalParent, internal_field=' _int ', plonegroup_org_id=' org ',
                               plonegroup_pers_id=' pers ')
        self.assertEqual((section.internal_fld, section.pgo_id, section.pgp_id), (u'_int', u'org', u'pers'))

    def test___iter__(self):
        items = [self.item('organization', _ic=True), self.item('person', _ic=True),
                 self.item('held_position', _ic=True), self.item('organization', _ic=False),
                 self.item('person')]
        items = list(self.section(PlonegroupInternalParent, items))
        self.assertEqual([item.get('_parent') for item in items],
                         ['mydirectory/plonegroup-organization', 'mydirectory/personnel-folder', None, None, None])
        # other internal field and plonegroup ids
        items = [self.item('organization', _int=True), self.item('person', _int=True), self.item('person', _ic=True)]
        items = list(self.section(PlonegroupInternalParent, items, internal_field='_int', plonegroup_org_id='org',
                                  plonegroup_pers_id='pers'))
        self.assertEqual([item.get('_parent') for item in items], ['mydirectory/org', 'mydirectory/pers', None])
