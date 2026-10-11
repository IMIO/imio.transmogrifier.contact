# -*- coding: utf-8 -*-
from collective.contact.importexport.blueprints.main import ANNOTATION_KEY
from collective.transmogrifier.transmogrifier import Transmogrifier
from plone.app.testing import applyProfile
from plone.app.testing import IntegrationTesting
from plone.app.testing import PLONE_FIXTURE
from plone.app.testing import PloneSandboxLayer
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.dexterity.fti import DexterityFTI
from plone.supermodel import model
from z3c.relationfield.schema import RelationList
from zope.annotation.interfaces import IAnnotations
from zope.globalrequest import setLocal

import collective.behavior.internalnumber
import collective.contact.core
import collective.transmogrifier
import imio.transmogrifier.contact
import unittest


# imio.dms.mail types having contact relations (InbwMerger), imio.dms.mail isn't a dependency
MAIL_TYPES = ("dmsincomingmail", "dmsincoming_email", "dmsoutgoingmail", "contact_list")


class IMail(model.Schema):
    """Contact relation fields of MAIL_TYPES."""

    sender = RelationList()
    recipients = RelationList()
    contacts = RelationList()


class ImioTransmogrifierContactLayer(PloneSandboxLayer):

    defaultBases = (PLONE_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        self.loadZCML(package=collective.contact.core)
        self.loadZCML(package=collective.transmogrifier)
        self.loadZCML(package=collective.behavior.internalnumber)
        self.loadZCML(package=imio.transmogrifier.contact)

    def setUpPloneSite(self, portal):
        setLocal("request", portal.REQUEST)  # for collective.fingerpointing
        setRoles(portal, TEST_USER_ID, ["Manager"])
        applyProfile(portal, "collective.contact.core:test_data")  # creates mydirectory
        applyProfile(portal, "collective.behavior.internalnumber:default")  # internal_number index
        for portal_type in MAIL_TYPES:
            portal.portal_types._setObject(
                portal_type, DexterityFTI(portal_type, schema="imio.transmogrifier.contact.testing.IMail")
            )


IMIO_TRANSMOGRIFIER_CONTACT_FIXTURE = ImioTransmogrifierContactLayer()

IMIO_TRANSMOGRIFIER_CONTACT_INTEGRATION_TESTING = IntegrationTesting(
    bases=(IMIO_TRANSMOGRIFIER_CONTACT_FIXTURE,), name="ImioTransmogrifierContactLayer:IntegrationTesting"
)


class BaseTestCase(unittest.TestCase):
    """Builds sections as a collective.contact.importexport pipeline does, after its main section."""

    layer = IMIO_TRANSMOGRIFIER_CONTACT_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        self.transmogrifier = Transmogrifier(self.portal)
        # storage filled by the importexport main section
        self.storage = {
            "directory_path": "mydirectory",
            "ids": {"organization": {"set1": {}}, "person": {"set1": {}}, "held_position": {"set1": {}}},
            "fieldnames": {"organization": [], "person": [], "held_position": []},
        }
        IAnnotations(self.transmogrifier)[ANNOTATION_KEY] = self.storage

    def section(self, blueprint, items=(), **options):
        return blueprint(self.transmogrifier, "section", options, iter(items))

    @staticmethod
    def item(_type, **values):
        """A csv line as read by the importexport main section."""
        return dict({"_set": "set1", "_id": "1", "_ln": 2, "_type": _type}, **values)

    def error(self, func, *args, **kwargs):
        """Returns the message of the exception raised by func."""
        with self.assertRaises(Exception) as cm:
            func(*args, **kwargs)
        return cm.exception.args[0]
