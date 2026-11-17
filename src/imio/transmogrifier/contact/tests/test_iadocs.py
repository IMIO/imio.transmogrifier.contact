from collective.transmogrifier.interfaces import ISectionBlueprint
from imio.transmogrifier.contact.blueprints.iadocs import CreatingGroupInserter
from imio.transmogrifier.contact.blueprints.iadocs import InbwMerger
from imio.transmogrifier.contact.blueprints.iadocs import InbwSubtitleUpdater
from imio.transmogrifier.contact.blueprints.iadocs import UseridInserter
from imio.transmogrifier.contact.testing import BaseTestCase
from plone import api
from plone.api.exc import InvalidParameterError
from plone.api.exc import MissingParameterError
from plone.registry import field
from plone.registry.interfaces import IRegistry
from plone.registry.record import Record
from types import ModuleType
from z3c.relationfield import RelationValue
from zc.relation.interfaces import ICatalog
from zope.component import getUtility
from zope.intid.interfaces import IIntIds
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary

import sys


ENCODER = "imio.dms.mail.browser.settings.IImioDmsMailConfig.contact_group_encoder"


class ActiveCreatingGroupVocabulary:
    """Stands for imio.dms.mail.vocabularies.ActiveCreatingGroupVocabulary: one creating group, armeedeterre."""

    def __call__(self, context):
        org = context["mydirectory"]["armeedeterre"]
        return SimpleVocabulary([SimpleTerm(org.UID(), title=org.title)])


class TestUseridInserter(BaseTestCase):
    def test___init__(self):
        self.assertIs(
            getUtility(ISectionBlueprint, "imio.transmogrifier.contact.iadocs_userid_inserter"), UseridInserter
        )
        section = self.section(UseridInserter)
        self.assertEqual(section.portal, self.portal)
        self.assertIs(section.ids, self.storage["ids"])
        self.assertTrue(section.roe)
        self.assertFalse(self.section(UseridInserter, raise_on_error="0").roe)

    def test___iter__(self):
        api.user.create(email="jdoe@example.com", username="jdoe")
        others = [
            self.item("person", _ic=False, internal_number="jdoe"),
            self.item("person", _ic=True, internal_number=""),
            self.item("organization", _ic=True, internal_number="jdoe"),
        ]
        items = list(
            self.section(
                UseridInserter,
                [self.item("person", _ic=True, internal_number="jdoe")] + [dict(item) for item in others],
            )
        )
        self.assertEqual(items, [self.item("person", _ic=True, internal_number=None, userid="jdoe")] + others)
        # unknown user
        item = self.item("person", _ic=True, internal_number="unknown")
        self.assertEqual(self.error(list, self.section(UseridInserter, [item])), "User not found ! See log...")
        self.assertTrue(item["_error"])
        items = list(
            self.section(UseridInserter, [self.item("person", _ic=True, internal_number="unknown")], raise_on_error="0")
        )
        self.assertEqual(items, [self.item("person", _ic=True, internal_number=None, _error=True)])


class TestCreatingGroupInserter(BaseTestCase):
    def setUp(self):
        super().setUp()
        # imio.dms.mail isn't a dependency: its registry record and vocabularies module are faked
        getUtility(IRegistry).records[ENCODER] = Record(field.Bool(), True)
        vocabularies = ModuleType("imio.dms.mail.vocabularies")
        vocabularies.ActiveCreatingGroupVocabulary = ActiveCreatingGroupVocabulary
        for module in (ModuleType("imio.dms"), ModuleType("imio.dms.mail"), vocabularies):
            sys.modules[module.__name__] = module
            self.addCleanup(sys.modules.pop, module.__name__)
        self.org = self.portal["mydirectory"]["armeedeterre"]

    def test___init__(self):
        self.assertIs(
            getUtility(ISectionBlueprint, "imio.transmogrifier.contact.iadocs_creating_group_inserter"),
            CreatingGroupInserter,
        )
        section = self.section(CreatingGroupInserter, creating_group=" Armée de terre ")
        self.assertEqual(section.creating_org, self.org.UID())
        self.assertIs(section.ids, self.storage["ids"])
        self.assertEqual(
            self.error(self.section, CreatingGroupInserter),
            "section: You have to set creating_group value in this section !",
        )
        self.assertEqual(
            self.error(self.section, CreatingGroupInserter, creating_group="Corps A"),
            "section: given creating_group 'Corps A' isn't an active creating group organization",
        )
        api.portal.set_registry_record(ENCODER, False)
        self.assertEqual(
            self.error(self.section, CreatingGroupInserter, creating_group="Armée de terre"),
            "section: You have to activate the contact creating group option in iadocs config",
        )
        # imio.dms.mail not installed
        del getUtility(IRegistry).records[ENCODER]
        self.assertRaises(InvalidParameterError, self.section, CreatingGroupInserter, creating_group="Armée de terre")

    def test___iter__(self):
        items = list(
            self.section(
                CreatingGroupInserter, [self.item("organization"), self.item("person")], creating_group="Armée de terre"
            )
        )
        self.assertEqual(
            items,
            [
                self.item("organization", creating_group=self.org.UID()),
                self.item("person", creating_group=self.org.UID()),
            ],
        )


class TestInbwSubtitleUpdater(BaseTestCase):
    def test___init__(self):
        self.assertIs(
            getUtility(ISectionBlueprint, "imio.transmogrifier.contact.iadocs_inbw_subtitle_updater"),
            InbwSubtitleUpdater,
        )
        self.assertEqual(
            self.error(self.section, InbwSubtitleUpdater), "section: '_service' field is not defined in fieldnames"
        )
        self.storage["fieldnames"]["organization"].append("_service")
        self.assertIs(self.section(InbwSubtitleUpdater).fieldnames, self.storage["fieldnames"])

    def test___iter__(self):
        self.storage["fieldnames"]["organization"].append("_service")
        items = [
            self.item("organization", title="CPAS", _service="c/o Jean Dupont"),
            self.item("organization", title="CPAS", _service="Service social"),
            self.item("organization", title="CPAS", _service=""),
            self.item("person", lastname="Dupont"),
        ]
        self.assertEqual(
            [item.get("title") for item in self.section(InbwSubtitleUpdater, items)],
            ["CPAS c/o Jean Dupont", "CPAS ,% Service social", "CPAS", None],
        )


class TestInbwMerger(BaseTestCase):
    """Relations come from contact.core test data (held_position position) and from the mail types of the layer."""

    def setUp(self):
        super().setUp()
        self.storage["fieldnames"]["organization"].append("_merger")
        self.intids = getUtility(IIntIds)
        self.directory = self.portal["mydirectory"]
        self.replacement = self.directory["armeedeterre"]["corpsb"]
        self.set_internal_number(self.replacement, "CORPSB")

    def set_internal_number(self, obj, number):
        obj.internal_number = number
        obj.reindexObject()

    def relations(self, *objs):
        return [RelationValue(self.intids.getId(obj)) for obj in objs]

    def test___init__(self):
        self.assertIs(getUtility(ISectionBlueprint, "imio.transmogrifier.contact.iadocs_inbw_merger"), InbwMerger)
        section = self.section(InbwMerger)
        self.assertEqual(section.catalog, self.portal.portal_catalog)
        self.assertEqual((section.rel_catalog, section.intids), (getUtility(ICatalog), self.intids))
        self.assertIs(section.ids, self.storage["ids"])
        self.assertTrue(section.roe)
        self.assertFalse(self.section(InbwMerger, raise_on_error="0").roe)
        del self.storage["fieldnames"]["organization"][:]
        self.assertEqual(self.error(self.section, InbwMerger), "section: '_merger' field is not defined in fieldnames")

    def test___iter__(self):
        corpsa = self.directory["armeedeterre"]["corpsa"]
        regimenth = corpsa["divisionalpha"]["regimenth"]
        # no merger
        items = [self.item("organization", _merger="", _path="mydirectory/armeedeterre")]
        self.assertEqual(list(self.section(InbwMerger, items)), items)
        # Plone 4 bug: person and held_position items need a _merger key too
        self.assertRaises(KeyError, list, self.section(InbwMerger, [self.item("person")]))
        # current contact not found
        item = self.item("organization", _merger="CORPSB", _path="mydirectory/nothing", _act="update")
        self.assertEqual(self.error(list, self.section(InbwMerger, [item])), "Cannot find current object intid 'None'")
        self.assertTrue(item["_error"])
        # replacement not found or found twice: error or item skipped
        self.set_internal_number(corpsa, "TWICE")
        self.set_internal_number(regimenth, "TWICE")
        for number, error in (
            ("UNKNOWN", "Cannot find object with internal number 'UNKNOWN'"),
            ("TWICE", "Find multiple objects with internal number 'TWICE'"),
        ):
            item = self.item("organization", _merger=number, _path="mydirectory/armeedeterre/corpsb")
            self.assertEqual(self.error(list, self.section(InbwMerger, [item])), error)
            self.assertTrue(item["_error"])
            self.assertEqual(list(self.section(InbwMerger, [dict(item)], raise_on_error="0")), [])
        # relation not handled: incoming mail recipients
        api.content.create(
            container=self.portal, type="dmsincomingmail", id="im0", recipients=self.relations(regimenth)
        )
        item = self.item(
            "organization", _merger="CORPSB", _path="mydirectory/armeedeterre/corpsa/divisionalpha/regimenth"
        )
        self.assertEqual(
            self.error(list, self.section(InbwMerger, [item])),
            "Relation type not handled! pt 'dmsincomingmail', field 'recipients'",
        )
        # relation from the current contact: held position
        hp = self.directory["rambo"]["brigadelh"]
        self.set_internal_number(self.directory["pepper"]["sergent_pepper"], "HP")
        item = self.item("held_position", _merger="HP", _path="mydirectory/rambo/brigadelh")
        self.assertEqual(
            self.error(list, self.section(InbwMerger, [item])),
            f"relation from_id not handled! to paths '{hp.position.to_path}'",
        )
        # contact merged: relations moved to the replacement, contact deleted
        current = corpsa["divisionbeta"]
        hp = self.directory["draper"]["divisionbeta"]
        mails = {"dmsincomingmail": "sender", "dmsincoming_email": "sender", "contact_list": "contacts"}
        for portal_type, fieldname in mails.items():
            api.content.create(
                container=self.portal, type=portal_type, id=portal_type, **{fieldname: self.relations(current)}
            )
        om = api.content.create(
            container=self.portal,
            type="dmsoutgoingmail",
            id="om",
            recipients=self.relations(current, self.directory["pepper"]),
        )
        item = self.item(
            "organization", _merger="CORPSB", _path="mydirectory/armeedeterre/corpsa/divisionbeta", _act="update"
        )
        self.assertEqual(
            list(self.section(InbwMerger, [item])),
            [
                self.item(
                    "organization",
                    _merger="CORPSB",
                    _act="delete",
                    _del_path="mydirectory/armeedeterre/corpsa/divisionbeta",
                )
            ],
        )
        self.assertNotIn("divisionbeta", corpsa)
        self.assertEqual(hp.position.to_object, self.replacement)
        self.assertEqual(
            {pt: [rel.to_object for rel in getattr(self.portal[pt], fn)] for pt, fn in mails.items()},
            {pt: [self.replacement] for pt in mails},
        )
        self.assertEqual([rel.to_object for rel in om.recipients], [self.directory["pepper"], self.replacement])
        # Plone 4 bug: with raise_on_error=0, a missing current contact gets the broken relations (target deleted)
        # then api.content.delete(obj=None) fails
        hp = self.directory["rambo"]["brigadelh"]
        api.content.delete(obj=hp.position.to_object, check_linkintegrity=False)
        self.assertIsNone(hp.position.to_object)
        item = self.item("organization", _merger="CORPSB", _path="mydirectory/nothing", _act="update")
        self.assertRaises(MissingParameterError, list, self.section(InbwMerger, [item], raise_on_error="0"))
        self.assertEqual(hp.position.to_object, self.replacement)
        # Plone 4 bug: replacement without intid raises KeyError (the "repl_iid is None" branch is dead code)
        self.intids.unregister(self.replacement)
        item = self.item("organization", _merger="CORPSB", _path="mydirectory/armeedeterre/corpsa")
        self.assertRaises(KeyError, list, self.section(InbwMerger, [item]))
