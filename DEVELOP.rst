Using the development buildout
==============================

Create the Plone 6.2 environment (pyenv with Python 3.13 and virtualenv required)::

    $ make setup plone=6.2

Run buildout::

    $ make buildout

Start Plone in foreground::

    $ ./bin/instance fg


Running tests
-------------

    $ make test

Code analysis::

    $ ./bin/code-analysis
