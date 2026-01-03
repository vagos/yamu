Import Review Flow
==================

yamu's import process is intentionally interactive. Import plugins fetch
metadata in the background while yamu asks you to confirm each new game.

Run the importer:

::

    yamu import

For each new game, yamu will show the metadata it found and offer you a chance
to edit or skip it before it is added to your library. Existing games are
updated in place without prompting.

If you prefer to edit after import, use ``yamu edit`` or ``yamu update`` to
modify fields later.
