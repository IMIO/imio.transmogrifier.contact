.. This README is meant for consumption by humans and pypi. Pypi can render rst files so please do not use Sphinx features.
   If you want to learn more about writing documentation, please check out: http://docs.plone.org/about/documentation_styleguide.html
   This text does not appear on pypi or github. It is a comment.

===========================
imio.transmogrifier.contact
===========================

Propose some blueprints for collective.contact.import export

- imio.transmogrifier.contact.plonegrouporganizationpath : link plonegroup-organization with an input item
- imio.transmogrifier.contact.plonegroupinternalparent : change _parent when we have an internal plonegroup element
- imio.transmogrifier.contact.iadocs_userid_inserter : set userid field for iadocs internal person
- imio.transmogrifier.contact.iadocs_creating_group_inserter : set creating_group field on iadocs contacts
- imio.transmogrifier.contact.iadocs_inbw_subtitle_updater : update title with _service column for inbw customer
- imio.transmogrifier.contact.iadocs_inbw_merger : replace contact with _merger column containing
  replacing internal number

Installation
------------

Install imio.transmogrifier.contact by adding it to your buildout::

    [buildout]

    ...

    eggs =
        imio.transmogrifier.contact


and then running ``bin/buildout``


Contribute
----------

- Issue Tracker: https://github.com/collective/imio.transmogrifier.contact/issues
- Source Code: https://github.com/collective/imio.transmogrifier.contact
- Documentation: https://docs.plone.org/foo/bar


Support
-------

If you are having issues, please let us know on github.


License
-------

The project is licensed under the GPLv2.
