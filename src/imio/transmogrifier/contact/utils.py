# -*- coding: utf-8 -*-

from collective.contact.importexport.utils import input_error
from z3c.relationfield import RelationValue
from zope.lifecycleevent import modified


def replace_relation(item, portal, catalog, rel, path='from_path', field='', repl_iid=None):
    obj = portal.unrestrictedTraverse(getattr(rel, path), default=None)
    if obj is None:
        input_error(item, u"cannot find linked object: {}".format(rel.from_path))
        catalog.unindex(rel)  # remove bad relation...
        return

    value = getattr(obj, field)
    if isinstance(value, RelationValue):
        value = RelationValue(repl_iid)
    else:
        if isinstance(value, tuple):
            value = list(value)
        value.remove(rel)
        value.append(RelationValue(repl_iid))
    setattr(obj, field, value)
    modified(obj)  # will update relations catalog too
