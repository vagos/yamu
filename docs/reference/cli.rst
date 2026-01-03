Command-Line Interface
======================

``yamu`` is the command-line interface to yamu.

Usage
-----

::

    yamu [--db PATH] COMMAND [ARGS...]

Global flags:

- ``--db``: override the database path in the config.

Commands
--------

import
~~~~~~

::

    yamu import [-f]

Run all enabled import plugins. New games are queued for interactive review.
By default, existing games are skipped; pass ``-f`` to reprocess existing games
and run metadata searches for confirmation.

list
~~~~

::

    yamu list [QUERY...]

List games in the library. Without a query, lists all titles. Queries accept
simple ``field:value`` filters or free-text substring matches. See
:doc:`/reference/query`.

add
~~~

::

    yamu add --title TITLE [--platform PLATFORM]

Create a game entry manually.

update
~~~~~~

::

    yamu update QUERY... --field FIELD --value VALUE

Update a single field for all matching games.

remove
~~~~~~

::

    yamu remove QUERY...

Remove games from the library.

edit
~~~~

::

    yamu edit QUERY...

Interactively edit games in your editor.
