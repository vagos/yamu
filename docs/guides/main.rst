Getting Started
===============

yamu manages a local game library database and uses plugins to import metadata
from sources like Steam. The core workflow is:

1. Configure your plugins and API keys.
2. Run ``yamu import`` to fetch games and queue new ones.
3. Review and edit new entries interactively.
4. Use ``yamu list`` and ``yamu web`` to browse your library.

Create a config file at ``~/.config/yamu/config.yaml`` and enable your plugins:

::

    library: ~/.local/share/yamu/library.db
    plugins:
      - steam
      - web
      - fetchart
      - completion
    steam:
      api_key: "YOUR_STEAM_KEY"
      steam_ids:
        - 76561198074847543

Import your library:

::

    yamu import

During import, yamu prompts you to confirm metadata for newly discovered games.
To reprocess existing entries and run metadata searches, use ``yamu import -f``.
If you need to update an existing entry manually, use ``yamu edit`` or
``yamu update``.

Listing and browsing
--------------------

List games with optional query filters:

::

    yamu list
    yamu list platform:steam
    yamu list "half life"

Run the lightweight web UI:

::

    yamu web

Completion status
-----------------

Use the completion plugin to track played, beaten, abandoned, or completionist
status:

::

    yamu completion
