Epic
====

The ``epic`` plugin imports your Epic Games library using the `legendary` CLI.

Enable it in your config:

::

    plugins:
      - epic
    epic:
      legendary_path: "legendary"

Setup
-----

Install and log in with legendary before running ``yamu import``:

::

    legendary auth
    legendary list --json

Import behavior
---------------

When enabled, ``yamu import`` will import Epic games using
``legendary list --json``. The plugin also looks up metadata for entries that
already have ``path: epic://<app_name>`` using ``legendary info --json``.
