FAQ
===

Where does yamu store its data?
--------------------------------

By default, the database is stored at ``~/.local/share/yamu/library.db`` and artwork is stored under ``~/.local/share/yamu/art``.

Does yamu modify game files?
-----------------------------

No. yamu stores metadata in its own database and does not modify game installs.

How do I add new sources?
-------------------------

yamu uses a plugin system. New importers can be added as plugins that fetch metadata during ``yamu import``.
