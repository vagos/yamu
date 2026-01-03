Query Syntax
============

yamu supports simple query strings for ``list`` commands.

Field queries
-------------

Use ``field:value`` to match fields (substring for text fields, exact for
numeric fields):

::

    yamu list platform:steam
    yamu list status:beaten
    yamu list release_date:2004

Free-text queries
-----------------

Free-text terms match the default field (``title``) using case-insensitive
substring search:

::

    yamu list "half life"

Combine terms
-------------

Multiple terms are combined with AND semantics:

::

    yamu list platform:steam "half life"
